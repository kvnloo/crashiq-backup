"""Run every incorporated California city through CrashIQ's data steps (tab 1 corridor + crash pull, tab 2 placement
and assignment), using the app's own API in-process, and write one JSON result per city.

- CCRS: the local mirror (`ccrs_mirror.py`), so the app's exact SQL runs offline.
- OSM: the app's own Overpass call (cached in data/tester.sqlite), corridors from `corridors.py`.
- App database: data/tester.sqlite (never the shared data/crashiq.sqlite).
- Independent check: no-GPS reports in the city that name the corridor street and one of the corridor's study
  cross streets, found here with plain SQL on the mirror; any the app did not pull is a silent drop.

Results are cached per city in data/statewide/results/, keyed on the backend code version (git tree of backend/)
and the corridor, so a rerun only redoes cities whose code or corridor changed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
os.environ.setdefault("DO_NOT_TRACK", "1")

import ccrs_mirror  # noqa: E402
import checks  # noqa: E402
from checks import indep_core, lead_dir  # noqa: E402
import corridors  # noqa: E402
import osm_local  # noqa: E402
from crashiq import network as network_mod  # noqa: E402
from crashiq.db import Database  # noqa: E402
from crashiq.names import street_key  # noqa: E402
from crashiq.server import create_app  # noqa: E402
from crashiq.settings import Settings  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

DATA = ROOT / "data" / "statewide"
CACHE = ROOT / "data" / "cache" / "statewide"
OSM = CACHE / "osm"
RESULTS = DATA / "results"
OSM_DB = ROOT / "data" / "osm" / "ca_osm.sqlite"
LOCAL = osm_local.LocalOSM(OSM_DB) if OSM_DB.exists() else None   # extract replaces live Overpass when present
YEARS = [2021, 2022, 2023, 2024, 2025]


FROZEN = HERE / "corridors_frozen.json"
# Corridor list v2 (PM, PR #148): a second, separately labelled series from run 4. v1 stays the like-for-like series;
# v2 = v1 with the corridors that lie mostly outside their own city re-picked inside it. Never mixed with v1.
FROZEN_V2 = HERE / "corridors_frozen_v2.json"
RESULTS_V2 = DATA / "results_corridors_v2"
V2_BELOW_PCT = 50.0          # "mostly outside": under half the v1 corridor's vertices inside its own city
HARNESS = "7"   # bump when the harness's own checks or rules change, so cached cities are rerun (4: v3 check, 5: v4, 6: DMS counts, 7: fatal outcomes)
# Known open bugs that affect a city's result, shown on the Cities sheet (PM, run 3).
KNOWN_ISSUES: dict = {}   # run 3-4: San Jose "affected by #143"; fixed in #159 (run 5)


def code_version() -> str:
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD:backend"], capture_output=True,
                          text=True).stdout.strip()[:12]


def commit() -> str:
    """The commit that last changed backend/: identifies the app code under test, unchanged by test-only commits."""
    return subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h", "--", "backend"], capture_output=True,
                          text=True).stdout.strip()


def mirror_built() -> str:
    """Date the CCRS mirror was copied from data.ca.gov (oldest table download)."""
    import datetime as dt
    files = sorted(CACHE.glob("crashes_*.csv"), key=lambda f: f.stat().st_mtime)
    return dt.datetime.fromtimestamp(files[0].stat().st_mtime).isoformat(timespec="minutes") if files else ""


def freeze() -> None:
    """Write the corridors actually run (lines + settings) so a rerun after fixes uses exactly the same basis."""
    out = {"note": "Same-basis corridor list for the #73 statewide test (user decision, PR #86). Reruns reuse it.",
           "years": YEARS, "mirror_built": mirror_built(), "cities": []}
    for f in sorted(RESULTS.glob("*/*.json")):
        r = json.loads(f.read_text())
        if r.get("code_version") != code_version():
            continue
        out.setdefault("settings", r.get("settings"))
        out.setdefault("osm_source", r.get("osm_source"))
        out["cities"].append({k: r.get(k) for k in ("city", "county", "osm_boundary", "corridor", "reason")})
    out["cities"].sort(key=lambda c: (c["county"], c["city"]))
    FROZEN.write_text(json.dumps(out, indent=1))
    print(f"froze {len(out['cities'])} cities -> {FROZEN}")


def cities(mirror: ccrs_mirror.Mirror) -> list[dict]:
    """Incorporated cities in CCRS (City Is Incorporated), with crash count and main local reporting agency."""
    rids = [r for r, t in mirror.db.execute("SELECT rid, tbl FROM _meta WHERE tbl='crashes'")]
    agg: dict[tuple, Counter] = {}
    total: Counter = Counter()
    for rid in rids:
        q = (f'SELECT "City Name" c, "County Code" k, "NCIC Code" a, COUNT(*) n FROM "{rid}" '
             f'WHERE "City Is Incorporated" = \'True\' AND COALESCE("IsDeleted", \'\') <> \'True\' GROUP BY 1, 2, 3')
        for r in mirror.db.execute(q):
            key = (str(r["c"]).strip(), str(r["k"]).strip())
            agg.setdefault(key, Counter())[str(r["a"]).strip()] += r["n"]
            total[key] += r["n"]
    out = []
    for (c, k), ags in agg.items():
        if not c or c == "None":
            continue
        local = [(a, n) for a, n in ags.most_common() if not a.startswith("9")]
        out.append({"city": c, "county": k, "crashes_5y": total[(c, k)],
                    "agency": local[0][0] if local else None,
                    "agency_share": round(100 * local[0][1] / total[(c, k)], 1) if local else 0,
                    "chp_share": round(100 * sum(n for a, n in ags.items() if a.startswith("9")) / total[(c, k)], 1)})
    out.sort(key=lambda r: -r["crashes_5y"])
    return out


def freeze_v2(source_tree: str) -> None:
    """Write corridors_frozen_v2.json: the v1 list, with every corridor under V2_BELOW_PCT inside its own city (as
    measured in `source_tree`'s results) re-picked by `corridors.pick_inside`. Written once; reruns reuse it."""
    if FROZEN_V2.exists():
        raise SystemExit(f"{FROZEN_V2.name} exists: the v2 list is frozen (delete it only with a new baseline)")
    v1 = json.loads(FROZEN.read_text())
    measured = {(r["city"], r["county"]): r.get("corridor_inside_own_city_pct")
                for r in (json.loads(f.read_text()) for f in (RESULTS / source_tree).glob("*.json"))}
    bounds = corridors.local_boundaries(LOCAL)
    out = {**{k: v for k, v in v1.items() if k != "cities"},
           "note": ("Corridor list v2 for the #73 statewide test (PM, PR #148): a second series with its own baseline "
                    "from run 4, never mixed with v1. Same as corridors_frozen.json except the corridors marked "
                    f"`repicked`: those had under {V2_BELOW_PCT:g}% of their vertices inside their own city in "
                    f"results/{source_tree} and were re-picked from the parts of the city's roads inside the city."),
           "series": "v2", "based_on": FROZEN.name, "source_results": source_tree, "cities": []}
    n = 0
    for c in v1["cities"]:
        pct = measured.get((c["city"], c["county"]))
        if pct is None or pct >= V2_BELOW_PCT:
            out["cities"].append(c)
            continue
        b = bounds.get(corridors.norm_city(c["city"]))
        corr = corridors.pick_inside(b["rel"], LOCAL) if b else {"reason": "no OSM city boundary"}
        out["cities"].append({**c, "corridor": corr if "line" in corr else None, "reason": corr.get("reason"),
                              "repicked": True, "v1_inside_own_city_pct": pct, "v1_road": (c.get("corridor") or {}).get("road")})
        n += 1
        print(f"{c['city']}: {pct}% inside -> {corr.get('road')} ({corr.get('inside_own_city_pct')}% inside)"
              if "line" in corr else f"{c['city']}: {pct}% inside -> no corridor: {corr['reason']}", flush=True)
    FROZEN_V2.write_text(json.dumps(out, indent=1))
    print(f"re-picked {n} of {len(out['cities'])} -> {FROZEN_V2}")


def _sq(s: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def city_reports_naming(mirror, city: str, core: str) -> int:
    """Reports in the city (any GPS) whose primary or secondary road contains the street core."""
    if len(core) < 3:
        return 0
    n = 0
    for (rid,) in mirror.db.execute("SELECT rid FROM _meta WHERE tbl='crashes'"):
        q = (f'SELECT "PrimaryRoad" p, "SecondaryRoad" s FROM "{rid}" WHERE "City Name" = ? '
             f'AND COALESCE("IsDeleted", \'\') <> \'True\'')
        n += sum(1 for r in mirror.db.execute(q, (city,)) if core in _sq(r["p"]) or core in _sq(r["s"]))
    return n


def independent_no_gps(mirror, city: str, corridor_core: str, cross_cores: list[str],
                       corridor_dir: str | None = None) -> set[str]:
    """No-GPS crash ids in the city whose one road names the corridor and the other a study cross street.
    v2: a report whose road states the opposite direction ('W COLORADO BL' for East Colorado) isn't counted."""
    core = _sq(corridor_core)
    crosses = [_sq(c) for c in cross_cores if len(_sq(c)) >= 3 and _sq(c) != core]
    if len(core) < 3 or not crosses:
        return set()
    ids = set()
    for (rid,) in mirror.db.execute("SELECT rid FROM _meta WHERE tbl='crashes'"):
        q = (f'SELECT "Collision Id" i, "PrimaryRoad" p, "SecondaryRoad" s FROM "{rid}" WHERE "City Name" = ? '
             f'AND ("Latitude" IS NULL OR "Longitude" IS NULL) AND COALESCE("IsDeleted", \'\') <> \'True\'')
        for r in mirror.db.execute(q, (city,)):
            p, s = _sq(r["p"]), _sq(r["s"])
            for a, b, raw in ((p, s, r["p"]), (s, p, r["s"])):
                d = lead_dir(raw)
                if corridor_dir and d and d != corridor_dir:
                    continue
                if core in a and any(x in b for x in crosses):
                    ids.add(str(int(r["i"])) if isinstance(r["i"], (int, float)) else str(r["i"]))
    return ids


def independent_no_gps_v3(mirror, city: str, core: str, cross_cores: list[str],
                          corridor_dir: str | None = None) -> set[str]:
    """v3 (PM, PR #148, from run 4): as v2, but the roads must BE the corridor and a study cross street (whole street
    cores, `checks.names_pair_v3`), not merely contain them."""
    ids = set()
    for (rid,) in mirror.db.execute("SELECT rid FROM _meta WHERE tbl='crashes'"):
        q = (f'SELECT "Collision Id" i, "PrimaryRoad" p, "SecondaryRoad" s FROM "{rid}" WHERE "City Name" = ? '
             f'AND ("Latitude" IS NULL OR "Longitude" IS NULL) AND COALESCE("IsDeleted", \'\') <> \'True\'')
        for r in mirror.db.execute(q, (city,)):
            if checks.names_pair_v3(r["p"], r["s"], core, cross_cores, corridor_dir):
                ids.add(str(int(r["i"])) if isinstance(r["i"], (int, float)) else str(r["i"]))
    return ids


CROSS_CLASSES = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
                 "living_street", "road", "primary_link", "secondary_link", "tertiary_link", "trunk_link"}


def silent_drops_v4(mirror, line, core: str, cross_cores: list[str], dropped3: list[str],
                    tol_ft: float = checks.V4_TOLERANCE_FT) -> tuple[list[str], list[dict]] | None:
    """v4 (PM, after #149): v3's drops less reports whose own stated offset (CCRS SecondaryDistance/Direction/Unit)
    puts them more than `tol_ft` past either end of the stretch the study cross streets span. Cross-street points are
    the OSM nodes nearest the frozen line (local extract), never the app's intersections. A report whose offset,
    direction or cross street can't be used stays a drop. Returns (drops, cleared with their computed distance)."""
    if not LOCAL or not dropped3:
        return (list(dropped3), []) if LOCAL else None
    els = LOCAL.around([tuple(p) for p in line], 40, CROSS_CLASSES)["elements"]
    pts = {n["id"]: (n["lat"], n["lon"]) for n in els if n["type"] == "node"}
    by_core: dict[str, list] = {}
    for w in els:
        if w["type"] == "way" and w.get("tags", {}).get("name"):
            by_core.setdefault(indep_core(w["tags"]["name"]), []).extend(pts[i] for i in w["nodes"] if i in pts)
    cross_pt = {c: checks.nearest_to_line(line, by_core[c]) for c in set(cross_cores) if c != core and c in by_core}
    if not cross_pt:
        return list(dropped3), []
    st = [checks.station(line, p) for p in cross_pt.values()]
    lo, hi = min(st), max(st)
    rows = {}
    for (rid,) in mirror.db.execute("SELECT rid FROM _meta WHERE tbl='crashes'"):
        q = (f'SELECT "Collision Id" i, "PrimaryRoad" p, "SecondaryRoad" s, "SecondaryDirection" d, '
             f'"SecondaryDistance" n, "SecondaryUnitOfMeasure" u FROM "{rid}" '
             f'WHERE "Collision Id" IN ({",".join("?" * len(dropped3))})')
        for r in mirror.db.execute(q, [int(x) for x in dropped3]):
            rows[str(int(r["i"]))] = r
    keep, cleared = [], []
    for cid in dropped3:
        r = rows.get(cid)
        cross = None if r is None else next((indep_core(x) for x in (r["s"], r["p"]) if indep_core(x) != core), None)
        off = checks.offset_ft(r["n"], r["u"]) if r is not None else None
        d = str(r["d"] or "").strip().upper() if r is not None else ""
        if cross not in cross_pt or off is None or d not in checks.DIRV:
            keep.append(cid)
            continue
        past = checks.beyond_stretch(checks.report_station(line, cross_pt[cross], d, off), lo, hi)
        if past > tol_ft:
            cleared.append({"crash_id": cid, "cross_street": cross, "direction": d, "offset_ft": round(off),
                            "past_stretch_end_ft": round(past)})
        else:
            keep.append(cid)
    return keep, cleared


def run_city(client: TestClient, mirror, c: dict, corr: dict) -> dict:
    st = client.post("/api/studies", json={"name": f"statewide {c['city']}", "mode": "profile",
                                           "from_year": YEARS[0], "to_year": YEARS[-1]}).json()
    sid = st["id"]
    settings = {k: st.get(k) for k in ("from_year", "to_year", "radius_ft", "buffer_ft", "include_freeway")}
    empty_retries = 0
    while True:
        r = client.put(f"/api/studies/{sid}/corridor", json={"line": corr["line"]})
        if r.status_code != 200:
            return {"stage": "corridor", "error": f"HTTP {r.status_code}: {r.text[:200]}"}
        net = r.json()
        # Overpass sometimes answers a valid query with 0 elements under load, and the app caches that answer
        # (bug filed). Harness only: clear that cache row and ask again, counting the retries.
        q = network_mod.overpass_query([tuple(p) for p in corr["line"]])
        key = "overpass:" + hashlib.sha1(q.encode()).hexdigest()
        hit = client.app.state.db.one("SELECT body FROM http_cache WHERE key = ?", (key,))
        if LOCAL or not hit or json.loads(hit["body"]).get("elements") or empty_retries >= 4:
            break
        client.app.state.db.execute("DELETE FROM http_cache WHERE key = ?", (key,))
        empty_retries += 1
        time.sleep(20 * empty_retries)
    inters = net.get("intersections", [])
    r = client.post(f"/api/studies/{sid}/crashes/pull")
    if r.status_code != 200:
        return {"stage": "pull", "error": f"HTTP {r.status_code}: {r.text[:200]}", "corridor_name": net.get("corridor_name"),
                "intersections": len(inters)}
    pull = r.json()
    crashes = client.get(f"/api/studies/{sid}/crashes").json()["crashes"]
    a = client.get(f"/api/studies/{sid}/assignment")
    asg = a.json() if a.status_code == 200 else {}
    log = pull["cleaning"]
    src = Counter(x.get("location_source") for x in crashes)
    pull_excluded = Counter(x.get("exclude_rule") for x in crashes if x.get("exclude_rule"))
    candidates = [x for x in crashes if not x.get("exclude_rule")]
    located = sum(1 for x in candidates if x.get("location_source") not in ("unmatched", None))
    review = sum(1 for x in candidates if x.get("location_source") == "unmatched")
    k = street_key(net.get("corridor_name"))
    cross = [part for i in inters for part in str(i.get("name") or "").split("/")]
    cross_cores = [street_key(x).core for x in cross if street_key(x)]
    expected = independent_no_gps(mirror, c["city"], k.core if k else "", cross_cores)
    got = {str(x["crash_id"]) for x in crashes}
    dropped = sorted(expected - got)
    core2 = indep_core(net.get("corridor_name") or (corr.get("road")))
    expected2 = independent_no_gps(mirror, c["city"], core2, [indep_core(x) for x in cross],
                                   lead_dir(net.get("corridor_name")))
    dropped2 = sorted(expected2 - got)
    expected3 = independent_no_gps_v3(mirror, c["city"], core2, [indep_core(x) for x in cross],
                                      lead_dir(net.get("corridor_name")))
    dropped3 = checks.silent_drops_v3(expected3, got, log.get("same_crash_refiled") or [])
    v4 = silent_drops_v4(mirror, corr["line"], core2, [indep_core(x) for x in cross], dropped3,
                         max(checks.V4_TOLERANCE_FT, float(settings.get("radius_ft") or 0)))
    # fatal crashes first (#174/#178): every fatal crash the pull kept, by what happened to it
    akind = {str(x["crash_id"]): x for x in asg.get("assignments", [])}
    fatal_out = Counter()
    for x in crashes:
        if (x.get("killed") or 0) <= 0 or x.get("exclude_rule"):
            continue
        a_ = akind.get(str(x["crash_id"]), {})
        if a_.get("kind") in ("intersection", "segment"):
            fatal_out[f"placed_{x.get('location_source')}"] += 1
        elif a_.get("kind") == "excluded":
            fatal_out[f"excluded_{a_.get('rule')}"] += 1
        elif x.get("location_source") == "unmatched":
            fatal_out["unplaced_with_fars_hint" if x.get("fars_hint") else "unplaced"] += 1
        else:
            fatal_out[f"other_{a_.get('kind')}"] += 1
    return {
        "fatal_outcomes": dict(fatal_out), "fars_placement": log.get("fars"),
        "stage": "done", "study_id": sid, "settings": settings, "overpass_empty_retries": empty_retries, "corridor_name": net.get("corridor_name"),
        "ends": [inters[0]["name"], inters[-1]["name"]] if inters else [None, None],
        "intersections": len(inters), "length_ft": net.get("length_ft"),
        "pulled": len(crashes), "with_gps": src.get("gps", 0),
        "placed_by_tier": {t: n for t, n in src.items() if t not in ("gps", "unmatched", None)},
        "unmatched": src.get("unmatched", 0), "candidates": len(candidates), "located": located, "review": review,
        "excluded_at_pull": dict(pull_excluded), "assignment": asg.get("counts", {}),
        "excluded_by_rule": asg.get("excluded_by_rule", {}),
        "warning": log.get("warning"), "area_source": log.get("area_source"),
        "years_missing": log.get("years_missing"), "parties_missing_years": log.get("parties_missing_years"),
        "no_coords_read": log.get("no_coords_read"), "duplicate_versions_dropped": log.get("duplicate_versions_dropped"),
        "independent_expected": len(expected), "silent_drops": len(dropped), "silent_drop_ids": dropped[:10],
        "assignment_status": a.status_code,
        "corridor_cities": log.get("corridor_cities"),
        "corridor_inside_own_city_pct": _inside_pct(corr.get("line"), c["city"]),
        "independent_core_v2": core2, "independent_expected_v2": len(expected2), "silent_drops_v2": len(dropped2),
        "silent_drop_ids_v2": dropped2[:10], "independent_expected_v3": len(expected3), "silent_drops_v3": len(dropped3),
        "silent_drop_ids_v3": dropped3[:10],
        "silent_drops_v4": None if v4 is None else len(v4[0]), "silent_drop_ids_v4": None if v4 is None else v4[0][:10],
        "v4_cleared": None if v4 is None else v4[1],
        "gps_dms_corrected": log.get("gps_dms_corrected"), "gps_dms_unconfirmed": log.get("gps_dms_unconfirmed"),
        "gps_dms_agencies": log.get("gps_dms_agencies"), "city_reports_naming_street_v2": city_reports_naming(mirror, c["city"], core2),
    }


def _inside_pct(line, city: str) -> float | None:
    """Share of the frozen corridor's vertices inside its own city's OSM boundary (the picker took any road with a
    node inside the city, so a few windows lie partly outside: Palm Springs, run 3)."""
    if not LOCAL or not line:
        return None
    key = corridors.norm_city(city)
    if not any(corridors.norm_city(b["name"]) == key for b in LOCAL.boundaries()):
        return None                                        # no OSM boundary (Compton): can't say
    hit = sum(any(a.get("admin_level") in ("8", "6") and corridors.norm_city(a.get("name")) == key
                  for a in LOCAL.is_in(lat, lon)) for lat, lon in line)        # 6: San Francisco is a city-county
    return round(100 * hit / len(line), 1)


def classify_v2(r: dict) -> tuple[str, str]:
    """Run 2 rule (PM review of #112): silent drops from the independent v2 core, and 0 crashes pulled counts as
    fail (suspected silent drop) unless no report in the city names the street at all."""
    if r.get("stage") != "done":
        return classify(r)
    if "corridor_cities" in r and r["corridor_cities"] is None:   # #142's city filter silently off: not a valid test
        return "untested", "city filter unavailable (OSM couldn't say which cities the corridor enters)"
    if r.get("silent_drops_v2"):
        return "fail", (f"{r['silent_drops_v2']} no-GPS reports naming the corridor and a study cross street were "
                        "not pulled")
    if r.get("corridor_name") and r["pulled"] == 0:
        if r.get("city_reports_naming_street_v2"):
            return "fail", (f"0 crashes pulled while {r['city_reports_naming_street_v2']} reports in the city name "
                            f"{r.get('independent_core_v2')} (suspected silent drop)")
        return "untested", "0 crashes: no report in the city names this street (nothing to test)"
    return classify({**r, "silent_drops": 0})


def classify_v3(r: dict) -> tuple[str, str]:
    """Run-2 rule with silent drops from check v3 (PM, PR #148): a new column from run 4; `result` (v2) stays."""
    if r.get("stage") != "done" or "silent_drops_v3" not in r:
        return classify_v2(r)
    return classify_v2({**r, "silent_drops_v2": r["silent_drops_v3"]})


def classify_v4(r: dict) -> tuple[str, str]:
    """Run-2 rule with silent drops from check v4 (PM, after #149): a new column from run 4; v3 stays."""
    if r.get("stage") != "done" or r.get("silent_drops_v4") is None:
        return classify_v3(r)
    return classify_v2({**r, "silent_drops_v2": r["silent_drops_v4"]})


def classify(r: dict) -> tuple[str, str]:
    """Run 1 rule (#73 proposal, user to confirm)."""
    if r.get("stage") != "done":
        return "untested", f"{r.get('stage')} step failed: {r.get('error', r.get('reason', ''))[:120]}"
    if r["silent_drops"]:
        return "fail", f"{r['silent_drops']} no-GPS reports naming the corridor and a study cross street were not pulled"
    if not r.get("corridor_name"):
        return "fail", "the app found no corridor street on a line drawn along " + str(r.get("corridor", {}).get("road"))
    if r["pulled"] == 0:
        return ("fail", "0 crashes pulled while CCRS has reports naming the corridor") if r["independent_expected"] \
            else ("untested", "0 crashes: no CCRS report names this corridor (nothing to test)")
    if not r["candidates"]:
        return "warn", "every pulled crash was excluded at pull time"
    loc = r["located"] / r["candidates"]
    rev = r["review"] / r["candidates"]
    if loc < 0.70:
        return "fail", f"only {loc:.0%} of crashes located (GPS) or placed"
    if loc < 0.90 or rev > 0.20:
        return "warn", f"{loc:.0%} located or placed, {rev:.0%} sent for review"
    return "pass", f"{loc:.0%} located or placed"


NOT_A_CITY = re.compile(r"\b(PK|PARK|DIST|UNIV|UC|CSU|CAL POLY|STATE|AIRPORT|AIRPRT|INTL|HARBOR|PORT|CLG|COLLEGE|"
                        r"MEDICAL|CENTER)\b", re.I)


def gps_box(mirror, city: str) -> list[list[tuple]] | None:
    """Area for a city OSM has no boundary for (Compton): the 2nd-98th percentile box of the city's own crash GPS."""
    pts = []
    for (rid,) in mirror.db.execute("SELECT rid FROM _meta WHERE tbl='crashes'"):
        pts += mirror.db.execute(f'SELECT "Latitude", "Longitude" FROM "{rid}" WHERE "City Name" = ? AND '
                                 f'"Latitude" BETWEEN 32 AND 42.1 AND "Longitude" BETWEEN -124.5 AND -114', (city,)
                                 ).fetchall()
    if len(pts) < 50:
        return None
    la = sorted(p[0] for p in pts)
    lo = sorted(p[1] for p in pts)
    q = lambda v, f: v[int(f * (len(v) - 1))]  # noqa: E731
    s_, n_, w_, e_ = q(la, .02), q(la, .98), q(lo, .02), q(lo, .98)
    return [[(s_, w_), (s_, e_), (n_, e_), (n_, w_), (s_, w_)]]


def prefetch() -> None:
    """Download every city's OSM roads (file cache only), last city first, to run beside `main`."""
    mirror = ccrs_mirror.Mirror(DATA / "ccrs_mirror.sqlite", CACHE)
    bounds = corridors.boundaries(OSM)
    for c in reversed(cities(mirror)):
        try:
            b = bounds.get(corridors.norm_city(c["city"])) or corridors.find_rel(c["city"], OSM)
            if b:
                corridors.pick(b["rel"], OSM)
        except Exception as e:  # noqa: BLE001
            print(c["city"], e, flush=True)


class _Watch:
    """Worker heartbeat and exit reason (PM, after run 6: two workers stopped silently near the end, twice).
    Every HEARTBEAT_S a line with the city in progress, the elapsed time and the peak memory; on any exit a line
    saying why: finished, a signal (SIGTERM/SIGHUP/SIGINT), or an exception with its traceback. A worker that stops
    with no exit line was killed by SIGKILL or lost its machine (sleep, power): the last heartbeat says when."""
    HEARTBEAT_S = 60

    def __init__(self, tag: str):
        import atexit
        import signal
        import threading
        self.tag, self.city, self.n, self.total, self.t0, self.done = tag, "-", 0, 0, time.time(), False
        for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            signal.signal(sig, self._on_signal)
        atexit.register(self._on_exit)
        threading.Thread(target=self._beat, daemon=True).start()
        self.log("started")

    def log(self, what: str) -> None:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)      # macOS: bytes -> MB
        print(f"[worker {self.tag}] {time.strftime('%H:%M:%S')} {what} · city {self.n}/{self.total} {self.city} · "
              f"{time.time() - self.t0:.0f}s · peak {rss:.0f} MB", flush=True)

    def _beat(self) -> None:
        while True:
            time.sleep(self.HEARTBEAT_S)
            self.log("heartbeat")

    def _on_signal(self, signum, _frame) -> None:
        import signal
        self.log(f"EXIT: stopped by signal {signal.Signals(signum).name}")
        self.done = True
        os._exit(128 + signum)

    def _on_exit(self) -> None:
        if not self.done:
            self.log("EXIT: finished" if self.n >= self.total else "EXIT: ended before its last city")


