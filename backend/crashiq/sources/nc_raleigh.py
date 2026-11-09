"""Raleigh, NC: Raleigh Police crash reports (DMV-349 form), Open Data Raleigh, 2015-present, updated daily.

Crashes (layer 0) and Persons (layer 1) share `key_crash`. Coordinates are typed by the officer; the city publishes
only crashes whose point falls in Raleigh, so the GPS share is 100% by construction (not the state's rate).
Since Oct 2024 the table no longer fills weather, road class, road feature, traffic control or relation to road.
Terms: Open Raleigh Data Policy + RPD disclaimer (no explicit licence; the city may require use to stop).
Item: https://www.arcgis.com/home/item.html?id=3f503c43a0bd4490be7dec17650bcda9
Standalone reader: not wired into the app (state-pack seam, issue #19).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable

from .nc_arcgis import EASTERN, coord, query, text

SERVICE = "https://utility.arcgis.com/usrsvcs/servers/3f503c43a0bd4490be7dec17650bcda9/rest/services/Crash_Reports/FeatureServer"
CRASHES, PERSONS = SERVICE + "/0", SERVICE + "/1"
SEVERITY_ORDER = "KABCUO"   # NC: U = injury unknown (NCDOT's own crash-severity code), O = no injury

INJURY = {"KILLED": "K", "A TYPE INJURY (DISABLING)": "A", "B TYPE INJURY (EVIDENT)": "B",
          "C TYPE INJURY (POSSIBLE)": "C", "NO INJURY": "O", "UNKNOWN": "U"}
FREEWAY = re.compile(r"^\s*(I|INTERSTATE)[- ]?\d")


def _num(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def when(r: dict) -> str | None:
    """Since October 2024 `DateOfCrash` holds local wall time labelled UTC (before: true UTC). `Crash_Date_Hour`
    is local either way, so it says which reading is right, row by row."""
    ms = r.get("DateOfCrash")
    if ms in (None, ""):
        return None
    utc = datetime.fromtimestamp(ms / 1000, timezone.utc)
    east = utc.astimezone(EASTERN)
    return (east if east.hour == r.get("Crash_Date_Hour") else utc).replace(tzinfo=None).isoformat()


def crash(r: dict) -> dict:
    lat, lon = coord(r.get("LocationLatitude"), r.get("LocationLongitude"))
    feet, miles = r.get("LocationFeetFromRoad"), r.get("LocationMilesFromRoad")
    try:
        off = float(feet) if text(feet) else float(miles) * 5280 if text(miles) else None
    except ValueError:
        off = None
    at = (text(r.get("LocationAtFromIndicator")) or "").upper() == "AT"
    k, a, b, c, u = (_num(r.get(f)) for f in ("killed", "type_a_injury", "type_b_injury", "type_c_injury",
                                               "injury_unknown"))
    primary = text(r.get("LocationRoadNameOn"))
    return {
        "collision_id": str(r["key_crash"]), "report_number": text(r.get("LocalUse")),
        "datetime": when(r), "lat": lat, "lon": lon,
        "primary_road": primary, "secondary_road": text(r.get("LocationRoadNameAt")),
        "toward_road": text(r.get("LocationRoadNameTo")),
        "offset_ft": None if at else off, "offset_dir": None if at else text(r.get("LocationDirectionFromRoad")),
        "city_name": text(r.get("LocationCity")), "county_code": None,   # not in the table; Raleigh spans Wake (37183) and Durham
        "killed": k, "injured": a + b + c, "injury_unknown": u,
        "severity": "K" if k else "A" if a else "B" if b else "C" if c else "U" if u else "O",
        "collision_type": text(r.get("FirstHarmfulEvent")), "most_harmful": text(r.get("MostHarmfulEvent")),
        "lighting": None, "surface": None,                                # not published by Raleigh
        "weather": text(r.get("WeatherCondition1")), "road_feature": text(r.get("RoadFeature")),
        "traffic_control": text(r.get("TrafficControlType")),
        "relation_to_road": text(r.get("LocationRelationToRoad")),
        "is_freeway": (text(r.get("RoadClassification")) or "").upper().startswith("INTERSTATE")
                      or bool(FREEWAY.match(primary or "")),
        "pedestrians": _num(r.get("pedestrians")), "pedalcyclists": _num(r.get("pedalcyclists")),
    }


def person(r: dict) -> dict:
    inj = text(r.get("Injury"))
    return {"collision_id": str(r["key_crash"]), "person_type": text(r.get("PersonType")),
            "injury": inj, "kabco": INJURY.get((inj or "").upper()), "age": text(r.get("Age")),
            "vehicle_type": text(r.get("VehicleType")), "alcohol_suspected": text(r.get("AlcoholSuspected"))}


def crash_severity(c: dict, persons: Iterable[dict]) -> str:
    """Most severe outcome over the crash's people, never below what the crash row's counts say."""
    best = c["severity"]
    for p in persons:
        k = p.get("kabco")
        if k and SEVERITY_ORDER.index(k) < SEVERITY_ORDER.index(best):
            best = k
    return best


def fetch_crashes(where: str) -> list[dict]:
    """e.g. fetch_crashes("Crash_Date_Year=2025")."""
    return [crash(r) for r in query(CRASHES, where)]


def fetch_persons(collision_ids: list[str], chunk: int = 200) -> list[dict]:
    out = []
    for i in range(0, len(collision_ids), chunk):
        ids = ",".join(str(int(x)) for x in collision_ids[i:i + chunk])   # int(): ids go into SQL
        out += [person(r) for r in query(PERSONS, f"key_crash IN ({ids})")]
    return out
