"""Tester: statewide profile of how each California reporting agency records crashes in CCRS.

Output: one JSON row per agency (NCIC code) with the measures below.

Each measure maps to a way the CrashIQ pull (`backend/crashiq/crashes.py`) can lose or misplace crashes:
  gps_pct            no GPS -> the crash is found only by street name (Union City PD: 0%)
  sec_blank_pct      no usable cross street (blank, NOT STATED, PRIVATE PROPERTY, 1-2 characters) -> a no-GPS
                     crash can't be tied to a study intersection (excluded as off the study stretch)
  sec_no_key_pct     cross street the app's name normalizer can't read (street_key is None)
  route_pct          road written as a route number (SR-1, RT 82, HWY 99): never matches an OSM street name
  address_pct        house address in a road field ("1234 MAIN ST")
  no_suffix_pct      street written with no suffix (MAIN vs MAIN ST)
  offset_pct         distance from the cross street given
  miles_gt2          "miles" offsets over 2 (feet typed as miles)
  pdo_pct            0 killed and 0 injured
  amended_pct        crashes whose latest report version is > 1 (amended reports)
  dup_same_crash     report numbers carried by 2+ collision ids with the same two roads: one crash filed twice
                     (the app de-duplicates on collision id only, so it counts these twice)
  top_point_share    share of the agency's GPS crashes on its single most used point (~11 m grid)
  low_precision_pct  GPS with 2 or fewer decimals (~1 km)
  exact_point_n      crashes on the agency's most used exact coordinate (a default point: station, city hall)
  piled_pct          share of GPS crashes on exact coordinates used 10+ times
  snapped_far_pct    of street GPS crashes the report puts > 250 ft from the cross street, the share sitting on a
                     piled point: GPS snapped to the intersection, so a mid-block crash lands inside the 250 ft area
  drop_ratio         worst year 2021-2025 / median of 2016-2019 reports: below 0.5 = the agency stopped filing most
                     reports to CCRS (TIMS shows the same gap: it is built from the same records)
  off_county_gps_pct GPS outside the crash's own county (county box = 0.5-99.5 percentile of all GPS in that
                     county + 5 km). A wrong point is never pulled by street name, so the crash is lost

Input: the local CCRS mirror (`ccrs_mirror.py`), study years 2021-2025; yearly counts 2016-2025 from data.ca.gov.
Run:  python tests/statewide/agency_scan.py   (writes data/statewide/agencies.json)
"""

from __future__ import annotations

import csv
import json
import math
import statistics
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from crashiq.names import street_key  # noqa: E402

ROUTE = re.compile(r"^\s*(I|US|SR|CA|STATE ROUTE|STATE HWY|INTERSTATE|HWY|HIGHWAY|ROUTE|RT|RTE|SH)[\s\-#]*\d+\b")
ADDRESS = re.compile(r"^\s*\d{2,6}\s+[A-Z]|\bBLOCK\b|\bBLK\b")
SUFFIXES = {"ST", "STREET", "AVE", "AV", "AVENUE", "BLVD", "BL", "BOULEVARD", "DR", "DRIVE", "RD", "ROAD", "WAY",
            "WY", "LN", "LANE", "CT", "COURT", "PL", "PLACE", "PKWY", "PARKWAY", "HWY", "HIGHWAY", "CIR", "CIRCLE",
            "TER", "TERRACE", "EXPY", "EXPRESSWAY", "PLZ", "PLAZA", "SQ", "ALY", "ALLEY", "LOOP", "TRL", "TRAIL",
            "ROW", "WALK", "PATH", "CRES", "RUN", "PT", "XING", "FWY", "FREEWAY", "TPKE", "MALL", "PASS", "GRADE"}
DIR_TAIL = re.compile(r"\b([NSEW]/?B|NORTHBOUND|SOUTHBOUND|EASTBOUND|WESTBOUND)\b")


def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _decimals(s: str) -> int:
    s = (s or "").strip()
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


UNUSABLE = {"NOT STATED", "PRIVATE PROPERTY", "UNKNOWN", "NONE", "NA", "N/A", "PARKING LOT"}


def _road_key(road: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (road or "").upper())


def _style(road: str) -> str:
    """route | address | no_suffix | suffix | blank for one road field."""
    r = (road or "").strip().upper()
    if not r or r in UNUSABLE or len(_road_key(r)) <= 2:
        return "blank"
    if ROUTE.match(r):
        return "route"
    if ADDRESS.search(r):
        return "address"
    toks = DIR_TAIL.sub(" ", re.sub(r"[^A-Z0-9/ ]", " ", r)).split()
    return "suffix" if toks and toks[-1] in SUFFIXES else "no_suffix"


def _km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    x = math.radians(lo2 - lo1) * math.cos(math.radians((la1 + la2) / 2))
    return 6371 * math.hypot(x, math.radians(la2 - la1))