def main(limit: int | None = None, only: str | None = None, shard: tuple[int, int] = (0, 1),
         series: str = "v1", only_list: set[str] | None = None) -> None:
    """series v1: the frozen v1 list into results/<tree>/. series v2: only the re-picked corridors of the v2 list,
    into results_corridors_v2/<tree>/ (the v2 series' other corridors are the v1 lines, whose results are v1's)."""
    mirror = ccrs_mirror.Mirror(DATA / "ccrs_mirror.sqlite", CACHE)
    ver = code_version()
    out_dir = (RESULTS_V2 if series == "v2" else RESULTS) / ver
    out_dir.mkdir(parents=True, exist_ok=True)
    flist = FROZEN_V2 if series == "v2" else FROZEN
    frozen = {(c["city"], c["county"]): c for c in json.loads(flist.read_text())["cities"]} if flist.exists() else {}
    if series == "v2":
        if not frozen:
            raise SystemExit("no corridors_frozen_v2.json: run --freeze-v2 <tree> first")
        frozen = {k: c for k, c in frozen.items() if c.get("repicked")}
    city_list = cities(mirror)
    (DATA / "cities.json").write_text(json.dumps(city_list, indent=1))
    bounds = corridors.local_boundaries(LOCAL) if LOCAL else corridors.boundaries(OSM)
    osm_source = (f"{LOCAL.meta.get('source')} {LOCAL.meta.get('timestamp')}" if LOCAL else "Overpass (live)")
    earlier = {}                                   # corridors already run on live Overpass: same lines, rerun
    for f in [*RESULTS.glob("*/*.json"), *(DATA / "results_live_overpass").glob("*.json")]:
        r = json.loads(f.read_text())
        if (r.get("corridor") or {}).get("line"):
            earlier.setdefault((r["city"], r["county"]), r)
    # Worker 0 uses the Tester database; extra parallel workers get their own Tester-only copies (one SQLite writer
    # each), never the shared data/crashiq.sqlite.
    db_path = ROOT / "data" / "tester.sqlite" if shard[0] == 0 else DATA / f"tester_worker{shard[0]}.sqlite"
    if LOCAL:   # one OSM source per run: drop live-Overpass cache rows (archived first by archive_live_cache)
        import sqlite3
        if db_path.exists():
            con = sqlite3.connect(db_path)
            con.execute("DELETE FROM http_cache WHERE source = 'overpass'")
            con.commit()
            con.close()
    settings = Settings(db_path=db_path, app_password=None, anthropic_api_key=None,
                        typesafe_api_key=None, study_ai_cap_usd=0.0, dist_dir=ROOT / "no-dist", fixtures_dir=None)
    db = Database(settings.db_path)
    app = create_app(settings, db)
    app.state.ckan = mirror
    # harness: street data source (Method sheet): the local extract when built, else the Overpass server list
    app.state.overpass = LOCAL.transport if LOCAL else corridors.app_transport
    todo = [c for i, c in enumerate(city_list) if (not only or c["city"] == only) and i % shard[1] == shard[0]
            and (not only_list or c["city"] in only_list)
            and (series == "v1" or (c["city"], c["county"]) in frozen)][:limit]
    t0 = time.time()
    watch = _Watch(f"{shard[0]}/{shard[1]} {series}")
    watch.total = len(todo)
    try:
        _loop(app, todo, out_dir, frozen, earlier, bounds, mirror, ver, osm_source, series, watch, t0)
    except BaseException:
        watch.log("EXIT: exception\n" + traceback.format_exc())
        watch.done = True
        raise
    watch.log("EXIT: finished")
    watch.done = True
    db.close()


