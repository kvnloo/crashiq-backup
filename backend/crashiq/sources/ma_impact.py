"""Massachusetts crash source: MassDOT IMPACT open data (ArcGIS REST, no login).

Not wired into the app yet (state-pack seam, #19). One FeatureServer per year with Crash, Vehicle and Person layers;
crashes and persons share `CRASH_NUMB`. Severity is KABCO (`MAX_INJR_SVRTY_CL` per crash, `INJY_STAT_DESCR` per
person); reports before 2019 use the older injury words, mapped below. Closed years (2002-2019) say "public domain";
the open years (2020+ on this server) carry only MassDOT's disclaimer (research_notes/ma-2026-11-07/ma-import.md).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

OPEN = "https://gis.crashdata.dot.mass.gov/arcgis/rest/services/MassDOT/MASSDOT_ODP_OPEN_{}/FeatureServer"
CLOSED = "https://gis.massdot.state.ma.us/arcgis/rest/services/CrashClosedYear/CrashClosedYear{}/FeatureServer"
# Hub item URLs (massdot-impact-crashes-vhb.opendata.arcgis.com, 2026-11-07): 2020 sits in its own service and 2023
# is the "v" (versioned) copy. Closed years 2002-2019 follow CLOSED.
SPECIAL = {2020: "https://gis.massdot.state.ma.us/arcgis/rest/services/Roads/CrashClosedYears/FeatureServer",
           2023: OPEN.format("2023v")}
UA = {"User-Agent": "CrashIQ/0.1"}
PAGE = 2000   # the services' maxRecordCount

CRASH_FIELDS = ("OBJECTID", "CRASH_NUMB", "CITY_TOWN_NAME", "CNTY_NAME", "CRASH_DATE_TEXT", "CRASH_TIME_2",
                "MAX_INJR_SVRTY_CL", "NUMB_FATAL_INJR", "NUMB_NONFATAL_INJR", "POLC_AGNCY_TYPE_DESCR",
                "MANR_COLL_DESCR", "AMBNT_LIGHT_DESCR", "WEATH_COND_DESCR", "ROAD_SURF_COND_DESCR", "STREET_NUMB",
                "RDWY", "DIST_DIRC_FROM_INT", "NEAR_INT_RDWY", "MM_RTE", "MILEMARKER", "EXIT_RTE", "EXIT_NUMB",
                "LANDMARK", "RDWY_JNCT_TYPE_DESCR", "IS_GEOCODED", "GEOCODING_METHOD_NAME", "LAT", "LON",
                "NON_MTRST_TYPE_CL", "HIT_RUN_DESCR", "F_CLASS", "AADT", "AADT_YEAR", "SPEED_LIMIT")
PERSON_FIELDS = ("CRASH_NUMB", "PERS_NUMB", "VEHC_UNIT_NUMB", "PERS_TYPE", "INJY_STAT_DESCR", "AGE")

# Both wordings MassDOT has used: KABCO labels since 2019, the older injury words on earlier reports (2018 layer:
# "Non-fatal injury - Incapacitating" 2,198 crashes, 2026-11-07). "Deceased not caused by crash" is not K.
KABCO = {
    "FATALINJURYK": "K", "FATALINJURY": "K",
    "SUSPECTEDSERIOUSINJURYA": "A", "NONFATALINJURYINCAPACITATING": "A",
    "SUSPECTEDMINORINJURYB": "B", "NONFATALINJURYNONINCAPACITATING": "B",
    "POSSIBLEINJURYC": "C", "NONFATALINJURYPOSSIBLE": "C",
    "NOAPPARENTINJURYO": "O", "NOINJURY": "O",
}
SEVERITY_ORDER = "KABCUO"   # same codes as CCRS: U = injured, level not reported; O = property damage only
MA_LAT, MA_LON = (41.2, 42.9), (-73.6, -69.9)


def kabco(v) -> str | None:
    return KABCO.get("".join(ch for ch in str(v or "").upper() if ch.isalnum()))


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and MA_LAT[0] <= lat <= MA_LAT[1] and MA_LON[0] <= lon <= MA_LON[1]


_RTE = re.compile(r"\s+RTE\b.*$", re.I)   # " Washington St Rte W", "Chelsea St Rte 1 E", "US1 N Rte": route/heading tag


def _road(v) -> str | None:
    t = _RTE.sub("", " ".join(str(v or "").split())).strip()
    return t or None


def split_rdwy(rdwy, near) -> tuple[str | None, str | None]:
    """IMPACT writes an intersection in one field ("Columbus Ave Rte N  / Dimock St Rte N"); the near-intersection
    road, when given, is the cross street. -> (primary, secondary)."""
    parts = [p for p in (_road(x) for x in str(rdwy or "").split(" / ")) if p]
    prim = parts[0] if parts else None
    sec = _road(near) or (parts[1] if len(parts) > 1 else None)
    return prim, sec


_OFFSET = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(FEET|FT|MILES?|MI|YARDS?)\s+([NSEW])?", re.I)
_UNIT_FT = {"F": 1.0, "M": 5280.0, "Y": 3.0}


def offset(v) -> tuple[float | None, str | None]:
    """'15 feet N  of' -> (15.0, 'N'); '0 feet    of' -> (0.0, None)."""
    m = _OFFSET.match(str(v or ""))
    if not m:
        return None, None
    return float(m[1]) * _UNIT_FT[m[2][0].upper()], (m[3] or "").upper() or None


def house_number(v, rdwy=None) -> int | None:
    """The house number, unless it is the route the road names ("495" on "495 SB", "US1" on "US1 N")."""
    t = str(v or "").strip()
    if not t.isdigit() or not 0 < int(t) < 100000 or t in re.findall(r"\d+", str(rdwy or "")):
        return None
    return int(t)


def _dt(date_text, time_text) -> tuple[str, int | None, int | None]:
    try:
        d = datetime.strptime(str(date_text).strip(), "%m %d %Y")
    except ValueError:
        return "", None, None
    try:
        h = datetime.strptime(str(time_text).strip().upper(), "%I:%M %p").hour
    except ValueError:
        h = None
    return d.strftime("%Y-%m-%d"), d.year, h


def _s(v) -> str | None:
    return (" ".join(str(v).split()) or None) if v is not None else None


def crash_record(a: dict) -> dict:
    """One Crash-layer row -> the shared crash shape (as CCRS normalizes); severity comes with the persons."""
    lat, lon = a.get("LAT"), a.get("LON")
    has = plausible(lat, lon)
    prim, sec = split_rdwy(a.get("RDWY"), a.get("NEAR_INT_RDWY"))
    off_ft, off_dir = offset(a.get("DIST_DIRC_FROM_INT"))
    date, year, hour = _dt(a.get("CRASH_DATE_TEXT"), a.get("CRASH_TIME_2"))
    nm = str(a.get("NON_MTRST_TYPE_CL") or "").upper()
    return {
        "collision_id": str(a["CRASH_NUMB"]),
        "date": date, "year": year, "hour": hour,
        "datetime": f"{date} {hour:02d}:00" if date and hour is not None else date,
        "lat": lat if has else None, "lon": lon if has else None,
        "bad_coords": lat is not None and lon is not None and not has,
        "geocode_method": _s(a.get("GEOCODING_METHOD_NAME")),
        "primary_road": prim, "secondary_road": sec,
        "house_number": house_number(a.get("STREET_NUMB"), a.get("RDWY")),
        "offset_ft": off_ft, "offset_dir": off_dir,
        "sec_distance": off_ft, "sec_direction": off_dir,
        "mile_marker_route": _s(a.get("MM_RTE")), "mile_marker": a.get("MILEMARKER"),
        "exit_route": _s(a.get("EXIT_RTE")), "exit_number": _s(a.get("EXIT_NUMB")),
        "landmark": _s(a.get("LANDMARK")),
        "city_name": _s(a.get("CITY_TOWN_NAME")), "county_code": _s(a.get("CNTY_NAME")),
        "agency_type": _s(a.get("POLC_AGNCY_TYPE_DESCR")),
        "killed": int(a.get("NUMB_FATAL_INJR") or 0), "injured": int(a.get("NUMB_NONFATAL_INJR") or 0),
        "collision_type": _s(a.get("MANR_COLL_DESCR")), "lighting": _s(a.get("AMBNT_LIGHT_DESCR")),
        "weather": _s(a.get("WEATH_COND_DESCR")), "surface": _s(a.get("ROAD_SURF_COND_DESCR")),
        "junction": _s(a.get("RDWY_JNCT_TYPE_DESCR")),
        "is_freeway": _s(a.get("F_CLASS")) in ("Interstate", "Principal Arterial - Other Freeways or Expressways"),
        "functional_class": _s(a.get("F_CLASS")), "aadt": a.get("AADT"), "aadt_year": a.get("AADT_YEAR"),
        "speed_limit": a.get("SPEED_LIMIT"),
        "hit_run": str(a.get("HIT_RUN_DESCR") or "").upper().startswith("YES"),
        "ped": "PEDESTRIAN" in nm, "bike": "BICYCLIST" in nm or "CYCLIST" in nm,
        "max_injury": _s(a.get("MAX_INJR_SVRTY_CL")),
    }


def person_record(a: dict) -> dict:
    return {"person_number": a.get("PERS_NUMB"), "vehicle_unit": a.get("VEHC_UNIT_NUMB"),
            "person_type": _s(a.get("PERS_TYPE")), "injury": _s(a.get("INJY_STAT_DESCR")),
            "kabco": kabco(a.get("INJY_STAT_DESCR")), "age": a.get("AGE")}


def severity(crash: dict, persons: list[dict]) -> str:
    """Most severe outcome, counted once: the crash's own max injury and every person's KABCO, then the counts."""
    codes = [c for c in [kabco(crash.get("max_injury"))] + [p["kabco"] for p in persons] if c]
    best = min(codes, key=SEVERITY_ORDER.index, default="O")
    if crash["killed"] > 0:
        return "K"
    if best == "O" and crash["injured"] > 0:
        return "U"
    return best


# ---- fetching (ArcGIS REST) ----

def _get(url: str, **params) -> dict:
    params["f"] = "json"
    body = urllib.parse.urlencode(params).encode()
    for attempt in range(4):   # the open-year server returned 503s for minutes on 2026-11-07
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=UA), timeout=300) as r:
                d = json.load(r)
            if "error" in d:
                raise RuntimeError(f"IMPACT error: {d['error']}")
            return d
        except (urllib.error.URLError, RuntimeError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt * 5)
    raise AssertionError("unreachable")


def service(year: int) -> str:
    return SPECIAL.get(year) or (CLOSED.format(year) if year < 2020 else OPEN.format(year))


def layers(year: int) -> dict[str, int]:
    """{'crash': id, 'person': id, 'vehicle': id}: the order differs (open years Crash/Vehicle/Person, closed years
    Crash/Person/Vehicle), so resolve by name."""
    out = {}
    for lyr in _get(service(year))["layers"]:
        n = lyr["name"].lower()
        kind = "person" if "person" in n else "vehicle" if "vehicle" in n else "crash" if "crash" in n else None
        if kind and kind not in out:
            out[kind] = lyr["id"]
    missing = {"crash", "person"} - set(out)
    if missing:
        raise RuntimeError(f"IMPACT {year}: no {sorted(missing)} layer")
    return out


def _rows(url: str, where: str, fields) -> list[dict]:
    ids = sorted(_get(url + "/query", where=where, returnIdsOnly="true").get("objectIds") or [])
    out = []
    for i in range(0, len(ids), PAGE):   # page by object id (politeness rule; offsets aren't stable)
        d = _get(url + "/query", objectIds=",".join(map(str, ids[i:i + PAGE])), outFields=",".join(fields),
                 returnGeometry="false")
        out += [f["attributes"] for f in d["features"]]
    return out


def fetch(year: int, where: str, cache_dir: Path) -> list[dict]:
    """Crashes of `year` matching an ArcGIS `where` (e.g. "CNTY_NAME='MIDDLESEX'"), each with its persons
    and a crash-level severity in KABCUO. Cached as JSON per (year, where)."""
    cache = cache_dir / f"ma_impact_{year}_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    base, lay = service(year), layers(year)
    crashes = [crash_record(a) for a in _rows(f"{base}/{lay['crash']}", where, CRASH_FIELDS)]
    by_id: dict[str, list[dict]] = {c["collision_id"]: [] for c in crashes}
    ids = list(by_id)
    for i in range(0, len(ids), 200):
        for a in _rows(f"{base}/{lay['person']}", f"CRASH_NUMB IN ({','.join(ids[i:i + 200])})", PERSON_FIELDS):
            by_id.get(str(a["CRASH_NUMB"]), []).append(person_record(a))
    for c in crashes:
        c["persons"] = by_id[c["collision_id"]]
        c["severity"] = severity(c, c["persons"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(crashes))
    return crashes
