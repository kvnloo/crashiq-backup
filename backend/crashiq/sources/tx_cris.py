"""Texas crash source: the TxDOT CRIS Public Extract (free self-registration, CSV files; not wired into the app).

Built against TxDOT's "2018 and Greater, Public File Extract Specification" (spec dated 06/13/25):
https://www.txdot.gov/content/dam/docs/division/trf/crash-records/public-extract-file-specification.xlsx
How to request an extract: CRIS Automated Interface User Guide v29,
https://www.txdot.gov/content/dam/docs/division/trf/crash-records/automated-interface-guide-for-public-and-standard-extracts-v29.pdf

One request gives one password-protected zip with eight CSV files named
extract_public_{dateTime}_{extractType}_{dateFilter}_{locationFilter}.csv (crash, unit, person, primaryperson, charges,
damages, endorsements, restrictions, lookup). Unzip it (with the extract password) into a folder and pass the folder;
several requests (one per year) may share the folder. `Crash_ID` links every file. The person and primaryperson files
both carry people (primaryperson = drivers, pedestrians, cyclists; person = everyone else), so severity reads both.

Each crash comes out in the shared shape CCRS normalizes to (collision_id, datetime, lat, lon, primary_road, ...) plus
both CRIS location sets: what the officer reported (street + intersecting street + block, or highway + reference marker,
offset from either) and what TxDOT's locator derived (highway, control-section-milepoint, DFO, reference marker
displacement, street name). Severity: per-person KABCO from Prsn_Injry_Sev_ID, crash level in KABCUO.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

from .ca_ccrs import SEVERITY_ORDER, parse_dt

SPEC_URL = "https://www.txdot.gov/content/dam/docs/division/trf/crash-records/public-extract-file-specification.xlsx"
FILE = re.compile(r"^extract_public_\d+_(crash|unit|person|primaryperson|lookup)_", re.I)

# INJRY_SEV_LKP / CRASH_SEV_LKP (same ids both): 4 fatal, 1 suspected serious, 2 suspected minor, 3 possible,
# 5 not injured, 0 unknown (MMUCC wording from 2018-01-01; the ids did not change)
KABCO = {"4": "K", "1": "A", "2": "B", "3": "C", "5": "O"}
# RWY_SYS_LKP (the officer's roadway system) -> the abbreviation TxDOT's own highway names use
RWY_SYS = {"1": "IH", "2": "US", "3": "SH", "4": "FM", "5": "RR", "6": "RM", "7": "BI", "8": "BU", "9": "BS",
           "10": "BF", "11": "SL", "12": "TOLL", "13": "ALT", "14": "SPUR", "15": "CR", "16": "PR"}
FREEWAY_FUNC_SYS = {"1", "11", "12"}       # FUNC_SYS_LKP: rural interstate, urban IH, urban other freeway
BAD = {"", "NOT REPORTED", "UNKNOWN", "NO DATA", "N/A", "NONE"}
TX_LAT, TX_LON = (25.8, 36.6), (-106.7, -93.5)
UOM_FT = {"F": 1.0, "FT": 1.0, "FEET": 1.0, "M": 5280.0, "MI": 5280.0, "MILES": 5280.0}
# Lookup tables needed to decode a crash, by the crash column; the lookup CSV's ColumnName is matched against both.
# shortcut: the spec doesn't show ColumnName values (only "Lookup Column Name"); confirm on the first real file.
LOOKUP = {"fhe_collsn_id": ("FHE_COLLSN_ID", "COLLSN_ID"), "light_cond_id": ("LIGHT_COND_ID",),
          "wthr_cond_id": ("WTHR_COND_ID",), "surf_cond_id": ("SURF_COND_ID",), "city_id": ("CITY_ID",),
          "cnty_id": ("CNTY_ID", "CRIS_CNTY_ID")}


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            yield {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}   # headers in any case


def _files(folder: Path) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(Path(folder).glob("*.csv")):
        m = FILE.match(p.name)
        if m:
            out[m.group(1).lower()].append(p)
    if not out.get("crash"):
        raise FileNotFoundError(f"no extract_public_*_crash_*.csv in {folder} (unzip the CRIS extract there)")
    return out


def _num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


_CLOCK = re.compile(r"^(\d{1,2}):(\d{2})(?::\d{2})?\s*([AP]M)?$", re.I)


def _clock(t: str) -> tuple[int | None, int]:
    """'02:50 PM' (seen in CRIS copies) or '14:50[:00]' (spec: TIME, 8 characters) -> (14, 50); (None, 0) if neither."""
    m = _CLOCK.match(t.strip())
    if not m:
        return None, 0
    h = int(m[1]) % 12 + (12 if (m[3] or "").upper() == "PM" else 0) if m[3] else int(m[1])
    return (h, int(m[2])) if 0 <= h <= 23 else (None, 0)


def _gps(lat, lon) -> tuple[float, float] | None:
    a, b = _num(lat), _num(lon)
    if a is None or b is None or not (TX_LAT[0] <= a <= TX_LAT[1] and TX_LON[0] <= b <= TX_LON[1]):
        return None
    return a, b


def _street(r: dict, sec: str = "") -> str | None:
    """The officer's road: prefix + name + suffix, or the highway (roadway system + number + suffix) when no name."""
    name = r.get(f"rpt{sec}_street_name", "")
    if name.upper() not in BAD:
        parts = (r.get(f"rpt{sec}_street_pfx", ""), name, r.get(f"rpt{sec}_street_sfx", ""))
        return " ".join(p for p in parts if p and p.upper() not in BAD)
    num = r.get(f"rpt{sec}_hwy_num", "")
    if not num:
        return None
    sys_id = r.get(f"rpt{sec}_rdwy_sys_id") if sec else r.get("rpt_rdwy_sys_id")
    return f"{RWY_SYS.get(sys_id, 'HWY')} {num.lstrip('0') or num}{r.get(f'rpt{sec}_hwy_sfx', '')}"


