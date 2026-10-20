"""California crash source: CHP's CCRS open data on data.ca.gov (public domain).

One adapter per state lives in `crashiq.sources`. Each returns crashes in the shared
shape documented on `CRASH_FIELDS`, so the locate/assign/profile engine never sees a
state-specific column name.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://data.ca.gov/api/3/action/"
PACKAGE = "ccrs"

# Shared crash shape (all states map onto this).
CRASH_FIELDS = (
    "crash_id", "report_number", "agency_code", "datetime", "lat", "lon",
    "primary_road", "secondary_road", "offset_ft", "offset_dir", "is_freeway",
    "collision_type", "killed", "injured", "beat",
)

_COLUMNS = {
    "crash_id": "Collision Id", "report_number": "Report Number", "agency_code": "NCIC Code",
    "datetime": "Crash Date Time", "lat": "Latitude", "lon": "Longitude",
    "primary_road": "PrimaryRoad", "secondary_road": "SecondaryRoad",
    "_dist": "SecondaryDistance", "offset_dir": "SecondaryDirection", "_unit": "SecondaryUnitOfMeasure",
    "is_freeway": "IsFreeway", "collision_type": "Collision Type Description",
    "killed": "NumberKilled", "injured": "NumberInjured", "_deleted": "IsDeleted", "beat": "Beat",
}
_UNIT_FT = {"F": 1.0, "M": 5280.0, "Y": 3.0}  # feet, miles, yards


def _get(action: str, **params) -> dict:
    url = API + action + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):  # data.ca.gov returns occasional 502/504 under load
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                body = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504) or attempt == 3:
                raise
            time.sleep(2 ** attempt * 3)
    if not body.get("success"):
        raise RuntimeError(f"CCRS API error: {body.get('error')}")
    return body["result"]


def crash_resource_ids() -> dict[int, str]:
    """Year -> datastore resource id, resolved at runtime (ids change when CHP republishes)."""
    pkg = _get("package_show", id=PACKAGE)
    out = {}
    for res in pkg["resources"]:
        name = res.get("name", "")
        if name.startswith("Crashes_") and res.get("datastore_active"):
            out[int(name.split("_")[1])] = res["id"]
    return out


def _normalize(rec: dict) -> dict:
    c = {k: rec.get(v) for k, v in _COLUMNS.items()}
    c.pop("_deleted")
    dist, unit = c.pop("_dist"), (c.pop("_unit") or "F").strip().upper()
    c["offset_ft"] = float(dist) * _UNIT_FT.get(unit, 1.0) if dist not in (None, "") else None
    # Cleaning rule (2026-10-18): a "miles" offset over 2 is feet typed as miles (73 "miles" from 3rd St).
    c["offset_fixed"] = False
    if c["offset_ft"] is not None and unit == "M" and float(dist) > 2:
        c["offset_ft"], c["offset_fixed"] = float(dist), True
    c["is_freeway"] = str(c["is_freeway"]) == "True"
    c["report_number"] = str(c["report_number"] or "").strip()
    c["agency_code"] = str(c["agency_code"] or "").strip()
    for k in ("primary_road", "secondary_road", "offset_dir", "beat"):
        c[k] = (str(c[k]) if c[k] is not None else "").strip() or None
    return c


def fetch(year: int, where: str, cache_dir: Path, page: int = 5000) -> list[dict]:
    """All crashes for `year` matching a SQL `where` clause, cached as JSON. Cleaning counts: `cleaning_log`."""
    return _fetch(year, where, cache_dir, page)["rows"]


def cleaning_log(year: int, where: str, cache_dir: Path) -> dict:
    """Counts per cleaning step for a cached pull: rows read, CHP-deleted dropped, feet-typed-as-miles fixed."""
    return _fetch(year, where, cache_dir)["cleaning"]


def _fetch(year: int, where: str, cache_dir: Path, page: int = 5000) -> dict:
    cache = cache_dir / f"ccrs_{year}_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json"
    if cache.exists():
        data = json.loads(cache.read_text())
        if isinstance(data, dict):
            return data
    rid = crash_resource_ids()[year]
    cols = ", ".join(f'"{v}"' for v in _COLUMNS.values())
    raw, offset = [], 0
    while True:
        sql = f'SELECT {cols} FROM "{rid}" WHERE {where} ORDER BY "Collision Id" LIMIT {page} OFFSET {offset}'
        batch = _get("datastore_search_sql", sql=sql)["records"]
        raw += batch
        if len(batch) < page:
            break
        offset += page
    rows = [_normalize(r) for r in raw if str(r.get("IsDeleted")) != "True"]  # CHP-deleted reports
    data = {"rows": rows, "cleaning": {
        "rows_read": len(raw),
        "deleted_dropped": len(raw) - len(rows),
        "feet_typed_as_miles_fixed": sum(1 for c in rows if c["offset_fixed"]),
    }}
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


# =====================================================================================================
# Product adapter (C3, #9): the three CCRS tables for one corridor study, cleaned, in a state-neutral shape.
# Everything California-specific (resource names, column names, code values, severity mapping) lives here,
# so a later state pack replaces this file and the rest of CrashIQ is unchanged (#19).
# =====================================================================================================

TABLE_PREFIX = {"crashes": "crashes_", "parties": "parties_", "iwp": "injuredwitnesspassengers_"}

# Logical field -> candidate column names (resolved against the live datastore at runtime; CHP has renamed
# columns between exports, and the published layout doc doesn't always match the datastore).
CRASH_COLS = {
    "collision_id": ["Collision Id", "CollisionId"],
    "report_version": ["Report Version", "ReportVersion"],
    "is_preliminary": ["Is Preliminary", "IsPreliminary"],
    "is_deleted": ["IsDeleted", "Is Deleted"],
    "datetime": ["Crash Date Time", "CrashDateTime"],
    "collision_time": ["Collision Time", "CollisionTime"],
    "day_of_week": ["Day of Week", "DayOfWeek"],
    "lat": ["Latitude"],
    "lon": ["Longitude"],
    "primary_road": ["PrimaryRoad", "Primary Road", "Primary Rd"],
    "secondary_road": ["SecondaryRoad", "Secondary Road", "Secondary Rd"],
    "sec_distance": ["SecondaryDistance"],
    "sec_direction": ["SecondaryDirection"],
    "sec_unit": ["SecondaryUnitOfMeasure"],
    "city_code": ["City Code", "CityCode"],
    "city_name": ["City Name", "CityName"],
    "county_code": ["County Code", "CountyCode"],
    "ncic": ["NCIC Code", "NCICCode"],
    "collision_type": ["Collision Type Description", "CollisionTypeDescription"],
    "killed": ["NumberKilled", "Number Killed"],
    "injured": ["NumberInjured", "Number Injured"],
    "lighting": ["LightingDescription", "Lighting Description"],
    "weather": ["Weather 1", "Weather1"],
    "surface": ["RoadwaySurfaceDescription", "Roadway Surface Description", "RoadwaySurfaceCode"],
    "pcf": ["PrimaryCollisionFactorViolation", "Primary Collision Factor Violation", "PCF Violation"],
    "pcf_category": ["PrimaryCollisionFactorDescription", "Primary Collision Factor Description"],
    "involved_with": ["MotorVehicleInvolvedWithDesc", "Motor Vehicle Involved With Desc"],
    "ped_action": ["PedestrianActionDesc"],
    "hit_run": ["HitRun", "Hit Run"],
    "is_freeway": ["IsFreeway", "IsFreeWay"],
}
CRASH_REQUIRED = ("collision_id", "datetime", "lat", "lon", "primary_road", "secondary_road", "killed", "injured")

PARTY_COLS = {
    "collision_id": ["CollisionId", "Collision Id"],
    "party_number": ["PartyNumber", "Party Number"],
    "party_type": ["PartyType", "Party Type"],
    "at_fault": ["IsAtFault", "Is At Fault"],
    "movement": ["MovementPrecCollDescription", "Movement Prec Coll Description", "MovementPrecCollCode"],
    "vehicle_type": ["Vehicle1TypeDesc", "Vehicle 1 Type Desc"],
    "age": ["StatedAge", "Stated Age"],
    "direction": ["DirectionOfTravel", "Direction Of Travel"],
}
IWP_COLS = {
    "collision_id": ["CollisionId", "Collision Id"],
    "extent": ["ExtentOfInjury", "Extent Of Injury", "ExtentOfInjuryCode"],
    "person_type": ["InjuredPersonType", "Injured Person Type"],
    "witness_only": ["IsWitnessOnly", "Is Witness Only"],
}

SURFACE_CODES = {"A": "DRY", "B": "WET", "C": "SNOWY-ICY", "D": "SLIPPERY (MUDDY, OILY, ETC.)"}

# Extent of injury -> KABCO, keyed on the value with spaces and punctuation removed. The live table
# (`ExtentOfInjuryCode`) holds CODES, not the data dictionary's text (#75, 2026-10-19): Fatal, SuspectSerious,
# SuspectMinor, PossibleInjury, plus retired SWITRS levels kept on older reports (SevereInactive = severe injury,
# OtherVisibleInactive = other visible injury, ComplaintOfPainInactive = complaint of pain), which follow the
# standard SWITRS -> KABCO crosswalk (nuance N3). The dictionary text is mapped too.
KABCO = {
    "FATAL": "K", "FATALINJURY": "K", "KILLED": "K",
    "SUSPECTSERIOUS": "A", "SUSPECTEDSERIOUSINJURY": "A", "SEVEREINACTIVE": "A", "SEVEREINJURY": "A",
    "SUSPECTMINOR": "B", "SUSPECTEDMINORINJURY": "B", "OTHERVISIBLEINACTIVE": "B", "OTHERVISIBLEINJURY": "B",
    "POSSIBLEINJURY": "C", "COMPLAINTOFPAININACTIVE": "C", "COMPLAINTOFPAIN": "C",
}
NO_INJURY = {"", "NONE", "NOINJURY", "NOTINJURED"}   # blank = this person has no injury level (witness, uninjured)


def kabco(extent) -> str | None:
    return KABCO.get("".join(ch for ch in str(extent if extent is not None else "").upper() if ch.isalnum()))


SEVERITY_ORDER = "KABCUO"   # U = injured but the injury level wasn't reported (no IWP row); O = property damage only

TRUCK_WORDS = ("TRUCK TRACTOR", "TRACTOR", "SEMI", "HEAVY TRUCK", "TRUCK OR TRUCK TRACTOR")
MOTORCYCLE_WORDS = ("MOTORCYCLE", "MOTOR CYCLE", "MOTORCYCLE/SCOOTER", "MOTOR SCOOTER", "MOPED")


def _norm_col(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def resolve_columns(fields: list[dict], wanted: dict[str, list[str]]) -> tuple[dict[str, dict], list[str]]:
    """Map logical names to the datastore's real columns ({id, type}); returns (mapping, missing logical names)."""
    by_norm = {_norm_col(f["id"]): f for f in fields}
    out, missing = {}, []
    for logical, cands in wanted.items():
        hit = next((by_norm[_norm_col(c)] for c in cands if _norm_col(c) in by_norm), None)
        if hit:
            out[logical] = hit
        else:
            missing.append(logical)
    return out, missing


