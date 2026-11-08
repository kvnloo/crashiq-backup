"""Washington statewide crash source: WSDOT Crash Data & Reporting Branch. Two readers; the portal one is the WA state pack's (packs.py, #19).

1. `export_record`: one row of WSDOT's crash export (the "history report" layout a user gets from a crash data
   request, Form 780-032 or the Public Disclosure Request Center). The same layout is republished live by City of
   Tacoma open data ("Vision Zero Crashes (Tacoma)") and by SRTC (Spokane County), which is where this reader's column
   names and the recorded fixture come from. Column names are matched squeezed (case, spaces and underscores
   ignored), plus the 31-character truncations ArcGIS layers use.
   Location: city streets give PRIMARY TRAFFICWAY + INTERSECTING TRAFFICWAY, or PRIMARY TRAFFICWAY + DIST FROM REF
   POINT / MI or FT / COMP DIR FROM REF POINT / REFERENCE POINT NAME (the CCRS secondary + offset shape), plus BLOCK
   NUMBER. State routes give a route code (005FD12892) + MILEPOST/ARM only: those need WSDOT's LRS, not the locator.
2. `portal_record` / `fetch_portal`: the record-level JSON behind WSDOT's public Crash Data Portal
   (Api/CrashDataPortalService/GetPublicPortalData, undocumented, no login): report number, jurisdiction, county,
   city, date, time, most severe injury (KABCO), persons, lat/lon. No street names, no crash type.

Every WSDOT release carries the 23 USC 148 / 23 USC 407 notice: the data can't be used in discovery or as evidence in
a damages action. No licence for reuse is published (research_notes/wa-2026-11-07/wa-import.md).
"""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from .ca_ccrs import parse_dt

PORTAL = ("https://remoteapps.wsdot.wa.gov/highwaysafety/collision/data/portal/public/Api/CrashDataPortalService/"
          "GetPublicPortalData")
UA = {"User-Agent": "CrashIQ/0.1"}
PACIFIC = ZoneInfo("America/Los_Angeles")
NOTICE_407 = ("Under 23 U.S. Code 148 and 23 U.S. Code 407, safety data ... are not subject to discovery or admitted "
              "into evidence in a Federal or State court proceeding or considered for other purposes in any action "
              "for damages arising from any occurrence at a location mentioned or addressed in such reports.")

# MOST SEVERE INJURY TYPE -> KABCO. "Unknown" (5.8% of Tacoma 2016-2025) has no level: it maps to U, which in
# CrashIQ means "level not reported"; a user decision whether WSDOT's Unknown should count as injured.
KABCO = {"DEAD AT SCENE": "K", "DEAD ON ARRIVAL": "K", "DIED IN HOSPITAL": "K", "FATAL": "K",
         "SUSPECTED SERIOUS INJURY": "A", "SERIOUS INJURY": "A",
         "SUSPECTED MINOR INJURY": "B", "EVIDENT INJURY": "B",
         "POSSIBLE INJURY": "C", "NO APPARENT INJURY": "O", "NO INJURY": "O", "UNKNOWN": "U"}

COLS = {
    "report_number": ["REPORT NUMBER", "ColliRptNum"],
    "jurisdiction": ["JURISDICTION"],
    "county": ["COUNTY", "CountyName"],
    "city": ["CITY", "CityName"],
    "primary": ["PRIMARY TRAFFICWAY"],
    "block": ["BLOCK NUMBER"],
    "milepost": ["MILEPOST"],
    "ahead_back": ["A/B", "A_B", "A_B_"],
    "intersecting": ["INTERSECTING TRAFFICWAY"],
    "dist": ["DIST FROM REF POINT"],
    "unit": ["MI or FT"],
    "dir": ["COMP DIR FROM REF POINT"],
    "ref_point": ["REFERENCE POINT NAME"],
    "date": ["DATE", "FullDate"],
    "time": ["FULL TIME", "FullTime"],
    "severity": ["MOST SEVERE INJURY TYPE", "MostSevereInjuryType"],
    "fatalities": ["TOTAL FATALITIES"],
    "serious": ["TOTAL SERIOUS INJURIES"],
    "minor": ["TOTAL SUSPECTED MINOR INJURIES", "TOTAL MINOR INJURIES", "TOTAL EVIDENT INJURIES"],
    "possible": ["TOTAL POSSIBLE INJURIES"],
    "vehicles": ["TOTAL VEHICLES"],
    "pedestrians": ["TOTAL PEDESTRIANS INVOLVED"],
    "cyclists": ["TOTAL BICYCLISTS INVOLVED"],
    "collision_type": ["FIRST COLLISION TYPE / OBJECT STRUCK", "first_collision_type___object_s"],
    "junction": ["JUNCTION RELATIONSHIP"],
    "weather": ["WEATHER"],
    "surface": ["ROAD SURFACE CONDITIONS"],
    "lighting": ["LIGHTING CONDITIONS"],
    "lat": ["Latitude", "LAT"],
    "lon": ["Longitude", "LON"],
}
_UNIT_FT = {"F": 1.0, "M": 5280.0}
WA_LAT, WA_LON = (45.5, 49.1), (-124.9, -116.8)


