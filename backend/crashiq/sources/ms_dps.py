"""Mississippi crash source: Mississippi Department of Public Safety (DPS) public data, eCrash yearly workbooks
(https://publicdata.dps.ms.gov/Public-CrashData/eCrash/), statewide, 2019 (partial) to last year (DRAFT), no login.

One Excel workbook per year (about 100 MB): sheets Crashes, Drivers, Passengers, Non-Motorists, Vehicles, linked by
Crash ID (a GUID). Every 2024 crash (74,968 of 74,968) has a GPS point inside Mississippi. Street names: Street Name
and Intersecting Street Name, or a bare Road Number ("55") whose kind is the Road Classification ("Interstate").
Severity is KABCO per person ("(A) Suspected Serious Injury"); the crash takes its worst person. There is no manner of
collision in the public file, so `collision_type` is only VEHICLE/PEDESTRIAN.

A year is downloaded once, read (about 6 minutes with openpyxl), kept as gzipped crash records in the cache and the
workbook deleted. The cache name carries the file's URL, so when DPS replaces a DRAFT year the new file is read.

Licence: none published; DPS says the files are "made available to the public free of charge" (ms-import.md §2).
Wired into the app by the MS state pack (statepacks/ms.py, #19) through `fetch_contract`.
"""

from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import shutil
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

INDEX = "https://publicdata.dps.ms.gov/Public-CrashData/eCrash/"
FILE = re.compile(r'href="([^"]*\((\d\d)-01-01 to [^)]*\)( DRAFT)?\.xlsx)"')
MS_LAT, MS_LON = (30.0, 35.1), (-91.8, -88.0)        # Mississippi's extent with a small margin
INJURY = {"(K) Fatal Injury": "K", "(A) Suspected Serious Injury": "A", "(B) Suspected Minor Injury": "B",
          "(C) Possible Injury": "C", "(O) No Apparent Injury": "O"}
ROUTE = {"Interstate": "I-", "US highway": "US ", "State highway": "MS "}   # OSM's ref: the corridor matches "MS 25"
LIGHT = {"Daylight": "DAYLIGHT", "Dawn/dusk": "DUSK - DAWN", "Dark - lighted": "DARK - STREET LIGHTS",
         "Dark - not lighted": "DARK - NO STREET LIGHTS", "Dark - unknown lighting": "DARK - UNKNOWN STREET LIGHTS",
         "Other": "OTHER", "Unknown": "NOT STATED"}
PED = {"Pedestrian", "Other Pedestrian"}
BIKE = {"Bicyclist", "Other cyclist"}
MOTORCYCLE = {"2-wheeled motorcycle", "3-wheeled motorcycle", "Autocycle", "Moped or motorized bicycle"}
HEAVY_TRUCK = {"Truck tractor", "Single-unit truck", "Other truck"}


def plausible(lat, lon) -> bool:
    return (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
            and MS_LAT[0] <= lat <= MS_LAT[1] and MS_LON[0] <= lon <= MS_LON[1])


def _s(v) -> str:
    return str(v).strip() if v is not None else ""


def road(name, number, kind) -> str | None:
    """Street Name, else the Road Number written as a route: ("", "55", "Interstate") -> "I-55"."""
    name, number = _s(name), _s(number)
    if name:
        return name
    if not number:
        return None
    return ROUTE.get(kind, "HWY ") + number if number.isdigit() else number


def severity(people: list[str], killed: int, injured: int) -> str:
    """Worst person's KABCO; the report's own counts win when they say worse (a death or an injury nobody carries)."""
    worst = min(people, key="KABCO".index, default="O")
    if killed:
        return "K"
    if injured and worst == "O":
        return "U"
    return worst


def _words(v) -> str | None:
    v = _s(v).split(";")[0].strip()
    return v.upper() if v and v not in ("Unknown", "Not applicable") else None


