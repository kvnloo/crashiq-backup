"""Nebraska crash source: NDOT's Nebraska Transportation Information Portal (NTIP) crash map
(https://ntip2021.nebraska.gov/NTIP2021/Map), statewide, 2021 to now, no login.

The map's form posts to /NTIP2021/Map/Crashes (dates, a lat/long box, filters) and gets back every matching crash:
key, GPS point (all of them), severity 01-05 (K, A, B "Visible Injury", C, O), 06 non-reportable, 96 not stated, date,
time, weather, county, alcohol, and a location sentence ("INT-72ND STREET (5037) & DODGE STREET (006)",
"LEAVENWORTH STREET (5044) E OF 60TH STREET (5043)"). One row per crash: no people, vehicles, light, surface or road
class. Pedestrian, bicycle, motorcycle and freeway crashes are found by asking again with that filter on.
Non-reportable (06) and not-stated (96) crashes are left out and counted.

Licence: the portal shows a CONFIDENTIAL notice (23 U.S.C. 407) saying Nebraska "has not authorized further
distribution of this document or its contents"; NDOT's permission is a user action (ne-import.md §2). The endpoint is
the web map's own, not a published API. Wired in by statepacks/ne.py as reader_only (#19).
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from crashiq.packs import REF

URL = "https://ntip2021.nebraska.gov/NTIP2021/Map/Crashes"
NE_LAT, NE_LON = (39.9, 43.1), (-104.1, -95.3)       # Nebraska's extent with a small margin
SEVERITY = {"01": "K", "02": "A", "03": "B", "04": "C", "05": "O"}     # 06 non-reportable, 96 not stated: out
FLAGS = {"ped": {"pedInvol": "Y"}, "bike": {"bicycleInvol": "Y"}, "motorcycle": {"motoInvol": "Y"},
         "is_freeway": {"roadClass": ["1", "2"]}}     # interstate; other freeways and expressways
_CODE = re.compile(r"\s*\([^)]*\)")                  # NDOT's street / route codes: "(5044)", "(080)"
_SPLIT = re.compile(r"\s+&\s*|\s+(N|S|E|W|NE|NW|SE|SW) OF\s+")
_ROUTE = re.compile(r"^N-(\d+)")                     # Nebraska highway "N-133" -> OSM's ref "NE 133"
COUNTY = {v["name"].removesuffix(" County").upper(): k
          for k, v in json.loads((REF / "county_boxes_ne.json").read_text())["counties"].items()}


def plausible(lat, lon) -> bool:
    return (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
            and NE_LAT[0] <= lat <= NE_LAT[1] and NE_LON[0] <= lon <= NE_LON[1])


def location(text: str | None) -> dict:
    """NTIP's location sentence -> primary, secondary, offset direction, intersection."""
    s = _CODE.sub("", (text or "").upper()).strip()
    inter = s.startswith("INT-")
    s = s.removeprefix("INT-").strip()
    m = _SPLIT.search(s)
    if m:
        prim, sec, d = s[:m.start()], s[m.end():], m.group(1)
        sec = re.sub(r"\s+NEAR\s+.*$", "", sec)      # "... S OF W CENTER ROAD NEAR OMAHA": the town, not a street
    else:
        prim, _, sec = s.partition(" NEAR ")
        d = None
    fix = lambda r: _ROUTE.sub(r"NE \1", r.strip()) or None
    return {"primary_road": fix(prim), "secondary_road": fix(sec), "offset_dir": d, "intersection": inter}


def crash_record(c: dict, flags: dict[str, set]) -> dict | None:
    """One NTIP crash -> the shared crash shape (packs.check_crash); None for non-reportable / not stated."""
    sev = SEVERITY.get(c.get("s"))
    if sev is None:
        return None
    lat, lon = c.get("a"), c.get("o")
    has = plausible(lat, lon)
    t = datetime.strptime(f"{c['d']} {c.get('t') or '12:00 AM'}", "%m/%d/%Y %I:%M %p")
    k = c["k"]
    w = [x for x in c.get("w") or [] if x not in ("Unknown", "Other")]
    return {
        "crash_id": str(k), "report_version": 0, "deleted": False, "preliminary": False,
        "date": t.date().isoformat(), "year": t.year, "hour": t.hour if c.get("t") else None,
        "day_of_week": c.get("y"),
        "lat": lat if has else None, "lon": lon if has else None,
        "bad_coords": lat not in (None, 0) and not has,
        **location(c.get("l")), "offset_ft": None, "location_text": c.get("l"),
        "city": None, "county_code": c.get("c"), "county_fips": COUNTY.get((c.get("c") or "").upper()), "state": "NE",
        "is_freeway": k in flags["is_freeway"],
        "killed": 0, "injured": 0,                   # not published
        "severity": sev, "severity_reported": c.get("s"),
        "ped": k in flags["ped"], "bike": k in flags["bike"], "ebike": False, "escooter": False,
        "motorcycle": k in flags["motorcycle"], "heavy_truck": False, "hit_run": None, "parties": [],
        "collision_type": "VEHICLE/PEDESTRIAN" if k in flags["ped"] else None,
        "lighting": None, "weather": w[0].upper() if w else None, "surface": None, "contributing": None,
        "alcohol": c.get("r") == "Yes", "drugs": None, "work_zone": None,
    }


def query(box, year: int, extra: dict, opener=urllib.request.urlopen) -> list[dict]:
    """Every NTIP crash in the box (s, w, n, e) in one year, with optional form filters."""
    s, w, n, e = box
    form = {"fromDate": f"01/01/{year}", "toDate": f"12/31/{year}", "minLat": s, "maxLat": n, "minLong": w,
            "maxLong": e, **extra}
    req = urllib.request.Request(URL, data=urllib.parse.urlencode(form, doseq=True).encode(), method="POST",
                                 headers={"User-Agent": "CrashIQ/0.1", "X-Requested-With": "XMLHttpRequest"})
    with opener(req, timeout=600) as r:
        got = json.loads(r.read())
    return [c for g in got.get("CoordGroups") or [] for c in g["Crashes"]]


def fetch_year(box, year: int, cache_dir: Path | None, opener=urllib.request.urlopen) -> dict:
    """{"rows": [...], "flags": {name: [keys]}} for one box and year, cached per box and year."""
    key = hashlib.sha1(json.dumps([list(box), year]).encode()).hexdigest()[:10]
    cache = cache_dir / f"ne_ntip_{key}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    out = {"rows": query(box, year, {}, opener),
           "flags": {f: [c["k"] for c in query(box, year, q, opener)] for f, q in FLAGS.items()}}
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out))
    return out


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path,
                   opener=urllib.request.urlopen) -> dict:
    """Every reportable crash with a point in the box in those years (NTIP starts at 2021)."""
    out, missing, rows = [], [], 0
    left = {"06": 0, "96": 0}
    for y in years:
        if not 2021 <= y <= datetime.now().year:
            missing.append(y)
            continue
        got = fetch_year(box, y, Path(cache_dir), opener)
        flags = {f: set(v) for f, v in got["flags"].items()}
        rows += len(got["rows"])
        for c in got["rows"]:
            rec = crash_record(c, flags)
            if rec is None:
                left[c.get("s")] = left.get(c.get("s"), 0) + 1
            elif rec["lat"] is not None:
                out.append(rec)
    return {"crashes": out, "years_missing": missing,
            "cleaning": {"source_rows": rows, "non_reportable_left_out": left.get("06", 0),
                         "not_stated_left_out": sum(v for k, v in left.items() if k != "06")}}
