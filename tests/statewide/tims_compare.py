"""TIMS vs CCRS by county and year.

TIMS side: the SWITRS Summary tables (tims.berkeley.edu/tools/summary/), read in the signed-in Tester browser panel
and saved as text in data/cache/statewide/tims/ (no file download; the table is copied from the page). One table
per severity: `tims_<severity>_by_county_2021_2025.txt`, rows `COUNTY|2021|...|2025|Average`.
CCRS side: the local mirror, counted the way TIMS counts: one row per crash, deleted reports out, severity = the most
severe injury in the crash (NumberKilled for fatal, InjuredWitnessPassengers extent for serious).
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

YEARS = [2021, 2022, 2023, 2024, 2025]
SEVERITIES = {"fi": "Fatal and injury", "fatal": "Fatal", "serious": "Serious injury (A)"}
# Live CCRS writes codes (SuspectSerious; SevereInactive = the older SWITRS "severe" level), see bug #79.
SERIOUS = ("SUSPECTSERIOUS", "SEVEREINACTIVE", "SUSPECTED SERIOUS INJURY", "SEVERE INJURY")


def read_tims(folder: Path) -> dict[str, dict[str, list[int]]]:
    """severity -> COUNTY -> counts per year, for every table present."""
    out = {}
    for sev in SEVERITIES:
        f = folder / f"tims_{sev}_by_county_2021_2025.txt"
        if not f.exists():
            continue
        rows = {}
        for line in f.read_text().splitlines()[1:]:
            p = line.split("|")
            if len(p) >= 6:
                rows[p[0].strip().upper()] = [int(x.replace(",", "")) for x in p[1:6]]
        out[sev] = rows
    return out


def county_names(tims: dict) -> dict[str, str]:
    """County code ('1'..'58', alphabetical, the CHP/SWITRS order) -> name."""
    names = sorted(k for k in next(iter(tims.values())) if k != "STATEWIDE")
    return {str(i + 1): n for i, n in enumerate(names)}


def tims_city_names(folder: Path) -> set[str]:
    f = folder / "tims_city_2023_2024.txt"
    if not f.exists():
        return set()
    return {e.split("|")[0].strip().upper() for e in f.read_text().strip().split(";") if e}


def ccrs_counts(mirror_db: Path, tims_cities: set[str] | None = None) -> dict[tuple[str, int], Counter]:
    """(county code, year) -> Counter(total, fi, fatal, serious, pdo, special_district_fi).

    special_district_fi: F+I crashes filed under a "city" TIMS doesn't list (state park, campus, airport, harbor)."""
    tims_cities = tims_cities or set()
    con = sqlite3.connect(mirror_db)
    meta = {(t, y): rid for rid, t, y in con.execute("SELECT rid, tbl, year FROM _meta")}
    out: dict[tuple[str, int], Counter] = {}
    for y in YEARS:
        crid, irid = meta[("crashes", y)], meta.get(("iwp", y))
        serious = set()
        if irid:
            q = f'SELECT DISTINCT "CollisionId" FROM "{irid}" WHERE UPPER("ExtentOfInjuryCode") IN ({",".join("?" * len(SERIOUS))})'
            serious = {r[0] for r in con.execute(q, SERIOUS)}
        q = (f'SELECT "Collision Id", "County Code", COALESCE("NumberKilled",0), COALESCE("NumberInjured",0), '
             f'"City Name", "City Is Incorporated" FROM "{crid}" WHERE COALESCE("IsDeleted", \'\') <> \'True\'')
        for cid, cty, k, i, city, inc in con.execute(q):
            c = out.setdefault((str(cty), y), Counter())
            c["total"] += 1
            if k > 0:
                c["fatal"] += 1
            elif cid in serious:
                c["serious"] += 1
            if k > 0 or i > 0:
                c["fi"] += 1
                cu = str(city or "").strip().upper()
                if tims_cities and cu not in tims_cities and cu not in ("UNINCORPORATED", "") \
                        and cu.replace(" ", "") not in {t.replace(" ", "").replace("-", "") for t in tims_cities}:
                    c["special_district_fi"] += 1
            else:
                c["pdo"] += 1
    con.close()
    return out


def compare(mirror_db: Path, tims_dir: Path) -> list[dict]:
    tims = read_tims(tims_dir)
    if not tims:
        return []
    names = county_names(tims)
    cc = ccrs_counts(mirror_db, tims_city_names(tims_dir))
    rows = []
    for code, name in names.items():
        for i, y in enumerate(YEARS):
            c = cc.get((code, y), Counter())
            row = {"county_code": int(code), "county": name.title(), "year": y,
                   "ccrs_total": c["total"], "ccrs_pdo": c["pdo"], "ccrs_special_district_fi": c["special_district_fi"]}
            for sev in SEVERITIES:
                t = tims.get(sev, {}).get(name)
                row[f"ccrs_{sev}"] = c[sev]
                row[f"tims_{sev}"] = t[i] if t else None
                row[f"diff_{sev}"] = (c[sev] - t[i]) if t else None
                row[f"diff_{sev}_pct"] = round(100 * (c[sev] - t[i]) / t[i], 1) if t and t[i] else None
            row["reason"] = reason(row)
            rows.append(row)
    return rows


def reason(r: dict) -> str:
    """Likely reason for the F+I gap, from the counts only (code decides; thresholds stated in Method)."""
    d, t = r.get("diff_fi"), r.get("tims_fi")
    parts = []
    if r["year"] >= 2025:
        parts.append("2025 is provisional in both sources; counts still change")
    if d is None:
        return "TIMS table not captured"
    if t and abs(d) <= max(3, 0.02 * t):
        parts.append("match within 2%")
    elif d > 0 and r["ccrs_special_district_fi"] >= 0.5 * d:
        parts.append(f"CCRS has {r['ccrs_special_district_fi']} F+I crashes filed for special districts "
                     "(state parks, campuses, airports, harbors) that TIMS doesn't list")
    elif d > 0:
        parts.append("CCRS has more F+I crashes than TIMS; reason not identified from counts")
    else:
        parts.append("TIMS has more F+I crashes than CCRS; reason not identified from counts")
    parts.append(f"PDO ({r['ccrs_pdo']}) is in CCRS only; TIMS excludes it")
    return "; ".join(parts)
