"""Ohio crash source: ODOT's public crash layers in TIMS (Transportation Information Mapping System), one ArcGIS map
service per year (Safety/<year>_Crash_Locations), no login.

Each row is one OH-1 crash report as ODOT's crash system holds it (ODPS data): document number, year, month, day of
week, hour, KABCO crash severity, crash type, ODOT's location type (intersection kind, ramp, driveway), functional
class, lanes, county, the GPS point and the ODOT route (NLFID) and log point it sits on. The public layer has no street
names, no day of the month, no people counts and no light, weather or surface.

Severity is KABCO as ODOT gives it (1 Fatal, 2 Serious Injury Suspected, 3 Minor Injury Suspected, 4 Injury Possible,
5 PDO/No Injury). The 2025 layer's 264,530 crashes and 1,033 fatal crashes match ODOT's own 2025 counts (CrashCostsUpdate.pdf,
p. 1: 264,529 and 1,033), measured 2026-11-08.

Licence: TIMS's notice, "The data published within the Ohio Department of Transportation (ODOT) TIMS application is in
the public domain and as such it is not copyrighted" (https://tims.dot.state.oh.us/tims/support); the REST endpoints
"are maintained to support the TIMS application and are subject to change without notice".
Wired into the app through the OH state pack (statepacks/oh.py) by `fetch_contract`.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE = "https://tims.dot.state.oh.us/ags/rest/services/Safety/{year}_Crash_Locations/MapServer/0/query"
PAGE = 2000
OH_LAT, OH_LON = (38.3, 42.4), (-84.9, -80.4)        # Ohio's extent (Lake Erie line included) with a small margin
FIELDS = ("DOCUMENT_NBR", "CRASH_YR", "MONTH_OF_CRASH", "DAY_IN_WEEK_CD", "HOUR_OF_CRASH", "CRASH_SEVERITY_CD",
          "CRASH_TYPE_CD", "CRASH_TYPE_TXT", "ODOT_CRASH_LOCATION_TXT", "FUNCTIONAL_CLASS_CD", "ODOT_LANES_NBR",
          "COUNTY_CD", "ODOT_LATITUDE_NBR", "ODOT_LONGITUDE_NBR", "NLFID", "CTL_BEGIN_NBR")
SEVERITY = {1: "K", 2: "A", 3: "B", 4: "C", 5: "O"}
# 1 = Sunday: inferred from 2024's counts by code (1 lowest, 6 highest = Friday, 7 Saturday); ODOT's code list not found
DOW = {1: "Sunday", 2: "Monday", 3: "Tuesday", 4: "Wednesday", 5: "Thursday", 6: "Friday", 7: "Saturday"}
# ODOT's crash types -> the CCRS words the profile and the collision diagram read; any other type keeps ODOT's words
CCRS_TYPE = {"Rear End": "REAR END", "Angle": "BROADSIDE", "Head On": "HEAD-ON", "Sideswipe - Passing": "SIDE SWIPE",
             "Sideswipe - Meeting": "SIDE SWIPE", "Fixed Object": "HIT OBJECT", "Other Object": "HIT OBJECT",
             "Overturning": "OVERTURNED", "Pedestrian": "VEHICLE/PEDESTRIAN"}
# ODOT's 3-letter county codes sort in the same order as the county names, and Ohio's FIPS run 001, 003 ... by name
CODES = ("ADA ALL ASD ATB ATH AUG BEL BRO BUT CAR CHP CLA CLE CLI COL COS CRA CUY DAR DEF DEL ERI FAI FAY FRA FUL GAL "
         "GEA GRE GUE HAM HAN HAR HAS HEN HIG HOC HOL HUR JAC JEF KNO LAK LAW LIC LOG LOR LUC MAD MAH MAR MED MEG MER "
         "MIA MOE MOT MRG MRW MUS NOB OTT PAU PER PIC PIK POR PRE PUT RIC ROS SAN SCI SEN SHE STA SUM TRU TUS UNI VAN "
         "VIN WAR WAS WAY WIL WOO WYA").split()
FIPS = {c: f"39{2 * i + 1:03d}" for i, c in enumerate(CODES)}
# NLFID: system letter + county code + route type + 5-digit number (SFRAIR00070**C = I-70 in Franklin County)
NLFID = re.compile(r"^[A-Z][A-Z]{3}(IR|US|SR)(\d{5})")
ROUTE = {"IR": "I-{}", "US": "US {}", "SR": "SR {}"}


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and OH_LAT[0] <= lat <= OH_LAT[1] and OH_LON[0] <= lon <= OH_LON[1])


def route(nlfid: str | None) -> str | None:
    """The interstate, US or state route a crash's NLFID names ('I-70', 'US 23', 'SR 161'); None on other roads
    (county, township and municipal NLFIDs carry an inventory number, not a street name)."""
    m = NLFID.match(nlfid or "")
    return ROUTE[m.group(1)].format(int(m.group(2))) if m else None


def contract_record(a: dict) -> dict:
    """One TIMS crash row (attributes) -> the shared crash dict (packs.check_crash)."""
    lat, lon = a.get("ODOT_LATITUDE_NBR"), a.get("ODOT_LONGITUDE_NBR")
    has = plausible(lat, lon)
    year = a.get("CRASH_YR")
    hour = a.get("HOUR_OF_CRASH")
    ctype = (a.get("CRASH_TYPE_TXT") or "").strip() or None
    fc = a.get("FUNCTIONAL_CLASS_CD")
    rt = route(a.get("NLFID"))
    return {"crash_id": str(a["DOCUMENT_NBR"]), "report_version": 0, "deleted": False,
            "preliminary": bool(year and year >= date.today().year),
            "date": "",                       # the public layer has the month, not the day: never invent one
            "year": year, "month": a.get("MONTH_OF_CRASH"), "hour": hour if hour is not None and 0 <= hour < 24 else None,
            "day_of_week": DOW.get(a.get("DAY_IN_WEEK_CD")),
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,
            "city": None, "county_code": a.get("COUNTY_CD"), "county_fips": FIPS.get(a.get("COUNTY_CD") or ""),
            "state": "OH", "is_freeway": fc in (1, 2),            # FHWA functional class 1-2: interstates, freeways
            "killed": 0, "injured": 0,                             # not in the public layer (PACK.data_notes)
            "severity": SEVERITY.get(a.get("CRASH_SEVERITY_CD")),   # an unknown code is dropped, never guessed
            "ped": a.get("CRASH_TYPE_CD") == 8, "bike": a.get("CRASH_TYPE_CD") == 11, "ebike": False,
            "escooter": False, "motorcycle": False, "heavy_truck": False, "parties": [],
            "collision_type": CCRS_TYPE.get(ctype, ctype.upper() if ctype else None),
            "lighting": None, "weather": None, "surface": None,
            "road_number": rt, "nlfid": a.get("NLFID"), "log_point": a.get("CTL_BEGIN_NBR"),
            "location_type": a.get("ODOT_CRASH_LOCATION_TXT"), "functional_class": fc, "lanes": a.get("ODOT_LANES_NBR")}


# -- the service -------------------------------------------------------------------------------------------------
def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "CrashIQ/0.1"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def query_year(box, year: int, get=_get) -> list[dict] | None:
    """Every crash row with its point in the box (s, w, n, e) in one year; None when TIMS has no service for it."""
    s, w, n, e = box
    where = (f"ODOT_LATITUDE_NBR >= {s} AND ODOT_LATITUDE_NBR <= {n} AND "
             f"ODOT_LONGITUDE_NBR >= {w} AND ODOT_LONGITUDE_NBR <= {e}")
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"where": where, "outFields": ",".join(FIELDS), "returnGeometry": "false",
                                    "orderByFields": "OBJECTID", "resultOffset": offset, "resultRecordCount": PAGE,
                                    "f": "json"})
        got = get(BASE.format(year=year) + "?" + q)
        if "error" in got:
            if got["error"].get("code") == 404 and offset == 0:          # {"code":404,"message":"Service not found"}
                return None
            raise RuntimeError(f"TIMS {year} query error: {got['error']}")
        feats = got.get("features") or []
        rows += [f["attributes"] for f in feats]
        if len(feats) < PAGE and not got.get("exceededTransferLimit"):
            return rows
        offset += len(feats)


def fetch_year(box, year: int, cache_dir: Path | None, get=_get) -> list[dict] | None:
    key = hashlib.sha1(f"{box}|{year}".encode()).hexdigest()[:10]
    cache = cache_dir / f"oh_tims_{key}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    rows = query_year(box, year, get)
    if cache and rows is not None and year < date.today().year:      # the current year still grows; never freeze it
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows))
    return rows


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, get=_get) -> dict:
    """Every crash with a GPS point in the box (s, w, n, e) in those years. TIMS's layers are points, so every crash
    in them has GPS; a year TIMS has no service for is `years_missing` (never half-counted)."""
    recs, missing, raw = [], [], 0
    for y in years:
        rows = fetch_year(box, y, cache_dir, get)
        if rows is None:
            missing.append(y)
            continue
        raw += len(rows)
        recs += [contract_record(r) for r in rows]
    out = [r for r in recs if r["county_fips"] and r["severity"]]
    return {"crashes": out, "years_missing": missing,
            "cleaning": {"source_rows": raw, "no_county_or_severity": len(recs) - len(out),
                         "no_day_of_month": len(out)}}