def table_resources(package: dict) -> dict[str, dict[int, str]]:
    """{'crashes': {2021: id, ...}, 'parties': {...}, 'iwp': {...}}; datastore-queryable resources only."""
    out: dict[str, dict[int, str]] = {k: {} for k in TABLE_PREFIX}
    for res in package.get("resources", []):
        name = str(res.get("name", "")).lower().replace(" ", "")
        if not res.get("datastore_active"):
            continue
        for table, prefix in TABLE_PREFIX.items():
            if name.startswith(prefix):
                tail = name[len(prefix):][:4]
                if tail.isdigit():
                    out[table][int(tail)] = res["id"]
    return out


# CHP stores many description fields with their code letter ("C-DARK-STREET LIGHTS", "A - Clear", "F – Felony")
# and keeps its own spellings ("VEHICLE/PEDESTRAIN"). Normalize once here so every table and test sees one form.
_CODE_PREFIX = re.compile(r"^\s*[A-Z]\s*[-\u2013\u2014]\s*(?=\S)")
_SPELLING = {"VEHICLE/PEDESTRAIN": "VEHICLE/PEDESTRIAN", "PEDESTRAIN": "PEDESTRIAN"}
CODED_FIELDS = ("collision_type", "lighting", "weather", "surface", "involved_with", "ped_action", "hit_run")


