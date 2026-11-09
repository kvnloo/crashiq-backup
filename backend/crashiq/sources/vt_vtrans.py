"""Vermont crash source: VTrans "CrashPQT", the open ArcGIS layer behind the VTrans Public Crash Data Query Tool
(https://apps.vtrans.vermont.gov/CrashPublicQueryTool/), public, no login.

One row per crash report, 2010 to now (updated near-daily; latest 2026-11-06 at the 2026-11-08 check). Point on
about 98% of rows (VTrans LRS, XY, geocode or officer lat/long), the officer's street (`STREETADDRESS`: "US-7
Shelburne Rd", "28 Killington Ave.") and cross street (`INTERSECTIONWITH`) on most. One crash table: no units or
persons, and no people counts.

Severity is NOT KABCO: `InjuryType` is Fatal / Injury / Property Damage Only, so the pack's crashes are K, U or O and
the pack sets `severity_note`. A row with no InjuryType is almost always a non-reportable crash (`NonReportableAddress`
set, every other detail blank); those aren't read and are counted in `cleaning`.

ACCIDENTDATE is the local wall-clock time sent as if it were UTC (the earliest row is 2010-01-01 00:00 "UTC").
County: VTrans' town id is <county number><2-digit town> with the county number 1-14 in alphabetical order (04xx =
Chittenden), which is FIPS 2n-1 (50007).

Licence: no open licence; the tool's disclaimer (see research_notes/vt-2026-11-08/vt-import.md).
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAYER = "https://services1.arcgis.com/NXmBVyW5TaiCXqFs/arcgis/rest/services/CrashPQT/FeatureServer/0"
PAGE = 2000                                    # the layer's maxRecordCount
BOUNDS = (42.6, -73.5, 45.1, -71.4)            # Vermont's extent with a small margin (s, w, n, e)
SEVERITY = {"Fatal": "K", "Injury": "U", "Property Damage Only": "O"}
INVOLVING = {"Pedestrian": "ped", "Bicycle": "bike", "Motorcycle": "motorcycle", "Heavy Truck": "heavy_truck"}
NO_MILEPOINT = 999.99                          # VTrans' "no LRS measure"


def _s(v):
    return (str(v).strip() or None) if v is not None else None


def plausible(lat, lon) -> bool:
    s, w, n, e = BOUNDS
    return lat is not None and lon is not None and s <= lat <= n and w <= lon <= e


def county_fips(town_id) -> str | None:
    """'0403' or '403' (Burlington) -> '50007' (Chittenden); None when the town id is missing or not a county's."""
    t = _s(town_id)
    n = int(t) // 100 if t and t.isdigit() else 0
    return f"50{2 * n - 1:03d}" if 1 <= n <= 14 else None


def collision_type(v: str | None) -> str | None:
    """VTrans' direction-of-collision text -> CCRS words where it is one CCRS type; mixed types ("Sideswipe/Angle",
    "Head On/Angle"), single-vehicle and rear-to-rear keep VTrans' words."""
    v = _s(v)
    if not v or "/" in v:
        return v.upper() if v else None
    for word, ccrs in (("Broadside", "BROADSIDE"), ("Rear End", "REAR END"), ("Head On", "HEAD-ON"),
                       ("Sideswipe", "SIDE SWIPE")):
        if word in v:
            return ccrs
    return v.upper()