COLS = ("Collision Id", "Report Number", "Report Version", "NCIC Code", "City Name", "County Code", "IsFreeway",
        "Latitude", "Longitude", "PrimaryRoad", "SecondaryRoad", "SecondaryDistance", "SecondaryUnitOfMeasure",
        "NumberKilled", "NumberInjured", "IsDeleted")


def _s(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer() and abs(v) > 1000:
        return str(int(v))
    return str(v)


def mirror_rows(db_path: Path):
    """Crash rows (all study years) from the local CCRS mirror, as strings like the CSV export."""
    con = sqlite3.connect(db_path)
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes' ORDER BY year"):
        cols = ", ".join(f'"{c}"' for c in COLS)
        for row in con.execute(f'SELECT {cols} FROM "{rid}"'):
            yield {c: _s(v) for c, v in zip(COLS, row)}
    con.close()


def csv_rows(paths: list[str]):
    for p in paths:
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            yield from csv.DictReader(f)


def profile(rows) -> list[dict]:
    rows_by_cid: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if str(r.get("IsDeleted")) == "True":
            continue
        rows_by_cid[r["Collision Id"]].append(r)

    ag: dict[str, dict] = defaultdict(lambda: {"cids": 0, "multi": 0, "rows": []})
    for cid, rs in rows_by_cid.items():
        rs.sort(key=lambda r: int(_f(r.get("Report Version")) or 0))
        r = rs[-1]                                    # latest version, as the app keeps
        a = ag[(r.get("NCIC Code") or "").strip() or "?"]
        a["cids"] += 1
        a["multi"] += len(rs) > 1
        a["rows"].append(r)

    by_county: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for a in ag.values():
        for r in a["rows"]:
            la, lo = _f(r.get("Latitude")), _f(r.get("Longitude"))
            if la and lo and 32 <= la <= 42.1 and -124.5 <= lo <= -114:
                by_county[(r.get("County Code") or "").strip()].append((la, lo))
    cbox = {}
    for c, pts in by_county.items():
        las, los = sorted(p[0] for p in pts), sorted(p[1] for p in pts)
        q = lambda v, f: v[min(len(v) - 1, int(f * len(v)))]  # noqa: E731
        m = 5 / 111.0
        cbox[c] = (q(las, .005) - m, q(las, .995) + m, q(los, .005) - m * 1.25, q(los, .995) + m * 1.25)

    out = []
    for code, a in ag.items():
        rs = a["rows"]
        n = len(rs)
        cities = Counter((r.get("City Name") or "").strip() or "?" for r in rs)
        counties = Counter((r.get("County Code") or "").strip() for r in rs)
        fwy = sum(r.get("IsFreeway") == "True" for r in rs)
        street = [r for r in rs if r.get("IsFreeway") != "True"]      # city-street crashes: what CrashIQ places
        ns = max(1, len(street))
        pts = []
        for r in rs:
            la, lo = _f(r.get("Latitude")), _f(r.get("Longitude"))
            if la and lo and 32 <= la <= 42.1 and -124.5 <= lo <= -114:
                pts.append((la, lo, r))
        sty_p = Counter(_style(r.get("PrimaryRoad")) for r in street)
        sty_s = Counter(_style(r.get("SecondaryRoad")) for r in street)
        dist = [_f(r.get("SecondaryDistance")) for r in street]
        miles_gt2 = sum(1 for r, d in zip(street, dist)
                        if d and (r.get("SecondaryUnitOfMeasure") or "").strip().upper() == "M" and d > 2)
        sec_nokey = sum(1 for r in street if (r.get("SecondaryRoad") or "").strip()
                        and street_key(r.get("SecondaryRoad")) is None)
        pdo = sum((_f(r.get("NumberKilled")) or 0) == 0 and (_f(r.get("NumberInjured")) or 0) == 0 for r in rs)
        reps: dict[str, set] = defaultdict(set)
        for r in rs:
            reps[(r.get("Report Number") or "").strip()].add(
                (r["Collision Id"], _road_key(r.get("PrimaryRoad")), _road_key(r.get("SecondaryRoad"))))
        dup_same = sum(1 for k, v in reps.items() if k and len(v) > 1 and len({x[1:] for x in v}) == 1)
        blank_rep = len(reps.get("", ()))
        amended = sum(int(_f(r.get("Report Version")) or 1) > 1 for r in rs)
        grid = Counter((round(la, 4), round(lo, 4)) for la, lo, _ in pts)
        top_pt, top_n = grid.most_common(1)[0] if grid else (None, 0)
        low_prec = sum(1 for _, _, r in pts if max(_decimals(r.get("Latitude")), _decimals(r.get("Longitude"))) <= 2)
        exact = Counter((r.get("Latitude"), r.get("Longitude")) for _, _, r in pts)
        (ex_pt, ex_n) = exact.most_common(1)[0] if exact else (None, 0)
        ex_rows = [r for _, _, r in pts if (r.get("Latitude"), r.get("Longitude")) == ex_pt]
        ex_roads = Counter(f"{(r.get('PrimaryRoad') or '').strip()} & {(r.get('SecondaryRoad') or '').strip()}"
                           for r in ex_rows).most_common(2)
        piled = sum(v for v in exact.values() if v >= 10)

        def off_county(la, lo, r):
            b = cbox.get((r.get("County Code") or "").strip())
            return b is not None and not (b[0] <= la <= b[1] and b[2] <= lo <= b[3])
        far = sum(off_county(la, lo, r) for la, lo, r in pts)

        def offset_ft(r):
            d = _f(r.get("SecondaryDistance")) or 0
            return d * (5280 if (r.get("SecondaryUnitOfMeasure") or "").strip().upper() == "M" and d <= 2 else 1)
        far_rep = [r for _, _, r in pts if r.get("IsFreeway") != "True" and offset_ft(r) > 250]
        snapped = sum(exact[(r.get("Latitude"), r.get("Longitude"))] >= 10 for r in far_rep)
        out.append({
            "ncic": code, "type": "CHP" if code.startswith("9") else "local",
            "city": cities.most_common(1)[0][0], "n_cities": len(cities), "county": counties.most_common(1)[0][0],
            "crashes": n, "street_crashes": len(street), "freeway_pct": round(100 * fwy / n, 1),
            "gps_pct": round(100 * len(pts) / n, 1),
            "street_gps_pct": round(100 * sum(1 for la, lo, r in pts if r.get("IsFreeway") != "True") / ns, 1),
            "sec_blank_pct": round(100 * sty_s["blank"] / ns, 1),
            "sec_no_key_pct": round(100 * sec_nokey / ns, 1),
            "route_pct": round(100 * (sty_p["route"] + sty_s["route"]) / (2 * ns), 1),
            "address_pct": round(100 * (sty_p["address"] + sty_s["address"]) / (2 * ns), 1),
            "no_suffix_pct": round(100 * (sty_p["no_suffix"] + sty_s["no_suffix"]) / (2 * ns), 1),
            "offset_pct": round(100 * sum(1 for d in dist if d and d > 0) / ns, 1),
            "miles_gt2": miles_gt2,
            "pdo_pct": round(100 * pdo / n, 1),
            "amended_pct": round(100 * amended / n, 1),
            "dup_same_crash": dup_same, "blank_report_ids": blank_rep,
            "top_point_n": top_n, "top_point": top_pt,
            "top_point_share": round(100 * top_n / max(1, len(pts)), 1),
            "exact_point_n": ex_n, "exact_point": ex_pt, "exact_point_roads": ex_roads,
            "piled_pct": round(100 * piled / max(1, len(pts)), 1),
            "snapped_far_pct": round(100 * snapped / max(1, len(far_rep)), 1), "far_reported_n": len(far_rep),
            "low_precision_pct": round(100 * low_prec / max(1, len(pts)), 1),
            "off_county_gps_pct": round(100 * far / max(1, len(pts)), 1), "off_county_gps_n": far,
        })
    out.sort(key=lambda d: -d["crashes"])
    return out


def yearly_counts(cache: Path) -> dict[str, dict]:
    """Crashes per agency per year, 2016 to now, from data.ca.gov (one GROUP BY per year, cached)."""
    if cache.exists():
        return json.loads(cache.read_text())
    from crashiq.sources import ca_ccrs as cc
    out: dict[str, dict] = {}
    for y, rid in sorted(cc.crash_resource_ids().items()):
        sql = (f'SELECT "NCIC Code" AS a, COUNT(*) AS n FROM "{rid}" WHERE "IsDeleted"::text <> \'True\' '
               f'GROUP BY "NCIC Code"')
        for r in cc._get("datastore_search_sql", sql=sql)["records"]:
            out.setdefault(str(r["a"]).strip(), {})[str(y)] = int(r["n"])
    cache.write_text(json.dumps(out))
    return out


def reporting_gaps(agencies: list[dict], counts: dict[str, dict], last: int = 2025) -> None:
    """Flag an agency whose yearly report count fell below half its own 2016-2019 median in a later complete year.

    Adds `years` (count per year) and `drop_year` / `drop_ratio` (the worst year from 2021 to `last`)."""
    for a in agencies:
        c = counts.get(a["ncic"], {})
        a["years"] = {y: c.get(str(y), 0) for y in range(2016, last + 1)}
        base = statistics.median([c.get(str(y), 0) for y in range(2016, 2020)])
        a["base_2016_19"] = base
        worst = min(range(2021, last + 1), key=lambda y: c.get(str(y), 0))
        a["drop_year"] = worst
        a["drop_ratio"] = round(c.get(str(worst), 0) / base, 2) if base else None


def main(mirror_db: Path, out: Path, years_cache: Path) -> list[dict]:
    res = profile(mirror_rows(mirror_db))
    reporting_gaps(res, yearly_counts(years_cache))
    out.write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    r = main(root / "data/statewide/ccrs_mirror.sqlite", root / "data/statewide/agencies.json",
             root / "data/cache/statewide/agency_years.json")
    print(f"{len(r)} agencies, {sum(d['crashes'] for d in r)} crashes")
