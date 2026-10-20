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
import corridors  # noqa: E402
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
YEARS = [2021, 2022, 2023, 2024, 2025]


def code_version() -> str:
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD:backend"], capture_output=True,
                          text=True).stdout.strip()[:12]


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


def _sq(s: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def independent_no_gps(mirror, city: str, corridor_core: str, cross_cores: list[str]) -> set[str]:
    """No-GPS crash ids in the city whose one road names the corridor and the other a study cross street."""
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
            for a, b in ((p, s), (s, p)):
                if core in a and any(x in b for x in crosses):
                    ids.add(str(int(r["i"])) if isinstance(r["i"], (int, float)) else str(r["i"]))
    return ids


def run_city(client: TestClient, mirror, c: dict, corr: dict) -> dict:
    sid = client.post("/api/studies", json={"name": f"statewide {c['city']}", "mode": "profile",
                                            "from_year": YEARS[0], "to_year": YEARS[-1]}).json()["id"]
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
        if not hit or json.loads(hit["body"]).get("elements") or empty_retries >= 4:
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
    return {
        "stage": "done", "study_id": sid, "overpass_empty_retries": empty_retries, "corridor_name": net.get("corridor_name"),
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
    }


def classify(r: dict) -> tuple[str, str]:
    """Proposed pass/warn/fail rules from #73 (user to confirm on the first report)."""
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


def main(limit: int | None = None, only: str | None = None, shard: tuple[int, int] = (0, 1)) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    mirror = ccrs_mirror.Mirror(DATA / "ccrs_mirror.sqlite", CACHE)
    ver = code_version()
    city_list = cities(mirror)
    (DATA / "cities.json").write_text(json.dumps(city_list, indent=1))
    bounds = corridors.boundaries(OSM)
    # Worker 0 uses the Tester database; extra parallel workers get their own Tester-only copies (one SQLite writer
    # each), never the shared data/crashiq.sqlite.
    db_path = ROOT / "data" / "tester.sqlite" if shard[0] == 0 else DATA / f"tester_worker{shard[0]}.sqlite"
    settings = Settings(db_path=db_path, app_password=None, anthropic_api_key=None,
                        typesafe_api_key=None, study_ai_cap_usd=0.0, dist_dir=ROOT / "no-dist", fixtures_dir=None)
    db = Database(settings.db_path)
    app = create_app(settings, db)
    app.state.ckan = mirror
    todo = [c for i, c in enumerate(city_list) if (not only or c["city"] == only) and i % shard[1] == shard[0]][:limit]
    t0 = time.time()
    with TestClient(app) as client:
        for n, c in enumerate(todo, 1):
            out = RESULTS / f"{corridors.norm_city(c['city'])}_{c['county']}.json"
            try:
                b = bounds.get(corridors.norm_city(c["city"])) or corridors.find_rel(c["city"], OSM)
                corr = corridors.pick(b["rel"], OSM) if b else {"reason": "no OSM city boundary with this name"}
            except Exception as e:  # noqa: BLE001 - recorded per city, never skipped silently
                corr = {"reason": f"OSM error: {e}"}
            key = hashlib.sha1(json.dumps([ver, corr], sort_keys=True).encode()).hexdigest()[:12]
            if out.exists() and json.loads(out.read_text()).get("key") == key:
                continue
            row = {**c, "key": key, "code_version": ver, "osm_boundary": (b or {}).get("name") if "rel" in str(b) else None}
            if "line" not in corr:
                row.update(stage="corridor", reason=corr["reason"])
            else:
                row["corridor"] = corr
                try:
                    row.update(run_city(client, mirror, c, corr))
                except Exception as e:  # noqa: BLE001
                    row.update(stage="crash", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-800:])
            row["result"], row["result_reason"] = classify(row)
            out.write_text(json.dumps(row, indent=1, default=str))
            print(f"[{n}/{len(todo)} {time.time() - t0:.0f}s] {c['city']}: {row['result']} - {row['result_reason']}",
                  flush=True)
    db.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--city")
    ap.add_argument("--prefetch", action="store_true")
    ap.add_argument("--shard", default="0/1", help="worker i of n, e.g. 1/2")
    a = ap.parse_args()
    i, n = (int(x) for x in a.shard.split("/"))
    prefetch() if a.prefetch else main(a.limit, a.city, (i, n))
