"""New Jersey crash source: NJDOT crash records ("Crash Tables"), one zip per county, year and table, no login.

https://dot.nj.gov/transportation/refdata/accident/rawdata01-current.shtm (Bureau of Transportation Data and
Safety): Crash, Driver, Vehicle, Occupant and Pedestrian tables from the police NJTR-1 reports, fixed-width text,
linked by Year + County Code + Municipality Code + Department Case Number. The page's year list shows 2001-2018, but
2019-2023 sit at the same paths (checked 2026-11-08; 2019 only on www.nj.gov, 2023 only on dot.nj.gov). Layout:
NJDOT "Crash Table Layout (2017 - Present)", printed 8/27/2025. Person severity is the NJTR-1 Box 86 physical
condition, 01-05 = K A B C O (NJTR-1 Crash Report Manual 2023). Statewide: 195,000-284,000 crashes a year; a point
on 26-38% of 2017-2022 crashes and 60% of 2023's, a cross street on 76-82%, a route + milepost on ~90%
(research_notes/nj-2026-11-08).

The Driver and Pedestrian tables carry home towns, ZIP codes and birth dates: this reader reads only the columns
named below and caches only the contract fields, never the zips.
"""

from __future__ import annotations

import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from ..settings import ROOT

HOSTS = ("https://dot.nj.gov", "https://www.nj.gov")
# dot.nj.gov's firewall (Incapsula) answers a bare "CrashIQ/0.1" with 403 after a few files; a Mozilla-style UA passes
UA = "Mozilla/5.0 CrashIQ/0.1"
ZIP_PATH = "/transportation/refdata/accident/{year}/{county}{year}{table}.zip"
# shortcut: 2017-2023 share one layout and are what NJDOT posts (2026-11-08); 2001-2016 use the older layout and
# 2024+ isn't posted (the Crash Data Portal has it, interactive only). Add a year when NJDOT posts it.
YEARS = range(2017, 2024)
SEVERITY_ORDER = "KABCUO"
NJ_LAT, NJ_LON = (38.8, 41.4), (-75.6, -73.8)

# 1-based (from, to) positions, NJDOT Crash Table Layout (2017 - Present)
CRASH = {"county": (5, 6), "muni": (7, 8), "county_name": (33, 44), "muni_name": (46, 69), "date": (71, 80),
         "time": (85, 88), "killed": (135, 136), "injured": (138, 139), "severity": (147, 147),
         "crash_type": (155, 156), "location": (161, 210), "route": (214, 217), "sri": (221, 236),
         "milepost": (238, 244), "road_system": (246, 247), "surface": (261, 262), "light": (264, 265),
         "environment": (267, 268), "distance": (276, 279), "unit": (281, 282), "direction": (284, 284),
         "cross": (286, 320), "lat": (362, 370), "lon": (372, 380)}
OCCUPANT = {"condition": (39, 40)}
PEDESTRIAN = {"number": (33, 34), "condition": (36, 37), "bicyclist": (388, 388)}
VEHICLE_TYPE = 17     # comma field: the 2023 file's fields sit off the layout's positions (model is 30 wide)

PERSON_KABCO = {"01": "K", "02": "A", "03": "B", "04": "C", "05": "O"}   # Box 86; blank before 2023 = no injury
CRASH_FLOOR = {"F": "K", "I": "U", "P": "O"}                            # crash Severity: never below it
COLLISION = {"01": "REAR END", "02": "SIDE SWIPE", "03": "BROADSIDE", "04": "HEAD-ON", "05": "SIDE SWIPE",
             "06": "PARKED MOTOR VEHICLE", "07": "LEFT TURN/U-TURN", "08": "BACKING", "09": "ENCROACHMENT",
             "10": "OVERTURNED", "11": "HIT OBJECT", "12": "ANIMAL", "13": "VEHICLE/PEDESTRIAN",
             "14": "PEDALCYCLIST", "15": "NON-FIXED OBJECT", "16": "RAILCAR VEHICLE", "99": "OTHER"}
LIGHT = {"01": "DAYLIGHT", "02": "DUSK - DAWN", "03": "DUSK - DAWN", "04": "DARK - STREET LIGHTS NOT FUNCTIONING",
         "05": "DARK - NO STREET LIGHTS", "06": "DARK - STREET LIGHTS", "07": "DARK - STREET LIGHTS"}
WEATHER = {"01": "CLEAR", "02": "RAINING", "03": "SNOWING", "04": "FOG", "05": "CLOUDY", "06": "SLEET/HAIL",
           "07": "FREEZING RAIN", "08": "BLOWING SNOW", "09": "BLOWING SAND/DIRT", "10": "WIND"}
SURFACE = {"01": "DRY", "02": "WET", "03": "SNOWY", "04": "ICY", "05": "SLUSH", "06": "WATER", "07": "SAND",
           "08": "OIL/FUEL", "09": "MUD, DIRT, GRAVEL"}
HEAVY = {str(n) for n in range(20, 28)}           # Vehicle Type 20-27: single-unit trucks and tractors
DIRECTION = {"N", "S", "E", "W"}

