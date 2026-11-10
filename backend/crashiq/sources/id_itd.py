"""Idaho crash source: ITD's open CrashLayers MapServer (Office of Highway Safety's statewide crash database), no login.

One row per crash in layer 11 ("Crash 2005 to Present"; 2008 on all but ~15 rows have GPS, 2005-2007 mostly have none),
crash-level KABCO in words (Severity, e.g. "B Injury Accident"), counts of people killed and injured, ITD's route id
("02290AIN084": system IN = Interstate, US, SH = state highway, OH = off the state system) and an intersection flag.
There is no street text, so each crash is placed by its GPS alone. Layer 35 ("Crash Unit 2005 to Present") shares
Serial_Number and gives each unit's vehicle type and most harmful event: the reader takes the pedestrian, bicycle,
motorcycle and truck flags and the collision type from it. Layer 23 (persons) repeats the crash severity, so there is
no per-person KABCO.

The service lags: on 2026-11-08 it held 2005-2022 in full and 2023 only to 2023-10-01 (18,488 of the 27,679 crashes
ITD's 2024 annual report counts for 2023), and no 2024-2025. The reader asks the layer for its newest crash date and
treats every later, part-loaded year as missing (rows dropped, year in `years_missing`), so a study never counts a part
year as a whole one.

Licence: ITD's spatial data disclaimer only ("as is", "sole responsibility of the user to determine the usability");
no reuse grant (research_notes/id-2026-11-08/id-import.md). Wired into the app through statepacks/id.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from datetime import timezone
from pathlib import Path

from crashiq.packs import REF

from . import from_epoch

SERVICE = "https://gis.itd.idaho.gov/arcgisprod/rest/services/ArcGISOnline/CrashLayers/MapServer"
CRASH, UNIT = 11, 35
PAGE = 5000                                       # under the layers' maxRecordCount (70,000), small responses
ID_LAT, ID_LON = (41.9, 49.1), (-117.3, -111.0)  # Idaho's extent with a small margin

SEVERITY = {"Fatal Accident": "K", "A Injury Accident": "A", "B Injury Accident": "B", "C Injury Accident": "C",
            "Property Dmg Report": "O"}
_boxes = json.loads((REF / "county_boxes_id.json").read_text())
FIPS = {v["name"].removesuffix(" County"): k for k, v in _boxes["counties"].items()}

# ITD's most harmful event of unit 1 -> the CCRS words the profile and the collision diagram read; others keep ITD's
CCRS_TYPE = {"Angle": "BROADSIDE", "Angle Turning": "BROADSIDE", "Head-On": "HEAD-ON", "Head-On Turning": "HEAD-ON",
             "Rear-End": "REAR END", "Rear-End Turning": "REAR END", "Side Swipe Same": "SIDE SWIPE",
             "Side Swipe Opposite": "SIDE SWIPE", "Overturn": "OVERTURNED", "Pedestrian": "VEHICLE/PEDESTRIAN"}
TRUCK = {"Bobtail/Tractor - No Trailer", "Tractor - 1 Trailer", "Tractor - 2 Trailers", "Tractor - 3 Trailers",
         "Truck - 2 Axle/6 Tires", "Truck - 3+ Axle"}


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and ID_LAT[0] <= lat <= ID_LAT[1] and ID_LON[0] <= lon <= ID_LON[1])


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def contract_record(a: dict, units=()) -> dict:
    """One crash-layer attributes dict (+ its unit rows) -> the shared crash dict (packs.check_crash)."""
    s = lambda v: (str(v).strip() or None) if v is not None else None                  # noqa: E731
    lat, lon = _num(a.get("Latitude")), _num(a.get("Longitude"))
    has = plausible(lat, lon)
    # Accident_Date_Time is Idaho's wall-clock time sent as if it were UTC (Accident_Time matches it in UTC)
    when = (from_epoch(a["Accident_Date_Time"] / 1000, timezone.utc)
            if a.get("Accident_Date_Time") is not None else None)
    sev = SEVERITY.get(s(a.get("Severity")))
    vt = {s(u.get("Vehicle_Type")) for u in units}
    first = min(units, key=lambda u: u.get("Unit_Number") or 99, default={})
    mhe = s(first.get("Most_Harmful_Event"))
    route = s(a.get("RouteID")) or ""
    return {"crash_id": str(a["Serial_Number"]), "report_version": 0, "deleted": False, "preliminary": False,
            "date": when.date().isoformat() if when else "", "year": when.year if when else None,
            "hour": when.hour if when else None, "day_of_week": when.strftime("%A") if when else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,  # no street text
            "city": None, "county_code": s(a.get("County")), "county_fips": FIPS.get(s(a.get("County")) or ""),
            "state": "ID", "is_freeway": route[6:8] == "IN",
            "killed": max(int(a.get("Number_Of_Fatalities") or 0), int(sev == "K")),
            "injured": max(int(a.get("Number_Of_Injuries") or 0), int(sev in ("A", "B", "C"))),
            "severity": sev, "ped": "Pedestrian" in vt, "bike": "Pedalcycle" in vt, "ebike": False, "escooter": False,
            "motorcycle": "Motorcycle" in vt, "heavy_truck": bool(vt & TRUCK), "parties": [],
            "collision_type": CCRS_TYPE.get(mhe, mhe.upper() if mhe else None),
            "lighting": None, "weather": None, "surface": None,
            "report_number": None, "route_id": route or None, "measure": a.get("Measure"),
            "intersection_related": s(a.get("IntersectionRelated")) == "Y",
            "contributing": s(first.get("Contrib_Circ_1"))}


def _get(layer: int, params: dict, opener) -> dict:
    req = urllib.request.Request(f"{SERVICE}/{layer}/query?" + urllib.parse.urlencode({**params, "f": "json"}),
                                 headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=180) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"ITD crash layer {layer} query error: {body['error']}")
    return body


def _rows(layer: int, where: str, geo: dict, fields: str, opener) -> list[dict]:
    raw, last = [], 0
    while True:
        b = _get(layer, {"where": f"({where}) AND OBJECTID>{last}", **geo, "outFields": fields,
                         "orderByFields": "OBJECTID", "resultRecordCount": PAGE, "returnGeometry": "false"}, opener)
        batch = [f["attributes"] for f in b.get("features", [])]
        raw += batch
        if len(batch) < PAGE and not b.get("exceededTransferLimit"):
            return raw
        last = batch[-1]["OBJECTID"]


def last_full_year(opener) -> int:
    """The newest year the layer holds in full: the newest crash's year if it falls in late December, else the year
    before (2023 stopped at 2023-10-01 when checked)."""
    b = _get(CRASH, {"where": "1=1", "outStatistics": json.dumps([{"statisticType": "max",
             "onStatisticField": "Accident_Date_Time", "outStatisticFieldName": "hi"}])}, opener)
    hi = from_epoch(b["features"][0]["attributes"]["hi"] / 1000, timezone.utc)
    return hi.year if (hi.month, hi.day) >= (12, 25) else hi.year - 1


def fetch_raw(box, years: list[int], cache_dir: Path | None = None, opener=urllib.request.urlopen) -> dict:
    """Crash rows with a point in the box (s, w, n, e) in those years, their unit rows, and the last full year;
    cached as raw JSON per query when cache_dir is given."""
    s, w, n, e = box
    geo = {"geometry": f"{w},{s},{e},{n}", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
           "spatialRel": "esriSpatialRelIntersects"}
    where = "Accident_Year IN (" + ", ".join(f"'{y}'" for y in years) + ")"
    key = hashlib.sha1(json.dumps([geo, where]).encode()).hexdigest()[:10]
    cache = cache_dir / f"id_itd_{key}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    raw = {"last_full_year": last_full_year(opener),
           "crashes": _rows(CRASH, where, geo, "*", opener),
           "units": _rows(UNIT, where, geo, "OBJECTID,Serial_Number,Unit_Number,Vehicle_Type,Most_Harmful_Event,"
                                           "Contrib_Circ_1", opener)}
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return raw


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box in those years; years after the layer's last full year are missing.
    Crashes with no point aren't read (about 15 from 2008 on; most of 2005-2007)."""
    raw = fetch_raw(box, years, cache_dir, opener)
    units: dict[str, list] = {}
    for u in raw["units"]:
        units.setdefault(u["Serial_Number"], []).append(u)
    full = raw["last_full_year"]
    rows = [contract_record(a, units.get(a["Serial_Number"], [])) for a in raw["crashes"]]
    have = {r["year"] for r in rows if r["year"] is not None and r["year"] <= full}
    out = [r for r in rows if r["county_fips"] and r["severity"] and r["year"] is not None and r["year"] <= full]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "no_county": sum(not r["county_fips"] for r in rows),
                         "no_severity": sum(not r["severity"] for r in rows),
                         "part_year_dropped": sum(r["year"] is not None and r["year"] > full for r in rows),
                         "last_full_year": full,
                         "no_gps_not_read": "crashes with no point aren't read (~15 statewide from 2008 on)"}}
