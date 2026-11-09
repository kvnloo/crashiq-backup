"""Washington DC crashes: DDOT's 'Crashes in DC' layer (one row per crash) and its 'Crash Details' table (one row per
person), from MPD's COBALT crash reports. Open, no login; CC BY 4.0 per the Open Data DC items (70392a096a8e…,
70248b73c20f…), so the app must credit "District Department of Transportation / Open Data DC".

  crashes  https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Public_Safety_WebMercator/MapServer/24
  persons  …/MapServer/25, linked by CRIMEID (one crash : many persons)

Location: every published crash has a point (DDOT drops crashes it can't locate). `lat`/`lon` are MPD's own GPS when it
falls inside DC, else DDOT's geocode of the address (`location_source` says which). The report's ADDRESS is a house
address ("1201 U STREET NW"), an intersection ("FLORIDA AVENUE NE & NEW YORK AVENUE NE"), or a street alone; for
house addresses the cross street is DDOT's nearest intersecting street with its distance and approach direction.

Severity: DDOT publishes FATAL / MAJORINJURY / MINORINJURY flags, not the KABCO code MPD records (MMUCC since 2016).
fatal -> K, major -> A (MMUCC suspected serious), minor -> B. shortcut: DC "minor" folds MMUCC B and C together, so
C never appears; upgrade when DDOT publishes the injury code or the user picks another split.

Wired into the app through the DC state pack (packs.py, #19) by `fetch_contract`.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BASE = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Public_Safety_WebMercator/MapServer"
CRASH_URL, PERSON_URL = f"{BASE}/24/query", f"{BASE}/25/query"
ATTRIBUTION = "Crashes in DC, District Department of Transportation (Open Data DC), CC BY 4.0"
UA = {"User-Agent": "CrashIQ/0.1"}
M_TO_FT = 3.28084
PAGE = 1000                      # the layer's maxRecordCount
DC_LAT, DC_LON = (38.79, 39.00), (-77.12, -76.90)   # DC's extent with a small margin
EASTERN = ZoneInfo("America/New_York")
MODES = ("BICYCLIST", "DRIVER", "PEDESTRIAN")
SEVERITY_ORDER = "KABCUO"
FREEWAY = re.compile(r"\bINTERSTATE\b|\bI-?\s?\d+\b|\bFREEWAY\b|\bFWY\b")  # shortcut: by name; upgrade to DDOT's route class
HOUSE = re.compile(r"^(\d+)(?:\s*1/2)?\s+(.+)$")
DIRS = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHEAST": "NE", "NORTHWEST": "NW",
        "SOUTHEAST": "SE", "SOUTHWEST": "SW"}


def _get(url: str, params: dict, opener=urllib.request.urlopen) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode({**params, "f": "json"}).encode(), headers=UA)
    with opener(req, timeout=120) as r:
        d = json.load(r)
    if "error" in d:
        raise RuntimeError(f"DC ArcGIS error: {d['error']}")
    return d


def _pages(url: str, where: str, opener) -> list[dict]:
    """Every row matching `where`, paged by OBJECTID (the server caps a page at PAGE rows)."""
    rows, last = [], 0
    while True:
        d = _get(url, {"where": f"({where}) AND OBJECTID > {last}", "outFields": "*", "returnGeometry": "false",
                       "orderByFields": "OBJECTID", "resultRecordCount": PAGE}, opener)
        page = [f["attributes"] for f in d.get("features", [])]
        if not page:
            return rows
        rows += page
        last = page[-1]["OBJECTID"]


def fetch(year: int, opener=urllib.request.urlopen) -> list[dict]:
    """All crashes reported in `year`, with their persons, in the shared crash shape."""
    crashes = _pages(CRASH_URL, f"REPORTDATE >= date '{year}-01-01' AND REPORTDATE < date '{year + 1}-01-01'", opener)
    ids = [c["CRIMEID"] for c in crashes]
    persons = []
    for i in range(0, len(ids), 100):   # IN lists of 100 keep the request small
        persons += _pages(PERSON_URL, "CRIMEID IN (" + ",".join(f"'{x}'" for x in ids[i:i + 100]) + ")", opener)
    return records(crashes, persons)


def records(crash_rows: list[dict], person_rows: list[dict]) -> list[dict]:
    by_crash: dict[str, list[dict]] = {}
    for p in person_rows:
        by_crash.setdefault(p["CRIMEID"], []).append(person_record(p))
    out = []
    for raw in crash_rows:
        c = crash_record(raw)
        c["persons"] = by_crash.get(c["collision_id"], [])
        c["severity"] = severity(raw, c["persons"])
        out.append(c)
    return out


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and DC_LAT[0] <= lat <= DC_LAT[1] and DC_LON[0] <= lon <= DC_LON[1]


def local_time(ms) -> datetime | None:
    """REPORTDATE is epoch ms in UTC; the crash happened in DC time."""
    if ms is None:
        return None
    t = (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=ms)).astimezone(EASTERN)  # pre-1970 OK on Windows
    return t if 2000 <= t.year <= 2100 else None    # the layer holds a few 1825 dates


def split_address(address: str | None) -> dict:
    """{'form', 'primary', 'secondary', 'house_number'} from MPD's ADDRESS text (city line dropped)."""
    a = (address or "").split("\n")[0].strip().rstrip(",").strip()
    if not a:
        return {"form": "none", "primary": None, "secondary": None, "house_number": None}
    if re.fullmatch(r"-?\d+\.\d+,\s*-?\d+\.\d+", a):
        return {"form": "coords", "primary": None, "secondary": None, "house_number": None}
    if "&" in a:
        p, s = (x.strip() or None for x in a.split("&", 1))
        return {"form": "intersection", "primary": p, "secondary": s, "house_number": None}
    m = HOUSE.match(a)
    if m:
        return {"form": "house", "primary": m[2].strip(), "secondary": None, "house_number": int(m[1])}
    return {"form": "street", "primary": a, "secondary": None, "house_number": None}


