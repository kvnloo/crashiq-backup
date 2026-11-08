"""Maine crash source: MaineDOT "Crash Locations - 10 Years Complete", the open ArcGIS layer behind the Maine Public
Crash Query Tool (MaineDOT.IT on ArcGIS Online, public, no login, refreshed weekly).

One row per crash, 2016 to now (the current year is partial), placed by MaineDOT on its Route Log Mile network: all
but 4 of 359,187 crashes have a point (2026-11-08). Crash-level KABCO (INJURY_LEVEL K/A/B/C/PD) and per-crash counts
of K, A, B and C people. Only crashes coded to Maine public roads are in it (MaineDOT's user notes: parking lots,
driveways and private roads are left out).

There are NO street names: PRIMARY_ROUTE_NAME is MaineDOT's route code ("US 302", "ST RTE 26", "INT 295 SB", or a
road-inventory id "RD INV 05 60621" for a local street), and there's no cross street. The code goes in `route`, and
`primary_road` stays None: the core would read "RD INV ..." as another street and drop the crash as "not on corridor
street", and "ST RTE 26" doesn't match OSM's "ME 26". Placement is by MaineDOT's point alone.

Licence: no open licence; the MEGIS disclaimer on the item ("Users must assume responsibility in determining the
usability of this data for their purposes"). See research_notes/me-2026-11-08/me-import.md.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LAYER = ("https://services1.arcgis.com/RbMX0mRVOFNTdLzd/arcgis/rest/services/"
         "Crashes_Attributes_10_Year_and_Current_Year_Test_View/FeatureServer/44")
PAGE = 2000                                    # the layer's maxRecordCount
BOUNDS = (42.9, -71.1, 47.5, -66.9)            # Maine's extent with a small margin (s, w, n, e)
_TZ = ZoneInfo("America/New_York")             # ACCIDENT_DATE is local midnight sent as UTC epoch ms
SEVERITY = {"K": "K", "A": "A", "B": "B", "C": "C", "PD": "O"}

# MaineDOT words -> the CCRS words the profile and the collision diagram read, only where they mean the same thing.
# "Rear End / Sideswipe", "Head-on / Sideswipe" and "Intersection Movement" merge CCRS types, so they keep Maine's words.
CCRS_TYPE = {"Pedestrians": "VEHICLE/PEDESTRIAN", "Rollover": "OVERTURNED", "Object in Road": "HIT OBJECT"}
CCRS_LIGHT = {"Daylight": "DAYLIGHT", "Dawn": "DUSK - DAWN", "Dusk": "DUSK - DAWN",
              "Dark - Lighted": "DARK - STREET LIGHTS", "Dark - Not Lighted": "DARK - NO STREET LIGHTS",
              "Dark - Unknown Lighting": "DARK - UNKNOWN STREET LIGHTS"}


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _s(v):
    return (str(v).strip() or None) if v is not None else None


def plausible(lat, lon) -> bool:
    s, w, n, e = BOUNDS
    return lat is not None and lon is not None and s <= lat <= n and w <= lon <= e


def contract_record(a: dict) -> dict:
    """One layer row -> the shared crash dict (packs.check_crash), plus Maine's route, milepoint and node."""
    lat, lon = a.get("LATITUDE"), a.get("LONGITUDE")
    has = plausible(lat, lon)
    d = datetime.fromtimestamp(a["ACCIDENT_DATE"] / 1000, _TZ).date() if a.get("ACCIDENT_DATE") is not None else None
    hour = _int(a.get("ACCIDENT_HOUR")) if a.get("ACCIDENT_HOUR") is not None else None
    county = _s(a.get("COUNTY_CODE"))
    route = _s(a.get("PRIMARY_ROUTE_NAME"))
    counts = {k: _int(a.get(f"NO_OF_{k}_INJ")) for k in "KABC"}
    up = lambda v: _s(v).upper() if _s(v) else None
    ctype, light = _s(a.get("TYPE_OF_CRASH_DESCR")), _s(a.get("LIGHT_CONDITION_DESCR"))
    return {
        "crash_id": str(a.get("CRASH_ID") or a["MDOTID"]), "report_version": 0, "deleted": False,
        "preliminary": bool(d and d.year >= datetime.now(_TZ).year),     # the current year is still coming in
        "date": d.isoformat() if d else "", "year": d.year if d else None,
        "hour": hour if hour is not None and 0 <= hour <= 23 else None,
        "day_of_week": d.strftime("%A") if d else None,
        "lat": lat if has else None, "lon": lon if has else None,
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,   # see module doc
        "city": up(a.get("TOWN_NAME")), "county_code": county,
        "county_fips": f"23{int(county):03d}" if county and county.isdigit() else None,   # MaineDOT's code = FIPS county
        "state": "ME", "is_freeway": bool(route and route.startswith("INT ")),
        # shortcut: freeway = Interstate routes only (MaineDOT's layer has no functional class); a non-Interstate
        # expressway (US 1 Brunswick bypass, Route 9 parts) counts as arterial; upgrade with MaineDOT's road layer
        "killed": counts["K"], "injured": counts["A"] + counts["B"] + counts["C"],
        "severity": SEVERITY.get(_s(a.get("INJURY_LEVEL")) or "") or next((k for k in "KABC" if counts[k]), "O"),
        "person_kabco": [k for k in "KABC" for _ in range(counts[k])],
        "ped": a.get("PED_YN") == "Y", "bike": a.get("BICYCLE_YN") == "Y", "ebike": False, "escooter": False,
        "motorcycle": a.get("MOTORCYCLE_YN") == "Y", "heavy_truck": False, "parties": [],
        "collision_type": CCRS_TYPE.get(ctype, up(ctype)), "lighting": CCRS_LIGHT.get(light, up(light)),
        "weather": up(a.get("WEATHER_CONDITION_DESCR")), "surface": up(a.get("ROAD_SURF_COND_DESCR")),
        "agency": _s(a.get("REPORTING_AGENCY_DESCR")), "report_number": _s(a.get("REPORT_NUMBER")),
        "route": route, "milepost": a.get("PRIMARY_ROUTE_MP"), "node": a.get("NODE_ID"),
        "location_type": _s(a.get("LOCATION_TYPE")), "aadt": a.get("FACTORED_AADT"),
    }


