"""Kansas crash source: KDOT "Crashes in Kansas", an open ArcGIS layer (KanPlan), no login.

One row per crash, the past ten years plus the current one (2016 to now, about 55-63k a year), KDOT's point on
every row (the layer holds only crashes KDOT could locate: about 91-95% of reported crashes), per-crash counts of
people killed (K), disabling (A), non-incapacitating (B) and possible (C) injuries. There are NO street names, no
cross street and no person or vehicle tables, so `primary_road`/`secondary_road` are always None.

Licence: no open licence; KDOT's item notice (23 USC 407, no warranty) and the KDOT Website Terms of Use apply
(research_notes/ks-2026-11-08/ks-import.md § licence). Plugged in by crashiq/statepacks/ks.py (`fetch_contract`).
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import date as _date
from pathlib import Path

LAYER = "https://kanplan.ksdot.gov/arcgis_web_adaptor/rest/services/Transportation/Accidents/FeatureServer/0"
PAGE = 2000                                    # well under the layer's maxRecordCount (25,000)
KS_LAT, KS_LON = (36.9, 40.1), (-102.1, -94.5)  # Kansas's extent with a small margin
BOXES = Path(__file__).resolve().parents[3] / "data" / "reference" / "county_boxes_ks.json"
FIELDS = ("OBJECTID,ACCIDENT_KEY,REPORT_IMAGE_LINK,LATITUDE,LONGITUDE,ACC_COUNTY,ACC_CITY,ACC_YEAR,ACC_MONTH_NUMBER,"
          "ACC_DAY_OF_MONTH,ACC_HOUR,ACC_SEVERITY,FATALITIES,DISABLING_INJURIES,NON_INCAPACITATING_INJURIES,"
          "POSSIBLE_INJURIES,CWOV_FHE_ACC_TYPE,ACCIDENT_CLASS_FHE_DESC,LIGHT_CONDITIONS_DESC,WEATHER_CONDITIONS_DESC,"
          "ON_ROAD_TYPE,TURNPIKE_INVOLVED,STATE_SYSTEM_IND,PEDESTRIAN_ACCS,PEDAL_CYCLIST_ACCS,MOTORCYCLE_ACCS,"
          "LARGE_TRUCK_ACCS,ON_ROAD_SPEED_LIMIT")
FREEWAY_ROADS = {"Interstate Highway", "Ramp"}  # plus the Turnpike flag; a US/K route built as a freeway isn't flagged
# KDOT words -> the CCRS words the profile and the collision diagram read; any other type keeps KDOT's own words
CCRS_TYPE = {"REAR END": "REAR END", "ANGLE - SIDE IMPACT": "BROADSIDE", "HEAD ON": "HEAD-ON",
             "SIDESWIPE: SAME DIRECTION": "SIDE SWIPE", "SIDESWIPE: OPPOSITE DIRECTION": "SIDE SWIPE",
             "COLL W FIXED OBJECT": "HIT OBJECT", "COLL W PEDESTRIAN": "VEHICLE/PEDESTRIAN", "OVERTURNED": "OVERTURNED"}
CCRS_LIGHT = {"DARK--STREET LIGHTS ON": "DARK - STREET LIGHTS", "DARK--NO STREET LIGHTS": "DARK - NO STREET LIGHTS"}


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _county_fips() -> dict:
    """'SEDGWICK' -> '20173', from the Census names in county_boxes_ks.json (all 105 KDOT names match, 2026-11-08)."""
    boxes = json.loads(BOXES.read_text())["counties"]
    return {v["name"].upper().removesuffix(" COUNTY"): k for k, v in boxes.items()}


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and KS_LAT[0] <= lat <= KS_LAT[1] and KS_LON[0] <= lon <= KS_LON[1]


def severity(a: dict) -> str:
    """Worst person from KDOT's counts; with no count, KDOT's crash severity (FATAL -> K, INJURY -> U, else O)."""
    for k, f in zip("KABC", ("FATALITIES", "DISABLING_INJURIES", "NON_INCAPACITATING_INJURIES", "POSSIBLE_INJURIES")):
        if _int(a.get(f)):
            return k
    return {"FATAL": "K", "INJURY": "U"}.get(a.get("ACC_SEVERITY"), "O")


def contract_record(a: dict, fips: dict) -> dict:
    """One layer attributes dict -> the shared crash dict (packs.check_crash)."""
    s = lambda v: (str(v).strip() or None) if v is not None else None
    lat, lon = a.get("LATITUDE"), a.get("LONGITUDE")
    has = plausible(lat, lon)
    try:
        d = _date(int(a["ACC_YEAR"]), int(a["ACC_MONTH_NUMBER"]), int(a["ACC_DAY_OF_MONTH"]))
    except (TypeError, ValueError, KeyError):
        d = None                                  # ~480 of 607k rows have no date: the core drops them as bad dates
    hour = _int(a["ACC_HOUR"]) if s(a.get("ACC_HOUR")) and s(a["ACC_HOUR"]).isdigit() else None
    vv, fhe = s(a.get("CWOV_FHE_ACC_TYPE")), s(a.get("ACCIDENT_CLASS_FHE_DESC"))
    kind = vv if fhe == "COLL W OTHER MOTOR VEHICLE" and vv else fhe   # vehicle-vehicle crashes carry their manner
    light = s(a.get("LIGHT_CONDITIONS_DESC"))
    sev = severity(a)
    return {"crash_id": str(a["ACCIDENT_KEY"]), "report_version": 0, "deleted": False,
            "preliminary": bool(d and d.year >= _date.today().year),   # the current year is still arriving
            "date": d.isoformat() if d else "", "year": d.year if d else None, "hour": hour,
            "day_of_week": d.strftime("%A") if d else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,   # no street names
            "city": s(a.get("ACC_CITY")), "county_code": s(a.get("ACC_COUNTY")),
            "county_fips": fips.get(s(a.get("ACC_COUNTY")) or ""), "state": "KS",
            "is_freeway": s(a.get("ON_ROAD_TYPE")) in FREEWAY_ROADS or s(a.get("TURNPIKE_INVOLVED")) == "Y",
            "killed": _int(a.get("FATALITIES")),
            "injured": sum(_int(a.get(f)) for f in ("DISABLING_INJURIES", "NON_INCAPACITATING_INJURIES",
                                                    "POSSIBLE_INJURIES")),
            "severity": sev, "severity_reported": s(a.get("ACC_SEVERITY")),
            "severity_mismatch": {"K": "FATAL", "O": "PROPERTY DAMAGE ONLY"}.get(sev, "INJURY") != s(a.get("ACC_SEVERITY")),
            "ped": _int(a.get("PEDESTRIAN_ACCS")) > 0, "bike": _int(a.get("PEDAL_CYCLIST_ACCS")) > 0,
            "ebike": False, "escooter": False, "motorcycle": _int(a.get("MOTORCYCLE_ACCS")) > 0,
            "heavy_truck": _int(a.get("LARGE_TRUCK_ACCS")) > 0, "parties": [],
            "collision_type": CCRS_TYPE.get(kind, kind), "lighting": CCRS_LIGHT.get(light, light),
            "weather": s(a.get("WEATHER_CONDITIONS_DESC")), "surface": None,
            "report_number": s(a.get("REPORT_IMAGE_LINK")), "road_type": s(a.get("ON_ROAD_TYPE")),
            "state_system": s(a.get("STATE_SYSTEM_IND")) == "Y", "speed_limit": a.get("ON_ROAD_SPEED_LIMIT")}


def _get(where: str, last: int, opener) -> list[dict]:
    q = {"where": f"({where}) AND OBJECTID>{last}", "outFields": FIELDS, "orderByFields": "OBJECTID",
         "resultRecordCount": PAGE, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(LAYER + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"KDOT crash layer query error: {body['error']}")
    return [f["attributes"] for f in body.get("features", [])]


def fetch_raw(where: str, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every layer row matching an ArcGIS `where`, paged by OBJECTID; cached as raw JSON per `where`."""
    cache = cache_dir / f"ks_kdot_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    raw, last = [], 0
    while True:
        batch = _get(where, last, opener)
        raw += batch
        if len(batch) < PAGE:
            break
        last = batch[-1]["OBJECTID"]
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return raw


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years. Every published row has a point (607,257 of
    607,257 on 2026-11-08); crashes KDOT couldn't locate aren't published at all."""
    s, w, n, e = box
    yrs = ", ".join(f"'{y}'" for y in years)
    where = (f"LATITUDE >= {s:.6f} AND LATITUDE <= {n:.6f} AND LONGITUDE >= {w:.6f} AND LONGITUDE <= {e:.6f} "
             f"AND ACC_YEAR IN ({yrs})")
    fips = _county_fips()
    rows = [contract_record(a, fips) for a in fetch_raw(where, cache_dir, opener)]
    have = {r["year"] for r in rows}
    out = [r for r in rows if r["county_fips"]]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "no_county": len(rows) - len(out),
                         "severity_differs_from_kdot": sum(r["severity_mismatch"] for r in rows),
                         "not_published": "KDOT publishes only crashes it could locate (about 91% of 2024's)"}}
