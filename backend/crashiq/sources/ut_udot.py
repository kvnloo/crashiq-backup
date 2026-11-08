"""Utah crash source: UDOT's public "Utah Crash Locations" FeatureServer (UPlan / ArcGIS Online), no login.

One layer per year (2019 on, named "2024 Crash Locations"), one row per crash, refreshed nightly: a point (asked for in
WGS84), the crash-level KABCO in words (crash_severity_desc), counts of people at UDOT's levels 5-2 (number_fatalities,
number_four_injuries = A, number_three = B, number_two = C), the main road ("I-15", "Bangerter Highway Southbound",
or a house address "6844 S HIGHLAND DR"), a location sentence with the cross street ("I-15, at 249 Feet S of 700
South, ..."), functional class, light, weather, surface, manner of collision and yes/no flags (pedestrian, bicyclist,
motorcycle, commercial vehicle, DUI, speed). No person or vehicle tables are public (those are in UDOT's Numetric
app, which needs a login).

crash_datetime is real UTC (the 2025 layer runs 2025-01-01T07:06Z to 2025-12-31T06:59Z), so it's converted to Utah
time before the date and hour are taken.

Licence: the item's terms say the data "is for informational purposes only and must be field verified prior to being
used on a project", and that it "is protected under 23 USC 407"; no reuse grant (research_notes/ut-2026-11-08).
Wired into the app through statepacks/ut.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from crashiq.packs import REF

SERVICE = "https://services.arcgis.com/pA2nEVnB6tquxgOW/arcgis/rest/services/Utah_Crash_Locations/FeatureServer"
PAGE = 2000                                        # the service's maxRecordCount
UT_LAT, UT_LON = (36.9, 42.1), (-114.1, -108.9)   # Utah with a small margin
UTAH = ZoneInfo("America/Denver")

SEVERITY = {"Fatal": "K", "Suspected Serious Injury": "A", "Suspected Minor Injury": "B", "Possible Injury": "C",
            "No Injury/PDO": "O"}
_boxes = json.loads((REF / "county_boxes_ut.json").read_text())
FIPS = {v["name"].removesuffix(" County").upper(): k for k, v in _boxes["counties"].items()}
# UDOT manner of collision -> the CCRS words the profile and the collision diagram read
CCRS_TYPE = {"Front to Rear": "REAR END", "Angle": "BROADSIDE", "Head On (front-to-front)": "HEAD-ON",
             "Sideswipe Same Direction": "SIDE SWIPE", "Sideswipe Opposite Direction": "SIDE SWIPE",
             "Rear to Side": "BROADSIDE", "Rear to Rear": "REAR END", "Parked Vehicle": "OTHER", "Other": "OTHER"}
FREEWAY = {"Interstate", "Other Freeways and Expressways"}
CROSS = re.compile(r", at (\d+) Feet ([NSEW]) of ([^,]+)")


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and UT_LAT[0] <= lat <= UT_LAT[1] and UT_LON[0] <= lon <= UT_LON[1])


def collision_type(a: dict) -> str | None:
    yes = lambda k: a.get(k) == "Y"                                                     # noqa: E731
    if yes("pedestrian_involved") or yes("bicyclist_involved"):
        return "VEHICLE/PEDESTRIAN"
    m = a.get("manner_collision_desc")
    if m in CCRS_TYPE:
        return CCRS_TYPE[m]
    if yes("overturn_rollover"):
        return "OVERTURNED"
    if yes("collision_with_fixed_object"):
        return "HIT OBJECT"
    return "OTHER" if m else None


def contract_record(f: dict, preliminary: bool = False) -> dict:
    """One feature ({attributes, geometry} in WGS84) -> the shared crash dict (packs.check_crash)."""
    a, g = f["attributes"], f.get("geometry") or {}
    s = lambda v: (str(v).strip() or None) if v is not None else None                  # noqa: E731
    n = lambda k: int(a.get(k) or 0)                                                    # noqa: E731
    lat, lon = g.get("y"), g.get("x")
    has = plausible(lat, lon)
    when = datetime.fromisoformat(a["crash_datetime"]).astimezone(UTAH) if a.get("crash_datetime") else None
    sev = SEVERITY.get(s(a.get("crash_severity_desc")) or "")
    cross = CROSS.search(a.get("location_desc") or "")
    main = s(a.get("main_road_name"))
    county = s(a.get("county_name"))
    return {"crash_id": str(a["crash_id"]), "report_version": 0, "deleted": False, "preliminary": preliminary,
            "date": when.date().isoformat() if when else "", "year": when.year if when else None,
            "hour": when.hour if when else None, "day_of_week": when.strftime("%A") if when else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": main, "secondary_road": cross.group(3).strip() if cross else None,
            "offset_ft": float(cross.group(1)) if cross and cross.group(1) != "0" else None,
            "offset_dir": cross.group(2) if cross and cross.group(1) != "0" else None,
            "city": None, "county_code": county, "county_fips": FIPS.get((county or "").upper()), "state": "UT",
            "is_freeway": s(a.get("functional_class")) in FREEWAY,
            "killed": max(n("number_fatalities"), int(sev == "K")),
            "injured": max(n("number_four_injuries") + n("number_three_injuries") + n("number_two_injuries"),
                           int(sev in ("A", "B", "C"))),
            "severity": sev, "ped": a.get("pedestrian_involved") == "Y", "bike": a.get("bicyclist_involved") == "Y",
            "ebike": False, "escooter": False, "motorcycle": a.get("motorcycle_involved") == "Y",
            "heavy_truck": a.get("commercial_motor_veh_involved") == "Y", "parties": [],
            "collision_type": collision_type(a),
            "lighting": s(a.get("light_condition_desc")), "weather": s(a.get("weather_condition_desc")),
            "surface": s(a.get("roadway_surf_condition_desc")), "hit_run": a.get("hit_and_run") == "Y",
            "report_number": None, "location_desc": s(a.get("location_desc")),
            "functional_class": s(a.get("functional_class")), "junction": s(a.get("roadway_junct_feature_desc")),
            "dui": a.get("dui") == "Y", "speed_related": a.get("speed_related") == "Y"}


def _get(path: str, params: dict, opener) -> dict:
    req = urllib.request.Request(f"{SERVICE}{path}?" + urllib.parse.urlencode({**params, "f": "json"}),
                                 headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=180) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"UDOT crash service {path} error: {body['error']}")
    return body


def layers(opener=urllib.request.urlopen) -> dict[int, int]:
    """{year: layer id} from the service's layer names ("2024 Crash Locations")."""
    return {int(m.group(1)): lyr["id"] for lyr in _get("", {}, opener)["layers"]
            if (m := re.match(r"(\d{4}) Crash Locations", lyr["name"]))}