def _get(where: str, last: int, opener) -> list[dict]:
    q = {"where": f"({where}) AND OBJECTID>{last}", "outFields": "*", "orderByFields": "OBJECTID",
         "resultRecordCount": PAGE, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(LAYER + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"MaineDOT crash layer query error: {body['error']}")
    return [f["attributes"] for f in body.get("features", [])]


def fetch(where: str, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every row matching an ArcGIS `where`, paged by OBJECTID, normalized; cached raw per `where`."""
    cache = cache_dir / f"me_mainedot_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json" if cache_dir else None
    if cache and cache.exists():
        raw = json.loads(cache.read_text())
    else:
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
    return [contract_record(a) for a in raw]


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years. The 4 crashes of 359,187 with no point
    (2020-2021) aren't read: with no street names there is nothing to place them by."""
    s, w, n, e = box
    yrs = ", ".join(str(int(y)) for y in years)
    where = (f"LATITUDE >= {s:.6f} AND LATITUDE <= {n:.6f} AND LONGITUDE >= {w:.6f} AND LONGITUDE <= {e:.6f} "
             f"AND ACCIDENT_YEAR IN ({yrs})")
    rows = fetch(where, cache_dir, opener)
    have = {r["year"] for r in rows}
    out = [r for r in rows if r["county_fips"]]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "no_county": len(rows) - len(out),
                         "no_gps_not_read": "4 of 359,187 statewide crashes have no point; not read"}}