def _hwy(sys_, nbr, sfx) -> str | None:
    """TxDOT locator highway: IH + 0035 + E -> 'IH 35E'."""
    n = _num(nbr)
    return f"{sys_} {int(n)}{sfx}" if sys_ and n is not None else None


def load_lookups(paths: list[Path]) -> dict[tuple[str, str], str]:
    out = {}
    for p in paths:
        for r in _rows(p):
            out[(r.get("columnname", "").upper(), r.get("id", ""))] = r.get("description", "")
    return out


def _decode(lk: dict, col: str, value: str) -> str | None:
    if not value:
        return None
    for name in (col.upper(), *LOOKUP.get(col, ())):
        if (name, value) in lk:
            return lk[(name, value)]
    return value                                   # no lookup row: keep the id rather than lose it


def crash_record(r: dict, lk: dict) -> dict:
    """One crash-file row (lower-cased headers) -> the shared crash shape, without severity (needs the persons)."""
    date, year, _ = parse_dt(r.get("crash_date", ""))
    hour, minute = _clock(r.get("crash_time", ""))
    located, officer = _gps(r.get("latitude"), r.get("longitude")), _gps(r.get("rpt_latitude"), r.get("rpt_longitude"))
    pt = located or officer
    dist = _num(r.get("rpt_ref_mark_offset_amt"))
    ft = dist * UOM_FT.get(r.get("rpt_ref_mark_dist_uom", "").upper(), 1.0) if dist is not None else None
    marker = r.get("rpt_ref_mark_nbr") or None
    s = lambda k: r.get(k) or None
    return {
        "collision_id": r["crash_id"],
        "case_id": s("case_id"),
        "datetime": f"{date}T{hour:02d}:{minute:02d}" if date and hour is not None else date,
        "date": date, "year": year, "hour": hour,
        "lat": pt[0] if pt else None, "lon": pt[1] if pt else None,
        "gps_source": "txdot_locator" if located else "officer" if officer else None,
        "located": r.get("located_fl") == "Y",
        # officer-reported location (CR-3). The offset is from the reference marker when one is given, else from
        # the intersection with the secondary road (spec: "Distance from Intersection or Reference Marker")
        "primary_road": _street(r), "secondary_road": _street(r, "_sec"),
        "block_number": s("rpt_block_num"),
        "at_intersection": r.get("at_intrsct_fl") == "Y",
        "offset_ft": None if marker else ft, "offset_dir": None if marker else s("rpt_ref_mark_dir"),
        "ref_marker": marker, "ref_marker_offset_ft": ft if marker else None,
        "ref_marker_dir": s("rpt_ref_mark_dir") if marker else None,
        # TxDOT locator (system-generated)
        "on_system": r.get("onsys_fl") == "Y",
        "highway": _hwy(r.get("hwy_sys"), r.get("hwy_nbr"), r.get("hwy_sfx", "")),
        "highway_2": _hwy(r.get("hwy_sys_2"), r.get("hwy_nbr_2"), r.get("hwy_sfx_2", "")),
        "control": s("control"), "section": s("section"), "milepoint": _num(r.get("milepoint")),
        "dfo": _num(r.get("dfo")),
        "txdot_ref_marker": s("ref_mark_nbr"), "txdot_ref_marker_displ": _num(r.get("ref_mark_displ")),
        "locator_street": s("street_name"), "locator_street_nbr": s("street_nbr"), "locator_street_2": s("street_name_2"),
        "aadt": int(_num(r.get("adt_curnt_amt")) or 0) or None, "aadt_year": s("adt_curnt_year"),
        "city_name": _decode(lk, "city_id", r.get("city_id") or r.get("rpt_city_id", "")),
        "county_code": s("cnty_id") or s("rpt_cris_cnty_id"),
        "county_name": _decode(lk, "cnty_id", r.get("cnty_id") or r.get("rpt_cris_cnty_id", "")),
        "killed": int(_num(r.get("death_cnt")) or 0),
        "injured": int(_num(r.get("tot_injry_cnt")) or 0),
        "crash_sev_id": s("crash_sev_id"),
        "collision_type": _decode(lk, "fhe_collsn_id", r.get("fhe_collsn_id", "")),
        "lighting": _decode(lk, "light_cond_id", r.get("light_cond_id", "")),
        "weather": _decode(lk, "wthr_cond_id", r.get("wthr_cond_id", "")),
        "surface": _decode(lk, "surf_cond_id", r.get("surf_cond_id", "")),
        "is_freeway": r.get("hwy_sys") == "IH" or r.get("func_sys_id") in FREEWAY_FUNC_SYS,
        "private_drive": r.get("private_dr_fl") == "Y",
        "txdot_reportable": r.get("txdot_rptable_fl") == "Y",
    }


