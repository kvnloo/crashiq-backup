"""Missouri crash source: the Missouri State Highway Patrol's public STARS crash layer (the ArcGIS service behind MSHP's
"Traffic Crashes Online Mapping", www.mshp.dps.missouri.gov/TR15Map), every Missouri Uniform Crash Report in STARS,
statewide, no login.

One row per crash: report number, agency, date and time, killed, injured, disabling and minor injuries, MSHP's crash
severity (Fatal / Personal Injury / Property Damage), county and city, the officer's "On" and "Intersecting" roads with
the distance, roadway direction and After / Before / At (MUCR Preparation Manual 2019, Location, p. 40-41), light,
first-harmful-event type, the driver flags and GPS. No driver, vehicle or person rows.

Severity: MSHP keeps only two injury counts. A disabling (suspected serious) injury is A; a minor injury covers
MUCR's evident and probable injuries, B and C together (MoDOT EPG 905.3.6.1.4: "Minor Injury: B & C"), so it is U.

Licence: none published (research_notes/mo-2026-11-08/mo-import.md § Licence). Wired in by statepacks/mo.py.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

LAYER = "https://www.mshp.dps.missouri.gov/arcgis/rest/services/STARS_CRASHES/MapServer/0"
FIRST_YEAR = 2013               # the layer has 2002, part of 2003, then nothing until 2013 (counted 2026-11-08)
MO_LAT, MO_LON = (35.9, 40.7), (-95.8, -89.0)
REF = Path(__file__).resolve().parents[3] / "data" / "reference"

# The officer's road prefixes (MUCR "On" field): city street, county road, private road, alley: the name follows
NAME_PREFIX = ("CST ", "CRD ", "PVT ", "ALY ")
# "Intersecting" entries that are not a street: MoDOT ramp / reference point, emergency reference marker, bridge,
# crossover, weigh station
NOT_A_STREET = ("RP ", "ERM ", "BRIDGE ", "CO ", "WS ")
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
CCRS_TYPE = {"Pedestrian": "VEHICLE/PEDESTRIAN", "Fixed Object": "HIT OBJECT", "Other Object": "HIT OBJECT",
             "Overturn": "OVERTURNED", "Overturning": "OVERTURNED"}
CCRS_LIGHT = {"Daylight": "DAYLIGHT", "Dark-Lighted": "DARK - STREET LIGHTS", "Dark-Unlighted": "DARK - NO STREET LIGHTS",
              "Dark-Unknown Lighting": "DARK - UNKNOWN STREET LIGHTS"}


def _county_fips() -> dict[str, str]:
    boxes = json.loads((REF / "county_boxes_mo.json").read_text())["counties"]
    return {v["name"].upper().removesuffix(" COUNTY"): k for k, v in boxes.items()}   # "ST. LOUIS CITY" stays


FIPS = _county_fips()


def _s(v) -> str | None:
    return (str(v).strip() or None) if v is not None else None


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and MO_LAT[0] <= lat <= MO_LAT[1] and MO_LON[0] <= lon <= MO_LON[1]


def road(raw: str | None) -> str | None:
    """MSHP's road text -> a name the locator reads: 'CST DALE AVE' -> 'DALE AVE', 'IS 70' -> 'I 70'; 'MO 78',
    'US 40', 'RT J' as written. A parking-lot line ('PP PARKING LOT AT ...') is no road."""
    s = _s(raw)
    if not s or s.startswith("PP "):
        return None
    if s.startswith(NAME_PREFIX):
        return s[4:].strip() or None
    return "I " + s[3:] if s.startswith("IS ") else s


def severity(a: dict) -> str:
    if a.get("SEVERITY") == "Fatal" or (a.get("KILLED") or 0) > 0:
        return "K"
    if (a.get("DIS_INJ") or 0) > 0:
        return "A"
    return "U" if a.get("SEVERITY") == "Personal Injury" or (a.get("INJURED") or 0) > 0 else "O"


def offset(a: dict) -> tuple[int | None, str | None]:
    """Feet from the intersecting road and the compass way to go: 'After' is along the roadway direction,
    'Before' against it (MUCR Preparation Manual 2019, Location, p. 40-41); 'AT' is at the intersection."""
    loc, way, ft = _s(a.get("INTER_LOC")), _s(a.get("DIRECTION")), a.get("DIST_FEET") or 0
    if loc not in ("A", "B") or way not in OPPOSITE or ft <= 0:
        return None, None
    return int(ft), way if loc == "A" else OPPOSITE[way]


def contract_record(a: dict) -> dict:
    """One layer row -> the shared crash dict (packs.check_crash)."""
    lat, lon = a.get("GPS_LAT"), a.get("GPS_LONG")
    has = plausible(lat, lon)
    day = datetime.fromtimestamp(a["ACC_DATE"] / 1000, tz=timezone.utc).date() if a.get("ACC_DATE") else None
    t = _s(a.get("ACC_TIME")) or ""
    hour = int(t[:2]) if len(t) >= 5 and t[:2].isdigit() and int(t[:2]) < 24 else None
    at = _s(a.get("AT_STREET"))
    ft, way = offset(a)
    county = (_s(a.get("COUNTY")) or "").upper()
    on = _s(a.get("ON_STREET")) or ""
    kind = _s(a.get("ACC_TYPE"))
    return {"crash_id": f"{_s(a.get('ACCIDENT'))}-{_s(a.get('AGENCY'))}", "report_version": 0, "deleted": False,
            "preliminary": bool(day and day.year >= date.today().year),
            "date": day.isoformat() if day else "", "year": day.year if day else None, "hour": hour,
            "day_of_week": day.strftime("%A") if day else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": road(on), "secondary_road": None if not at or at.startswith(NOT_A_STREET) else road(at),
            "offset_ft": ft, "offset_dir": way,
            "city": _s(a.get("CITY")), "county_code": county or None, "county_fips": FIPS.get(county), "state": "MO",
            "is_freeway": on.startswith("IS "),
            "killed": int(a.get("KILLED") or 0), "injured": int(a.get("INJURED") or 0), "severity": severity(a),
            "ped": kind == "Pedestrian", "bike": kind == "Pedalcycle", "ebike": False, "escooter": False,
            "motorcycle": _s(a.get("MOTORCYCLE")) == "Y", "heavy_truck": _s(a.get("CMV")) == "Y", "parties": [],
            "collision_type": CCRS_TYPE.get(kind, kind.upper() if kind else None),
            "lighting": CCRS_LIGHT.get(_s(a.get("LIGHT_COND")), (_s(a.get("LIGHT_COND")) or "").upper() or None),
            "weather": None, "surface": None,
            "dui": "Y" in (_s(a.get("DR_DRINK")), _s(a.get("DR_DRUG"))), "speeding": _s(a.get("SPEED")) == "Y",
            "hit_and_run": _s(a.get("LEFT_SCENE")) == "Y", "agency": _s(a.get("AGENCY")),
            "location_text": " / ".join(x for x in (on, at) if x) or None,
            "disabling_injuries": int(a.get("DIS_INJ") or 0), "minor_injuries": int(a.get("MIN_INJ") or 0)}


# -- the layer ---------------------------------------------------------------------------------------------------
def _post(url: str, params: dict) -> dict:
    import httpx
    resp = httpx.post(url, data=params, headers={"User-Agent": "CrashIQ/0.1"}, timeout=300)
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:                    # ArcGIS reports query errors with HTTP 200
        raise RuntimeError(f"MSHP crash layer error: {body['error']}")
    return body


def attributes(where: str, get, page: int = 2000) -> list[dict]:
    """Every row matching `where`, paged by object id."""
    ids = sorted(get(LAYER + "/query", {"where": where, "returnIdsOnly": "true", "f": "json"}).get("objectIds") or [])
    out = []
    for i in range(0, len(ids), page):
        body = get(LAYER + "/query", {"objectIds": ",".join(map(str, ids[i:i + page])), "outFields": "*",
                                      "returnGeometry": "false", "f": "json"})
        out += [f["attributes"] for f in body["features"]]
    return out


def where(box, year: int, counties: list[str]) -> str:
    """One year: crashes with a point in the box, plus those with no usable point in the corridor's counties (the
    core places those by street name)."""
    s, w, n, e = box
    area = ", ".join("'" + c.replace("'", "''") + "'" for c in counties) or "''"
    return (f"ACC_DATE >= '{year}-01-01 00:00:00' AND ACC_DATE < '{year + 1}-01-01 00:00:00' AND "
            f"((GPS_LAT >= {s:.6f} AND GPS_LAT <= {n:.6f} AND GPS_LONG >= {w:.6f} AND GPS_LONG <= {e:.6f}) OR "
            f"((GPS_LAT IS NULL OR GPS_LAT < {MO_LAT[0]} OR GPS_LAT > {MO_LAT[1]}) AND COUNTY IN ({area})))")


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path | None, get=None) -> dict:
    get = get or _post
    names = {v: k for k, v in FIPS.items()}
    counties = sorted(names[f] for f in county_fips if f in names)
    rows: list[dict] = []
    for y in [y for y in years if y >= FIRST_YEAR]:
        q = where(box, y, counties)
        cache = cache_dir / f"mo_mshp_{hashlib.sha1(q.encode()).hexdigest()[:10]}.json" if cache_dir else None
        if cache and cache.exists():
            rows += json.loads(cache.read_text())
            continue
        got = attributes(q, get)
        if cache and y < date.today().year:          # the current year still grows; never freeze it
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(got))
        rows += got
    recs = [contract_record(a) for a in rows]
    have = {r["year"] for r in recs}
    out = [r for r in recs if r["county_fips"]]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "no_county": len(recs) - len(out),
                         "no_gps": sum(r["lat"] is None for r in out),
                         "severity": "K/A/U/O: MSHP's minor injury is MUCR's B and C together"}}
