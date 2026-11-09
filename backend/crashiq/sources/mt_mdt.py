"""Montana crash source: MDT "Public Crash Information", an open ArcGIS MapServer layer, statewide, no login.

One row per crash, 2016-2025 (219,418 rows, checked 2026-11-08), every public road: each crash carries MDT's linear
reference (ROUTE_ID corridor + RP reference point) and a point MDT derives from it (all but 2 junk rows). Crash-level
KABCO only (CRASH_SEVERITY), plus collision type, weather, surface and light. There is no crash report number, no
time of day, no street names, no people or vehicle counts and no person table (research_notes/mt-2026-11-08).

Freeway crashes: a ROUTE_ID on MDT's interstate mainline or an interstate ramp (data/reference/mt_interstate_routes.json,
read from MDT's Routes service). Licence: MDT's item page says "provided 'as-is' … for planning purposes only"; no open
licence. Wired into the app by the MT plug-in (crashiq/statepacks/mt.py) through `fetch_contract`.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from ..settings import ROOT

LAYER = "https://gis.mtmdt.us/server/rest/services/MDTGIS/Public_Crash_Information/MapServer/0"
PAGE = 2000                          # the layer's maxRecordCount
# shortcut: the layer's years as read 2026-11-08 (MDT adds a year each autumn); widen when 2026 appears
LAYER_YEARS = range(2016, 2026)
_REF = ROOT / "data" / "reference"

SEVERITY = {"Fatal crash": "K", "Suspected Serious Injury": "A", "Suspected Minor Injury": "B",
            "Possible injury crash": "C", "No apparent Injury (property damage only crash)": "O"}
# MDT's "Unknown" (3.7% statewide) has no level: U, as WSDOT's Unknown (a user decision whether it counts as injury)
CCRS_TYPE = {"Rear-End": "REAR END", "Right Angle": "BROADSIDE", "Head On": "HEAD-ON",
             "Sideswipe, Same Direction": "SIDE SWIPE", "Sideswipe, Opposite Direction": "SIDE SWIPE",
             "Fixed Object": "HIT OBJECT", "Roll Over": "OVERTURNED", "Pedestrian": "VEHICLE/PEDESTRIAN"}
CCRS_LIGHT = {"Dark-Lighted": "DARK - STREET LIGHTS", "Dark-Not Lighted": "DARK - NO STREET LIGHTS",
              "Dark-Unknown Lighting": "DARK - UNKNOWN STREET LIGHTS"}


def _freeway_routes() -> frozenset:
    r = json.loads((_REF / "mt_interstate_routes.json").read_text())
    return frozenset(r["mainline"]) | frozenset(r["ramps"])


FREEWAY_ROUTES = _freeway_routes()


def _fips_by_county() -> dict[str, str]:
    boxes = json.loads((_REF / "county_boxes_mt.json").read_text())["counties"]
    return {v["name"].removesuffix(" County").upper(): k for k, v in boxes.items()}


FIPS = _fips_by_county()


def contract_record(f: dict) -> dict:
    """One layer feature (attributes + WGS84 geometry) -> the shared crash dict (packs.check_crash)."""
    a, g = f["attributes"], f.get("geometry") or {}
    up = lambda v: v.upper() if v else None
    d = date.fromisoformat(a["CRASH_DATE"]) if a.get("CRASH_DATE") else None
    lat, lon = g.get("y"), g.get("x")
    has = lat is not None and lon is not None and 44.3 <= lat <= 49.1 and -116.1 <= lon <= -104.0
    route, kind = a.get("ROUTE_ID"), a.get("COL_TYPE")
    return {"crash_id": str(a["OBJECTID"]), "report_version": 0, "deleted": False, "preliminary": False,
            "date": d.isoformat() if d else "", "year": d.year if d else None, "hour": None,
            "day_of_week": d.strftime("%A") if d else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and not has,
            "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,
            "city": up(a.get("CITY_NAME")), "county_code": a.get("COUNTY"),
            "county_fips": FIPS.get((a.get("COUNTY") or "").upper()), "state": "MT",
            "is_freeway": route in FREEWAY_ROUTES, "killed": 0, "injured": 0,      # MDT's layer has no people counts
            "severity": SEVERITY.get(a.get("CRASH_SEVERITY"), "U"), "severity_reported": a.get("CRASH_SEVERITY"),
            "ped": kind == "Pedestrian", "bike": kind == "Bicycle", "ebike": False, "escooter": False,
            "motorcycle": False, "heavy_truck": False, "parties": [],
            "collision_type": CCRS_TYPE.get(kind, up(kind)), "lighting": CCRS_LIGHT.get(a.get("LIGHT_COND"),
                                                                                        up(a.get("LIGHT_COND"))),
            "weather": up(a.get("WEATHER")), "surface": up(a.get("SURF_COND")),
            "route": route, "milepost": a.get("RP")}


def _get(params: dict, last: int, opener) -> list[dict]:
    q = {**params, "where": f"({params['where']}) AND OBJECTID>{last}", "outFields": "*", "outSR": "4326",
         "orderByFields": "OBJECTID", "resultRecordCount": PAGE, "f": "json"}
    req = urllib.request.Request(LAYER + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:                                  # ArcGIS reports query errors with HTTP 200
        raise RuntimeError(f"MDT crash layer error: {body['error']}")
    return body.get("features", [])


def fetch(params: dict, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every raw feature matching the query `params` (a `where`, optionally a geometry), paged by OBJECTID; cached as
    raw JSON per query when cache_dir is given."""
    key = json.dumps(params, sort_keys=True)
    cache = cache_dir / f"mt_mdt_{hashlib.sha1(key.encode()).hexdigest()[:10]}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    raw, last = [], 0
    while True:
        batch = _get(params, last, opener)
        raw += batch
        if len(batch) < PAGE:
            break
        last = batch[-1]["attributes"]["OBJECTID"]
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return raw


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years. The layer has no unlocated crashes to add
    (2 of 219,418 rows have no point, and no date or county either)."""
    s, w, n, e = box
    yrs = [y for y in years if y in LAYER_YEARS]
    if not yrs:
        return {"crashes": [], "years_missing": list(years), "cleaning": {}}
    params = {"where": f"CRASH_DATE >= DATE '{min(yrs)}-01-01' AND CRASH_DATE < DATE '{max(yrs) + 1}-01-01'",
              "geometry": f"{w:.6f},{s:.6f},{e:.6f},{n:.6f}", "geometryType": "esriGeometryEnvelope", "inSR": "4326",
              "spatialRel": "esriSpatialRelIntersects"}
    rows = [contract_record(f) for f in fetch(params, cache_dir, opener)]
    out = [c for c in rows if c["county_fips"] and c["year"] in yrs]
    return {"crashes": out, "years_missing": [y for y in years if y not in LAYER_YEARS],
            "cleaning": {"source_rows": len(rows), "no_county_or_date": len(rows) - len(out),
                         "severity_unknown": sum(c["severity"] == "U" for c in out),
                         "layer_years": f"{LAYER_YEARS.start}-{LAYER_YEARS.stop - 1}"}}