def severity(crash: dict, person_kabco: list[str | None]) -> str:
    """Most severe outcome, counted once, in KABCUO. U = level unknown: CRIS 0 'UNKNOWN', or injured with no level."""
    if crash["killed"] > 0:
        return "K"
    levels = [k for k in person_kabco if k] + ([KABCO[crash["crash_sev_id"]]] if crash["crash_sev_id"] in KABCO else [])
    best = min(levels, key=SEVERITY_ORDER.index, default=None)
    if best is None:
        return "U" if crash["crash_sev_id"] == "0" or crash["injured"] > 0 else "O"
    return "U" if best == "O" and crash["injured"] > 0 else best


def read_extract(folder: Path) -> list[dict]:
    """Every crash in an unzipped CRIS public extract folder, with its persons, units and severity.
    shortcut: holds one extract's persons in memory (~130k rows for a large county-year); stream per year statewide."""
    files = _files(folder)
    lk = load_lookups(files.get("lookup", []))
    persons: dict[str, list[dict]] = defaultdict(list)
    for kind in ("primaryperson", "person"):
        for p in files.get(kind, []):
            for r in _rows(p):
                persons[r["crash_id"]].append({"unit": r.get("unit_nbr"), "person": r.get("prsn_nbr"),
                                               "type_id": r.get("prsn_type_id"), "primary": kind == "primaryperson",
                                               "kabco": KABCO.get(r.get("prsn_injry_sev_id", ""))})
    units: dict[str, list[dict]] = defaultdict(list)
    for p in files.get("unit", []):
        for r in _rows(p):
            units[r["crash_id"]].append({"unit": r.get("unit_nbr"), "desc_id": r.get("unit_desc_id"),
                                         "body_style_id": r.get("veh_body_styl_id"), "hit_run": r.get("veh_hnr_fl") == "Y"})
    out = []
    for p in files["crash"]:
        for r in _rows(p):
            c = crash_record(r, lk)
            ps, us = persons.get(c["collision_id"], []), units.get(c["collision_id"], [])
            c["persons"], c["units"] = ps, us
            c["severity"] = severity(c, [x["kabco"] for x in ps])
            # VEH_UNIT_DESC_LKP 3 pedalcyclist / 4 pedestrian; PRSN_TYPE_LKP 3, 4 the same, 5-6 motorcycle riders;
            # VEH_BODY_STYL_LKP 71 motorcycle, 90 police motorcycle
            c["ped"] = any(u["desc_id"] == "4" for u in us) or any(x["type_id"] == "4" for x in ps)
            c["bike"] = any(u["desc_id"] == "3" for u in us) or any(x["type_id"] == "3" for x in ps)
            c["motorcycle"] = any(u["body_style_id"] in ("71", "90") for u in us) or any(x["type_id"] in ("5", "6") for x in ps)
            out.append(c)
    return out
