"""Illinois crash source: IDOT's statewide crash layers on its public ArcGIS hub (gis-idot.opendata.arcgis.com,
"Crashes - <year>", owner IDOTAdmin), one hosted layer per frozen year 2014-2025, no login (checked 2026-11-08).

Every police-reported crash in Illinois (Chicago included, ~100,000 a year), one row per crash with IDOT's GPS point,
IDOT's K/A/B/C injury counts (its crash KABCO is the worst of them). Street names (road, the
"<road>/<cross street>" pair, house number, distance and direction from the intersection) are in the 2025 layer only;
2014-2024 give a route number and milestation, so those years are read by GPS alone.
Field meanings: IDOT "Illinois Traffic Crash Report SR 1050 Instruction Manual" (2019).

Licence: 2014-2020 layers say CC BY-SA 2.0; 2021-2025 carry no licence, 2024 IDOT's map disclaimer
(research_notes/il-2026-11-08/il-import.md). Wired into the app by statepacks/il.py through `fetch_contract`.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE = "https://services2.arcgis.com/aIrBD8yn1TDTEXoz/arcgis/rest/services"
LAYERS = {2014: "Crashes_2014_SDMExtract", 2015: "Crashes_2015_SDMExtract", 2016: "Crashes_2016_SDMExtract",
          2017: "Crashes_2017_SDMExtract", 2018: "Crashes_2018_SDMExtract", 2019: "Crashes2019", 2020: "Crashes_2020",
          2021: "CRASHES2021", 2022: "CRASHES_2022", 2023: "CRASHES_2023", 2024: "CRASHES__2024",
          2025: "CRASHES___2025"}
IL_LAT, IL_LON = (36.9, 42.6), (-91.6, -87.0)
PAGE = 1000
# IDOT's TypeOfFirstCrash -> the CCRS words the profile and the collision diagram read; others keep IDOT's words
CCRS_TYPE = {"FRONT TO REAR": "REAR END", "REAR END": "REAR END", "ANGLE": "BROADSIDE", "FRONT TO FRONT": "HEAD-ON",
             "HEAD ON": "HEAD-ON", "SIDESWIPE SAME DIRECTION": "SIDE SWIPE", "SIDESWIPE OPPOSITE DIRECTION": "SIDE SWIPE",
             "FIXED OBJECT": "HIT OBJECT", "PEDESTRIAN": "VEHICLE/PEDESTRIAN", "OVERTURNED": "OVERTURNED"}
CCRS_LIGHT = {"DARKNESS / LIGHTED ROAD": "DARK - STREET LIGHTS", "DARKNESS, LIGHTED ROAD": "DARK - STREET LIGHTS",
              "DARKNESS": "DARK - NO STREET LIGHTS", "DUSK": "DUSK - DAWN", "DAWN": "DUSK - DAWN",
              "UNKNOWN": None}
NOT_STATED = {"", "(UNK)", "(N/A)", "NONE", "UNKNOWN"}


def _s(v) -> str | None:
    t = str(v).strip() if v is not None else ""
    return None if t.upper() in NOT_STATED else t


def _int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and IL_LAT[0] <= lat <= IL_LAT[1] and IL_LON[0] <= lon <= IL_LON[1])


def county_fips(code) -> str | None:
    """IDOT numbers Illinois' 102 counties alphabetically (1 Adams ... 16 Cook ... 102 Woodford), as Census FIPS does
    in odd numbers: FIPS = 2 * code - 1."""
    c = _int(code)
    return f"17{2 * c - 1:03d}" if 1 <= c <= 102 else None


def cross_street(pair: str | None, primary: str | None) -> str | None:
    """2025's AtIntersectionWith is "<road>/<cross street>" in either order ("Moss/Western", "(UNK)/W Wabansia Ave");
    the other street is what's left once the crash's own road is taken out (a name may hold a slash: "S/B Kennicott")."""
    t = _s(pair)
    if not t:
        return None
    if primary and primary.upper() in t.upper():
        i = t.upper().index(primary.upper())
        rest = t[:i] + t[i + len(primary):]
    else:
        rest = t.split("/", 1)[1] if "/" in t else t
    return _s(rest.strip(" /"))


def severity(a: dict) -> str:
    """The worst of IDOT's K/A/B/C counts (they match IDOT's own crash KABCO row for row in 2014 and 2025); an injury
    crash with none of them U. Not CrashSeverityCd: in the 2019 layer ~25% of rows have the columns after
    TrafficwayDescrip shifted by an unquoted comma ("Divided, No Median Barrier"), the counts come before it."""
    for k, f in (("K", "TotalFatals"), ("A", "AInjuries"), ("B", "BInjuries"), ("C", "CInjuries")):
        if _int(a.get(f)) > 0:
            return k
    injury = _int(a.get("TotalInjured")) > 0 or str(a.get("CrashSeverity") or "").strip() in ("Injury", "Fatal")
    return "U" if injury else "O"


def contract_record(a: dict, geom: dict | None, year: int) -> dict:
    """One layer row (attributes `a`, WGS84 point `geom`) of `year`'s layer -> the shared crash dict
    (packs.check_crash). The point is the layer geometry: 2014's own longitude column lost its sign."""
    lat, lon = (geom or {}).get("y"), (geom or {}).get("x")
    has = plausible(lat, lon)
    mo, d = _int(a.get("CrashMonth")), _int(a.get("CrashDay"))
    day = date(year, mo, d) if 1 <= mo <= 12 and 1 <= d <= 31 else None
    hour = _int(a.get("CrashHour")) if str(a.get("CrashHour") or "").strip().isdigit() else None
    primary = _s(a.get("HighwayorStreetName"))
    dist, units = _s(a.get("NonIntersectionDistance")), (_s(a.get("NonIntersectionUnits")) or "").upper()
    try:
        off = float(dist) * (5280 if units == "M" else 1) if dist and units in ("F", "M") else None
    except ValueError:
        off = None
    first = (_s(a.get("TypeOfFirstCrash")) or "").upper()
    # ClassOfTrafficway too: it sits before 2019's column shift ("Urban InterState (PAS)") and is filled before 2025
    fc = f"{a.get('RoadwayFunctionalClass') or ''} {a.get('ClassOfTrafficway') or ''}".upper()
    light = (_s(a.get("LightingCond")) or "").upper()
    return {"crash_id": str(a["CrashID"]).strip(), "report_version": 0, "deleted": False, "preliminary": False,
            "date": day.isoformat() if day else "", "year": year, "hour": hour if hour is not None and hour < 24 else None,
            "day_of_week": day.strftime("%A") if day else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": primary, "secondary_road": cross_street(a.get("AtIntersectionWith"), primary),
            "offset_ft": off, "offset_dir": (_s(a.get("NonIntersectionDirection")) or "")[:1] or None if off else None,
            "house_number": _s(a.get("AddressNo")),
            "city": (_s(a.get("CityName")) or "").upper() or None, "county_code": _s(a.get("CrashReportCounty")),
            "county_fips": county_fips(a.get("CountyCode")), "state": "IL",
            "is_freeway": "INTERSTATE" in fc or "FREEWAY" in fc,
            "killed": _int(a.get("TotalFatals")), "injured": _int(a.get("TotalInjured")), "severity": severity(a),
            "ped": first == "PEDESTRIAN", "bike": first == "PEDALCYCLIST", "ebike": False, "escooter": False,
            "motorcycle": False, "heavy_truck": False, "parties": [],
            "collision_type": CCRS_TYPE.get(first, first or None),
            "lighting": CCRS_LIGHT.get(light, light or None), "weather": (_s(a.get("WeatherCond")) or "").upper() or None,
            "surface": (_s(a.get("RoadSurfaceCond")) or "").upper() or None,
            "hit_and_run": str(a.get("HitAndRun") or "").strip().upper() == "Y",
            "route": _s(a.get("RouteNumber")), "milepoint": a.get("Milestation", a.get("MileStation")),
            "cause": _s(a.get("Cause1")), "intersection_related": str(a.get("IntersectionRelated") or "").strip() == "Y"}


