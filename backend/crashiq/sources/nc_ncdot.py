"""North Carolina statewide (NCDOT Traffic Safety Unit), the two record-level layers NCDOT publishes with no login.

- KA: fatal (K) and serious-injury (A) crashes on public roads, last 10 years (2016-2025 at 2026-11-07), ~54k rows,
  GPS (TEAAS-located: XY or route/milepost), on-road / from-road / toward-road with distance in miles and direction.
- NON_MOTORIST: every police-reported crash involving a pedestrian, cyclist or other non-motorist, 2007-2025,
  ~58k rows, GPS, KABCO for the crash, the non-motorist and the driver. No street names.
Both carry the statewide TEAAS Crash_ID and NCDOT's LRS route + milepost. Licence: NCDOT liability disclaimer only.
Items: https://www.arcgis.com/home/item.html?id=a9125212cca34f2eb321de3bb0f1b7f2 (KA),
       https://www.arcgis.com/home/item.html?id=11309c4876f844a593868e742143eca4 (non-motorist)
All other crashes are in TEAAS (agencies, planning organisations and researchers only). Standalone reader.
"""

from __future__ import annotations

from .nc_arcgis import coord, day_time, kabco_letter, query, text

ORG = "https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services"
KA = ORG + "/NC_FatalAndSeriousInjuryCrashes/FeatureServer/0"
NON_MOTORIST = ORG + "/NCDOT_NonMotoristCrashes/FeatureServer/0"


def _city(v) -> str | None:
    v = text(v)
    return None if v is None or v.upper() in ("RURAL", "NONE - RURAL CRASH") else v


def ka_crash(r: dict) -> dict:
    lat, lon = coord(r.get("Latitude"), r.get("Longitude"))
    try:
        off = float(r["Distance"]) * 5280 if r.get("Distance") not in (None, "") else None
    except ValueError:
        off = None
    return {
        "collision_id": str(r["Crash_ID"]), "datetime": day_time(r.get("Date"), r.get("Time")),
        "lat": lat, "lon": lon, "map_method": text(r.get("MapMethod")),
        "primary_road": text(r.get("On_Road")), "secondary_road": text(r.get("From_Road")),
        "toward_road": text(r.get("Toward_Roa")),
        "offset_ft": off or None, "offset_dir": text(r.get("Direction")) if off else None,
        "gis_route": text(r.get("GIS_RteTxt")), "gis_milepost": r.get("GIS_Milepo"),
        "city_name": _city(r.get("City")), "county_name": text(r.get("County_Nam")), "county_code": None,
        "severity": kabco_letter(r.get("Crash_Seve")), "killed": None, "injured": None,   # counts not published
        "collision_type": text(r.get("Crash_Type")), "lighting": text(r.get("Light_Cond")),
        "weather": text(r.get("Weather")), "surface": text(r.get("Road_Condi")),
        "vehicles": r.get("Num_Vehicl"), "non_motorists": r.get("Num_Non_Mo"),
        "is_freeway": (text(r.get("On_Road")) or "").upper().startswith("I "),
        "flags": {k: r.get(f) == "Y" for k, f in (("alcohol", "Alcohol_Re"), ("speed", "Speed_Rela"),
                  ("unbelted", "Unbelted_D"), ("motorcycle", "Motorcycle"), ("heavy_truck", "Heavy_Truc"))},
    }


def non_motorist_crash(r: dict) -> dict:
    lat, lon = coord(r.get("Latitude"), r.get("Longitude"))
    return {
        "collision_id": str(r["CrashID"]), "datetime": day_time(r.get("CrashDate"), r.get("CrashHour")),
        "lat": lat, "lon": lon, "primary_road": None, "secondary_road": None,
        "gis_route": text(r.get("GIS_Route")), "gis_milepost": r.get("GIS_Milepo"),
        "city_name": _city(r.get("City")), "county_name": text(r.get("County")), "county_code": None,
        "severity": kabco_letter(r.get("CrashSevr")) or "U", "killed": None, "injured": None,
        "collision_type": text(r.get("CrashType")), "crash_type_group": text(r.get("CrashTypGr")),
        "lighting": text(r.get("LightCond")), "weather": text(r.get("Weather")), "surface": text(r.get("RdConditio")),
        "road_class": text(r.get("RdClass")), "is_freeway": (text(r.get("RdClass")) or "") == "Interstate",
        "persons": [
            {"person_type": text(r.get("NM_Type")), "kabco": kabco_letter(r.get("NM_Inj")) or "U",
             "injury": text(r.get("NM_Inj")), "age": text(r.get("NM_Age"))},
            {"person_type": "Driver", "kabco": kabco_letter(r.get("DrvrInjury")) or "U",
             "injury": text(r.get("DrvrInjury")), "age": text(r.get("DrvrAge")),
             "vehicle_type": text(r.get("DrvrVehTyp"))},
        ],
    }


def fetch_ka(where: str = "1=1") -> list[dict]:
    return [ka_crash(r) for r in query(KA, where, oid="FID")]


def fetch_non_motorist(where: str = "1=1") -> list[dict]:
    """e.g. fetch_non_motorist("CrashYear=2025 AND County='Wake'")."""
    return [non_motorist_crash(r) for r in query(NON_MOTORIST, where, oid="FID")]
