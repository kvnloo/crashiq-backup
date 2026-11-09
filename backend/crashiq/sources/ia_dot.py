"""Iowa crash source: Iowa DOT's open crash layers (Traffic_Safety ArcGIS services behind ICAT and the Traffic Safety
Data and Analysis site), no login.

  crashes   https://gis.iowadot.gov/agshost/rest/services/Traffic_Safety/Crash_Data/FeatureServer/0  (one row per crash)
  persons   …/Crash_Person_Data/FeatureServer/0   CRASH_KEY (text): read only for the non-motorist type
  vehicles  …/Crash_Vehicle_Data/FeatureServer/0  VEH_CRASH_KEY: read only for the vehicle configuration

The prior 10 years plus the current one, updated daily; every crash has an Iowa DOT point (UTM 15N, asked for in
WGS84). Severity: per-crash counts of fatalities, major, minor, possible and unknown injuries, so K/A/B/C come
straight from Iowa's own levels and "unknown injury" is U (Iowa's CSEV merges possible and unknown as 4). The street
text is Iowa DOT's LITERAL ("A AND B", "A MEASURING 45 FEET NORTH FROM B", "100 BLK NE 41ST ST", "I 80 W - 132.00MM").
Codes are decoded with Iowa DOT's metadata workbooks (Crash_Data.xlsx, Crash_Vehicle.xlsx, research_notes/ia-2026-11-08).

Licence: CC BY 4.0 on the ArcGIS items plus Iowa DOT's GIS Data Terms of Use ("for any purpose, including commercial
use, provided that you give appropriate credit"). Wired into the app by the IA plug-in (statepacks/ia.py).
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://gis.iowadot.gov/agshost/rest/services/Traffic_Safety"
CRASH_URL = f"{BASE}/Crash_Data/FeatureServer/0/query"
PERSON_URL = f"{BASE}/Crash_Person_Data/FeatureServer/0/query"
VEHICLE_URL = f"{BASE}/Crash_Vehicle_Data/FeatureServer/0/query"
PAGE = 2000                                    # the layers' maxRecordCount
UA = {"User-Agent": "CrashIQ/0.1"}
IA_LAT, IA_LON = (40.3, 43.6), (-96.7, -90.1)  # Iowa's extent with a small margin
CRASH_FIELDS = ("OBJECTID,CRASH_KEY,LECASENUM,CRASH_DATE,TIMESTR,COUNTY_NUMBER,CITY_NAME,SYSTEMSTR,LITERAL,FRSTHARM,"
                "CRCOMNNR,MAJCSE,DRUGALC,LIGHT,CSRFCND,WEATHER,RDTYP,CSEV,FATALITIES,INJURIES,MAJINJURY,MININJURY,"
                "POSSINJURY,UNKINJURY,VEHICLES")

# Crash_Data.xlsx sheets CrCoManner, Light, Weather, CSurfCond; text in the CCRS words where one matches
COLLISION = {1: "OTHER", 2: "HEAD-ON", 3: "REAR END", 4: "BROADSIDE", 5: "BROADSIDE", 6: "SIDE SWIPE",
             7: "SIDE SWIPE", 8: "OTHER", 9: "OTHER", 98: "OTHER"}       # 4 = angle, oncoming left turn
LIGHT = {1: "DAYLIGHT", 2: "DUSK - DAWN", 3: "DUSK - DAWN", 4: "DARK - STREET LIGHTS", 5: "DARK - NO STREET LIGHTS",
         6: "DARK - UNKNOWN STREET LIGHTS"}
WEATHER = {1: "CLEAR", 2: "CLOUDY", 3: "FOG", 4: "RAINING", 5: "RAINING", 6: "SNOWING", 7: "SNOWING", 8: "SNOWING",
           9: "WIND", 10: "OTHER", 98: "OTHER"}
SURFACE = {1: "DRY", 2: "WET", 3: "SNOWY OR ICY", 4: "SNOWY OR ICY", 5: "SNOWY OR ICY", 6: "SLIPPERY", 7: "WET",
           8: "SLIPPERY", 9: "SLIPPERY", 10: "SLIPPERY", 98: "OTHER"}
FIRST_HARM_FIXED = range(40, 66)               # FirstHarm 40-65 + 97: collision with a fixed object
MOTORCYCLE = {17, 18, 19}                      # VConfig: motorcycle, 3-wheeled enclosed / unenclosed
HEAVY_TRUCK = {7, 8, 11, 12, 13, 14, 15, 16}   # VConfig: single-unit trucks, truck/trailer, tractors, other > 10,000 lb
DIRS = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}

MEASURING = re.compile(r"^(.+?)\s+MEASURING\s+(\d+(?:\.\d+)?)\s+FEET\s+(NORTH|SOUTH|EAST|WEST)\s+FROM\s+(.+)$")
CROSS = re.compile(r"\s+(?:AND|&)\s+")
ROUTE = re.compile(r"^(?:I|US|IA)[ -]?\d")
BLOCK = re.compile(r"^(\d+)(?:\s*-\s*\d+)?\s*-?\s*BL(?:OC)?K\s+(?:OF\s+)?(.+)$")
HOUSE = re.compile(r"^(\d+)\s+(?!MM\b)([A-Z].*|\d+(?:ST|ND|RD|TH)\b.*)$")
MILEPOST = re.compile(r"^(.+?)\s*-?\s*(\d+(?:\.\d+)?)\s*MM$")


def county_fips(number) -> str | None:
    """Iowa DOT's county number (1-99, alphabetical: 77 = Polk) -> FIPS ('19153'): Iowa's FIPS codes are the odd
    numbers in the same alphabetical order."""
    return f"19{2 * number - 1:03d}" if isinstance(number, int) and 1 <= number <= 99 else None


def _one_name(part: str) -> str:
    """'US 6/MERLE HAY RD' -> 'MERLE HAY RD': the street name over the route number, as the map names the road."""
    names = [n.strip() for n in part.split("/") if n.strip()]
    return next((n for n in names if not ROUTE.match(n)), names[0]) if names else part


def split_literal(text: str | None) -> dict:
    """{'form', 'primary', 'secondary', 'offset_ft', 'offset_dir', 'house_number', 'milepost'} from LITERAL."""
    t = re.sub(r"\s+", " ", (text or "").upper()).strip().rstrip(",")
    out = {"form": "none", "primary": None, "secondary": None, "offset_ft": None, "offset_dir": None,
           "house_number": None, "milepost": None}
    if not t:
        return out
    if m := MEASURING.match(t):
        return {**out, "form": "offset", "primary": m[1], "secondary": m[4], "offset_ft": float(m[2]),
                "offset_dir": DIRS[m[3]]}
    parts = [p.strip() for p in CROSS.split(t, maxsplit=1)]
    if len(parts) == 2 and all(parts):        # "US 6/MERLE HAY RD AND DOUGLAS AVE": a slash names one road twice
        return {**out, "form": "intersection", "primary": _one_name(parts[0]), "secondary": _one_name(parts[1])}
    parts = [p.strip() for p in t.split("/", 1)]
    if len(parts) == 2 and all(parts):        # shortcut: a lone slash is read as a cross street ("SE DELAWARE/SE 16TH"),
        return {**out, "form": "intersection", "primary": parts[0], "secondary": parts[1]}  # though some are aliases
    if m := BLOCK.match(t):
        return {**out, "form": "block", "primary": m[2], "house_number": int(m[1])}
    if m := MILEPOST.match(t):
        return {**out, "form": "milepost", "primary": m[1].strip(" -"), "milepost": float(m[2])}
    if m := HOUSE.match(t):
        return {**out, "form": "house", "primary": m[2], "house_number": int(m[1])}
    return {**out, "form": "street", "primary": t}


def _n(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def severity(a: dict) -> str:
    """Most severe level from Iowa's per-crash injury counts; U = injured at an unknown level, O = none."""
    for level, field in (("K", "FATALITIES"), ("A", "MAJINJURY"), ("B", "MININJURY"), ("C", "POSSINJURY"),
                         ("U", "UNKINJURY")):
        if _n(a.get(field)):
            return level
    return "O"


