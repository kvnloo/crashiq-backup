"""New Mexico crash source: "Crashes Five Year 2020 - 2024", an open ArcGIS layer the City of Albuquerque publishes.

Every reported crash in Bernalillo County 2020-2024 (75,460 rows, checked 2026-11-08), "compiled by UNM's Geospatial
and Population Studies group on behalf of NMDOT ... provided AS IS from UNM/NMDOT". Statewide NMDOT crash data is
records-request only (UNM-GPS "will not release traffic crash data directly to end users"), so this covers ONE county:
a box outside Bernalillo gets every year back as missing (research_notes/nm-2026-11-08).

One row per crash: GPS on all but 132, officer's primary street + secondary street or landmark with distance and
direction, people killed and class A/B/C injured (KABCO from the counts), light, weather, road-user flags. No people,
vehicles or road surface. Columns are UNM's crash-level export (data dictionary Feb. 2026), so an NMDOT records-request
export uses the same names. Wired into the app by the NM plug-in (crashiq/statepacks/nm.py) through `fetch_contract`.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from . import from_epoch

LAYER = ("https://services.arcgis.com/CWv1abTnC3urn4bV/arcgis/rest/services/Crashes_Five_Year_2020_2024/"
         "FeatureServer/0")
PAGE = 2000                                    # the layer's maxRecordCount
# shortcut: the layer's years and county as read 2026-11-08; the City republishes a new five years, so re-point LAYER
LAYER_YEARS = range(2020, 2025)
COVERED = {"35001"}                            # Bernalillo County
NM_LAT, NM_LON = (31.3, 37.0), (-109.05, -103.0)
_TZ = ZoneInfo("America/Denver")               # DATETIME is a true instant (15:43 MST arrives as 22:43 UTC)
FIPS = {"BERNALILLO": "35001", "SANDOVAL": "35043"}   # the only two COUNTY values in the layer

BLANK = {"", "LEFT BLANK", "INVALID CODE", "UNKNOWN OR NOT REPORTED"}
CCRS_LIGHT = {"Dark-Lighted": "DARK - STREET LIGHTS", "Dark-Not Lighted": "DARK - NO STREET LIGHTS",
              "Dark-Unknown Lighting": "DARK - UNKNOWN STREET LIGHTS"}
# First harmful event (the 2020+ form; ~97% filled in 2024) -> CCRS words. The old CLASSIFICATION/ANALYSIS pair is
# "Left Blank" on 95% of 2024 rows and is only the fallback.
FHE_OBJECT = {"Pedestrian": "VEHICLE/PEDESTRIAN", "Parked MV": "PARKED MOTOR VEHICLE", "Overturn/Rollover": "OVERTURNED"}
FHE_IMPACT = {"Front-to-Rear": "REAR END", "Front-to-Side": "BROADSIDE", "Sideswipe": "SIDE SWIPE",
              "Front-to-Front": "HEAD-ON"}
CCRS_CLASS = {"Pedestrian": "VEHICLE/PEDESTRIAN", "Fixed Object": "HIT OBJECT", "Other (Object)": "HIT OBJECT",
              "Overturn/Rollover": "OVERTURNED", "Rollover": "OVERTURNED", "Parked Vehicle": "PARKED MOTOR VEHICLE"}
ANALYSIS = (("Rear End", "REAR END"), ("Sideswipe", "SIDE SWIPE"), ("Entering At Angle", "BROADSIDE"),
            ("From Opposite Direction/Both Going Straight", "HEAD-ON"))


def _s(v):
    v = str(v).strip() if v is not None else ""
    return None if v.upper() in BLANK else v


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def severity(a: dict) -> str:
    """Most severe level from the people counts; U when people are injured but none has a class (none in 2020-24)."""
    for k, f in zip("KABC", ("KILLED", "CLASSA", "CLASSB", "CLASSC")):
        if _int(a.get(f)):
            return k
    return "U" if _int(a.get("INJURED")) or a.get("SEVERITY") == "Injury Crash" else "O"


def _collision(a: dict):
    obj = a.get("FHE_ANALYSIS")
    if obj in FHE_OBJECT:
        return FHE_OBJECT[obj]
    if a.get("FHE") == "Collision with Fixed Object":
        return "HIT OBJECT"
    if a.get("FHE_IMPACT") in FHE_IMPACT:
        return FHE_IMPACT[a["FHE_IMPACT"]]
    for words, ccrs in ANALYSIS:
        if words in (a.get("ANALYSIS") or ""):
            return ccrs
    c = _s(a.get("CLASSIFICATION"))
    return CCRS_CLASS.get(c, c.upper() if c else None)


def _cross_and_offset(a: dict):
    """Cross street and offset. The distance and direction are from LANDMARK (e.g. 100 FT E of CARLISLE BLVD SE),
    so the landmark is the cross street when it names one; milepost and exit landmarks (MM 179, IX 2222) aren't."""
    sec, land = _s(a.get("SECONDARY_ST")), _s(a.get("LANDMARK"))
    dist, unit = a.get("DISTANCE_FROM_LANDMARK"), (_s(a.get("DISTANCE_UNIT")) or "").upper()
    ft = dist * 5280 if dist and unit == "MI" else (dist if dist and unit == "FT" else None)
    street_land = land and not land.upper().startswith(("MM ", "MP ", "IX ", "MILE")) and "/" not in land \
        and "INTERSECTION" not in land.upper()
    if sec:
        # the offset is from the landmark: keep it only when the landmark is the secondary street itself
        return sec, (ft if street_land and land.upper() == sec.upper() else None)
    return (land, ft) if street_land else (None, None)