def _sq(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def resolve(columns) -> dict[str, str]:
    """Logical field -> the row's real column name (squeezed match, then a 31-char ArcGIS truncation)."""
    by = {_sq(c): c for c in columns}
    out = {}
    for logical, cands in COLS.items():
        for c in cands:
            hit = by.get(_sq(c)) or next((v for k, v in by.items() if len(k) >= 20 and _sq(c).startswith(k)), None)
            if hit:
                out[logical] = hit
                break
    return out


def _s(v) -> str | None:
    return (str(v).strip() or None) if v is not None else None


def _f(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _when(date_v, time_v) -> tuple[str | None, int | None, int | None]:
    """(ISO date, year, hour). ArcGIS layers hold epoch ms (the date as the UTC instant of local midnight);
    the export and the portal hold text ('2025-01-04T00:00:00', '4:30 PM', '1630')."""
    if isinstance(date_v, (int, float)):
        d = dt.datetime.fromtimestamp(date_v / 1000, PACIFIC)
        date, year, hour = d.date().isoformat(), d.year, None
    else:
        date, year, hour = parse_dt(date_v)
    if isinstance(time_v, (int, float)):        # the clock time is stored as if UTC (07:44Z = 7:44 AM, "Dawn")
        hour = dt.datetime.fromtimestamp(time_v / 1000, dt.timezone.utc).hour
    elif time_v:
        t = str(time_v).strip().upper()
        try:
            hour = (dt.datetime.strptime(t, "%I:%M %p").hour if t[-1] == "M"
                    else int(t.zfill(4)[:2]) if t.isdigit() else hour)
        except ValueError:
            pass
    return date, year, hour


def _latlon(lat, lon) -> tuple[float | None, float | None]:
    lat, lon = _f(lat), _f(lon)
    ok = lat is not None and lon is not None and WA_LAT[0] <= lat <= WA_LAT[1] and WA_LON[0] <= lon <= WA_LON[1]
    return (lat, lon) if ok else (None, None)


def export_record(row: dict, cols: dict[str, str] | None = None, geometry: dict | None = None) -> dict:
    """One WSDOT export row -> the shared crash shape. `geometry` = ArcGIS {x, y} in WGS84 when the row came from a
    republished layer; a raw WSDOT export has no lat/lon (state plane X/Y only in some layouts)."""
    cols = cols or resolve(row)
    g = lambda k: row.get(cols[k]) if k in cols else None
    date, year, hour = _when(g("date"), g("time"))
    sev_text = (_s(g("severity")) or "").upper()
    inter, ref = _s(g("intersecting")), _s(g("ref_point"))
    dist, unit = _f(g("dist")), (_s(g("unit")) or "F").upper()[:1]
    lat, lon = _latlon((geometry or {}).get("y", g("lat")), (geometry or {}).get("x", g("lon")))
    jur = _s(g("jurisdiction"))
    k = lambda key: int(_f(g(key)) or 0)
    return {
        "collision_id": _s(g("report_number")),
        "report_number": _s(g("report_number")),
        "date": date, "year": year, "hour": hour,
        "datetime": date,
        "lat": lat, "lon": lon,
        "jurisdiction": jur,                           # State Route | County Road | City Street | Miscellaneous Trafficway
        "primary_road": _s(g("primary")),
        "secondary_road": inter or ref,
        "sec_distance": dist * _UNIT_FT.get(unit, 1.0) if (dist is not None and not inter) else None,  # feet
        "sec_direction": _s(g("dir")) if not inter else None,
        "block_number": int(_f(g("block")) or 0) or None,
        "milepost": _f(g("milepost")), "ahead_back": _s(g("ahead_back")),
        "city_name": (_s(g("city")) or "").upper() or None,
        "county_code": _s(g("county")),
        "killed": k("fatalities"),
        "injured": k("serious") + k("minor") + k("possible"),
        "kabco_counts": {"K": k("fatalities"), "A": k("serious"), "B": k("minor"), "C": k("possible")},
        "collision_type": _s(g("collision_type")),
        "junction": _s(g("junction")),
        "lighting": _s(g("lighting")), "weather": _s(g("weather")), "surface": _s(g("surface")),
        "is_freeway": jur == "State Route",            # shortcut: every state route, until WSDOT's LRS access-control layer is joined
        "pedestrians": k("pedestrians"), "cyclists": k("cyclists"), "vehicles": k("vehicles"),
        "severity": KABCO.get(sev_text),
        "severity_text": sev_text or None,
    }


def portal_record(row: dict) -> dict:
    """One GetPublicPortalData row -> the shared crash shape (no street names: GPS is the only location)."""
    date, year, hour = _when(row.get("FullDate"), row.get("FullTime"))
    lat, lon = _latlon(row.get("Latitude"), row.get("Longitude"))
    sev_text = (_s(row.get("MostSevereInjuryType")) or "").upper()
    return {"collision_id": _s(row.get("ColliRptNum")), "report_number": _s(row.get("ColliRptNum")),
            "date": date, "year": year, "hour": hour, "datetime": date, "lat": lat, "lon": lon,
            "jurisdiction": _s(row.get("Jurisdiction")), "primary_road": None, "secondary_road": None,
            "city_name": (_s(row.get("CityName")) or "").upper() or None, "county_code": _s(row.get("CountyName")),
            "persons": int(row.get("InvolvedPersons") or 0),
            "is_freeway": row.get("Jurisdiction") == "State Route",
            "severity": KABCO.get(sev_text), "severity_text": sev_text or None}


def fetch_portal(year: int, location_type: str, location_name: str, cache_dir: Path) -> list[dict]:
    """All crashes of one year for a County or City, as the public portal returns them (cached raw)."""
    if location_type not in ("County", "City"):
        raise ValueError("location_type must be County or City")
    cache = cache_dir / f"wsdot_portal_{location_type}_{location_name}_{year}.json".replace(" ", "_")
    if not cache.exists():
        q = urllib.parse.urlencode({"rptCategory": "Summary Reports", "rptName": "Total Crashes",
                                    "locationType": location_type, "locationName": location_name, "jurisdiction": "",
                                    "reportStartDate": f"{year}0101", "reportEndDate": f"{year}1231"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(PORTAL + "?" + q, headers=UA), timeout=300) as r:
                    body = json.load(r)
                break
            except (urllib.error.URLError, TimeoutError):
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt * 5)
        rows = json.loads(body) if isinstance(body, str) else body   # the service returns JSON inside a string
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows))
    return [portal_record(r) for r in json.loads(cache.read_text())]