def clean_coded(v):
    if v is None:
        return None
    t = _CODE_PREFIX.sub("", str(v)).strip()
    return _SPELLING.get(t.upper(), t) or None


# California's extent, with a small margin: anything outside is a bad coordinate, not a location.
CA_LAT, CA_LON = (32.4, 42.1), (-124.6, -114.0)


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and CA_LAT[0] <= lat <= CA_LAT[1] and CA_LON[0] <= lon <= CA_LON[1])


_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{1,2}):(\d{2}))?")
_US = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::\d{2})?\s*([AP]M)?)?", re.I)


def parse_dt(raw) -> tuple[str | None, int | None, int | None]:
    """(ISO date, year, hour or None) from 'YYYY-MM-DD[ T]HH:MM…' or 'MM/DD/YYYY[ HH:MM[:SS] [AM|PM]]'.
    (None, None, None) when the text isn't a date we recognize; the caller counts those."""
    t = str(raw or "").strip()
    m = _ISO.match(t)
    if m:
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        h = int(m[4]) if m[4] else None
    else:
        m = _US.match(t)
        if not m:
            return None, None, None
        mo, d, y = int(m[1]), int(m[2]), int(m[3])
        h = int(m[4]) if m[4] else None
        if h is not None and m[6]:
            h = h % 12 + (12 if m[6].upper() == "PM" else 0)
    if not (1 <= mo <= 12 and 1 <= d <= 31 and 1990 <= y <= 2100) or (h is not None and not 0 <= h <= 23):
        return None, None, None
    return f"{y:04d}-{mo:02d}-{d:02d}", y, h