def contract_record(a: dict) -> dict:
    """One layer row (attributes) -> the shared crash dict (packs.check_crash)."""
    lat, lon = a.get("LAT"), a.get("LON")
    has = lat is not None and lon is not None and NM_LAT[0] <= lat <= NM_LAT[1] and NM_LON[0] <= lon <= NM_LON[1]
    ms = a.get("DATETIME") if a.get("DATETIME") is not None else a.get("DATE")   # 1.7% have a date but no time
    t = from_epoch(ms / 1000, _TZ) if ms is not None else None
    hour = t.hour if t and a.get("DATETIME") is not None else None
    cross, ft = _cross_and_offset(a)
    route = _s(a.get("ROUTE_NAME"))
    flag = lambda f: a.get(f) == "Involved"
    light = _s(a.get("LIGHTING"))
    return {"crash_id": str(a["REPORT_NUMBER"]), "report_version": 0, "deleted": False, "preliminary": False,
            "date": t.date().isoformat() if t else "", "year": t.year if t else None, "hour": hour,
            "day_of_week": t.strftime("%A") if t else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": _s(a.get("PRIMARY_ST")), "secondary_road": cross,
            "offset_ft": ft or None, "offset_dir": _s(a.get("DIR_LANDMARK")) if ft else None,
            "city": (_s(a.get("CITY")) or "").upper() or None, "county_code": a.get("COUNTY"),
            "county_fips": FIPS.get((a.get("COUNTY") or "").upper()), "state": "NM",
            "is_freeway": bool(route and route.startswith("I ")) or a.get("ROAD_SYSTEM") == "Rural Interstate",
            "killed": _int(a.get("KILLED")), "injured": _int(a.get("INJURED")),
            "severity": severity(a), "severity_reported": a.get("SEVERITY"),
            "ped": flag("PED_INVOLVED"), "bike": flag("PEDALCYCLE_INVOLVED"), "ebike": False, "escooter": False,
            "motorcycle": flag("MOTORCYCLE_INVOLVED"), "heavy_truck": flag("HEAVY_TRUCK_INVOLVED"),
            "hit_run": a.get("HIT_RUN") == "Yes", "parties": [], "collision_type": _collision(a),
            "lighting": CCRS_LIGHT.get(light, light.upper() if light else None),
            "weather": (_s(a.get("WEATHER")) or "").upper() or None, "surface": None,     # the layer has no surface
            "report_number": str(a["REPORT_NUMBER"]), "route": route, "milepost": a.get("MILEPOST")}


def _get(where: str, last: int, opener) -> list[dict]:
    q = {"where": f"({where}) AND OBJECTID>{last}", "outFields": "*", "orderByFields": "OBJECTID",
         "resultRecordCount": PAGE, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(LAYER + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:                                  # ArcGIS reports query errors with HTTP 200
        raise RuntimeError(f"Albuquerque crash layer error: {body['error']}")
    return [f["attributes"] for f in body.get("features", [])]


def fetch(where: str, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every raw row matching an ArcGIS `where`, paged by OBJECTID; cached as raw JSON per `where`."""
    cache = cache_dir / f"nm_cabq_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json" if cache_dir else None
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
    """Every crash with a point in the box (s, w, n, e) in those years. Outside Bernalillo County, or outside
    2020-2024, the layer has nothing: those years come back missing, never as zero crashes."""
    yrs = [y for y in years if y in LAYER_YEARS]
    if not yrs or not COVERED & set(county_fips):
        return {"crashes": [], "years_missing": list(years),
                "cleaning": {"coverage": "Bernalillo County 2020-2024 only (statewide NMDOT data is by request)"}}
    s, w, n, e = box
    where = (f"LAT >= {s:.6f} AND LAT <= {n:.6f} AND LON >= {w:.6f} AND LON <= {e:.6f} "
             f"AND YEAR IN ({', '.join(str(y) for y in yrs)})")
    rows = [contract_record(a) for a in fetch(where, cache_dir, opener)]
    seen, out = set(), []
    for c in rows:
        if c["county_fips"] and c["year"] in yrs and c["crash_id"] not in seen:
            seen.add(c["crash_id"])
            out.append(c)
    return {"crashes": out, "years_missing": [y for y in years if y not in LAYER_YEARS],
            "cleaning": {"source_rows": len(rows), "dropped_duplicate_or_undated": len(rows) - len(out),
                         "severity_differs_from_unm": sum(
                             (c["severity"] == "K") != (c["severity_reported"] == "Fatal Crash") for c in out),
                         "coverage": "Bernalillo County 2020-2024 only (statewide NMDOT data is by request)"}}