# -- state-pack contract (#19): the statewide portal, with Seattle's SDOT feed as enrichment inside Seattle ----------
SDOT_TYPE = {"REAR ENDED": "REAR END", "ANGLES": "BROADSIDE", "SIDESWIPE": "SIDE SWIPE", "HEAD ON": "HEAD-ON",
             "PEDESTRIAN": "VEHICLE/PEDESTRIAN"}


def contract_record(r: dict, county_fips: str, sdot: dict | None = None) -> dict:
    """One portal_record() -> the shared crash dict. `sdot`: the same report in Seattle's feed (wa_sdot.crash_record),
    which adds what the portal lacks: street names (block crashes too), crash type, light, weather, surface, road users."""
    d = dt.date.fromisoformat(r["date"]) if r["date"] else None
    e = sdot or {}
    up = lambda v: str(v).upper() if v else None
    ctype = up(e.get("collision_type"))
    return {"crash_id": r["collision_id"], "report_version": 0, "deleted": False, "preliminary": False,
            "date": r["date"], "year": r["year"], "hour": r["hour"], "day_of_week": d.strftime("%A") if d else None,
            "lat": r["lat"], "lon": r["lon"], "bad_coords": False,
            "primary_road": e.get("primary_road"), "secondary_road": e.get("secondary_road"),
            "block_end_road": e.get("block_end_road"), "offset_ft": None, "offset_dir": None,
            "city": r["city_name"] or "UNINCORPORATED", "county_code": r["county_code"], "county_fips": county_fips,
            "state": "WA", "is_freeway": r["is_freeway"], "killed": e.get("killed", 0), "injured": e.get("injured", 0),
            "severity": r["severity"],
            "ped": bool(e.get("pedestrians")), "bike": bool(e.get("cyclists")), "ebike": False, "escooter": False,
            "motorcycle": False, "heavy_truck": False, "parties": [],
            "collision_type": SDOT_TYPE.get(ctype or "", ctype), "lighting": up(e.get("lighting")),
            "weather": up(e.get("weather")), "surface": up(e.get("surface")), "report_number": r["report_number"],
            "jurisdiction": r["jurisdiction"], "enriched_by": "SDOT" if sdot else None}


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, boxes: dict) -> dict:
    """Every portal crash with a point in the box (s, w, n, e), county by county and year by year; inside Seattle,
    the SDOT record of the same report number fills in the street names and crash details."""
    from . import wa_sdot
    s, w, n, e = box
    out, missing, enriched, no_sev = [], [], 0, 0
    for y in years:
        got = 0
        sdot = None
        for f in county_fips:
            rows = [r for r in fetch_portal(y, "County", boxes[f]["name"].removesuffix(" County"), cache_dir)
                    if r["lat"] is not None and s <= r["lat"] <= n and w <= r["lon"] <= e]
            got += len(rows)
            if sdot is None and any(r["city_name"] == "SEATTLE" for r in rows):
                sdot = {c["report_number"]: c for c in wa_sdot.fetch(y, cache_dir)}
            for r in rows:
                m = (sdot or {}).get(r["report_number"]) if r["city_name"] == "SEATTLE" else None
                enriched += m is not None
                no_sev += r["severity"] is None
                out.append(contract_record(r, f, m))
        if not got:
            missing.append(y)
    return {"crashes": out, "years_missing": missing,
            "cleaning": {"enriched_by_sdot": enriched, "no_severity": no_sev}}
