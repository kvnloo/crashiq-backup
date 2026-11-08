"""Delaware crash source: "Public Crash Data" (Delaware Department of Safety and Homeland Security, DSHS), on
data.delaware.gov (Socrata 827n-m6xc, mirrored on FirstMap ArcGIS), statewide, 2009 to about six months ago, no login.

One row per crash: GPS on all but one of 591,222 rows (2026-11-08), crash class (fatal / personal injury / property
damage only / non-reportable), manner of impact, light, weather, surface, pedestrian / bicycle / motorcycle flags.
There are NO street names, no route or milepost, no report number and no people or vehicle tables, so:
- severity is K (fatality crash), U (personal injury crash: no A/B/C level is published) or O;
- `crash_id` is the portal's row id (`:id`), the only key it has;
- killed and injured aren't published: 0, and the pack says people aren't counted.
Non-reportable crashes (private property, or under Delaware's $2,000 damage reporting threshold, 21 Del. C. § 4203)
are left out: DelDOT's HSIP screens on "fatal, personal injury, and/or property damage only crashes" (de-import.md §3).

Licence: none published (the portal's licence field is empty); DSHS's description is quoted in the pack's `legal`.
Wired into the app by the DE state pack (statepacks/de.py, #19) through `fetch_contract`.
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

URL = "https://data.delaware.gov/resource/827n-m6xc.json"
PAGE = 50000
DE_LAT, DE_LON = (38.4, 39.9), (-75.8, -75.0)    # Delaware's extent with a small margin
_TZ = ZoneInfo("America/New_York")               # crash_datetime is UTC (FirstMap CRASH_TIME 1155 = 16:55Z in Feb)
COUNTY = {"K": "10001", "N": "10003", "S": "10005"}
SEVERITY = {"04": "K", "03": "U", "02": "O"}      # crash_class; 01 non-reportable is left out
# impact (manner of impact) -> CCRS words; rear-to-side, rear-to-rear, other keep DSHS's words
COLLISION = {"01": "REAR END", "02": "HEAD-ON", "03": "BROADSIDE", "04": "SIDE SWIPE", "05": "SIDE SWIPE"}
LIGHT = {"01": "DAYLIGHT", "02": "DUSK - DAWN", "03": "DUSK - DAWN", "04": "DARK - STREET LIGHTS",
         "05": "DARK - NO STREET LIGHTS", "06": "DARK - UNKNOWN STREET LIGHTS", "88": "OTHER", "99": "NOT STATED"}
SELECT = ("crash_datetime,year,crash_class,day_of_week_desc,ped_involved,bike_involved,mc_involved,impact,impact_desc,"
          "light_cond,weather_1_desc,road_surface_desc,latitude,longitude,county,pri_contrib_circum_desc,"
          "alcohol_involved,drug_involved,work_zone,:id")


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and DE_LAT[0] <= lat <= DE_LAT[1] and DE_LON[0] <= lon <= DE_LON[1])


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _words(v) -> str | None:
    return v.upper() if v and v not in ("NA", "Unknown") else None


def crash_record(r: dict) -> dict | None:
    """One portal row -> the shared crash shape (packs.check_crash); None for a non-reportable or unclassed crash."""
    sev = SEVERITY.get(r.get("crash_class"))
    if sev is None:
        return None
    lat, lon = _num(r.get("latitude")), _num(r.get("longitude"))
    has = plausible(lat, lon)
    when = r.get("crash_datetime")
    t = datetime.fromisoformat(when.replace("Z", "+00:00")).astimezone(_TZ) if when else None
    ped = r.get("ped_involved") == "Y"
    imp = r.get("impact")
    return {
        "crash_id": r[":id"], "report_version": 0, "deleted": False,
        "preliminary": False,                    # DSHS posts a crash about six months after it; later edits unknown
        "date": t.date().isoformat() if t else "", "year": t.year if t else int(r["year"]),
        "hour": t.hour if t else None, "day_of_week": r.get("day_of_week_desc"),
        "lat": lat if has else None, "lon": lon if has else None,
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,   # no street names
        "city": None, "county_code": r.get("county"), "county_fips": COUNTY.get(r.get("county")), "state": "DE",
        "is_freeway": False,                     # no road class in the data
        "killed": 0, "injured": 0,               # not published
        "severity": sev, "severity_reported": r.get("crash_class"),
        "ped": ped, "bike": r.get("bike_involved") == "Y", "ebike": False, "escooter": False,
        "motorcycle": r.get("mc_involved") == "Y", "heavy_truck": False, "hit_run": None, "parties": [],
        "collision_type": "VEHICLE/PEDESTRIAN" if ped and imp == "00" else COLLISION.get(imp, _words(r.get("impact_desc"))),
        "lighting": LIGHT.get(r.get("light_cond")), "weather": _words(r.get("weather_1_desc")),
        "surface": _words(r.get("road_surface_desc")),
        "contributing": _words(r.get("pri_contrib_circum_desc")),
        "alcohol": r.get("alcohol_involved") == "Y", "drugs": r.get("drug_involved") == "Y",
        "work_zone": r.get("work_zone") == "Y",
    }


def _get(params: dict, opener) -> list[dict]:
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=300) as r:
        return json.loads(r.read())


def fetch(where: str, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every portal row matching a SoQL `where`, paged by :id. Cached as raw JSON per `where`."""
    cache = cache_dir / f"de_dshs_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    raw = []
    while True:
        batch = _get({"$select": SELECT, "$where": where, "$order": ":id", "$limit": PAGE, "$offset": len(raw)}, opener)
        raw += batch
        if len(batch) < PAGE:
            break
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return raw


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path,
                   opener=urllib.request.urlopen) -> dict:
    """Every reportable crash with a point in the box (s, w, n, e) in those years. The one row of 591k with no point
    isn't read: the data says nothing else about where it is."""
    s, w, n, e = box
    yrs = ", ".join(f"'{y}'" for y in years)
    where = (f"latitude >= {s:.6f} AND latitude <= {n:.6f} AND longitude >= {w:.6f} AND longitude <= {e:.6f} "
             f"AND year IN ({yrs})")
    rows = fetch(where, Path(cache_dir), opener)
    out = [c for c in map(crash_record, rows) if c is not None]
    have = {c["year"] for c in out}
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows),
                         "non_reportable_left_out": sum(r.get("crash_class") == "01" for r in rows),
                         "unclassed_left_out": sum(r.get("crash_class") not in (*SEVERITY, "01") for r in rows)}}
