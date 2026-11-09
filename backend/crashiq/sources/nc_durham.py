"""Durham, NC: City of Durham Vision Zero "All Durham Crashes" layer, 2016-2025, TEAAS fields, one row per person.

Rows are people (and units); grouped here by the statewide TEAAS Crash_ID into crashes with persons. Road names are
TEAAS style, without street type ("FAYETTEVILLE", "I 85"), so the locator's relaxed tier is the one that matches.
The layer sits behind the city's Vision Zero dashboard: it isn't in the Durham open data catalog and has no licence
text (A*: undocumented endpoint, licence unclear). DirFrom is mostly digits 1-6, not compass letters; kept raw.
Item: https://www.arcgis.com/home/item.html?id=cce39a051d34496498857046fde17f23
Standalone reader: not wired into the app.
"""

from __future__ import annotations

from typing import Iterable

from .nc_arcgis import coord, day_time, kabco_letter, query, text

LAYER = "https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/arcgis/rest/services/All_Durham_Crashes/FeatureServer/2"
COMPASS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}


def crashes(rows: Iterable[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for r in rows:
        cid = str(r["Crash_ID"])
        c = by_id.get(cid)
        if c is None:
            lat, lon = coord(r.get("Latitude"), r.get("Longitude"))
            try:
                off = float(r["DistMiles"]) * 5280 if r.get("DistMiles") not in (None, "") else None
            except ValueError:
                off = None
            d = text(r.get("DirFrom"))
            c = by_id[cid] = {
                "collision_id": cid, "report_number": text(r.get("LocalUseCode")),
                "datetime": day_time(r.get("Date"), r.get("Time")), "lat": lat, "lon": lon,
                "map_method": text(r.get("MapMethod")),
                "primary_road": text(r.get("OnRoad")), "secondary_road": text(r.get("FromRoad")),
                "toward_road": text(r.get("TowardRoad")),
                "offset_ft": off or None, "offset_dir": d if off and d in COMPASS else None, "dir_from_raw": d,
                "gis_route": text(r.get("GIS_RteTxt")), "gis_milepost": r.get("GIS_Milepost"),
                "city_name": text(r.get("CityName")), "county_name": text(r.get("CountyName")), "county_code": "37063",
                "severity": kabco_letter(r.get("CrashSeverity")) or ("U" if text(r.get("CrashSeverity")) else None),
                "killed": r.get("NumFatalities"),
                "injured": sum(int(r.get(f) or 0) for f in ("NumA_Injuries", "NumB_Injuries", "NumC_Injuries")),
                "collision_type": text(r.get("CrashType")), "lighting": text(r.get("LightCondition")),
                "weather": text(r.get("Weather")), "surface": text(r.get("RoadCondition")),
                "traffic_control": text(r.get("TrafControlDevice")), "road_class": text(r.get("Road_Class")),
                "is_freeway": (text(r.get("OnRoad")) or "").upper().startswith("I "),
                "persons": [], "_seen": set(),
            }
        key = (r.get("UnitNum"), r.get("PersonNum"), r.get("PersonType"))
        if key not in c["_seen"]:                      # the layer repeats a person once per joined row
            c["_seen"].add(key)
            inj = text(r.get("PersonInjury"))
            c["persons"].append({"person_type": text(r.get("PersonType")), "unit": r.get("UnitNum"),
                                 "injury": inj, "kabco": kabco_letter(inj) or ("U" if inj else None),
                                 "age": r.get("Age"), "vehicle_type": text(r.get("vehicle_type"))})
    for c in by_id.values():
        del c["_seen"]
    return list(by_id.values())


def fetch(where: str = "1=1") -> list[dict]:
    """e.g. fetch("Date >= DATE '2025-01-01'")."""
    return crashes(query(LAYER, where, oid="OBJECTID_1"))