def _loop(app, todo, out_dir, frozen, earlier, bounds, mirror, ver, osm_source, series, watch, t0) -> None:
    with TestClient(app) as client:
        for n, c in enumerate(todo, 1):
            watch.n, watch.city = n, c["city"]
            out = out_dir / f"{corridors.norm_city(c['city'])}_{c['county']}.json"
            fz = frozen.get((c["city"], c["county"])) or earlier.get((c["city"], c["county"]))
            if fz and not (fz.get("corridor") or {}).get("line") and series == "v1":
                fz = None                             # frozen without a line: may get one now ("added" below)
            b = None
            if fz:                                    # same basis as the earlier run: the exact same line
                corr = fz.get("corridor") or {"reason": fz.get("reason") or "not in the frozen corridor list"}
                b = {"name": fz.get("osm_boundary")}
            else:
                try:
                    b = bounds.get(corridors.norm_city(c["city"])) or (None if LOCAL else
                                                                         corridors.find_rel(c["city"], OSM))
                    if b:
                        corr = corridors.pick(b["rel"], OSM, LOCAL)
                    elif LOCAL and not NOT_A_CITY.search(c["city"]) and (box := gps_box(mirror, c["city"])):
                        b = {"name": "crash-GPS box (OSM has no boundary for this city)"}
                        corr = corridors.pick_in_rings(box, LOCAL)
                    else:
                        corr = {"reason": "no OSM city boundary with this name (CCRS also files state parks, "
                                          "campuses, airports and some unincorporated places as cities)"}
                except corridors.OverpassUnavailable as e:
                    print(f"[{n}/{len(todo)}] {c['city']}: not tested (Overpass) - {e}", flush=True)
                    continue                          # not saved: the next pass tries again
                except Exception as e:  # noqa: BLE001 - recorded per city, never skipped silently
                    corr = {"reason": f"OSM error: {e}"}
            key = hashlib.sha1(json.dumps([ver, corr, osm_source, HARNESS], sort_keys=True).encode()).hexdigest()[:12]
            if out.exists() and json.loads(out.read_text()).get("key") == key:
                continue
            row = {**c, "key": key, "harness": HARNESS, "corridor_list": series, "code_version": ver, "commit": commit(), "mirror_built": mirror_built(),
                   "osm_boundary": (b or {}).get("name"), "osm_source": osm_source,
                   "corridor_source": ("frozen list v2 (re-picked inside the city)" if series == "v2" else
                                       "frozen list" if fz and (c["city"], c["county"]) in frozen else
                                       "earlier run (live Overpass)" if fz else
                                       "picked (added after the corridor list was frozen)" if frozen else "picked")}
            if "line" not in corr:
                row.update(stage="corridor", reason=corr["reason"])
            else:
                row["corridor"] = corr
                try:
                    row.update(run_city(client, mirror, c, corr))
                except Exception as e:  # noqa: BLE001
                    row.update(stage="crash", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-800:])
            if "Overpass" in json.dumps(row.get("error", "")) or "OverpassUnavailable" in str(row.get("error", "")):
                print(f"[{n}/{len(todo)}] {c['city']}: not tested (Overpass) - {row.get('error', '')[:120]}", flush=True)
                continue                              # the app's corridor fetch got no streets: retry next pass
            if (c["city"], c["county"]) in KNOWN_ISSUES:
                row["known_issue"] = KNOWN_ISSUES[(c["city"], c["county"])]
            row["result_v1"], row["result_reason_v1"] = classify(row)
            row["result"], row["result_reason"] = classify_v2(row)
            row["result_v3"], row["result_reason_v3"] = classify_v3(row)
            row["result_v4"], row["result_reason_v4"] = classify_v4(row)
            out.write_text(json.dumps(row, indent=1, default=str))
            print(f"[{n}/{len(todo)} {time.time() - t0:.0f}s] {c['city']}: {row['result']} - {row['result_reason']}",
                  flush=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--city")
    ap.add_argument("--prefetch", action="store_true")
    ap.add_argument("--shard", default="0/1", help="worker i of n, e.g. 1/2")
    ap.add_argument("--freeze", action="store_true", help="write corridors_frozen.json from this code version's run")
    ap.add_argument("--freeze-v2", metavar="TREE", help="write corridors_frozen_v2.json from results/TREE")
    ap.add_argument("--corridors", choices=("v1", "v2"), default="v1", help="corridor list series to run")
    ap.add_argument("--cities-file", help="only the cities named in this file, one per line (a re-check, not a run)")
    a = ap.parse_args()
    i, n = (int(x) for x in a.shard.split("/"))
    (prefetch() if a.prefetch else freeze() if a.freeze else freeze_v2(a.freeze_v2) if a.freeze_v2
     else main(a.limit, a.city, (i, n), a.corridors,
               set(Path(a.cities_file).read_text().split("\n")) - {""} if a.cities_file else None))