def q(col: str) -> str:
    return '"' + col.replace('"', '""') + '"'


def num_expr(field: dict) -> str:
    """A numeric SQL expression for a column, whether the datastore stored it as number or text."""
    col = q(field["id"])
    if field.get("type", "text") in ("numeric", "float8", "int4", "int8", "float", "int"):
        return col
    return f"CAST(NULLIF({col}, '') AS float)"


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "t", "yes", "y")


def _num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _hour(dt_hour: int | None, ctime) -> int | None:
    t = str(ctime or "").strip()
    if t.isdigit() and len(t) <= 4:
        t = t.zfill(4)
        h = int(t[:2])
        return h if 0 <= h <= 23 else None
    return dt_hour


def crash_record(raw: dict, cols: dict[str, dict]) -> dict:
    """One CCRS Crashes row -> the shared crash shape (no severity yet; that needs IWP)."""
    g = lambda k: raw.get(cols[k]["id"]) if k in cols else None
    date, year, dt_hour = parse_dt(g("datetime"))
    lat, lon = _num(g("lat")), _num(g("lon"))
    has = plausible(lat, lon)
    dist, unit = _num(g("sec_distance")), str(g("sec_unit") or "F").strip().upper()[:1]
    offset = dist * _UNIT_FT.get(unit, 1.0) if dist is not None else None
    fixed = offset is not None and unit == "M" and dist > 2
    if fixed:                                                 # feet typed as miles (2026-10-18 cleaning rule)
        offset = dist
    surface = g("surface")
    surface = SURFACE_CODES.get(str(surface).strip()[:1], surface) if surface is not None and len(str(surface).strip()) == 1 else surface
    s = lambda v: (str(v).strip() or None) if v is not None else None
    return {
        "crash_id": str(g("collision_id")),
        "report_version": int(_num(g("report_version")) or 0),
        "preliminary": _truthy(g("is_preliminary")),
        "deleted": _truthy(g("is_deleted")),
        "date": date or "",
        "year": year,
        "hour": _hour(dt_hour, g("collision_time")),
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "day_of_week": s(g("day_of_week")),
        "lat": lat if has else None,
        "lon": lon if has else None,
        "primary_road": s(g("primary_road")),
        "secondary_road": s(g("secondary_road")),
        "offset_ft": offset,
        "offset_dir": s(g("sec_direction")),
        "offset_fixed": fixed,
        "city": s(g("city_name")) or s(g("city_code")),
        "city_code": s(g("city_code")),
        "county_code": s(g("county_code")),
        "collision_type": clean_coded(s(g("collision_type"))),
        "killed": int(_num(g("killed")) or 0),
        "injured": int(_num(g("injured")) or 0),
        "lighting": clean_coded(s(g("lighting"))),
        "weather": clean_coded(s(g("weather"))),
        "surface": clean_coded(s(surface)),
        "pcf": s(g("pcf")),
        "pcf_category": s(g("pcf_category")),
        "involved_with": clean_coded(s(g("involved_with"))),
        "ped_action": clean_coded(s(g("ped_action"))),
        "hit_run": clean_coded(s(g("hit_run"))),
        "is_freeway": _truthy(g("is_freeway")),
    }


