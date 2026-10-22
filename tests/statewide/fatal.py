"""Fatal crashes first (#166, measure only): which fatal crashes CrashIQ can't place, and whether FARS can.

1. Unplaced fatal crashes: on the test corridors (latest run's pulls) and statewide (CCRS 2021-2025 fatal crashes
   without GPS), by reason and by agency.
2. FARS (NHTSA, public domain): California accident rows 2021-2024 (data/cache/fars/accident_<year>_ca.csv, kept
   from the national files the user OK'd on 2026-10-21). Each CCRS fatal crash is linked by county + date + time
   (within LINK_MINUTES; FARS unknown time 99 matches any) + number killed, roads as the tie-break. A FARS point is
   *usable* for an unplaced crash when it is a real point (not a FARS unknown code, not shared by 3+ FARS crashes)
   and fits the report: a road the report names runs within GPS_CHECK_FT (+ the report's own offset) of it, from the
   local OSM extract. Nothing here goes into the app.
3. Residue: unplaced fatal crashes FARS can't place, listed for a later human-confirmed lookup (no web lookups).

Run: python tests/statewide/fatal.py   (writes data/statewide/fatal.json and data/statewide/fatal_residue.csv)
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import checks

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
FARS_DIR = ROOT / "data" / "cache" / "fars"
FARS_YEARS = (2021, 2022, 2023, 2024)
LINK_MINUTES = 60
GPS_CHECK_FT = 400.0          # the app's own GPS check distance (assign.GPS_CHECK_FT), plus the report's offset
UNUSABLE = {"", "NOTSTATED", "UNKNOWN", "NONE", "NA", "PRIVATEPROPERTY", "PARKINGLOT"}
ROAD_CLASSES = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
                "living_street", "road", "motorway_link", "trunk_link", "primary_link", "secondary_link",
                "tertiary_link"}


def fips(ccrs_county: int) -> int:
    """CCRS County Code (California's alphabetical 1-58) -> FIPS county code (1, 3, 5, ... 115)."""
    return 2 * int(ccrs_county) - 1


_ROUTE = re.compile(r"\b(?:SR|RT|RTE|HWY|ROUTE|CA|I|US|STATE ROUTE|INTERSTATE)[\s-]*(\d{1,3})\b")


def _routes(t: str | None) -> set[str]:
    return set(_ROUTE.findall(str(t or "").upper()))


def road_match(ccrs_roads: list[str | None], fars_ways: list[str | None]) -> bool:
    """Does a CCRS road name the same road as a FARS trafficway (route number, or the same street core)?"""
    for a in ccrs_roads:
        for b in fars_ways:
            if not a or not b:
                continue
            if _routes(a) & _routes(b):
                return True
            ca, cb = checks.indep_core(a), checks.indep_core(b)
            if len(ca) >= 4 and len(cb) >= 4 and (ca == cb or ca in cb or cb in ca):
                return True
    return False


def case_key(r: dict) -> str:
    """FARS ST_CASE numbers restart every year (60011 exists in 2021 and 2024): a case is year + ST_CASE."""
    return f"{r['YEAR']}-{r['ST_CASE']}"


def index(fars_rows: list[dict]) -> dict:
    out = defaultdict(list)
    for r in fars_rows:
        out[(int(r["COUNTY"]), dt.date(int(r["YEAR"]), int(r["MONTH"]), int(r["DAY"])))].append(r)
    return out


def _minutes(r: dict) -> int | None:
    h, m = int(r["HOUR"]), int(r["MINUTE"])
    return None if h > 23 else h * 60 + (0 if m > 59 else m)


def link(c: dict, idx: dict) -> tuple[str, str | None]:
    """('linked', ST_CASE) | ('ambiguous', None) | ('unlinked', None) for one CCRS fatal crash."""
    t = dt.datetime.fromisoformat(c["dt"][:19])
    cands = [r for r in idx.get((fips(c["county"]), t.date()), []) if int(r["FATALS"]) == int(c["killed"])]
    cm = t.hour * 60 + t.minute
    cands = [r for r in cands if _minutes(r) is None or abs(_minutes(r) - cm) <= LINK_MINUTES]
    if len(cands) > 1:
        roads = [r for r in cands if road_match(c["roads"], [r.get("TWAY_ID"), r.get("TWAY_ID2")])]
        if len(roads) == 1:
            return "linked", case_key(roads[0])
        return "ambiguous", None
    return ("linked", case_key(cands[0])) if cands else ("unlinked", None)


def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x else None


def _offset_ft(c: dict) -> float:
    return checks.offset_ft(c.get("dist"), c.get("unit")) or 0.0


def fits(local, lat: float, lon: float, c: dict) -> bool:
    """A road the report names runs within GPS_CHECK_FT + the report's offset of the point (local OSM extract)."""
    tol_m = (GPS_CHECK_FT + _offset_ft(c)) / 3.28084
    els = local.around([(lat, lon)], tol_m, ROAD_CLASSES)["elements"]
    names = [t.get(k) for w in els if w["type"] == "way" for t in [w.get("tags", {})] for k in ("name", "ref")]
    return road_match([x for x in c["roads"] if checks.indep_core(x) not in UNUSABLE], names)


def ccrs_fatal(mirror_db: Path) -> list[dict]:
    con = sqlite3.connect(mirror_db)
    con.row_factory = sqlite3.Row
    out = {}
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl='crashes'"):
        q = (f'SELECT "Collision Id" i, "Crash Date Time" t, "County Code" k, "City Name" city, "NCIC Code" a, '
             f'"NumberKilled" n, "PrimaryRoad" p, "SecondaryRoad" s, "SecondaryDistance" d, "SecondaryUnitOfMeasure" u, '
             f'"Latitude" la, "Longitude" lo FROM "{rid}" WHERE "NumberKilled" > 0 AND COALESCE("IsDeleted", \'\') <> \'True\'')
        for r in con.execute(q):
            cid = str(int(r["i"]))
            la, lo = _num(r["la"]), _num(r["lo"])
            out[cid] = {"crash_id": cid, "dt": r["t"], "year": int(r["t"][:4]), "county": int(r["k"]), "city": r["city"],
                        "agency": str(r["a"]), "killed": int(r["n"]), "roads": [r["p"], r["s"]], "dist": r["d"],
                        "unit": r["u"], "gps": la is not None and lo is not None,
                        "no_cross": checks.indep_core(r["s"]) in UNUSABLE or len(checks.indep_core(r["s"])) <= 2}
    con.close()
    return list(out.values())


def corridor_fatal(results: list[dict], dbs: list[Path]) -> list[dict]:
    """Fatal crashes kept for a test corridor in the latest run, with how each was placed."""
    want = {r["study_id"]: r for r in results if r.get("study_id")}
    out = []
    for db in dbs:
        if not db.exists():
            continue
        con = sqlite3.connect(db)
        for sid, payload in con.execute("SELECT study_id, payload FROM crash_pull"):
            if sid not in want:
                continue
            for c in json.loads(payload)["crashes"]:
                if (c.get("killed") or 0) > 0 and not c.get("exclude_rule"):
                    src = c.get("location_source")
                    reason = ("placed" if src != "unmatched" else
                              "no cross street" if c.get("review_reason") == "no_cross_street" else
                              "relaxed match held by the gate" if (c.get("suggestion") or {}).get("tier") == "relaxed"
                              else "no locator match")
                    out.append({"city": want[sid]["city"], "crash_id": str(c["crash_id"]), "source": src,
                                "reason": reason})
        con.close()
    return out


def main() -> None:
    import build_workbook as bw
    import osm_local
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    ver = bw.versions()[-1]
    results = bw.load_results(ver)
    dbs = [ROOT / "data" / "tester.sqlite", *sorted(DATA.glob("tester_worker*.sqlite"))]
    agencies = {a["ncic"]: a for a in json.loads((DATA / "agencies.json").read_text())}
    fars = [r for y in FARS_YEARS for r in csv.DictReader(open(FARS_DIR / f"accident_{y}_ca.csv"))]
    idx = index(fars)
    by_case = {case_key(r): r for r in fars}
    shared = Counter((r["LATITUDE"][:9], r["LONGITUD"][:10]) for r in fars)

    def fars_point(case: str | None) -> tuple[float, float] | None:
        r = by_case.get(case or "")
        if not r:
            return None
        la, lo = _num(r["LATITUDE"]), _num(r["LONGITUD"])
        if la is None or lo is None or not (32 <= la <= 42.1 and -124.6 <= lo <= -114):    # 77.77/88.88/99.99 codes
            return None
        if shared[(r["LATITUDE"][:9], r["LONGITUD"][:10])] >= 3:
            return None                                                                    # degenerate point
        return la, lo

    allf = ccrs_fatal(DATA / "ccrs_mirror.sqlite")
    by_id = {c["crash_id"]: c for c in allf}
    links = {}
    for c in allf:
        links[c["crash_id"]] = link(c, idx) if c["year"] in FARS_YEARS else ("no FARS year", None)
    in_fars = [c for c in allf if c["year"] in FARS_YEARS]
    link_counts = Counter(links[c["crash_id"]][0] for c in in_fars)
    fars_used = Counter(links[c["crash_id"]][1] for c in in_fars if links[c["crash_id"]][0] == "linked")

    def fars_verdict(c: dict) -> str:
        status, case = links[c["crash_id"]]
        if status == "no FARS year":
            return "2025: FARS not published yet"
        if status != "linked":
            return {"unlinked": "not found in FARS", "ambiguous": "FARS ambiguous"}[status]
        p = fars_point(case)
        if p is None:
            return "FARS point unusable (unknown or shared)"
        return "FARS point fits the report's roads" if fits(local, p[0], p[1], c) else "FARS point off the report's roads"

    # 1a: test corridors
    cor = corridor_fatal(results, dbs)
    cor_unplaced = [x for x in cor if x["source"] == "unmatched"]
    for x in cor_unplaced:
        x["fars"] = fars_verdict(by_id[x["crash_id"]]) if x["crash_id"] in by_id else "not in CCRS fatal list"
    # 1b: statewide, fatal crashes CCRS gives no GPS for
    nogps = [c for c in allf if not c["gps"]]
    for c in nogps:
        c["fars"] = fars_verdict(c)
    agency_rows = Counter(c["agency"] for c in nogps)
    residue = [c for c in nogps if c["fars"] != "FARS point fits the report's roads"]
    out = {
        "basis": {"backend_tree": ver, "ccrs_years": "2021-2025", "fars_years": list(FARS_YEARS),
                  "link_minutes": LINK_MINUTES, "gps_check_ft": GPS_CHECK_FT},
        "ccrs_fatal": len(allf), "ccrs_fatal_by_year": dict(sorted(Counter(c["year"] for c in allf).items())),
        "fars_ca_by_year": {y: sum(1 for r in fars if int(r["YEAR"]) == y) for y in FARS_YEARS},
        "link": {"ccrs_fatal_in_fars_years": len(in_fars), **dict(link_counts),
                 "link_pct": round(100 * link_counts["linked"] / len(in_fars), 1) if in_fars else None,
                 "fars_crashes_linked_twice": sum(1 for v in fars_used.values() if v > 1)},
        "corridor": {"fatal_kept": len(cor), "placed": sum(x["source"] != "unmatched" for x in cor),
                     "unplaced": len(cor_unplaced), "unplaced_by_reason": dict(Counter(x["reason"] for x in cor_unplaced)),
                     "unplaced_fars": dict(Counter(x["fars"] for x in cor_unplaced)), "unplaced_list": cor_unplaced},
        "statewide_no_gps": {"count": len(nogps), "pct_of_fatal": round(100 * len(nogps) / len(allf), 1),
                             "no_cross_street": sum(c["no_cross"] for c in nogps),
                             "fars": dict(Counter(c["fars"] for c in nogps)),
                             "by_agency": [{"ncic": a, "agency": (agencies.get(a) or {}).get("city") or a, "type":
                                            (agencies.get(a) or {}).get("type"), "fatal_no_gps": n}
                                           for a, n in agency_rows.most_common(25)]},
        "residue_count": len(residue),
        "residue_by_year": dict(sorted(Counter(c["year"] for c in residue).items())),
        "residue_in_fars_years": sum(1 for c in residue if c["year"] in FARS_YEARS),
    }
    (DATA / "fatal.json").write_text(json.dumps(out, indent=1, default=str))
    with open(DATA / "fatal_residue.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["crash_id", "date_time", "city", "county_code", "agency", "killed", "primary_road", "secondary_road",
                    "no_cross_street", "why_no_point"])
        for c in sorted(residue, key=lambda c: c["dt"]):
            w.writerow([c["crash_id"], c["dt"][:16], c["city"], c["county"], c["agency"], c["killed"], c["roads"][0],
                        c["roads"][1], c["no_cross"], c["fars"]])
    print(json.dumps({k: v for k, v in out.items() if k != "corridor"} | {"corridor": {k: v for k, v in out["corridor"].items()
                                                                                    if k != "unplaced_list"}}, indent=1))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    main()