def crash_record(r: dict, people: list[str], nm: set, bodies: set, hit_run: bool | None, surface,
                 preliminary: bool) -> dict:
    """One Crashes row and its people / vehicles -> the shared crash shape (packs.check_crash)."""
    lat, lon = r.get("Latitude"), r.get("Longitude")
    has = plausible(lat, lon)
    day = _s(r.get("Crash Date")).replace("/", "-")
    hh = _s(r.get("Crash Time"))[:2]
    killed, injured = int(r.get("Fatality Count") or 0), int(r.get("Injury Count") or 0)
    kind = r.get("Road Classification")
    city = _s(r.get("City"))
    ped = bool(nm & PED)
    return {
        "crash_id": r["Crash ID"], "report_number": r.get("State Case Number"), "report_version": 0,
        "deleted": False, "preliminary": preliminary,
        "date": day, "year": int(day[:4]), "hour": int(hh) if hh.isdigit() else None,
        "lat": lat if has else None, "lon": lon if has else None,
        "bad_coords": lat not in (None, 0) and not has,
        "primary_road": road(r.get("Street Name"), r.get("Road Number"), kind),
        "secondary_road": road(r.get("Intersecting Street Name"), r.get("Intersecting Road Number"), kind),
        "offset_ft": None, "offset_dir": None,
        "milepost": r.get("Milepost Number"),
        "city": None if not city or city.startswith("Rural ") else city,      # "Rural Hinds": unincorporated
        "county_code": r.get("County"), "county_fips": f"28{2 * int(r['County ID']) - 1:03d}", "state": "MS",
        "is_freeway": kind == "Interstate", "road_class": kind,
        "killed": killed, "injured": injured,
        "severity": severity(people, killed, injured), "severity_reported": None,
        "ped": ped, "bike": bool(nm & BIKE), "ebike": False, "escooter": False,
        "motorcycle": bool(bodies & MOTORCYCLE), "heavy_truck": bool(bodies & HEAVY_TRUCK), "hit_run": hit_run,
        "parties": [],
        "collision_type": "VEHICLE/PEDESTRIAN" if ped else None,
        "lighting": LIGHT.get(r.get("Light Condition")), "weather": _words(r.get("Weather")),
        "surface": _words(surface), "contributing": None,
        "alcohol": r.get("Alcohol Involvement") == "Yes", "drugs": r.get("Drug Involvement") == "Yes",
        "work_zone": r.get("Work Zone Relation") == "Yes",
        "intersection": bool(r.get("Is Intersection?")),
        "traffic_control": _words(r.get("Intersection Traffic Control")),
    }


def read_workbook(path: Path, preliminary: bool = False) -> list[dict]:
    """Every crash in one DPS eCrash workbook, people and vehicles joined by Crash ID."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)

    def rows(sheet):
        it = wb[sheet].iter_rows(values_only=True)
        head = next(it)
        for r in it:
            d = dict(zip(head, r))            # Crashes repeats "Roadway Clearance Date": the later one wins, unused
            d["Crash ID"] = d.get("Crash ID") or d.get("Crash Id")     # Drivers and Passengers spell it "Crash Id"
            yield d

    people, nm, bodies, hit, surface = defaultdict(list), defaultdict(set), defaultdict(set), {}, {}
    for sheet in ("Drivers", "Passengers", "Non-Motorists"):
        for p in rows(sheet):
            if p.get("Injury Status") in INJURY:
                people[p["Crash ID"]].append(INJURY[p["Injury Status"]])
            if sheet == "Non-Motorists":
                nm[p["Crash ID"]].add(p.get("Non-Motorist Type"))
    for v in rows("Vehicles"):
        cid = v["Crash ID"]
        bodies[cid].add(v.get("Body Type"))
        hit[cid] = hit.get(cid, False) or _s(v.get("Hit And Run")).startswith("Yes")
        surface.setdefault(cid, v.get("Roadway Surface Condition"))
    out = [crash_record(r, people[r["Crash ID"]], nm[r["Crash ID"]], bodies[r["Crash ID"]], hit.get(r["Crash ID"]),
                        surface.get(r["Crash ID"]), preliminary)
           for r in rows("Crashes") if r["Crash ID"]]
    wb.close()
    return out


def _open(url: str, opener):
    return opener(urllib.request.Request(url, headers={"User-Agent": "CrashIQ/0.1"}), timeout=600)


def year_files(opener=urllib.request.urlopen) -> dict[int, tuple[str, bool]]:
    """{year: (workbook url, is DRAFT)} from the DPS eCrash index page."""
    with _open(INDEX, opener) as r:
        page = r.read().decode("utf-8", "replace")
    return {2000 + int(yy): (urllib.parse.quote(html.unescape(u), safe=":/()"), bool(d))
            for u, yy, d in FILE.findall(page)}


def fetch_year(year: int, files: dict, cache_dir: Path, opener=urllib.request.urlopen) -> list[dict] | None:
    """One year's crashes (None if DPS has no file for it), read once and cached as gzipped JSON."""
    if year not in files:
        return None
    url, draft = files[year]
    cache = cache_dir / f"ms_dps_{year}_{hashlib.sha1(url.encode()).hexdigest()[:8]}.json.gz"
    if cache.exists():
        return json.loads(gzip.decompress(cache.read_bytes()))
    cache_dir.mkdir(parents=True, exist_ok=True)
    book = cache_dir / f"ms_dps_{year}.xlsx"
    with _open(url, opener) as r, open(book, "wb") as f:
        shutil.copyfileobj(r, f)
    try:
        recs = read_workbook(book, draft)
    finally:
        book.unlink(missing_ok=True)             # 100 MB a year: keep only the records
    cache.write_bytes(gzip.compress(json.dumps(recs).encode()))
    return recs


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path,
                   opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years."""
    s, w, n, e = box
    files = year_files(opener)
    out, missing, read = [], [], 0
    for y in years:
        recs = fetch_year(y, files, Path(cache_dir), opener)
        if recs is None:
            missing.append(y)
            continue
        read += len(recs)
        out += [c for c in recs if c["lat"] is not None and s <= c["lat"] <= n and w <= c["lon"] <= e]
    return {"crashes": out, "years_missing": missing,
            "cleaning": {"statewide_rows_read": read, "draft_years": sorted(y for y in years if files.get(y, ("", 0))[1])}}