# -- the layers --------------------------------------------------------------------------------------------------
def _post(url: str, params: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(),
                                 headers={"User-Agent": "CrashIQ/0.1"})       # id lists outgrow a GET URL
    with urllib.request.urlopen(req, timeout=300) as r:
        body = json.load(r)
    if "error" in body:                    # ArcGIS reports query errors with HTTP 200
        raise RuntimeError(f"IDOT layer error: {body['error']}")
    return body


def fetch_year(box, year: int, get=None) -> list[dict]:
    """Every crash row of one year's layer with a point in the box (s, w, n, e): [{attributes, geometry}]."""
    get = get or _post
    s, w, n, e = box
    url = f"{BASE}/{LAYERS[year]}/FeatureServer/0/query"
    ids = sorted(get(url, {"where": "1=1", "geometry": f"{w},{s},{e},{n}", "geometryType": "esriGeometryEnvelope",
                           "inSR": "4326", "spatialRel": "esriSpatialRelIntersects", "returnIdsOnly": "true",
                           "f": "json"}).get("objectIds") or [])
    out = []
    for i in range(0, len(ids), PAGE):
        body = get(url, {"objectIds": ",".join(map(str, ids[i:i + PAGE])), "outFields": "*", "returnGeometry": "true",
                         "outSR": "4326", "f": "json"})
        out += [{"attributes": f["attributes"], "geometry": f.get("geometry")} for f in body["features"]]
    return out


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, get=None) -> dict:
    """Every crash with a GPS point in the box in those years, cached per box and year. The layers are queried by point,
    so a crash with no GPS isn't read (538 of 303,087 in 2025, 0.18%)."""
    recs, raw = [], 0
    for y in years:
        if y not in LAYERS:
            continue
        key = hashlib.sha1(f"{box}|{y}".encode()).hexdigest()[:10]
        cache = Path(cache_dir) / f"il_idot_{key}.json"
        if cache.exists():
            rows = json.loads(cache.read_text())
        else:
            rows = fetch_year(box, y, get)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(rows))
        raw += len(rows)
        recs += [contract_record(r["attributes"], r.get("geometry"), y) for r in rows]
    out = [c for c in recs if c["county_fips"] and c["date"]]
    have = {c["year"] for c in out}
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": raw, "no_county_or_date": len(recs) - len(out),
                         "layer_years": f"{min(LAYERS)}-{max(LAYERS)}",
                         "street_names": "2025 layer only; 2014-2024 by GPS alone"}}