def _rows(layer: int, geo: dict, opener) -> list[dict]:
    raw, last = [], 0
    while True:
        b = _get(f"/{layer}/query", {"where": f"OBJECTID>{last}", **geo, "outFields": "*", "outSR": 4326,
                                     "orderByFields": "OBJECTID", "resultRecordCount": PAGE}, opener)
        batch = b.get("features", [])
        raw += batch
        if len(batch) < PAGE and not b.get("exceededTransferLimit"):
            return raw
        last = batch[-1]["attributes"]["OBJECTID"]


def fetch_raw(box, years: list[int], cache_dir: Path | None = None, opener=urllib.request.urlopen) -> dict:
    """{year: features with a point in the box (s, w, n, e)}, and the years with no layer; cached per query."""
    s, w, n, e = box
    geo = {"geometry": f"{w},{s},{e},{n}", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
           "spatialRel": "esriSpatialRelIntersects"}
    key = hashlib.sha1(json.dumps([geo, sorted(years)]).encode()).hexdigest()[:10]
    cache = cache_dir / f"ut_udot_{key}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    ids = layers(opener)
    raw = {"newest": max(ids), "missing": [y for y in years if y not in ids],
           "years": {str(y): _rows(ids[y], geo, opener) for y in years if y in ids}}
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return raw


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box in those years. The current year and the one before are preliminary
    (UDOT: "2025 numbers are preliminary and could change at any time"). Every row has a point, so none is read
    by county alone."""
    raw = fetch_raw(box, years, cache_dir, opener)
    out, rows = [], 0
    no_county = no_sev = 0
    for y, feats in raw["years"].items():
        for f in feats:
            rows += 1
            c = contract_record(f, preliminary=int(y) >= raw["newest"] - 1)
            if not c["county_fips"]:
                no_county += 1
            elif not c["severity"]:
                no_sev += 1
            else:
                out.append(c)
    return {"crashes": out, "years_missing": raw["missing"],
            "cleaning": {"source_rows": rows, "no_county": no_county, "no_severity": no_sev}}
