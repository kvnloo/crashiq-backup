"""Arkansas crash source: ARDOT's Arkansas Crash Analytics Tool (ACAT) layer, an open ArcGIS FeatureServer, no login.

One row per crash, 2021-2025 (a rolling five years of ASP eCrash reports, cleaned and located by ARDOT's Traffic
Safety Section), GPS on all but 1,467 of 401,279 crashes, crash-level KABCO (CrashSeverity, e.g. "Fatal Injury (K)"),
and counts of people killed (NumFatalities) and seriously injured (NumSerInj) only. There is no person or vehicle
table and no officer street text: the primary road exists only inside ARDOT's road id ("60xNRODNEYPARHAMRDx102xA" =
county 60, road N RODNEY PARHAM RD with its spaces removed, section 102), and the cross street (IntersectingStreetName)
is filled on ~39% and sometimes also has no spaces ("KAVANAUGHBLVD"). Neither matches CrashIQ's street keys, so both
road fields stay None and the crash is placed by its GPS only (research_notes/ar-2026-11-08/shared-fixes.md).

Licence: none published. The item says the data "is not an official record" and is at the user's own risk, and cites
23 USC 409 (ar-import.md). Wired into the app through the AR state pack (statepacks/ar.py) by `fetch_contract`.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LAYER = "https://gis.ardot.gov/referenced/rest/services/TPP_TrafficSafety/NotForOfficialUse/FeatureServer/20"
PAGE = 2000                                      # the layer's maxRecordCount
AR_LAT, AR_LON = (32.9, 36.6), (-94.7, -89.6)    # Arkansas's extent with a small margin
_TZ = ZoneInfo("America/Chicago")                # CrashDate is the local date and time sent as UTC epoch ms

# Census FIPS are the odd numbers in this order (Arkansas 001 ... St. Francis 123, Saline 125 ... Yell 149). ARDOT's
# road id numbers the counties 1-75 in the same order except that St. Francis sorts after Sharp (68): measured on 200
# rows per county, 2026-11-08 (research_notes/ar-2026-11-08/county_prefix.json).
COUNTIES = ("Arkansas", "Ashley", "Baxter", "Benton", "Boone", "Bradley", "Calhoun", "Carroll", "Chicot", "Clark",
            "Clay", "Cleburne", "Cleveland", "Columbia", "Conway", "Craighead", "Crawford", "Crittenden", "Cross",
            "Dallas", "Desha", "Drew", "Faulkner", "Franklin", "Fulton", "Garland", "Grant", "Greene", "Hempstead",
            "Hot Spring", "Howard", "Independence", "Izard", "Jackson", "Jefferson", "Johnson", "Lafayette",
            "Lawrence", "Lee", "Lincoln", "Little River", "Logan", "Lonoke", "Madison", "Marion", "Miller",
            "Mississippi", "Monroe", "Montgomery", "Nevada", "Newton", "Ouachita", "Perry", "Phillips", "Pike",
            "Poinsett", "Polk", "Pope", "Prairie", "Pulaski", "Randolph", "St. Francis", "Saline", "Scott", "Searcy",
            "Sebastian", "Sevier", "Sharp", "Stone", "Union", "Van Buren", "Washington", "White", "Woodruff", "Yell")
FIPS = {name: f"05{2 * i + 1:03d}" for i, name in enumerate(COUNTIES)}
_rest = [c for c in COUNTIES if c != "St. Francis"]
ARDOT_NO = {n: c for n, c in enumerate(_rest[:67] + ["St. Francis"] + _rest[67:], start=1)}

# ARDOT's words -> the CCRS words the profile and the collision diagram read; any other value keeps ARDOT's words
CCRS_TYPE = {"Angle": "BROADSIDE", "Front to front (Head-on)": "HEAD-ON", "Front to rear (Rear-end)": "REAR END",
             "Sideswipe, same direction": "SIDE SWIPE", "Sideswipe, opposite direction": "SIDE SWIPE"}
CCRS_LIGHT = {"Dark - lighted": "DARK - STREET LIGHTS", "Dark - not lighted": "DARK - NO STREET LIGHTS",
              "Dark - unknown lighting": "DARK - UNKNOWN STREET LIGHTS"}
PED = {"Pedestrian", "Other pedestrian (wheelchair)", "Skater"}
BIKE = {"Bicyclist", "Other cyclist (tricycle, etc.)"}
FREEWAY = {"Interstate", "Ramp"}                 # RoadSystem; freeway-built US highways (US 67/167) are not marked


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and AR_LAT[0] <= lat <= AR_LAT[1] and AR_LON[0] <= lon <= AR_LON[1])


def county_fips(a: dict) -> str | None:
    """The road id's county (ARDOT's own location), else the County name; a crash ARDOT files under a neighbouring
    state's county (Texarkana's 'Bowie County') still gets its Arkansas county from the road id."""
    head = (a.get("AH_RoadID") or "").split("x")[0]
    name = ARDOT_NO.get(int(head)) if head.isdigit() else None
    return FIPS.get(name or (a.get("County") or "").strip())


def severity(a: dict) -> str | None:
    """'Fatal Injury (K)' -> 'K'; None for anything that isn't one KABCO letter in brackets."""
    t = (a.get("CrashSeverity") or "").strip()
    return t[-2] if len(t) > 3 and t.endswith(")") and t[-3] == "(" and t[-2] in "KABCO" else None


