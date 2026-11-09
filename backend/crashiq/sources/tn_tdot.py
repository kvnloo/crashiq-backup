"""Tennessee crash sources, all public ArcGIS layers, no login (checked 2026-11-08):

- TDOT (LAYER_TDOT): TDOT's "Tennessee Crashes JAN 2021_JAN 2025" (TDOT_GIS, ArcGIS Online item
  9a25e06f713a4a1688bec0a9cb2bc582): every crash statewide, 2021-2024, located by TDOT on its road network (route +
  log mile, a point), KABCO crash severity (TYPEOFCRAS), manner of collision, light, weather, junction relation. No
  street names (a route number only) and no person/vehicle rows. Read for 2021-2024.
- TDOSHS (LAYER): the Department of Safety and Homeland Security's crash layer behind its weekly Searchable Crash
  Dashboard (gis.safety.tn.gov, TITAN reports): fatal and injury crashes only, 2024-01-01 on, GPS, KABC (Crash_Type),
  pedestrian / bicycle / motorcycle / large-truck / DUI / speeding flags. Read for 2025 on (TDOT's layer stops).
- Metro Nashville (NASHVILLE): Traffic Accidents, Nashville Open Data, GPS and street address. Only its no-injury
  crashes are read, as O, and only for the TDOSHS years: the property-damage gap the state's layer leaves.

So a study up to 2024 has every crash with KABCO; 2025 on has fatal and injury crashes (plus PDO inside Nashville).
Licence: none published by TDOT or TDOSHS (TDOT's layer carries an informational-use, no-warranty disclaimer);
Metro's terms exempt Open Data Portal data from their commercial-use ban (research_notes/tn-2026-11-08/tn-import.md).
Wired in by the TN plug-in (statepacks/tn.py).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LAYER_TDOT = ("https://services2.arcgis.com/nf3p7v7Zy4fTOh6M/arcgis/rest/services/"
              "Tennessee_Crashes_JAN_2021_JAN_2025/FeatureServer/0")
LAYER = "https://tnmap.tn.gov/arcgis/rest/services/SAFETY/MapForDashboards/MapServer/0"
NASHVILLE = "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Traffic_Accidents_2/FeatureServer/0"
TDOT_YEARS = range(2021, 2025)                      # TDOT's layer: 2021-2024 (and 8,265 rows of January 2025, unused)
FIRST_YEAR = TDOT_YEARS.start
TN_LAT, TN_LON = (34.9, 36.7), (-90.4, -81.6)
DAVIDSON = "47037"
CENTRAL = ZoneInfo("America/Chicago")
REF = Path(__file__).resolve().parents[3] / "data" / "reference"

SEVERITY = {"Fatal": "K", "Suspected Serious Injury": "A", "Suspected Minor Injury": "B", "Possible Injury": "C"}
TDOT_SEVERITY = {**SEVERITY, "Prop Damage (over)": "O", "Prop Damage (under)": "O"}
# all three layers' light words -> the CCRS words the profile reads
CCRS_LIGHT = {"DAYLIGHT": "DAYLIGHT", "DARK-LIGHTED": "DARK - STREET LIGHTS", "DARK-NOT LIGHTED": "DARK - NO STREET LIGHTS",
              "DARK-UNKNOWN LIGHTING": "DARK - UNKNOWN STREET LIGHTS", "DUSK": "DUSK - DAWN", "DAWN": "DUSK - DAWN"}
CCRS_TYPE = {"ANGLE": "BROADSIDE", "REAR-END": "REAR END", "HEAD-ON": "HEAD-ON", "SIDESWIPE, SAME DIR": "SIDE SWIPE",
             "SIDESWIPE, OPP DIR": "SIDE SWIPE"}
_HOUSE = re.compile(r"^\d+[A-Z]?\s+")             # "1200 WEST END AVE" -> "WEST END AVE"
_PKE = re.compile(r"\bPKE\b")                      # Metro's Pike; names.street_key doesn't know PKE (shared-fixes.md)
_ROUTE = re.compile(r"^(I|SR)0*(\d+)$")           # TDOT route numbers: I0024, SR011; "03252" is a local road id


def _county_fips() -> dict[str, str]:
    boxes = json.loads((REF / "county_boxes_tn.json").read_text())["counties"]
    return {v["name"].upper().removesuffix(" COUNTY"): k for k, v in boxes.items()}


FIPS = _county_fips()


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and TN_LAT[0] <= lat <= TN_LAT[1] and TN_LON[0] <= lon <= TN_LON[1]


def _s(v) -> str | None:
    s = (str(v).strip() or None) if v is not None else None
    return None if s == "--" else s                 # TDOT writes "--" for blank


def _flag(v) -> bool:
    return _s(v) not in (None, "-", "No", "N")      # TDOSHS writes "-" for no, the flag's own name for yes


def _light(v) -> str | None:
    k = (_s(v) or "").upper().replace(" - ", "-")
    return CCRS_LIGHT.get(k, k or None)


def _point(lat, lon) -> dict:
    has = plausible(lat, lon)
    return {"lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has}


def _base(crash_id: str, day: date | None, hour, county: str, source: str) -> dict:
    return {"crash_id": crash_id, "report_version": 0, "deleted": False,
            "preliminary": bool(day and day.year >= date.today().year),
            "date": day.isoformat() if day else "", "year": day.year if day else None, "hour": hour,
            "day_of_week": day.strftime("%A") if day else None,
            "offset_ft": None, "offset_dir": None, "county_code": county or None, "county_fips": FIPS.get(county),
            "state": "TN", "ebike": False, "escooter": False, "parties": [], "surface": None, "source": source}


def tdot_record(a: dict) -> dict:
    """One TDOT row (attributes plus `_lat`/`_lon` from its point) -> the shared crash dict, KABCO."""
    day = datetime.fromtimestamp(a["DATEOFCRAS"] / 1000, tz=timezone.utc).date() if a.get("DATEOFCRAS") else None
    t = a.get("TIMEOFCRAS")
    route = _ROUTE.match(_s(a.get("NBR_RT2")) or "")
    harm = (_s(a.get("FIRSTHARMF")) or "").upper()
    manner = _s(a.get("MANNEROFCO"))
    return {**_base(f"TDOT{a['CASENO']}", day, t // 100 if isinstance(t, int) and 0 <= t < 2400 else None,
                    (_s(a.get("NBR_TENN_C")) or "").upper(), "TDOT"),
            **_point(a.get("_lat"), a.get("_lon")),
            "primary_road": f"{route.group(1)} {int(route.group(2))}" if route else None, "secondary_road": None,
            "city": None, "is_freeway": bool(route and route.group(1) == "I"),
            "killed": int(a.get("TOTALKILLE") or 0), "injured": int(a.get("TOTALINJUR") or 0),
            "severity": TDOT_SEVERITY[a["TYPEOFCRAS"]], "ped": harm == "PEDESTRIAN", "bike": harm == "PEDALCYCLE",
            "motorcycle": False, "heavy_truck": False,
            "collision_type": CCRS_TYPE.get(manner or "", manner),
            "lighting": _light(a.get("LIGHTCONDI")), "weather": (_s(a.get("WEATHERCON")) or "").upper() or None,
            "first_harmful_event": _s(a.get("FIRSTHARMF")), "junction": _s(a.get("RELATIONTO")),
            "route": _s(a.get("NBR_RT2")), "log_mile": a.get("BLM")}


def contract_record(a: dict) -> dict:
    """One TDOSHS row -> the shared crash dict, KABC."""
    y, m, d = a.get("Collision_Year"), a.get("Collision_Month"), a.get("Collision_Day")
    day = date(y, m, d) if y and m and d else None
    return {**_base(f"TN{a['MRN']}", day, a.get("Collision_Hour"), (_s(a.get("County")) or "").upper(), "TDOSHS"),
            **_point(a.get("Latitude"), a.get("Longitude")),
            "primary_road": None, "secondary_road": None, "city": (_s(a.get("City")) or "").upper() or None,
            "is_freeway": False, "killed": int(a.get("Fatality") or 0), "injured": int(a.get("Injury") or 0),
            "severity": SEVERITY[a["Crash_Type"]], "ped": _flag(a.get("Pedestrian")),
            "bike": _flag(a.get("Pedalcyclist")), "motorcycle": _flag(a.get("Motorcycle_Involved")),
            "heavy_truck": _flag(a.get("LargeTruck_Involved")), "collision_type": None,
            "lighting": _light(a.get("Light_Condition")), "weather": (_s(a.get("Weather")) or "").upper() or None,
            "first_harmful_event": _s(a.get("First_Harmfu_Event")), "agency": _s(a.get("Agency_Name")),
            "dui": _flag(a.get("Driver_Drinking")) or _flag(a.get("Driver_Drugged")),
            "speeding": _flag(a.get("Speeding_Involved"))}


def nashville_record(a: dict) -> dict:
    """One Metro Nashville row with no one hurt -> the shared crash dict, severity O."""
    # Metro's times are true UTC (the layer says so; read in Central time the night low falls at 2-4 am, 2026-11-08)
    t = datetime.fromtimestamp(a["Date_and_Time"] / 1000, tz=CENTRAL) if a.get("Date_and_Time") else None
    addr = _s(a.get("Street_Address"))
    road, _, cross = _PKE.sub("PIKE", _HOUSE.sub("", addr) if addr else "").partition(" & ")   # "X PKE & Y LN"
    return {**_base(f"NASH{a['Accident_Number']}", t.date() if t else None, t.hour if t else None, "DAVIDSON",
                    "Metro Nashville"),
            **_point(a.get("Lat"), a.get("Long")),
            "primary_road": road or None, "secondary_road": cross or None,
            "city": (_s(a.get("City")) or "NASHVILLE").upper(),
            "is_freeway": bool(road and re.search(r"\bI-?\s?\d+\b", road)), "killed": 0, "injured": 0,
            "severity": "O", "ped": False, "bike": False, "motorcycle": False, "heavy_truck": False,
            "collision_type": _s(a.get("Collision_Type_Description")),
            "lighting": _light(a.get("Illumination_Description")),
            "weather": (_s(a.get("Weather_Description")) or "").upper() or None,
            "hit_and_run": _s(a.get("Hit_and_Run")) == "Y", "location_text": addr}


# -- the layers --------------------------------------------------------------------------------------------------
def _post(url: str, params: dict) -> dict:
    import httpx
    resp = httpx.post(url, data=params, headers={"User-Agent": "CrashIQ/0.1"}, timeout=180)
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:                    # ArcGIS reports query errors with HTTP 200
        raise RuntimeError(f"Tennessee crash layer error: {body['error']}")
    return body


def attributes(layer: str, query: dict, get, page: int = 2000, points: bool = False) -> list[dict]:
    """Every row matching `query` (where, maybe a geometry), paged by object id (TDOT and TDOSHS answer 2,000 rows a
    call, Metro 1,000). `points` keeps each row's point as `_lat`/`_lon` (TDOT's layer has no coordinate columns)."""
    ids = sorted(get(layer + "/query", {**query, "returnIdsOnly": "true", "f": "json"}).get("objectIds") or [])
    out = []
    for i in range(0, len(ids), page):
        body = get(layer + "/query", {"objectIds": ",".join(map(str, ids[i:i + page])), "outFields": "*",
                                      "returnGeometry": "true" if points else "false", "outSR": "4326", "f": "json"})
        for f in body["features"]:
            g = f.get("geometry") or {}
            out.append({**f["attributes"], "_lat": g.get("y"), "_lon": g.get("x")} if points else f["attributes"])
    return out


def queries(box, tdot_years, tdoshs_years) -> dict[str, dict]:
    s, w, n, e = box
    out = {}
    if tdot_years:
        out["tdot"] = {"where": f"YEAROFCRAS IN ({', '.join(repr(str(y)) for y in tdot_years)})",
                       "geometry": f"{w:.6f},{s:.6f},{e:.6f},{n:.6f}", "geometryType": "esriGeometryEnvelope",
                       "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"}
    if tdoshs_years:
        out["tdoshs"] = {"where": f"Collision_Year IN ({', '.join(str(y) for y in tdoshs_years)}) AND Latitude >= "
                                  f"{s:.6f} AND Latitude <= {n:.6f} AND Longitude >= {w:.6f} AND Longitude <= {e:.6f}"}
        t0 = datetime(min(tdoshs_years), 1, 1, 6).strftime("%Y-%m-%d %H:%M:%S")   # Metro's UTC: 06:00 = midnight CST
        t1 = datetime(max(tdoshs_years) + 1, 1, 1, 6).strftime("%Y-%m-%d %H:%M:%S")
        out["nashville"] = {"where": f"Number_of_Injuries = 0 AND Number_of_Fatalities = 0 AND Date_and_Time >= "
                                     f"TIMESTAMP '{t0}' AND Date_and_Time < TIMESTAMP '{t1}' AND Lat >= {s:.6f} AND "
                                     f"Lat <= {n:.6f} AND Long >= {w:.6f} AND Long <= {e:.6f}"}
    return out


def _cached(cache_dir: Path | None, name: str, query: dict, fetch, final: bool) -> list[dict]:
    """Rows of one query, cached as raw JSON when `final` (no current year: that one still grows)."""
    key = hashlib.sha1(json.dumps(query, sort_keys=True).encode()).hexdigest()[:10]
    cache = cache_dir / f"tn_{name}_{key}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    rows = fetch()
    if cache and final:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows))
    return rows


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path | None, get=None) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years: TDOT's layer for 2021-2024, TDOSHS's for
    2025 on, plus Metro Nashville's no-injury crashes for 2025 on when the corridor is in Davidson County."""
    get = get or _post
    tdot_years = [y for y in years if y in TDOT_YEARS]
    later = [y for y in years if y >= TDOT_YEARS.stop]
    q = queries(box, tdot_years, later)
    final = max(years) < date.today().year
    raw = {"tdot": [], "tdoshs": [], "nashville": []}
    if "tdot" in q:                                    # a frozen snapshot: always cached
        raw["tdot"] = _cached(cache_dir, "tdot", q["tdot"],
                              lambda: attributes(LAYER_TDOT, q["tdot"], get, points=True), True)
    if "tdoshs" in q:
        raw["tdoshs"] = _cached(cache_dir, "tdoshs", q["tdoshs"], lambda: attributes(LAYER, q["tdoshs"], get), final)
        if DAVIDSON in county_fips:
            raw["nashville"] = _cached(cache_dir, "nashville", q["nashville"],
                                       lambda: attributes(NASHVILLE, q["nashville"], get, 1000), final)
    recs = ([tdot_record(a) for a in raw["tdot"] if a.get("TYPEOFCRAS") in TDOT_SEVERITY]
            + [contract_record(a) for a in raw["tdoshs"] if a.get("Crash_Type") in SEVERITY]
            + [nashville_record(a) for a in raw["nashville"]])
    recs = [r for r in recs if r["year"] in years]     # TDOT's January 2025 rows never mix with TDOSHS's
    have = {r["year"] for r in recs if r["source"] != "Metro Nashville"}
    out = [r for r in recs if r["county_fips"]]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"tdot_rows": len(raw["tdot"]), "tdoshs_rows": len(raw["tdoshs"]),
                         "nashville_no_injury_rows": len(raw["nashville"]), "no_county": len(recs) - len(out),
                         "severity": "KABCO from TDOT (2021-2024); KABC from TDOSHS (2025 on), O there only inside "
                                     "Nashville"}}