def party_record(raw: dict, cols: dict[str, dict]) -> dict:
    g = lambda k: raw.get(cols[k]["id"]) if k in cols else None
    s = lambda v: (str(v).strip() or None) if v is not None else None
    return {"party_number": s(g("party_number")),
            "party_type": (s(g("party_type")) or "").upper() or None, "at_fault": _truthy(g("at_fault")),
            "movement": s(g("movement")), "vehicle_type": s(g("vehicle_type")), "age": s(g("age")),
            "direction": s(g("direction"))}


def severity(crash: dict, iwp_extents: list[str] | None) -> tuple[str, list[str]]:
    """Most severe outcome of the crash, counted once (KABCO + U + O). Returns (code, unknown extent values)."""
    unknown = []
    best = "O"
    for e in iwp_extents or []:
        k = kabco(e)
        if k is None:
            raw = "" if e is None else str(e).strip()
            if "".join(ch for ch in raw.upper() if ch.isalnum()) not in NO_INJURY:
                unknown.append(raw)
            continue
        if SEVERITY_ORDER.index(k) < SEVERITY_ORDER.index(best):
            best = k
    if crash["killed"] > 0:
        best = "K"
    elif best == "O" and crash["injured"] > 0:
        best = "U"                                   # injured, level not reported
    return best, unknown


def mode_flags(crash: dict, parties: list[dict]) -> dict:
    types = {p["party_type"] for p in parties if p["party_type"]}
    vehicles = " | ".join((p["vehicle_type"] or "").upper() for p in parties)
    iw = (crash.get("involved_with") or "").upper()
    ct = (crash.get("collision_type") or "").upper()
    return {
        "ped": "PEDESTRIAN" in types or "PEDESTRIAN" in iw or "PEDESTR" in ct,
        "bike": "BICYCLIST" in types or "BICYCLE" in iw,
        "motorcycle": any(w in vehicles for w in MOTORCYCLE_WORDS),
        "heavy_truck": any(w in vehicles for w in TRUCK_WORDS),
    }
