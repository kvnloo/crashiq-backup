"""Kentucky crash source: Kentucky State Police's public Collision Analysis site (crashinformationky.org, KyOPS
collision reports), no login.

Two calls of the site's own map search, the ones its Location Search page makes:
  - POST /LocationSearch/ExecuteQuery: every collision inside a polygon in a date range, one row per crash, with the
    officer's road fields (KYTC road number, roadway name, intersecting and between streets), county, people killed and
    injured, manner of collision, light, weather and road surface. Its Latitude/Longitude are rounded to whole degrees.
  - POST /AdvancedSearch/GetMappingDataByReportType: the full GPS point of each crash, by the row's xIncidentGUID.
A range the site finds "too large" is split in halves until it answers.

Severity: the public rows carry the number killed and injured, never the injury level (KABCO lives only in KSP's and
KYTC's internal CRASH database). So a crash is K (someone killed), U (injured, level not reported) or O (no one hurt);
A, B and C are never invented (PACK.severity_note).

Licence: none published; the site says "no warranty, either expressed or implied, is given to the accuracy,
completeness, reliability, or suitability for any particular purpose" (research_notes/ky-2026-11-08/ky-import.md).
Wired into the app through the KY state pack (statepacks/ky.py) by `fetch_contract`.
"""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

BASE = "http://crashinformationky.org"
GPS_BATCH = 2000                                  # GUIDs per mapping call (2,000 answered in 3 s, 2026-11-08)
KY_LAT, KY_LON = (36.4, 39.2), (-89.6, -81.9)     # Kentucky's extent with a small margin
TOO_LARGE = "too large"
REF = Path(__file__).resolve().parents[3] / "data" / "reference"

# KSP's words -> the CCRS words the profile and the collision diagram read; any other value keeps KSP's words
CCRS_TYPE = {"ANGLE": "BROADSIDE", "HEAD ON": "HEAD-ON", "REAR END": "REAR END",
             "SIDESWIPE-SAME DIRECTION": "SIDE SWIPE", "SIDESWIPE-OPPOSITE DIRECTION": "SIDE SWIPE"}
CCRS_LIGHT = {"DARK-HWY LIGHTED/ON": "DARK - STREET LIGHTS", "DARK-HWY NOT LIGHTED": "DARK - NO STREET LIGHTS",
              "DARK-HWY LIGHTED/OFF": "DARK - STREET LIGHTS NOT FUNCTIONING",
              "DARK (UNKNOWN ROADWAY LIGHTING)": "DARK - UNKNOWN STREET LIGHTS"}
# KYTC road numbers: "I 0065" interstates, "WK9001"-style 9000-series state parkways (all limited access)
FREEWAY = re.compile(r"^(?:I |[A-Z]{2}9\d{3}$)")


def _county_fips() -> dict[str, str]:
    boxes = json.loads((REF / "county_boxes_ky.json").read_text())["counties"]
    return {v["name"].upper().removesuffix(" COUNTY"): k for k, v in boxes.items()}


FIPS = _county_fips()


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and KY_LAT[0] <= lat <= KY_LAT[1] and KY_LON[0] <= lon <= KY_LON[1])


def severity(row: dict) -> str:
    """K if anyone was killed, U if anyone was injured (level not reported), else O."""
    return "K" if (row.get("Number Killed") or 0) > 0 else "U" if (row.get("Number Injured") or 0) > 0 else "O"


def contract_record(row: dict, point: dict | None) -> dict:
    """One Location Search row plus its mapping point (or None) -> the shared crash dict (packs.check_crash)."""
    s = lambda v: (str(v).strip() or None) if v is not None else None                  # noqa: E731
    lat = point.get("xLatitude") if point else None
    lon = -abs(point["xLongitude"]) if point and point.get("xLongitude") is not None else None  # the site's own sign fix
    has = plausible(lat, lon)
    day = datetime.fromisoformat(row["Date"]).date() if row.get("Date") else None
    t = s(row.get("Time")) or ""
    hour = int(t[:2]) if len(t) == 4 and t.isdigit() and int(t[:2]) < 24 else None
    dirn = s(row.get("Dir Analysis Code")) or ""
    road_no = s(row.get("Rdwy Number")) or ""
    return {"crash_id": str(row["xIncidentID"]), "report_version": 0, "deleted": False,
            "preliminary": bool(day and day.year >= date.today().year),
            "date": day.isoformat() if day else "", "year": day.year if day else None, "hour": hour,
            "day_of_week": day.strftime("%A") if day else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": s(row.get("Roadway Name")),
            "secondary_road": s(row.get("Intersection Rdwy Name")) or s(row.get("Between St Rdwy Name 1")),
            "offset_ft": None, "offset_dir": None,
            "city": None, "county_code": s(row.get("County")), "county_fips": FIPS.get(s(row.get("County")) or ""),
            "state": "KY", "is_freeway": bool(FREEWAY.match(road_no)),
            "killed": int(row.get("Number Killed") or 0), "injured": int(row.get("Number Injured") or 0),
            "severity": severity(row), "ped": "PEDESTRIAN" in dirn, "bike": "BICYCL" in dirn, "ebike": False,
            "escooter": False, "motorcycle": False, "heavy_truck": False, "parties": [],
            "collision_type": CCRS_TYPE.get(s(row.get("Manner of Collision")), s(row.get("Manner of Collision"))),
            "lighting": CCRS_LIGHT.get(s(row.get("Light Condition")), s(row.get("Light Condition"))),
            "weather": s(row.get("Weather")), "surface": s(row.get("Rdwy Condition")),
            "hit_and_run": bool(row.get("Hit and Run")), "road_number": road_no or None,
            "milepoint": row.get("Milepoint"), "location_text": s(row.get("Location Description")),
            "agency": s(row.get("Agency Name")), "direction_analysis": dirn or None}