def contract_record(a: dict) -> dict:
    """One layer row -> the shared crash dict (packs.check_crash). Call only on rows with a known InjuryType."""
    lat, lon = a.get("LATITUDE"), a.get("LONGITUDE")
    has = plausible(lat, lon)
    t = datetime.fromtimestamp(a["ACCIDENTDATE"] / 1000, timezone.utc) if a.get("ACCIDENTDATE") is not None else None
    involving = INVOLVING.get(_s(a.get("Involving")) or "")
    mp = a.get("AOTACTUALMILEPOINT")
    route = _s(a.get("AOTROUTE"))
    day = _s(a.get("DayNight"))
    up = lambda v: _s(v).upper() if _s(v) else None
    agency, report = _s(a.get("REPORTINGAGENCYid")), _s(a.get("REPORTNUMBER"))
    return {
        "crash_id": f"{agency}:{report}" if agency and report else f"OID:{a['OBJECTID']}",
        "report_version": 0, "deleted": False,
        "preliminary": bool(t and t.year >= datetime.now(timezone.utc).year),
        "date": t.date().isoformat() if t else "", "year": t.year if t else None, "hour": t.hour if t else None,
        "day_of_week": t.strftime("%A") if t else None,
        "lat": lat if has else None, "lon": lon if has else None,
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "primary_road": _s(a.get("STREETADDRESS")), "secondary_road": _s(a.get("INTERSECTIONWITH")),
        "offset_ft": None, "offset_dir": None,
        "city": up(a.get("CITYORTOWN")), "county_code": _s(a.get("CITYORTOWNid")),
        "county_fips": county_fips(a.get("CITYORTOWNid")), "state": "VT",
        # shortcut: freeway = Interstate routes and their ramps ("I-89", "I-91 EXIT 10 RAMP A"); VT-289 and other
        # limited-access state routes count as arterials; upgrade with VTrans' functional class layer
        "is_freeway": bool(route and route.startswith("I-")),
        "killed": 0, "injured": 0,                          # VTrans publishes no people counts
        "severity": SEVERITY[_s(a.get("InjuryType"))],
        "ped": involving == "ped", "bike": involving == "bike", "ebike": False, "escooter": False,
        "motorcycle": involving == "motorcycle", "heavy_truck": involving == "heavy_truck", "parties": [],
        "collision_type": collision_type(a.get("DirOfCollision")),
        "lighting": {"Day": "DAYLIGHT", "Night": "DARK - UNKNOWN STREET LIGHTS"}.get(day or "", up(day)),
        "weather": up(a.get("Weather")), "surface": up(a.get("SurfaceCondition")),
        "agency": _s(a.get("ReportingAgency")), "report_number": report,
        "route": route, "milepost": None if mp is None or mp >= NO_MILEPOINT else mp,
        "how_mapped": _s(a.get("HOWMAPPED")), "road_group": _s(a.get("RoadGroup")),
    }


def _get(where: str, last: int, opener) -> list[dict]:
    q = {"where": f"({where}) AND OBJECTID>{last}", "outFields": "*", "orderByFields": "OBJECTID",
         "resultRecordCount": PAGE, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(LAYER + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"VTrans CrashPQT query error: {body['error']}")
    return [f["attributes"] for f in body.get("features", [])]


def fetch_raw(where: str, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every raw row matching an ArcGIS `where`, paged by OBJECTID; cached per `where`."""
    cache = cache_dir / f"vt_vtrans_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json" if cache_dir else None
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
    """Crashes with a point in the box (s, w, n, e), plus those with no point in the corridor's counties, in those
    years. Rows with no InjuryType (non-reportable crashes) aren't read."""
    s, w, n, e = box
    when = (f"ACCIDENTDATE >= TIMESTAMP '{min(years)}-01-01 00:00:00' "
            f"AND ACCIDENTDATE < TIMESTAMP '{max(years) + 1}-01-01 00:00:00'")
    raw = fetch_raw(f"LATITUDE >= {s:.6f} AND LATITUDE <= {n:.6f} AND LONGITUDE >= {w:.6f} AND LONGITUDE <= {e:.6f} "
                    f"AND {when}", cache_dir, opener)
    no_gps = fetch_raw(f"(LATITUDE IS NULL OR LATITUDE = 0) AND {when}", cache_dir, opener)   # statewide, ~1-5%/yr
    no_gps = [a for a in no_gps if _fips_in(a, county_fips)]
    rows, log = [], {"source_rows": len(raw) + len(no_gps), "no_gps_rows": len(no_gps), "no_severity_not_read": 0,
                     "no_county_not_read": 0, "outside_years": 0}
    for a in raw + no_gps:
        if _s(a.get("InjuryType")) not in SEVERITY:
            log["no_severity_not_read"] += 1
            continue
        c = contract_record(a)
        if not c["county_fips"]:
            log["no_county_not_read"] += 1
        elif c["year"] not in years:
            log["outside_years"] += 1
        else:
            rows.append(c)
    have = {c["year"] for c in rows}
    return {"crashes": rows, "years_missing": [y for y in years if y not in have], "cleaning": log}


def _fips_in(a: dict, wanted: list[str]) -> bool:
    return county_fips(a.get("CITYORTOWNid")) in wanted     # module-level county_fips (fetch_contract shadows it)