CSEV = {1: "K", 2: "A", 3: "B", 4: "CU", 5: "O"}   # Iowa DOT's own crash severity: 4 = possible/unknown


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and IA_LAT[0] <= lat <= IA_LAT[1] and IA_LON[0] <= lon <= IA_LON[1]


def crash_record(f: dict, nm_types: frozenset | set = frozenset(), vconfigs: frozenset | set = frozenset()) -> dict:
    """One crash feature (attributes + WGS84 geometry) -> the shared crash dict (packs.check_crash)."""
    a, g = f["attributes"], f.get("geometry") or {}
    lat, lon = g.get("y"), g.get("x")
    has = plausible(lat, lon)
    # CRASH_DATE is the local calendar date sent as UTC midnight
    d = datetime.fromtimestamp(a["CRASH_DATE"] / 1000, timezone.utc).date() if a.get("CRASH_DATE") is not None else None
    tm = re.fullmatch(r"(\d{1,2}):(\d{2})", (a.get("TIMESTR") or "").strip())
    hour = int(tm[1]) if tm and int(tm[1]) < 24 else None
    loc = split_literal(a.get("LITERAL"))
    house = loc["form"] in ("house", "block")
    sev, csev = severity(a), CSEV.get(a.get("CSEV"))
    system = (a.get("SYSTEMSTR") or "").strip()
    fh = a.get("FRSTHARM")
    bike = any(t.startswith("Pedalcycl") for t in nm_types if t)
    return {"crash_id": str(int(a["CRASH_KEY"])), "report_version": 0, "deleted": False,
            "preliminary": bool(d and d.year >= datetime.now(timezone.utc).year),   # the current year is still open
            "date": d.isoformat() if d else "", "year": d.year if d else None, "hour": hour,
            "day_of_week": d.strftime("%A") if d else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and not has and (lat, lon) != (0, 0),
            # a house or block number goes in front of the street, as the locator reads house addresses
            "primary_road": f"{loc['house_number']} {loc['primary']}" if house else loc["primary"],
            "secondary_road": loc["secondary"], "offset_ft": loc["offset_ft"], "offset_dir": loc["offset_dir"],
            "location_text": a.get("LITERAL"), "location_form": loc["form"], "milepost": loc["milepost"],
            "city": (a.get("CITY_NAME") or "").strip().upper() or None, "county_code": a.get("COUNTY_NUMBER"),
            "county_fips": county_fips(a.get("COUNTY_NUMBER")), "state": "IA",
            # shortcut: Interstates only; Iowa's other freeways (US 65, IA 5 ...) count as arterials until a route
            # class is read from Iowa DOT's road network
            "is_freeway": system.startswith("I-"), "route": None if system.isdigit() else system or None,   # a bare number = local road (the county number)
            "killed": _n(a.get("FATALITIES")), "injured": _n(a.get("INJURIES")), "severity": sev,
            "severity_iowa_dot": csev, "severity_mismatch": csev is not None and sev not in csev,
            "ped": "Pedestrian" in nm_types, "bike": bike,
            "ebike": False, "escooter": False,
            "motorcycle": bool(vconfigs & MOTORCYCLE), "heavy_truck": bool(vconfigs & HEAVY_TRUCK), "parties": [],
            # FirstHarm 32 = a non-motorist (pedestrian or cyclist); typed by manner of collision when it's a cyclist
            "collision_type": "VEHICLE/PEDESTRIAN" if fh == 32 and not bike else "HIT OBJECT" if fh in FIRST_HARM_FIXED or fh == 97
            else "OVERTURNED" if fh == 20 else COLLISION.get(a.get("CRCOMNNR")),
            "lighting": LIGHT.get(a.get("LIGHT")), "weather": WEATHER.get(a.get("WEATHER")),
            "surface": SURFACE.get(a.get("CSRFCND")), "report_number": a.get("LECASENUM"),
            "vehicles": _n(a.get("VEHICLES")), "impaired": a.get("DRUGALC") not in (None, 8)}


