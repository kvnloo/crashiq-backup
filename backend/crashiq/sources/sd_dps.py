"""South Dakota crash source: DPS Office of Accident Records "Raw Crash Data" (SDARS), one zip per year, no login.

https://www.safesd.gov/ ("Download Crash Data" → Raw Crash Data, "updated April 15 annually", pipe-delimited),
2011-2025 as listed 2026-11-08: https://www.safesd.gov/downloads/raw-data/SDARSFiles<year>.zip (~10 MB each).
Each zip holds Accident, Person, Vehicle, Weather and 9 more tables linked by AccidentSeqID. Accident has the DPS
report number, local date and time, a WGS84 point (all but 1 of 18,975 crashes in 2025), the road and nearest cross
street with the distance and direction from it, and crash severity (Fatal / Injury / PDO); Person has each person's
KABCO (research_notes/sd-2026-11-08).

The files also carry names, addresses, phone numbers, birth dates, VINs and plates: this reader reads only the columns
named below and caches only the contract fields, never the zip. Wired into the app by the SD plug-in
(crashiq/statepacks/sd.py) through `fetch_contract`.
"""

from __future__ import annotations

import csv
import io
import json
import re
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from ..settings import ROOT

ZIP_URL = "https://www.safesd.gov/downloads/raw-data/SDARSFiles{year}.zip"
# shortcut: the years safesd.gov lists on 2026-11-08 (DPS adds one each April 15); widen when 2026 appears
YEARS = range(2011, 2026)
SEVERITY_ORDER = "KABCUO"
SD_LAT, SD_LON = (42.4, 46.0), (-104.1, -96.4)

PERSON_KABCO = {"Fatal injury": "K", "Incapacitating": "A", "Non-incapacitating": "B", "Possible": "C",
                "No injury": "O", "Wild animal hit": "O"}     # wild-animal-hit is DPS's damage-only short form
CRASH_FLOOR = {"Fatal": "K", "Injury": "U", "PDO": "O"}       # Accident.Severity: a crash is never below it
CCRS_TYPE = {"Angle": "BROADSIDE", "Rear-end ( front to rear )": "REAR END", "Head-on ( front to front )": "HEAD-ON",
             "Sideswipe, same direction": "SIDE SWIPE", "Sideswipe, opposite direction": "SIDE SWIPE",
             "Overturn/rollover": "OVERTURNED", "Pedestrian": "VEHICLE/PEDESTRIAN"}
CCRS_LIGHT = {"Dark - lighted roadway": "DARK - STREET LIGHTS", "Dark - roadway not lighted": "DARK - NO STREET LIGHTS",
              "Dark - unknown roadway lighting": "DARK - UNKNOWN STREET LIGHTS"}
COMPASS = {"North": "N", "South": "S", "East": "E", "West": "W", "Northeast": "NE", "Northwest": "NW",
           "Southeast": "SE", "Southwest": "SW"}
HEAVY = {"Tractor/semi-trailer", "Truck pulling trailer(s) - GCWR 10,001 lbs or more", "Tractor/doubles",
         "Tractor/triples", "Single-unit truck (2 axle, 6 tires) GVWR 10,001 lbs or more",
         "Single-unit truck (3 or more axles)", "Truck tractor only (bobtail)", "Tractor/mobile home"}


def _fips_by_county() -> dict[str, str]:
    boxes = json.loads((ROOT / "data" / "reference" / "county_boxes_sd.json").read_text())["counties"]
    out = {v["name"].removesuffix(" County").upper(): k for k, v in boxes.items()}
    out["SHANNON"] = "46102"          # renamed Oglala Lakota County in 2015 (the 2011-2014 files may use the old name)
    return out


FIPS = _fips_by_county()


def _s(v) -> str | None:
    v = re.sub(r"\s+", " ", v or "").strip()
    return v or None


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _rows(zf: zipfile.ZipFile, table: str):
    name = next(n for n in zf.namelist() if n.lower().startswith(table.lower()))
    with zf.open(name) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter="|")


def street_pair(road, cross, inter) -> tuple[str | None, str | None]:
    """DPS's road and cross street, repaired: 'A / B' in the road field is an intersection in one field (171 crashes
    in 2025); a cross street equal to the road (610) is replaced by the intersection name when there is one (388)."""
    road, cross, inter = _s(road), _s(cross), _s(inter)
    if road and " / " in road:
        road, b = (_s(x) for x in road.split(" / ", 1))
        cross = b if not cross or cross in (road, b) else cross
    if cross and cross == road:
        cross = inter if inter and inter != road else None
    return road, cross