def contract_record(a: dict) -> dict:
    """One ACAT attributes dict -> the shared crash dict (packs.check_crash)."""
    s = lambda v: (str(v).strip() or None) if v is not None else None                  # noqa: E731
    lat, lon = a.get("Latitude"), a.get("Longitude")
    has = plausible(lat, lon)
    when = datetime.fromtimestamp(a["CrashDate"] / 1000, _TZ) if a.get("CrashDate") is not None else None
    sev = severity(a)
    nmt = s(a.get("NonMotoristType")) or ""
    # ARDOT counts only people killed and seriously injured; a K, B or C crash has at least one such person
    killed = max(int(a.get("NumFatalities") or 0), int(sev == "K"))
    injured = max(int(a.get("NumSerInj") or 0), int(sev in ("A", "B", "C")))
    up = lambda v: v.upper() if v else None                                              # noqa: E731
    return {"crash_id": str(a["StateCaseNumber"]), "report_version": 0, "deleted": False,
            "preliminary": bool(when and when.year >= datetime.now(_TZ).year),
            "date": when.date().isoformat() if when else "", "year": when.year if when else None,
            "hour": when.hour if when else None, "day_of_week": when.strftime("%A") if when else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,  # see module doc
            "city": up(s(a.get("City"))), "county_code": s(a.get("County")), "county_fips": county_fips(a),
            "state": "AR", "is_freeway": s(a.get("RoadSystem")) in FREEWAY, "killed": killed, "injured": injured,
            "severity": sev, "ped": nmt in PED, "bike": nmt in BIKE, "ebike": False, "escooter": nmt == "Scooter",
            "motorcycle": s(a.get("MotorcycleRelated")) == "Yes", "heavy_truck": s(a.get("CMVRelated")) == "Yes",
            "parties": [], "collision_type": CCRS_TYPE.get(s(a.get("CrashManner")), up(s(a.get("CrashManner")))),
            "lighting": CCRS_LIGHT.get(s(a.get("LightingConditions")), up(s(a.get("LightingConditions")))),
            "weather": None, "surface": up(s(a.get("RoadwaySurfaceConidtion"))),
            "report_number": s(a.get("LocalCaseNumber")), "road_system": s(a.get("RoadSystem")),
            "road_id": s(a.get("AH_RoadID")), "logmile": a.get("AH_Logmile"),
            "intersecting_street": s(a.get("IntersectingStreetName"))}


def _get(where: str, last: int, opener) -> list[dict]:
    q = {"where": f"({where}) AND OBJECTID>{last}", "outFields": "*", "orderByFields": "OBJECTID",
         "resultRecordCount": PAGE, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(LAYER + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"ARDOT ACAT query error: {body['error']}")
    return [f["attributes"] for f in body.get("features", [])]


def fetch_raw(where: str, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every row matching an ArcGIS `where`, paged by OBJECTID; cached as raw JSON per `where` when cache_dir is given."""
    cache = cache_dir / f"ar_ardot_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json" if cache_dir else None
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
    """Every crash with a point in the box (s, w, n, e) in those years. The 1,467 of 401,279 crashes with no point
    aren't read: they have no road id and no usable street text either."""
    s, w, n, e = box
    yrs = ", ".join(f"'{y}'" for y in years)
    where = (f"Latitude >= {s:.6f} AND Latitude <= {n:.6f} AND Longitude >= {w:.6f} AND Longitude <= {e:.6f} "
             f"AND Year IN ({yrs})")
    rows = [contract_record(a) for a in fetch_raw(where, cache_dir, opener)]
    have = {r["year"] for r in rows}
    out = [r for r in rows if r["county_fips"] and r["severity"]]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "no_county": sum(not r["county_fips"] for r in rows),
                         "no_severity": sum(not r["severity"] for r in rows),
                         "no_gps_not_read": "1,467 of 401,279 statewide crashes have no point; not read"}}