def _get(url: str, params: dict, opener) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode({**params, "f": "json"}).encode(), headers=UA)
    with opener(req, timeout=180) as r:
        d = json.load(r)
    if "error" in d:
        raise RuntimeError(f"Iowa DOT ArcGIS error: {d['error']}")
    return d


def _pages(url: str, where: str, box, fields: str, opener, geometry: bool = False) -> list[dict]:
    """Every feature in the box (s, w, n, e) matching `where`, paged by OBJECTID."""
    s, w, n, e = box
    rows, last = [], 0
    while True:
        d = _get(url, {"where": f"({where}) AND OBJECTID > {last}", "geometry": f"{w},{s},{e},{n}",
                       "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
                       "outFields": fields, "returnGeometry": str(geometry).lower(), "outSR": 4326,
                       "orderByFields": "OBJECTID", "resultRecordCount": PAGE}, opener)
        page = d.get("features", [])
        if not page:                          # until an empty page: a server capping below PAGE still reads in full
            return rows
        rows += page
        last = page[-1]["attributes"]["OBJECTID"]


def records(raw: dict) -> list[dict]:
    """{'crashes', 'persons', 'vehicles'} features -> shared crash dicts, persons and vehicles joined by crash key."""
    nm, vc = {}, {}
    for p in raw["persons"]:
        nm.setdefault(str(p["attributes"]["CRASH_KEY"]).split(".")[0], set()).add(p["attributes"]["NM_TYPE"])
    for v in raw["vehicles"]:
        vc.setdefault(str(int(v["attributes"]["VEH_CRASH_KEY"])), set()).add(v["attributes"]["VCONFIG"])
    out = []
    for f in raw["crashes"]:
        k = str(int(f["attributes"]["CRASH_KEY"]))
        out.append(crash_record(f, nm.get(k, set()), vc.get(k, set())))
    return out


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years, with its non-motorist and vehicle types.
    Cached raw per box + years. Every published Iowa crash has a point, so none is read by street name alone."""
    y0, y1 = min(years), max(years)
    when = f"CRASH_DATE >= DATE '{y0}-01-01' AND CRASH_DATE < DATE '{y1 + 1}-01-01'"
    yrs = ",".join(map(str, range(y0, y1 + 1)))
    key = hashlib.sha1(f"{box}|{y0}-{y1}".encode()).hexdigest()[:10]
    cache = Path(cache_dir) / f"ia_dot_{key}.json"
    if cache.exists():
        raw = json.loads(cache.read_text())
    else:
        raw = {"crashes": _pages(CRASH_URL, when, box, CRASH_FIELDS, opener, geometry=True),
               "persons": _pages(PERSON_URL, f"CRASH_YEAR IN ({yrs}) AND NM_TYPE IS NOT NULL", box,
                                 "OBJECTID,CRASH_KEY,NM_TYPE", opener),
               "vehicles": _pages(VEHICLE_URL, f"CRASH_YEAR IN ({yrs}) AND VCONFIG IN "
                                  f"({','.join(map(str, sorted(MOTORCYCLE | HEAVY_TRUCK)))})", box,
                                  "OBJECTID,VEH_CRASH_KEY,VCONFIG", opener)}
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    recs = records(raw)
    have = {r["year"] for r in recs}
    out = [r for r in recs if r["county_fips"] and r["year"] in years]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(recs), "no_county": sum(not r["county_fips"] for r in recs),
                         "severity_differs_from_iowa_dot": sum(r["severity_mismatch"] for r in recs),
                         "unknown_injury_as_u": sum(r["severity"] == "U" for r in recs)}}