def contract_record(a: dict, persons: list[str], units: set[str], weather: str | None) -> dict | None:
    """One Accident row (+ its persons' KABCO, unit types/configs, first weather) -> the shared crash dict, or None
    for a row whose columns slipped (a '|' inside a text field: 1 row in 2025)."""
    if a.get("Severity") not in CRASH_FLOOR:
        return None
    d = datetime.strptime(a["AccidentDateTime"].split()[0], "%m/%d/%Y").date() if a.get("AccidentDateTime") else None
    t = re.match(r"(\d{1,2}):\d{2}", a.get("AccidentTimeChar") or "")
    lat, lon = _num(a.get("LatitudeValue")), _num(a.get("LongitudeValue"))
    has = lat is not None and lon is not None and SD_LAT[0] <= lat <= SD_LAT[1] and SD_LON[0] <= lon <= SD_LON[1]
    qty, units_txt = _num(a.get("LocCrossDispQty")), a.get("CrossUnits") or ""
    offset = qty * 5280 if qty is not None and units_txt.startswith("Miles") else qty
    best = min([k for k in persons if k] + [CRASH_FLOOR[a["Severity"]]], key=SEVERITY_ORDER.index)
    fc, fh, moc = a.get("FuncClass") or "", _s(a.get("FHEvent")), _s(a.get("MOCDesc"))
    kind = moc if moc and not moc.startswith("No collision") else fh
    up = lambda v: v.upper() if v else None
    route = None if (a.get("PrimaryHwyNbr") or "0").strip() == "0" else a["PrimaryHwyNbr"].strip()  # 0 = off-system
    road, cross = street_pair(a.get("LocRoadwayName"), a.get("LocNearestCrossName"), a.get("LocIntersectionName"))
    return {"crash_id": a["AccidentNbr"].strip(), "report_version": 0, "deleted": False, "preliminary": False,
            "date": d.isoformat() if d else "", "year": d.year if d else None,
            "hour": int(t[1]) if t and int(t[1]) < 24 else None, "day_of_week": d.strftime("%A") if d else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": road, "secondary_road": cross,
            "offset_ft": offset or None, "offset_dir": COMPASS.get(a.get("CrossDir") or ""),
            "intersection_name": _s(a.get("LocIntersectionName")),
            "city": None if (a.get("CityName") or "Rural") == "Rural" else a["CityName"].upper(),
            "county_code": _s(a.get("CountyName")), "county_fips": FIPS.get((a.get("CountyName") or "").strip().upper()),
            "state": "SD", "is_freeway": "Interstate" in fc or "Freeway" in fc or a.get("HwyClassDesc") == "Ramp",
            "killed": persons.count("K"), "injured": sum(persons.count(k) for k in "ABC"), "severity": best,
            "severity_reported": a["Severity"],
            "ped": "Pedestrian" in units or fh == "Pedestrian", "bike": "Pedalcyclist driver" in units or fh == "Pedalcycle",
            "ebike": False, "escooter": False, "motorcycle": "Motorcycle" in units, "heavy_truck": bool(units & HEAVY),
            "parties": [], "collision_type": CCRS_TYPE.get(kind, up(kind)),
            "lighting": CCRS_LIGHT.get(a.get("LightDesc"), up(_s(a.get("LightDesc")))), "weather": up(weather),
            "surface": up(_s(a.get("RoadCondDesc"))), "wild_animal": a.get("IsWildAnimalHitInd") == "True",
            "route": route, "milepost": _num(a.get("ILTMRM")) if route else None}


def read_zip(zf: zipfile.ZipFile) -> tuple[list[dict], int]:
    """Every crash of one year's SDARS zip (contract dicts) and the number of slipped rows dropped."""
    persons: dict[str, list] = defaultdict(list)
    for p in _rows(zf, "Person"):
        persons[p["AccidentSeqID"]].append(PERSON_KABCO.get(p.get("InjuryStatusDesc")))
    units: dict[str, set] = defaultdict(set)
    for v in _rows(zf, "Vehicle"):
        units[v["AccidentSeqID"]] |= {v.get("UnitTypeDesc"), v.get("VehConfigDesc")}
    weather: dict[str, str] = {}
    for w in _rows(zf, "Weather"):
        if w.get("WeatherCondNbr") == "1":
            weather[w["AccidentSeqID"]] = _s(w.get("WeatherDesc"))
    out, bad = [], 0
    for a in _rows(zf, "Accident"):
        sid = a.get("AccidentSeqID")
        c = contract_record(a, persons.get(sid, []), units.get(sid, set()), weather.get(sid))
        if c is None:
            bad += 1
        else:
            out.append(c)
    return out, bad


def year(y: int, cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """One year's crashes, statewide: read from the slim cache, else downloaded, read and cached (the zip itself,
    which holds personal data, is deleted as soon as it's read)."""
    slim = cache_dir / f"sd_dps_{y}.json"
    if slim.exists():
        return json.loads(slim.read_text())
    cache_dir.mkdir(parents=True, exist_ok=True)
    part = cache_dir / f"sd_dps_{y}.zip.part"
    req = urllib.request.Request(ZIP_URL.format(year=y), headers={"User-Agent": "CrashIQ/0.1"})
    try:
        with opener(req, timeout=300) as r, open(part, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        with zipfile.ZipFile(part) as zf:
            crashes, bad = read_zip(zf)
    finally:
        part.unlink(missing_ok=True)
    got = {"year": y, "crashes": crashes, "slipped_rows": bad, "read": date.today().isoformat()}
    slim.write_text(json.dumps(got))
    return got


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Crashes with a point in the box (s, w, n, e), plus the corridor counties' crashes with no point (for the core's
    street-name sort), in those years."""
    s, w, n, e = box
    out, slipped, no_point = [], 0, 0
    for y in (y for y in years if y in YEARS):
        got = year(y, cache_dir, opener)
        slipped += got["slipped_rows"]
        for c in got["crashes"]:
            if c["lat"] is None:
                if c["county_fips"] in county_fips:
                    out.append(c)
                    no_point += 1
            elif s <= c["lat"] <= n and w <= c["lon"] <= e and c["county_fips"]:
                out.append(c)
    return {"crashes": out, "years_missing": [y for y in years if y not in YEARS],
            "cleaning": {"source_rows": len(out), "no_point_in_counties": no_point, "slipped_rows_dropped": slipped,
                         "files": f"SDARS {YEARS.start}-{YEARS.stop - 1}"}}
