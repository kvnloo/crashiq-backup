"""North Dakota: NDDOT crash records, statewide, 2017-2025, through the public ArcGIS layer NDSU's DOT Support Center
(Upper Great Plains Transportation Institute) hosts for NDDOT's crash dashboards. Open, no login (checked 2026-11-08).

LAYER below ("All Crash Data - 2017 to 2025", 104,008 crashes): one row per reportable crash with NDDOT's crash id,
date and hour, a WGS84 point (every row, all inside North Dakota), crash KABCO, county FIPS, city, manner of crash,
light, weather, surface, people killed and injured, and NDDOT's crash-type flags (pedestrian, bicycle, motorcycle,
truck, interstate ...). It has no street names, no driver or vehicle records and no person KABCO. Its 2024 count
(9,803) equals NDDOT's Crash Summary 2024 exactly (research_notes/nd-2026-11-08). Wired into the app by the ND
plug-in (crashiq/statepacks/nd.py) through `fetch_contract`.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

LAYER = ("https://dotsc.ugpti.ndsu.edu:6443/arcgis/rest/services/NDDOT_crash/ALL_CRASHES_2017_to_2025/"
         "FeatureServer/0")
# shortcut: the layer's years on 2026-11-08 (the service name says 2017-2025); widen when DOTSC republishes it
YEARS = range(2017, 2026)
ND_LAT, ND_LON = (45.9, 49.1), (-104.1, -96.5)
KABCO = set("KABCO")
SEV_ID = {"0": "O", "1": "K", "2": "A", "3": "B", "4": "C"}       # Crash_Severity_ID, when the KABCO text is blank
CCRS_TYPE = {"Angle": "BROADSIDE", "Front to Rear": "REAR END", "Front to Front": "HEAD-ON",
             "Sideswipe, Same Direction": "SIDE SWIPE", "Sideswipe, Opposite Direction": "SIDE SWIPE",
             "Rear to Side": "BROADSIDE", "Rear to Rear": "REAR END"}
CCRS_FIRST = {"Overturn/Rollover": "OVERTURNED", "Pedestrian": "VEHICLE/PEDESTRIAN"}   # for non-collision crashes
CCRS_LIGHT = {"Dark-Lighted": "DARK - STREET LIGHTS", "Dark-Not Lighted": "DARK - NO STREET LIGHTS",
              "Dark-Unknown Lighting": "DARK - UNKNOWN STREET LIGHTS"}


def _s(v) -> str | None:
    return (str(v).strip() or None) if v is not None else None


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _flag(v) -> bool:
    return _num(v) == 1


def contract_record(a: dict) -> dict:
    """One layer row (its attributes) -> the shared crash dict (packs.check_crash)."""
    d = dt.datetime.strptime(a["Crash_Date"], "%m/%d/%Y").date() if _s(a.get("Crash_Date")) else None
    h = _num(a.get("crshr"))
    lat, lon = _num(a.get("latitude")), _num(a.get("longitude"))
    has = lat is not None and lon is not None and ND_LAT[0] <= lat <= ND_LAT[1] and ND_LON[0] <= lon <= ND_LON[1]
    k = (_s(a.get("Crash_Severity_KABCO")) or " ")[0]
    sev = k if k in KABCO else SEV_ID.get(_s(a.get("Crash_Severity_ID")) or "", "O")
    fips = _s(a.get("FIPS"))
    manner, first = _s(a.get("Manner_Crash")), _s(a.get("First_Harmful_Event"))
    up = lambda v: v.upper() if v else None
    kind = CCRS_TYPE.get(manner or "") or CCRS_FIRST.get(first or "") or \
        up(first if manner and manner.startswith("Non-Collision") else manner)
    return {"crash_id": a["crashid"], "report_version": 0, "deleted": False, "preliminary": False,
            "date": d.isoformat() if d else "", "year": d.year if d else None,
            "hour": int(h) if h is not None and 0 <= h <= 23 else None,      # 24 and '6-' occur (7 rows)
            "day_of_week": d.strftime("%A") if d else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,
            "city": up(_s(a.get("Crash_City"))), "county_code": _s(a.get("county")),
            "county_fips": fips if fips and len(fips) == 5 and fips.startswith("38") else None, "state": "ND",
            "is_freeway": _flag(a.get("interstate")),
            "killed": int(_num(a.get("No_Fatalities")) or 0), "injured": int(_num(a.get("No_Nonfatally_Injured_Persons")) or 0),
            "severity": sev, "severity_reported": _s(a.get("Crash_Severity")),
            "ped": _flag(a.get("pedcrs")), "bike": _flag(a.get("bikcrs")), "ebike": False, "escooter": False,
            "motorcycle": _flag(a.get("mcyclecrs")), "heavy_truck": _flag(a.get("trckcrs")), "parties": [],
            "collision_type": kind, "lighting": CCRS_LIGHT.get(a.get("Light_Conditions") or "", up(_s(a.get("Light_Conditions")))),
            "weather": up(_s(a.get("Weather_Conditions"))), "surface": up(_s(a.get("Roadway_Surface_Condition")))}


def _post(url: str, params: dict) -> dict:
    import httpx
    resp = httpx.post(url, data=params, headers={"User-Agent": "CrashIQ/0.1"}, timeout=120)  # id lists outgrow a GET URL
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:                    # ArcGIS reports query errors with HTTP 200
        raise RuntimeError(f"NDDOT crash layer error: {body['error']}")
    return body


def _attributes(where: str, get, page: int = 2000) -> list[dict]:
    ids = sorted(get(LAYER + "/query", {"where": where, "returnIdsOnly": "true", "f": "json"})["objectIds"] or [])
    out = []
    for i in range(0, len(ids), page):
        body = get(LAYER + "/query", {"objectIds": ",".join(map(str, ids[i:i + page])), "outFields": "*",
                                      "returnGeometry": "false", "f": "json"})
        out += [f["attributes"] for f in body["features"]]
    return out


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, get=None) -> dict:
    """Crashes with a point in the box (s, w, n, e) in those years. Every row has a point, so there are no unplaced
    crashes to add for the corridor's counties; years outside 2017-2025 are missing (the layer has no others)."""
    s, w, n, e = box
    yrs = [y for y in years if y in YEARS]
    if not yrs:
        return {"crashes": [], "years_missing": list(years), "cleaning": {}}
    where = (f"crash_yr IN ({', '.join(repr(str(y)) for y in yrs)}) AND latitude >= {s:.6f} AND latitude <= {n:.6f} "
             f"AND longitude >= {w:.6f} AND longitude <= {e:.6f}")
    cache = cache_dir / f"nd_nddot_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json"
    if cache.exists():
        rows = json.loads(cache.read_text())
    else:
        rows = _attributes(where, get or _post)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows))
    out = [contract_record(a) for a in rows]
    kept = [c for c in out if c["county_fips"] and c["date"]]
    return {"crashes": kept, "years_missing": [y for y in years if y not in YEARS],
            "cleaning": {"source_rows": len(rows), "dropped_no_county_or_date": len(out) - len(kept),
                         "layer_years": f"{YEARS.start}-{YEARS.stop - 1}"}}
