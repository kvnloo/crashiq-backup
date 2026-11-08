"""New York City crash source: NYPD Motor Vehicle Collisions on NYC Open Data (crashes h9gi-nx95, persons f55k-p6yu).

- Police GPS on ~97% of 2025 crashes; street names as on/cross street, or a house address in `off_street_name`.
- Persons link to crashes by `collision_id`. Injury is only Injured / Killed / Unspecified (no A/B/C level), so
  person severity is K or U, and the crash severity is K, U (injured, level not reported) or O.
- Terms: NYC Open Data Terms of Use (data.cityofnewyork.us). Feeds pause at times: check max(crash_date).
Standalone: not wired into the app (state-pack seam, issue #19).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .ny_dmv import _get

CRASHES = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
PERSONS = "https://data.cityofnewyork.us/resource/f55k-p6yu.json"
BOROUGH_COUNTY = {"MANHATTAN": "061", "BROOKLYN": "047", "QUEENS": "081", "BRONX": "005", "STATEN ISLAND": "085"}
_INT = ("number_of_persons_injured", "number_of_persons_killed", "number_of_pedestrians_injured",
        "number_of_pedestrians_killed", "number_of_cyclist_injured", "number_of_cyclist_killed",
        "number_of_motorist_injured", "number_of_motorist_killed")
_VEH = ("vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code_3", "vehicle_type_code_4", "vehicle_type_code_5")
_CF = tuple(f"contributing_factor_vehicle_{i}" for i in range(1, 6))
PERSON_FIELDS = ("collision_id", "person_id", "vehicle_id", "person_type", "person_injury", "person_age", "ped_role",
                 "ped_action", "ped_location", "bodily_injury", "complaint", "position_in_vehicle", "person_sex")


def _pull(url: str, where: str, select: str, order: str, page: int = 50000) -> list[dict]:
    rows, offset = [], 0
    while True:
        batch = _get(url, {"$select": select, "$where": where, "$order": order, "$limit": page, "$offset": offset})
        rows += batch
        if len(batch) < page:
            return rows
        offset += page


def _clean(v) -> str | None:
    return re.sub(r"\s+", " ", str(v)).strip() or None if v is not None else None


def _int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def plausible(lat, lon) -> bool:
    """Inside the five boroughs' box; 0/0 and blanks are 'no GPS'."""
    return lat is not None and lon is not None and 40.4 < lat < 41.0 and -74.3 < lon < -73.6


def crash_record(raw: dict) -> dict:
    g = lambda k: _clean(raw.get(k))
    try:
        lat, lon = float(raw["latitude"]), float(raw["longitude"])
    except (KeyError, TypeError, ValueError):
        lat = lon = None
    has = plausible(lat, lon)
    on, cross, off = g("on_street_name"), g("cross_street_name"), g("off_street_name")
    n = {k: _int(raw.get(k)) for k in _INT}
    killed, injured = n["number_of_persons_killed"], n["number_of_persons_injured"]
    borough = g("borough")
    return {
        "collision_id": str(raw.get("collision_id")),
        "datetime": f"{(raw.get('crash_date') or '')[:10]} {raw.get('crash_time') or ''}".strip(),
        "date": (raw.get("crash_date") or "")[:10],
        "time": raw.get("crash_time"),
        "lat": lat if has else None,
        "lon": lon if has else None,
        "bad_coords": lat is not None and (lat, lon) != (0.0, 0.0) and not has,
        "primary_road": on,
        # an off-street crash gives a house address ('1501 WESTCHESTER AVENUE'); the locator's address tier reads it
        "secondary_road": cross or off,
        "on_street": on, "cross_street": cross, "off_street": off,
        "borough": borough,
        "city_name": "NEW YORK",
        "county_code": BOROUGH_COUNTY.get(borough or ""),     # 3-digit county FIPS, None when NYPD left borough blank
        "zip_code": g("zip_code"),
        "killed": killed,
        "injured": injured,
        "ped_killed": n["number_of_pedestrians_killed"], "ped_injured": n["number_of_pedestrians_injured"],
        "bike_killed": n["number_of_cyclist_killed"], "bike_injured": n["number_of_cyclist_injured"],
        "severity": "K" if killed else ("U" if injured else "O"),
        "contributing_factors": [x for x in (g(k) for k in _CF) if x and x.upper() != "UNSPECIFIED"],
        "vehicle_types": [x for x in (g(k) for k in _VEH) if x],
        "vehicles": sum(1 for k in _VEH if g(k)),
        "collision_type": None, "lighting": None, "weather": None, "surface": None,   # not published by NYPD
        "is_freeway": None,                                                        # no flag in the source
    }


def person_kabco(person_injury) -> str | None:
    """Killed -> K, Injured -> U (NYPD publishes no A/B/C level), anything else -> None (not injured)."""
    return {"KILLED": "K", "INJURED": "U"}.get(str(person_injury or "").strip().upper())


def person_record(raw: dict) -> dict:
    p = {k: _clean(raw.get(k)) for k in PERSON_FIELDS}
    p["kabco"] = person_kabco(p["person_injury"])
    return p


def severity(crash: dict, persons: list[dict]) -> str:
    """Most severe outcome, counted once, in KABCUO: the crash counts and its persons agree or the worse one wins."""
    codes = {p["kabco"] for p in persons} | {crash["severity"]}
    return next(k for k in "KABCUO" if k in codes)


def fetch(start: str, end: str, cache_dir: Path, persons: bool = True) -> tuple[list[dict], dict[str, list[dict]]]:
    """Crashes (and persons by collision_id) with crash_date in [start, end] (YYYY-MM-DD), cached as JSON."""
    where = f"crash_date between '{start}T00:00:00' and '{end}T23:59:59'"
    key = hashlib.sha1(f"{where}|{persons}".encode()).hexdigest()[:10]
    cache = cache_dir / f"ny_nyc_{key}.json"
    if cache.exists():
        data = json.loads(cache.read_text())
    else:
        data = {"crashes": _pull(CRASHES, where, "*", "collision_id"),
                "persons": _pull(PERSONS, where, ",".join(PERSON_FIELDS), "unique_id") if persons else []}
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data))
    crashes = [crash_record(r) for r in data["crashes"]]
    by_crash: dict[str, list[dict]] = {}
    for r in data["persons"]:
        p = person_record(r)
        by_crash.setdefault(p["collision_id"], []).append(p)
    for c in crashes:
        c["severity"] = severity(c, by_crash.get(c["collision_id"], []))
    return crashes, by_crash