ROUTE_ONLY = re.compile(r"^(?:[A-Z]+(?: [A-Z]+)? COUNTY|CR|CO RD|COUNTY ROUTE|ROUTE|RT|NJ|US|I) ?-? ?\d+\b")


def _county_files() -> dict[str, str]:
    """5-digit FIPS -> NJDOT's file prefix ('CapeMay')."""
    boxes = json.loads((ROOT / "data" / "reference" / "county_boxes_nj.json").read_text())["counties"]
    return {k: v["name"].removesuffix(" County").replace(" ", "") for k, v in boxes.items()}


COUNTY_FILES = _county_files()


def _s(v) -> str | None:
    v = re.sub(r"\s+", " ", v or "").strip()
    return v or None


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def road(v) -> str | None:
    """An NJTR-1 road or cross-street field in the form TIGER names it. Police write 'Fries Mill Road (GLOUCESTER
    COUNTY 655)', 'CR 681 / PATERSON PLANK RD' (route / name), 'I- 80 / E RIDGEWOOD AVE', 'MERCER COUNTY 622',
    'NJ 17', 'ROUTE 535' (a county route) and 'JACKSON RD **'; TIGER has 'Co Rd 622' and 'State Rte 17'."""
    v = _s(v)
    if not v:
        return None
    paren = re.search(r"\(([^)]*)\)?$", v)
    v = re.sub(r"\s*\([^)]*\)?$", "", v)                 # trailing '(X COUNTY 655)' or '(Cranbury Road)' alias
    v = re.sub(r"\s+SECONDARY\b.*$", "", v, flags=re.I)  # 'I-78 Secondary': the other carriageway, same road
    v = re.sub(r"[^\w)]+$", "", v).strip()
    parts = [p.strip() for p in v.split("/") if p.strip()] or [v]
    v = next((p for p in parts if not ROUTE_ONLY.match(p.upper())), parts[0])     # a street name beats a route
    up = v.upper()
    if m := re.match(r"^(?:[A-Z]+(?: [A-Z]+)? COUNTY|CR|COUNTY ROUTE|ROUTE|RT) ?(\d+)[A-Z]?$", up):
        if int(m[1]) >= 600 and paren and not re.search(r"\d", paren[1]):
            return _s(paren[1])                          # 600+ county routes have no number on the TIGER map
    if m := re.match(r"^(?:[A-Z]+(?: [A-Z]+)? COUNTY|CR|COUNTY ROUTE) ?(\d+[A-Z]?)$", up):
        return f"CO RD {m[1]}"
    if m := re.match(r"^(?:ROUTE|RT|NJ) ?-? ?(\d+)([A-Z]?)$", up):
        return f"CO RD {m[1]}" if int(m[1]) >= 500 else f"STATE RTE {m[1]}{m[2]}"   # 500+: county routes
    return v or None


def _field(line: str, spec: dict) -> dict:
    return {k: line[a - 1:b].strip() for k, (a, b) in spec.items()}


def _lines(zf: zipfile.ZipFile):
    with zf.open(zf.namelist()[0]) as f:
        for raw in io.TextIOWrapper(f, encoding="latin-1", newline=""):
            yield raw.rstrip("\r\n")


def contract_record(key: str, r: dict, persons: list[str], peds: list[dict], vtypes: set[str]) -> dict | None:
    """One Crash-table row (fields by CRASH) + its people and vehicle types -> the shared crash dict, or None for a
    row without a severity (1 of 250,498 in 2023)."""
    if r["severity"] not in CRASH_FLOOR:
        return None
    try:
        d = datetime.strptime(r["date"], "%m/%d/%Y").date()
    except ValueError:
        d = None
    hour = int(r["time"][:2]) if re.fullmatch(r"\d{4}", r["time"] or "") and int(r["time"][:2]) < 24 else None
    lat, lon = _num(r["lat"]), _num(r["lon"])
    lon = -lon if lon and lon > 0 else lon            # 2017-2022 files write west longitude unsigned (74.1568)
    has = lat is not None and lon is not None and NJ_LAT[0] <= lat <= NJ_LAT[1] and NJ_LON[0] <= lon <= NJ_LON[1]
    dist, unit = _num(r["distance"]), r["unit"]
    offset = 0.0 if unit == "AT" else dist * 5280 if dist is not None and unit == "MI" else dist
    levels = persons + [p["level"] for p in peds]
    best = min([k for k in levels if k] + [CRASH_FLOOR[r["severity"]]], key=SEVERITY_ORDER.index)
    county = r["county"]
    fips = f"34{2 * int(county) - 1:03d}" if county.isdigit() and 1 <= int(county) <= 21 else None
    rs = r["road_system"]
    return {"crash_id": key, "report_version": 0, "deleted": False, "preliminary": False,
            "date": d.isoformat() if d else "", "year": d.year if d else None, "hour": hour,
            "day_of_week": d.strftime("%A") if d else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": road(r["location"]), "secondary_road": road(r["cross"]),
            "offset_ft": offset or None, "offset_dir": r["direction"] if r["direction"] in DIRECTION else None,
            "city": (r["muni_name"] or "").upper() or None, "county_code": _s(r["county_name"]), "county_fips": fips,
            "state": "NJ", "is_freeway": rs in ("01", "03"),     # Box 99: 01 Interstate, 03 State/Interstate Authority
            # the crash's own totals: a crash entered twice (2,868 in 2023) lists its people twice
            "killed": int(_num(r["killed"]) or 0), "injured": int(_num(r["injured"]) or 0),
            "severity": best, "severity_reported": r["severity"],
            "ped": any(not p["bike"] for p in peds) or r["crash_type"] == "13",
            "bike": any(p["bike"] for p in peds) or r["crash_type"] == "14",
            "ebike": False, "escooter": False, "motorcycle": "08" in vtypes, "heavy_truck": bool(vtypes & HEAVY),
            "parties": [], "collision_type": COLLISION.get(r["crash_type"]),
            "lighting": LIGHT.get(r["light"]), "weather": WEATHER.get(r["environment"]),
            "surface": SURFACE.get(r["surface"]), "route": _s(r["sri"]), "milepost": _num(r["milepost"])}


