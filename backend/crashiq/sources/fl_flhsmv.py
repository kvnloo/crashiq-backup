"""Florida crash source: FLHSMV "Crash Facts" aggregated crash data (open download, no login).

https://www.flhsmv.gov/crash-facts/ posts one zip per quarter (e.g. "CrashData Q1.zip", 261 MB) holding one
'|'-delimited CSV (3.3 GB) of the preceding three full years plus the completed months of the current year. Each row
is one person or vehicle of a crash: crash columns first, then vehicle, then person (data dictionary:
https://www.flhsmv.gov/wp-content/uploads/Automated%20Crash%20Facts%20Report%20Dict.xlsx). Crash Key links the rows.

It has GPS (about 75% of crashes) and KABCO per person, but no street names, so crashes without GPS cannot be placed.
`read` streams the zip without extracting it and keeps only the crashes asked for (county / years).
Not wired into the app (state-pack seam, issue #19).
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Iterator

from .ca_ccrs import parse_dt
from .fl_s4 import FREEWAY_SYSTEMS, SEVERITY_ORDER, _num, _sq, plausible

# Person's Injury Severity / Crash Maximum Severity -> KABCO. FLHSMV counts only deaths within 30 days as fatal
# (dictionary: "non-traffic fatalities, people that die over 30 days after the crash, are considered a none").
KABCO = {"FATALWITHIN30DAYS": "K", "INCAPACITATING": "A", "NONINCAPACITATING": "B", "POSSIBLE": "C", "NONE": "O"}

C = {  # logical -> column header in the file
    "crash_id": "Crash Key", "codeable": "Crash Codeable Flag", "form": "Crash Form Type",
    "agency": "Crash Investigating Agency", "datetime": "Crash Date and Time", "county": "Crash County",
    "lat": "Crash Latitude", "lon": "Crash Longitude", "road_system": "Crash Road System Identifier",
    "intersection_type": "Crash Intersection Type", "first_harmful": "Crash First Harmful Event",
    "lighting": "Crash Light Condition", "weather": "Crash Weather Condition", "surface": "Crash Road Surface Condition",
    "collision_type": "Crash Manner of Collision", "max_severity": "Crash Maximum Severity",
    "vehicle_key": "Vehicle Key", "hit_run": "Vehicle Hit and Run Flag", "body_type": "Vehicle Body Type",
    "cmv": "Vehicle CMV Flag", "speed": "Vehicle Posted Speed", "person_key": "Person Key",
    "person_type": "Person Type", "injury": "Person's Injury Severity", "age": "Person's Age",
    "nonmotorist": "Non-Motorist Type",
}


def kabco(v) -> str | None:
    return KABCO.get(_sq(v))


def _open(path: Path):
    path = Path(path)
    if path.suffix.lower() == ".zip":
        z = zipfile.ZipFile(path)
        return io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8", errors="replace", newline="")
    return open(path, encoding="utf-8", errors="replace", newline="")


def _crash(first: dict, rows: list[dict]) -> dict:
    s = lambda k: (str(first.get(C[k]) or "").strip() or None)
    date, year, hour = parse_dt(first.get(C["datetime"]))
    lat, lon = _num(first.get(C["lat"])), _num(first.get(C["lon"]))
    has = plausible(lat, lon)
    persons, vehicles, hit_run = {}, set(), False
    nonmotorists = set()
    for r in rows:
        if (r.get(C["person_key"]) or "").strip():
            persons[r[C["person_key"]]] = kabco(r.get(C["injury"]))
            nm = _sq(r.get(C["nonmotorist"]))
            if nm:
                nonmotorists.add(nm)
        if (r.get(C["vehicle_key"]) or "").strip():
            vehicles.add(r[C["vehicle_key"]])
            hit_run |= _sq(r.get(C["hit_run"])) == "YES"
    levels = [k for k in persons.values() if k]
    sev = kabco(first.get(C["max_severity"]))
    best = min(levels, key=SEVERITY_ORDER.index) if levels else None
    if best and (sev is None or SEVERITY_ORDER.index(best) < SEVERITY_ORDER.index(sev)):
        sev = best
    return {
        "crash_id": s("crash_id"), "report_number": None,
        "date": date or "", "year": year, "hour": hour,
        "lat": lat if has else None, "lon": lon if has else None, "gps_source": "officer" if has else None,
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "primary_road": None, "secondary_road": None,          # not in this file: crashes without GPS can't be placed
        "offset_ft": None, "offset_dir": None,
        "city": None, "county_code": s("county"),
        "road_system": s("road_system"), "is_freeway": _sq(first.get(C["road_system"])) in FREEWAY_SYSTEMS,
        "intersection_type": s("intersection_type"), "first_harmful": s("first_harmful"),
        "collision_type": s("collision_type"), "lighting": s("lighting"), "weather": s("weather"),
        "surface": s("surface"),
        "hit_run": hit_run,
        "ped": any("PEDESTRIAN" in t for t in nonmotorists),
        "bike": any("BICYCL" in t for t in nonmotorists),
        "codeable": s("codeable") == "Yes", "form_type": s("form"), "agency": s("agency"),
        "vehicles": len(vehicles),
        # the max severity can name a person with no row of their own (Palm Beach 2025: 2 of 6 fatal crashes), so a
        # K/A/B/C crash counts at least one killed/injured
        "killed": max(levels.count("K"), int(sev == "K")),
        "injured": max(sum(k in "ABC" for k in levels), int(sev in ("A", "B", "C"))),
        "person_kabco": levels,
        "severity": sev,                                       # None = left blank on every row; the caller counts those
    }


def read(path: Path, county: str | None = None, years: set[int] | None = None) -> Iterator[dict]:
    """Crashes from the Crash Facts zip (or its CSV), optionally one county (as written, e.g. 'PALM BEACH') and years.
    Rows of one crash are grouped in memory per filtered crash only, so a county-year (~55k crashes) is cheap."""
    f = _open(path)
    r = csv.DictReader(f, delimiter="|")
    missing = [v for v in (C["crash_id"], C["datetime"], C["lat"], C["injury"]) if v not in (r.fieldnames or [])]
    if missing:
        raise ValueError(f"not a FLHSMV Crash Facts file: no column {missing}")
    groups: dict[str, list[dict]] = {}
    for row in r:
        if county and (row.get(C["county"]) or "").strip().upper() != county.upper():
            continue
        if years and (row.get(C["datetime"]) or "")[:4] not in {str(y) for y in years}:
            continue
        groups.setdefault(row[C["crash_id"]], []).append(row)
    f.close()
    for rows in groups.values():
        yield _crash(rows[0], rows)
