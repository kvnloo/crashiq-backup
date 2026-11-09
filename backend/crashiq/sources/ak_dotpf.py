"""Alaska: DOT&PF Public Crash Portal (public.alaskadata.net), statewide, the most recent five complete years (2021-2025
on 2026-11-08). Open, no login: the portal's map reads the crash points from the same API this reader calls.

The portal runs CARE (University of Alabama CAPS) on DMV crash reports. Its API (`API` below; datasource
"DOTPFDataCrash", 42,988 crashes, built 2026-11-04) gives per crash: crash number, date and time, a WGS84 point (all
but 446 crashes, which carry 0/0), crash KABCO, city, borough, manner of collision, light, weather, surface,
functional class, junction, and counts of pedestrians, pedalcycles, motorcycles and commercial vehicles. It has no
street names, no person records and no counts of people killed or injured (only fatal / injury flags). The portal
hides its download button, so this reads the map's own CSV feed: two calls per year (a date filter, then the CSV).
Wired into the app by the AK plug-in (crashiq/statepacks/ak.py) through `fetch_contract`.
"""

from __future__ import annotations

import csv
import io
import json
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

from ..settings import ROOT

API = "https://pub-ds.alaskadata.net/api/"
DATASET = "DOTPFDataCrash"
AK_LAT, AK_LON = (51.0, 71.6), (-180.0, -129.9)     # western hemisphere only (the Near Islands lie east of 180)
CATEGORICAL = ("Crash Severity", "City", "County-Borough", "Manner of Collision", "Lighting", "Weather", "Road Surface",
               "Functional Class", "Junction", "First Harmful Event", "Number of Pedestrians Involved",
               "Number of Pedalcycles Involved", "Number of Motorcycles Involved",
               "Number of Commercial Vehicles Involved")
NONCATEGORICAL = ("DateTime", "Latitude", "Longitude")
KABCO = {"Fatal Injury (Killed)": "K", "Suspected Serious Injury": "A", "Suspected Minor Injury": "B",
         "Possible Injury": "C", "No Apparent Injury": "O",
         "Died Prior to Crash": "O"}            # a death before the crash is not a crash injury (8 crashes 2021-2025)
FREEWAY_FC = {"Interstate", "Principal Arterial - Freeway/Expressway"}
CCRS_TYPE = {"Angle": "BROADSIDE", "Front-To-Rear": "REAR END", "Front-To-Front": "HEAD-ON",
             "Sideswipe - Same Direction": "SIDE SWIPE", "Sideswipe - Opposite Direction": "SIDE SWIPE",
             "Rear-To-Side": "BROADSIDE", "Rear-To-Rear": "REAR END"}
CCRS_FIRST = {"Overturn/Rollover": "OVERTURNED", "Pedestrian": "VEHICLE/PEDESTRIAN",   # for non-collision crashes
              "Motor Vehicle In-Transport": "OTHER"}                           # a collision whose manner is blank
CCRS_LIGHT = {"Dark - Lighted": "DARK - STREET LIGHTS", "Dark - Not Lighted": "DARK - NO STREET LIGHTS",
              "Dark - Unknown Lighting": "DARK - UNKNOWN STREET LIGHTS"}
NO_VALUE = {"", "Null value", "Unknown", "Other", "Not Applicable"}
BOXES = json.loads((ROOT / "data" / "reference" / "county_boxes_ak.json").read_text())["counties"]
FIPS = {v["name"]: k for k, v in BOXES.items()}       # the portal writes the Census names ('Kenai Peninsula Borough')


def _s(v) -> str | None:
    v = (v or "").strip()
    return None if v in NO_VALUE else v


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def county_fips(borough: str | None, lat: float | None, lon: float | None) -> str | None:
    """The borough's FIPS; for the portal's 'Unorganized Borough', 'Valdez-Cordova' (split in 2019) and blanks, the
    smallest county box that holds the point.
    shortcut: boxes overlap, so a point near a census-area line can get its neighbour; use polygons if that matters."""
    if borough in FIPS:
        return FIPS[borough]
    if lat is None:
        return None
    area = lambda b: (b[2] - b[0]) * (b[3] - b[1])
    hits = [(area(v["box"]), k) for k, v in BOXES.items()
            if v["box"][0] <= lat <= v["box"][2] and v["box"][1] <= lon <= v["box"][3]]
    return min(hits)[1] if hits else None