# -- the site ----------------------------------------------------------------------------------------------------
def session():
    """A post(path, fields) callable holding the site's cookie and anti-forgery token."""
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.addheaders = [("User-Agent", "CrashIQ/0.1"), ("X-Requested-With", "XMLHttpRequest")]
    page = op.open(BASE + "/LocationSearch", timeout=120).read().decode()
    tok = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', page).group(1)

    def post(path: str, fields: list) -> dict:
        body = urllib.parse.urlencode(fields + [("__RequestVerificationToken", tok)]).encode()
        with op.open(BASE + path, data=body, timeout=900) as r:
            text = r.read().decode()
        out = json.loads(text)
        return json.loads(out) if isinstance(out, str) else out          # the site double-encodes its JSON
    return post


def polygon(box) -> str:
    s, w, n, e = box
    return "|".join(f"({a:.6f}, {b:.6f})" for a, b in ((s, w), (s, e), (n, e), (n, w))) + "|"


def search(post, box, start: date, end: date) -> list[dict]:
    """Every collision in the box between two dates (inclusive), splitting a range the site calls too large."""
    got = post("/LocationSearch/ExecuteQuery", [
        ("ListCounties", "056"),     # required by the form; the polygon is what filters (measured 2026-11-08)
        ("DateRangeStart", start.strftime("%m/%d/%Y")), ("DateRangeEnd", end.strftime("%m/%d/%Y")),
        ("CircleRadius", ""), ("CircleCenterPoint", ""), ("LineString", ""), ("Polygon", polygon(box)),
        ("incidentTypeEnum", "0")])
    err = got.get("errorMessage")
    if err and TOO_LARGE in err and end > start:
        mid = start + (end - start) // 2
        return search(post, box, start, mid) + search(post, box, mid + timedelta(days=1), end)
    if err:
        raise RuntimeError(f"KSP Location Search error: {err}")
    return (got.get("result") or {}).get("results") or []


def points(post, guids: list[str]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(guids), GPS_BATCH):
        got = post("/AdvancedSearch/GetMappingDataByReportType",
                   [("aIncidentGUID[]", g) for g in guids[i:i + GPS_BATCH]]
                   + [("sIncidentType", "03"), ("bShowAllStatuses", "false")])
        out.update({p["xIncidentGUID"]: p for p in got.get("results") or []})
    return out


def fetch_year(box, year: int, cache_dir: Path | None, post=None) -> tuple[list[dict], dict]:
    """(rows, points by GUID) for one year in the box; cached as raw JSON per box and year."""
    key = hashlib.sha1(f"{polygon(box)}|{year}".encode()).hexdigest()[:10]
    cache = cache_dir / f"ky_ksp_{key}.json" if cache_dir else None
    if cache and cache.exists():
        d = json.loads(cache.read_text())
        return d["rows"], d["points"]
    post = post or session()
    end = min(date(year, 12, 31), date.today())
    rows = search(post, box, date(year, 1, 1), end) if end.year == year else []
    pts = points(post, [r["xIncidentGUID"] for r in rows])
    if cache and year < date.today().year:        # the current year still grows; never freeze it
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"rows": rows, "points": pts}))
    return rows, pts


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, post=None) -> dict:
    """Every crash with a GPS point in the box (s, w, n, e) in those years. The site searches by point only, so a
    crash with no GPS isn't read (none of 2,000 sampled statewide lacked one)."""
    recs, raw, no_point = [], 0, 0
    for y in years:
        rows, pts = fetch_year(box, y, cache_dir, post)
        raw += len(rows)
        for r in rows:
            p = pts.get(r["xIncidentGUID"])
            no_point += p is None
            recs.append(contract_record(r, p))
    have = {r["year"] for r in recs}
    out = [r for r in recs if r["county_fips"]]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": raw, "no_county": len(recs) - len(out), "no_mapping_point": no_point,
                         "severity": "K/U/O only: KSP's public rows have no injury level"}}