def read_tables(crash: zipfile.ZipFile, occupant: zipfile.ZipFile, pedestrian: zipfile.ZipFile,
                vehicle: zipfile.ZipFile) -> tuple[list[dict], Counter]:
    """Every crash of one county-year (contract dicts) and what was dropped, by reason."""
    persons: dict[str, list] = defaultdict(list)
    for line in _lines(occupant):
        persons[line[:31].strip()].append(PERSON_KABCO.get(_field(line, OCCUPANT)["condition"]))
    peds: dict[str, list] = defaultdict(list)
    for line in _lines(pedestrian):
        p = _field(line, PEDESTRIAN)
        peds[line[:31].strip()].append({"level": PERSON_KABCO.get(p["condition"]),
                                        "bike": p["number"].startswith("B") or p["bicyclist"] == "Y"})
    vtypes: dict[str, set] = defaultdict(set)
    for line in _lines(vehicle):
        if len(f := line.split(",")) == 40:          # a comma inside make/model: type unknown, left out
            vtypes[f[0].strip()].add(f[VEHICLE_TYPE].strip())
    out, seen, dropped = [], set(), Counter()
    for line in _lines(crash):
        if len(line) < CRASH["lon"][1]:          # a line break inside the free-text damage field
            dropped["broken_lines"] += 1
            continue
        key = line[:31].strip()
        if key in seen:
            dropped["duplicate_keys"] += 1
            continue
        seen.add(key)
        c = contract_record(key, _field(line, CRASH), persons.get(key, []), peds.get(key, []), vtypes.get(key, set()))
        if c is None:
            dropped["no_severity"] += 1
        else:
            out.append(c)
    return out, dropped


def _download(year: int, county: str, table: str, opener) -> bytes:
    """One table zip; tries both NJ hosts (each misses some years and answers a miss with an HTML page)."""
    for host in HOSTS:
        req = urllib.request.Request(host + ZIP_PATH.format(year=year, county=county, table=table),
                                     headers={"User-Agent": UA})
        try:
            with opener(req, timeout=300) as r:
                body = r.read()
        except urllib.error.HTTPError:
            continue
        if body[:2] == b"PK":
            return body
    raise FileNotFoundError(f"NJDOT has no {county} {year} {table} file")


def county_year(fips: str, y: int, cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """One county-year's crashes: read from the slim cache, else downloaded (4 zips, ~3 MB for a big county) and
    cached as contract fields only."""
    slim = cache_dir / f"nj_njdot_{fips}_{y}.json"
    if slim.exists():
        return json.loads(slim.read_text())
    county = COUNTY_FILES[fips]
    zips = [zipfile.ZipFile(io.BytesIO(_download(y, county, t, opener)))
            for t in ("Accidents", "Occupants", "Pedestrians", "Vehicles")]
    crashes, dropped = read_tables(*zips)
    got = {"county": fips, "year": y, "crashes": crashes, "dropped": dict(dropped), "read": date.today().isoformat()}
    cache_dir.mkdir(parents=True, exist_ok=True)
    slim.write_text(json.dumps(got))
    return got


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """The corridor counties' crashes in those years: those with a point in the box (s, w, n, e), plus those with no
    point (for the core's street-name sort)."""
    s, w, n, e = box
    out, dropped, no_point = [], Counter(), 0
    for fips in (f for f in county_fips if f in COUNTY_FILES):
        for y in (y for y in years if y in YEARS):
            got = county_year(fips, y, cache_dir, opener)
            dropped.update(got["dropped"])
            for c in got["crashes"]:
                if c["lat"] is None:
                    out.append(c)
                    no_point += 1
                elif s <= c["lat"] <= n and w <= c["lon"] <= e:
                    out.append(c)
    return {"crashes": out, "years_missing": [y for y in years if y not in YEARS],
            "cleaning": {"source_rows": len(out), "no_point_in_counties": no_point, **dropped,
                         "files": f"NJDOT crash tables {YEARS.start}-{YEARS.stop - 1}"}}