def contract_record(r: dict) -> dict:
    """One CSV row of the portal's feed -> the shared crash dict (packs.check_crash)."""
    t = datetime.strptime(r["DateTime"].strip(), "%m/%d/%Y %H:%M:%S") if (r.get("DateTime") or "").strip() else None
    lat, lon = _num(r.get("Latitude")), _num(r.get("Longitude"))
    has = lat is not None and lon is not None and AK_LAT[0] <= lat <= AK_LAT[1] and AK_LON[0] <= lon <= AK_LON[1]
    n = lambda k: int(_num((r.get(k) or "").replace("More than 5", "6")) or 0)
    manner, first = _s(r.get("Manner of Collision")), _s(r.get("First Harmful Event"))
    up = lambda v: v.upper() if v else None
    kind = CCRS_TYPE.get(manner or "") or CCRS_FIRST.get(first or "") or \
        up(first if not manner or manner.startswith("Not a Collision") else manner)
    city = _s(r.get("City"))
    return {"crash_id": r["Crash Number"].strip(), "report_version": 0, "deleted": False, "preliminary": False,
            "date": t.date().isoformat() if t else "", "year": t.year if t else None, "hour": t.hour if t else None,
            "day_of_week": t.strftime("%A") if t else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,
            "city": None if city in (None, "Outside Any City Boundary") else up(city.removesuffix(" Municipality")),
            "county_code": _s(r.get("County-Borough")),
            "county_fips": county_fips(_s(r.get("County-Borough")), lat if has else None, lon if has else None),
            "state": "AK", "is_freeway": r.get("Functional Class") in FREEWAY_FC,
            "killed": 0, "injured": 0,                     # the portal gives fatal/injury flags, not people counted
            "severity": KABCO.get((r.get("Crash Severity") or "").strip(), "O"),
            "severity_reported": (r.get("Crash Severity") or "").strip() or None,
            "ped": n("Number of Pedestrians Involved") > 0, "bike": n("Number of Pedalcycles Involved") > 0,
            "ebike": False, "escooter": False, "motorcycle": n("Number of Motorcycles Involved") > 0,
            "heavy_truck": n("Number of Commercial Vehicles Involved") > 0, "parties": [], "collision_type": kind,
            "lighting": CCRS_LIGHT.get(r.get("Lighting") or "", up(_s(r.get("Lighting")))),
            "weather": up(_s(r.get("Weather"))), "surface": up(_s(r.get("Road Surface")))}


def _call(opener, url: str, body: dict | None = None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"User-Agent": "CrashIQ/0.1", "Content-Type": "application/json"})
    with opener(req, timeout=300) as r:
        return r.read()


def year(y: int, cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """One year's crashes, statewide (~9,000 rows, ~2.5 MB of CSV): from the cache, else read from the portal.
    shortcut: a cached year is never re-read, though DMV still amends records ('slight modifications should be
    expected'); delete the cache file to refresh."""
    slim = cache_dir / f"ak_dotpf_{y}.json"
    if slim.exists():
        return json.loads(slim.read_text())
    builder = {"DatasourceName": DATASET, "DateRanges": [{"StartDate": f"{y}-01-01T00:00:00",
                                                          "EndDate": f"{y}-12-31T23:59:59"}],
               "RouteMilepostRanges": [], "JoinedVariableValues": {"VariableValueList": []}, "FilterNames": [],
               "KeyItems": []}
    filt = json.loads(_call(opener, f"{API}FilterCache/PostReplacementFilterToCache?datasourcename={DATASET}", builder))
    q = [("fileFormat", "1"), ("datasourcename", DATASET), ("filterid", filt["Id"])]
    q += [("CategoricalVariableName", v) for v in CATEGORICAL] + [("NonCategoricalVariableName", v) for v in NONCATEGORICAL]
    text = _call(opener, f"{API}VariableData/GetFileDownload?{urllib.parse.urlencode(q)}").decode("utf-8-sig")
    crashes = [contract_record(r) for r in csv.DictReader(io.StringIO(text))]
    got = {"year": y, "crashes": [c for c in crashes if c["year"] == y], "selected": filt.get("SelectedCount"),
           "read": date.today().isoformat()}
    if got["crashes"]:                     # an empty year (not in the portal's five) is never cached
        cache_dir.mkdir(parents=True, exist_ok=True)
        slim.write_text(json.dumps(got))
    return got


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Crashes with a point in the box (s, w, n, e), plus the corridor boroughs' crashes with no point (0/0 in the
    portal: no street names, so they stay unplaced), in those years; a year the portal doesn't hold is missing."""
    s, w, n, e = box
    out, missing, no_point = [], [], 0
    for y in years:
        got = year(y, cache_dir, opener)
        if not got["crashes"]:
            missing.append(y)
        for c in got["crashes"]:
            if c["lat"] is None:
                if c["county_fips"] in county_fips:
                    out.append(c)
                    no_point += 1
            elif s <= c["lat"] <= n and w <= c["lon"] <= e and c["county_fips"]:
                out.append(c)
    return {"crashes": out, "years_missing": missing,
            "cleaning": {"source_rows": len(out), "no_point_in_boroughs": no_point, "portal": "public.alaskadata.net"}}
