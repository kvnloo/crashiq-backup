"""Seattle crash source: SDOT Collisions All Years + Collisions Persons (City of Seattle open data, ArcGIS, no login).

Not wired into the app (state-pack seam, #19). Produces crashes in the keys CCRS normalizes to, plus per-person KABCO.

Layers (City of Seattle ArcGIS Online, verified 2026-11-07):
  crashes  https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/SDOT_Collisions_All_Years_1/FeatureServer/0
  persons  https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/SDOT_Collisions_Persons/FeatureServer/0
  Persons link to crashes on COLDETKEY. Points are SDOT's geocode, snapped to the intersection or the middle of the
  block, not the officer's GPS.
Licence: City of Seattle Open Data Policy §E, open licence, commercial use allowed. The Terms of Use bar commercial
use of data that "consists of a list of individuals" (read before using the persons layer commercially).
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .ca_ccrs import SEVERITY_ORDER, parse_dt

BASE = "https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/"
CRASHES = BASE + "SDOT_Collisions_All_Years_1/FeatureServer/0"
PERSONS = BASE + "SDOT_Collisions_Persons/FeatureServer/0"
UA = {"User-Agent": "CrashIQ/0.1"}

CRASH_FIELDS = ("OBJECTID,INCKEY,COLDETKEY,REPORTNO,STATUS,ADDRTYPE,INTKEY,LOCATION,INCDTTM,PERSONCOUNT,PEDCOUNT,"
                "PEDCYLCOUNT,VEHCOUNT,INJURIES,SERIOUSINJURIES,FATALITIES,JUNCTIONTYPE,ST_COLLISIONTYPE,SDOT_COLDESC,"
                "WEATHER,ROADCOND,LIGHTCOND,HITPARKEDCAR,SOURCE,MAXSEVERITYCODE,MAXSEVERITYDESC")
PERSON_FIELDS = "OBJECTID,COLDETKEY,ST_INJRY_CLSS_DESC,ST_PARTCPNT_TYPE_DESC,ST_AGE"

# Crash level (MAXSEVERITYCODE, 2025 values): 4 fatal, 3 serious injury, 2 injury, 1 property damage only.
# "Injury" doesn't say B or C, so it is U (injured, level not given) unless the persons layer says which.
CRASH_SEVERITY = {"4": "K", "3": "A", "2": "U", "1": "O"}
# Person level (ST_INJRY_CLSS_DESC). "Unknown" and blank have no level.
PERSON_KABCO = {"DEAD AT SCENE": "K", "DEAD ON ARRIVAL": "K", "DIED AT HOSPITAL": "K", "SERIOUS INJURY": "A",
                "NON SERIOUS INJURY (EVIDENT INJURY)": "B", "POSSIBLE INJURY": "C", "NO INJURY": "O"}
WA_LAT, WA_LON = (45.5, 49.1), (-124.9, -116.8)

# Roadway tags SDOT writes before the street type: BEACON ER AVE S = the east roadway of Beacon Ave S; 62ND E AVE S,
# 8TH N AVE N, 2ND AV ET S, S INDUSTRIAL WB WAY likewise. They aren't part of the street's name on any map.
_ROADWAY = re.compile(r"\s+(?:[NSEW]R|[EW]T|[NSEW]B|[NSEW])(?=\s+(?:AVE?|ST|WAY|PL|DR|BLVD|RD)\b)")
_ROADWAY_AFTER = re.compile(r"\b(AVE?|ST|WAY|PL|DR|BLVD|RD) (?:[NSEW]R|[EW]T)\b")     # 2ND AV ET S
_FREEWAY = re.compile(r"\b(?:I ?\d+|SR ?\d+)\b")


def clean_street(s: str | None) -> str | None:
    s = re.sub(r"\s+", " ", str(s or "")).strip().upper()
    return _ROADWAY_AFTER.sub(r"\1", _ROADWAY.sub("", s)) or None


def split_location(loc: str | None) -> tuple[str | None, str | None, str | None]:
    """'A AND B' -> (A, B, None); 'A BETWEEN B AND C' -> (A, B, C): the block of A from B to C."""
    loc = re.sub(r"\s+", " ", str(loc or "")).strip().upper()
    if " BETWEEN " in loc:
        a, rest = loc.split(" BETWEEN ", 1)
        b, _, c = rest.partition(" AND ")
        return clean_street(a), clean_street(b), clean_street(c)
    a, _, b = loc.partition(" AND ")
    return clean_street(a), clean_street(b), None


def _num(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def person_record(attrs: dict) -> dict:
    desc = str(attrs.get("ST_INJRY_CLSS_DESC") or "").strip().upper()
    return {"kabco": PERSON_KABCO.get(desc), "injury": desc or None,
            "person_type": (attrs.get("ST_PARTCPNT_TYPE_DESC") or None), "age": attrs.get("ST_AGE")}


def crash_record(feature: dict, persons: list[dict] | None = None) -> dict:
    """One SDOT Collisions feature (ArcGIS JSON, outSR=4326) -> the shared crash shape."""
    a, g = feature["attributes"], feature.get("geometry") or {}
    lat, lon = g.get("y"), g.get("x")
    ok = lat is not None and lon is not None and WA_LAT[0] <= lat <= WA_LAT[1] and WA_LON[0] <= lon <= WA_LON[1]
    date, year, hour = parse_dt(a.get("INCDTTM"))
    p, s, t = split_location(a.get("LOCATION"))
    persons = persons or []
    sev = CRASH_SEVERITY.get(str(a.get("MAXSEVERITYCODE") or "").strip())
    bc = [x["kabco"] for x in persons if x["kabco"] in ("B", "C")]
    if sev == "U" and bc:                          # the city's code wins; persons only say B or C for "injury"
        sev = min(bc, key=SEVERITY_ORDER.index)
    s_ = lambda k: (str(a.get(k)).strip() or None) if a.get(k) is not None else None
    return {
        "collision_id": str(a["COLDETKEY"]),
        "incident_key": str(a.get("INCKEY")),
        "report_number": s_("REPORTNO"),
        "datetime": a.get("INCDTTM"),
        "date": date, "year": year, "hour": hour,       # hour None when INCDTTM has no time (citizen reports)
        "lat": lat if ok else None, "lon": lon if ok else None,
        "location": s_("LOCATION"),
        "addr_type": s_("ADDRTYPE"),                    # I intersection, B block, A alley
        "primary_road": p, "secondary_road": s,
        "block_end_road": t,                           # B: the block of primary_road runs from secondary to this one
        "sec_distance": None, "sec_direction": None,
        "city_name": "SEATTLE", "county_code": "53033",
        "killed": _num(a.get("FATALITIES")),
        "injured": _num(a.get("INJURIES")),             # includes SERIOUSINJURIES (2025: always >=)
        "collision_type": s_("ST_COLLISIONTYPE") or s_("SDOT_COLDESC"),
        "junction": s_("JUNCTIONTYPE"),
        "lighting": s_("LIGHTCOND"), "weather": s_("WEATHER"), "surface": s_("ROADCOND"),
        # shortcut: freeway = an I-/SR- route number in the primary name; upgrade with WSDOT's LRS when wired
        "is_freeway": bool(_FREEWAY.search(p or "")),
        "pedestrians": _num(a.get("PEDCOUNT")), "cyclists": _num(a.get("PEDCYLCOUNT")),
        "vehicles": _num(a.get("VEHCOUNT")),
        "report_source": s_("SOURCE"),                 # PTCR police report, CVCR citizen report
        "severity": sev,
        "persons": persons,
    }


def _get(url: str, **params) -> dict:
    q = url + "?" + urllib.parse.urlencode({**params, "f": "json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=120) as r:
                body = json.load(r)
            if "error" in body:
                raise RuntimeError(f"ArcGIS error: {body['error']}")
            return body
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt * 3)
    raise AssertionError("unreachable")


def _features(url: str, where: str, fields: str, page: int = 2000) -> list[dict]:
    """All features matching `where`, paged by object id (the layer caps a query at 2,000)."""
    ids = sorted(_get(url + "/query", where=where, returnIdsOnly="true").get("objectIds") or [])
    out = []
    for i in range(0, len(ids), page):
        lo, hi = ids[i], ids[min(i + page, len(ids)) - 1]
        out += _get(url + "/query", where=f"OBJECTID >= {lo} AND OBJECTID <= {hi} AND ({where})", outFields=fields,
                    outSR=4326, returnGeometry="true", resultRecordCount=page)["features"]
    return out


def year_where(year: int) -> str:
    return f"INCDATE >= TIMESTAMP '{year}-01-01 00:00:00' AND INCDATE < TIMESTAMP '{year + 1}-01-01 00:00:00'"


def build(crash_features: list[dict], person_features: list[dict]) -> list[dict]:
    by_crash: dict = {}
    for f in person_features:
        by_crash.setdefault(f["attributes"]["COLDETKEY"], []).append(person_record(f["attributes"]))
    return [crash_record(f, by_crash.get(f["attributes"]["COLDETKEY"])) for f in crash_features]


def fetch(year: int, cache_dir: Path) -> list[dict]:
    """Every SDOT collision in `year`, with its persons, cached as the raw ArcGIS features."""
    cache = cache_dir / f"sdot_{year}.json"
    if cache.exists():
        raw = json.loads(cache.read_text())
    else:
        raw = {"crashes": _features(CRASHES, year_where(year), CRASH_FIELDS),
               "persons": _features(PERSONS, year_where(year), PERSON_FIELDS)}
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return build(raw["crashes"], raw["persons"])