def _n(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _count(raw: dict, level: str) -> int:
    """Persons at one injury level over every mode; passengers and 'other' are spelled without the underscore."""
    if level == "FATAL":
        return sum(_n(raw.get(f"FATAL_{m}")) for m in MODES) + _n(raw.get("FATALPASSENGER")) + _n(raw.get("FATALOTHER"))
    return (sum(_n(raw.get(f"{level}INJURIES_{m}")) for m in MODES)
            + _n(raw.get(f"{level}INJURIESPASSENGER")) + _n(raw.get(f"{level}INJURIESOTHER")))


def crash_record(raw: dict) -> dict:
    s = lambda v: (str(v).strip() or None) if v is not None else None
    t = local_time(raw.get("REPORTDATE"))
    timed = t is not None and (t.hour, t.minute, t.second) != (0, 0, 0)   # 3.7% of 2025 sit at 00:00:00: no time given
    mpd = (raw.get("MPDLATITUDE"), raw.get("MPDLONGITUDE"))
    ddot = (raw.get("LATITUDE"), raw.get("LONGITUDE"))
    src = "police_gps" if plausible(*mpd) else "ddot_geocode" if plausible(*ddot) else None
    lat, lon = mpd if src == "police_gps" else ddot if src else (None, None)
    a = split_address(raw.get("ADDRESS"))
    nearest = s(raw.get("NEARESTINTSTREETNAME"))
    nearest = None if nearest in (None, "Route not found") else nearest
    use_nearest = a["secondary"] is None and nearest is not None and a["form"] in ("house", "street")
    direction = s(raw.get("INTAPPROACHDIRECTION"))
    killed = _count(raw, "FATAL")
    return {
        "collision_id": s(raw.get("CRIMEID")),
        "report_number": s(raw.get("CCN")),
        "datetime": t.strftime("%Y-%m-%dT%H:%M") if t else None,
        "date": t.strftime("%Y-%m-%d") if t else "",
        "year": t.year if t else None,
        "hour": t.hour if timed else None,
        "lat": lat, "lon": lon, "location_source": src,
        "bad_coords": mpd != (None, None) and mpd != (0, 0) and src != "police_gps",
        "address": s(raw.get("ADDRESS")),
        "address_form": a["form"],
        "house_number": a["house_number"],
        "primary_road": a["primary"],
        "secondary_road": a["secondary"] or (nearest if use_nearest else None),
        "secondary_from_ddot": use_nearest,          # cross street derived by DDOT from the point, not the report
        # OFFINTERSECTION is metres (measured 2026-11-07: TIGER node to DDOT point / value = 3.28 on 655 crashes)
        "sec_distance": round(float(raw["OFFINTERSECTION"]) * M_TO_FT, 1)
        if use_nearest and raw.get("OFFINTERSECTION") is not None else None,
        "sec_direction": DIRS.get((direction or "").upper()) if use_nearest else None,
        "city_name": "WASHINGTON",
        "county_code": "11001",
        "ward": s(raw.get("WARD")),
        "killed": killed,
        "injured": sum(_count(raw, lv) for lv in ("MAJOR", "MINOR", "UNKNOWN")),
        "collision_type": None, "lighting": None, "weather": None, "surface": None,   # not published by DDOT
        "is_freeway": bool(FREEWAY.search((a["primary"] or "").upper())),
        "ped": _n(raw.get("TOTAL_PEDESTRIANS")) > 0,
        "bike": _n(raw.get("TOTAL_BICYCLES")) > 0,
        "vehicles": _n(raw.get("TOTAL_VEHICLES")),
        "speeding": _n(raw.get("SPEEDING_INVOLVED")) > 0,
        "impaired": any(_n(raw.get(f"{m}IMPAIRED")) > 0 for m in ("PEDESTRIANS", "BICYCLISTS", "DRIVERS")),
    }


def kabco(person: dict) -> str | None:
    """K / A / B from DDOT's injury flags; None = not injured (DC 'minor' = MMUCC B and C, see module doc)."""
    y = lambda k: str(person.get(k) or "").strip().upper() == "Y"
    return "K" if y("FATAL") else "A" if y("MAJORINJURY") else "B" if y("MINORINJURY") else None


def person_record(raw: dict) -> dict:
    s = lambda v: (str(v).strip() or None) if v is not None else None
    return {"person_id": s(raw.get("PERSONID")), "vehicle_id": s(raw.get("VEHICLEID")),
            "person_type": (s(raw.get("PERSONTYPE")) or "").upper() or None, "age": raw.get("AGE"),
            "vehicle_type": s(raw.get("INVEHICLETYPE")), "kabco": kabco(raw),
            "ticket": s(raw.get("TICKETISSUED")) == "Y", "impaired": s(raw.get("IMPAIRED")) == "Y",
            "speeding": s(raw.get("SPEEDING")) == "Y"}


def severity(raw: dict, persons: list[dict]) -> str:
    """Most severe outcome, from the persons and the crash's own counts (a count with no person row still counts);
    U = injured at an unknown level, O = no injury."""
    levels = [p["kabco"] for p in persons if p["kabco"]]
    levels += ["K"] * (_count(raw, "FATAL") > 0) + ["A"] * (_count(raw, "MAJOR") > 0) + ["B"] * (_count(raw, "MINOR") > 0)
    levels += ["U"] * (_count(raw, "UNKNOWN") > 0)
    return min(levels, key=SEVERITY_ORDER.index, default="O")


# -- state-pack contract (#19) --------------------------------------------------------------------------------------
def contract_record(c: dict) -> dict:
    """One records() crash -> the shared crash dict. DDOT's "minor" injury covers MMUCC B and C, so it is counted as
    injury, level not reported (U), never as B: no level is made up (#19)."""
    d = datetime.fromisoformat(c["date"]).date() if c["date"] else None
    return {"crash_id": c["collision_id"], "report_version": 0, "deleted": False, "preliminary": False,
            "date": c["date"], "year": c["year"], "hour": c["hour"], "day_of_week": d.strftime("%A") if d else None,
            "lat": c["lat"], "lon": c["lon"], "bad_coords": c["bad_coords"],
            "primary_road": c["primary_road"] if c["address_form"] != "house" else f"{c['house_number']} {c['primary_road']}",
            "secondary_road": None if c["address_form"] == "house" else c["secondary_road"],
            "offset_ft": None, "offset_dir": None, "city": "WASHINGTON", "county_code": "11001", "county_fips": "11001",
            "state": "DC", "is_freeway": c["is_freeway"], "killed": c["killed"], "injured": c["injured"],
            "severity": "U" if c["severity"] == "B" else c["severity"], "ped": c["ped"], "bike": c["bike"],
            "ebike": False, "escooter": False, "motorcycle": False, "heavy_truck": False, "parties": [],
            "collision_type": None, "lighting": None, "weather": None, "surface": None,
            "report_number": c["report_number"], "location_source_dc": c["location_source"]}


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir, opener=urllib.request.urlopen) -> dict:
    """Crashes whose DDOT point is in the box (s, w, n, e), year by year, with their persons; cached raw per year+box.
    Every published DC crash has a point (DDOT drops the ones it can't locate)."""
    import hashlib
    s, w, n, e = box
    out, missing = [], []
    for y in years:
        where = (f"REPORTDATE >= date '{y}-01-01' AND REPORTDATE < date '{y + 1}-01-01' AND LATITUDE >= {s:.6f} AND "
                 f"LATITUDE <= {n:.6f} AND LONGITUDE >= {w:.6f} AND LONGITUDE <= {e:.6f}")
        cache = cache_dir / f"dc_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json"
        if cache.exists():
            raw = json.loads(cache.read_text())
        else:
            crashes = _pages(CRASH_URL, where, opener)
            ids = [c["CRIMEID"] for c in crashes]
            persons = []
            for i in range(0, len(ids), 100):
                persons += _pages(PERSON_URL, "CRIMEID IN (" + ",".join(f"'{x}'" for x in ids[i:i + 100]) + ")", opener)
            raw = {"crashes": crashes, "persons": persons}
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(raw))
        got = [contract_record(c) for c in records(raw["crashes"], raw["persons"])]
        if not got:
            missing.append(y)
        out += got
    return {"crashes": out, "years_missing": missing,
            "cleaning": {"source_rows": len(out), "minor_injury_as_u": sum(c["severity"] == "U" for c in out)}}
