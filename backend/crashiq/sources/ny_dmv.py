"""New York statewide crash source: NYS DMV crash cases on data.ny.gov (OPEN-NY terms), placed by reference marker.

- Cases: https://data.ny.gov/resource/e8ky-4vqe ("Four Year Window", 2021-2024 as of 2026-11-07). No coordinates, no
  street names, no case number. About 36% of crashes carry `dot_reference_marker_location` (state highways).
- Persons (ir4y-sesj) and vehicles (xe9x-a24f) have no key back to the case, so crash severity comes from
  `accident_descriptor` only: Fatal -> K, injury -> U (level not given), property damage -> O.
- Placement: the reference marker is joined to NYSDOT's public marker layer (Roadway FeatureServer layer 0). Markers
  are posted every 0.1 mi, so a matched crash sits within about 0.05 mi of the marker, along the route, side unknown.
The NY state pack (packs.py, #19) reads it through `fetch_contract`; inside the five boroughs it uses NYC's\nopen data instead (ny_nyc), where this table has no location.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CASES = "https://data.ny.gov/resource/e8ky-4vqe.json"
MARKERS = "https://gisportalny.dot.ny.gov/hostingny/rest/services/Roadways/Roadway/FeatureServer/0/query"
UA = {"User-Agent": "CrashIQ/0.1"}
NYC_COUNTIES = {"NEW YORK", "KINGS", "QUEENS", "BRONX", "RICHMOND"}
SEVERITY = {"FATAL ACCIDENT": "K", "INJURY ACCIDENT": "U", "PROPERTY DAMAGE & INJURY ACCIDENT": "U",
            "PROPERTY DAMAGE ACCIDENT": "O"}
# Individual table injury_severity -> KABCO (MV-104 A/B/C = severe/moderate/minor). Not linkable to a case.
PERSON_KABCO = {"KILLED": "K", "SEVERE": "A", "MODERATE": "B", "MINOR": "C", "INJURED WITH UNKN SEVERITY": "U"}


def _get(url: str, params: dict):
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(full, headers=UA), timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
            time.sleep(5 * 2 ** attempt)


def panel(rm: str | None) -> str | None:
    """Crash marker -> NYSDOT panel: the crash table left-strips the 12-character panel ('9 84041008' = '  9 84041008')."""
    rm = (rm or "").rstrip()
    return rm.rjust(12) if 9 <= len(rm) <= 12 else None


def route(p: str | None) -> str | None:
    """The route part of a panel: '  9 84041008' -> '9', '278IX6M13057' -> '278I', '  9N12031058' -> '9N'."""
    return p[:4].strip() or None if p else None


def fetch_cases(where: str, cache_dir: Path, page: int = 50000) -> list[dict]:
    """Raw case rows matching a SoQL `where`, with the Socrata row id, cached as JSON."""
    cache = cache_dir / f"ny_dmv_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rows, offset = [], 0
    while True:
        batch = _get(CASES, {"$select": "*,:id", "$where": where, "$order": ":id", "$limit": page, "$offset": offset})
        rows += batch
        if len(batch) < page:
            break
        offset += page
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows))
    return rows


def marker_points(panels, chunk: int = 50) -> dict[str, tuple[float, float]]:
    """Panel -> (lat, lon) from NYSDOT's marker layer. A panel retired since (TO_DATE set) is used only when no
    current marker has that panel."""
    out, retired = {}, {}
    todo = sorted({p for p in panels if p})
    for i in range(0, len(todo), chunk):
        names = ",".join("'" + p.replace("'", "''") + "'" for p in todo[i:i + chunk])
        js = _get(MARKERS, {"where": f"Panel IN ({names})", "outFields": "Panel,TO_DATE", "outSR": 4326,
                            "returnGeometry": "true", "f": "json"})
        if "error" in js:
            raise RuntimeError(f"NYSDOT marker layer error: {js['error']}")
        for f in js.get("features", []):
            a, g = f["attributes"], f.get("geometry") or {}
            if g.get("y") is None:
                continue
            (retired if a.get("TO_DATE") else out).setdefault(a["Panel"], (g["y"], g["x"]))
    return {**retired, **out}


def crash_record(raw: dict, markers: dict[str, tuple[float, float]]) -> dict:
    """One case row -> the shared crash shape. lat/lon come from the reference marker, or stay None."""
    s = lambda k: (str(raw.get(k)).strip() or None) if raw.get(k) is not None else None
    p = panel(raw.get("dot_reference_marker_location"))
    pt = markers.get(p) if p else None
    desc = (s("accident_descriptor") or "").upper()
    sev = SEVERITY.get(desc)
    return {
        # shortcut: Socrata row id, not a DMV case number (the table has none); stable only within one dataset version
        "collision_id": f"nydmv-{raw.get(':id')}",
        "datetime": f"{(s('date') or '')[:10]} {s('time') or ''}".strip(),
        "date": (s("date") or "")[:10],
        "year": int(raw["year"]) if raw.get("year") else None,
        "lat": pt[0] if pt else None,
        "lon": pt[1] if pt else None,
        "location_method": "reference_marker" if pt else None,
        "reference_marker": p,
        "route": route(p),
        "primary_road": None,                     # the public table carries no street names
        "secondary_road": None,
        "city_name": s("municipality"),
        "county_code": s("county_name"),          # county name; the table has no code
        "killed": None,                           # counts not published; severity below is the crash's
        "injured": None,
        "severity": sev,
        "severity_raw": s("accident_descriptor"),
        "collision_type": s("collision_type_descriptor"),
        "lighting": s("lighting_conditions"),
        "weather": s("weather_conditions"),
        "surface": s("road_surface_conditions"),
        "traffic_control": s("traffic_control_device"),
        "road_descriptor": s("road_descriptor"),
        "event": s("event_descriptor"),
        "ped_bike_action": s("pedestrian_bicyclist_action"),
        "vehicles": int(raw["number_of_vehicles_involved"]) if raw.get("number_of_vehicles_involved") else None,
        "is_freeway": None,                       # unknown here; route functional class is in RDM_Roadway_Current
    }


def person_kabco(injury_severity) -> str | None:
    return PERSON_KABCO.get(str(injury_severity or "").strip().upper())


# -- state-pack contract (#19): statewide = this table outside NYC + NYC open data inside the five boroughs ----------
DMV_YEARS = range(2021, 2025)                     # the "Four Year Window" (2026-11-07)
NYC_FIPS = {"36005", "36047", "36061", "36081", "36085"}
CCRS_TYPE = {"REAR END": "REAR END", "RIGHT ANGLE": "BROADSIDE", "HEAD ON": "HEAD-ON", "SIDESWIPE": "SIDE SWIPE"}
CCRS_LIGHT = {"DARK-ROAD LIGHTED": "DARK - STREET LIGHTS", "DARK-ROAD UNLIGHTED": "DARK - NO STREET LIGHTS"}


def contract_record(c: dict, raw: dict, county_fips: str) -> dict:
    """One crash_record() -> the shared crash dict. Severity K, U or O (the table has no injury level); killed and
    injured aren't published, so they are 0 and the pack says people aren't counted outside NYC."""
    import datetime as _dt
    d = _dt.date.fromisoformat(c["date"]) if c["date"] else None
    up = lambda v: str(v).upper() if v else None
    t = raw.get("time") or ""
    ev = (c["event"] or "").upper()
    return {"crash_id": c["collision_id"], "report_version": 0, "deleted": False, "preliminary": False,
            "date": c["date"], "year": c["year"], "hour": int(t.split(":")[0]) if t[:1].isdigit() else None,
            "day_of_week": d.strftime("%A") if d else None, "lat": c["lat"], "lon": c["lon"], "bad_coords": False,
            "primary_road": None, "secondary_road": None, "offset_ft": None, "offset_dir": None,
            "city": up(c["city_name"]), "county_code": c["county_code"], "county_fips": county_fips, "state": "NY",
            "is_freeway": False, "killed": 0, "injured": 0, "severity": c["severity"],
            "ped": "PEDESTRIAN" in ev, "bike": "BICYCLIST" in ev, "ebike": False, "escooter": False,
            "motorcycle": False, "heavy_truck": False, "parties": [],
            "collision_type": CCRS_TYPE.get(up(c["collision_type"]) or "", up(c["collision_type"])),
            "lighting": CCRS_LIGHT.get(up(c["lighting"]) or "", up(c["lighting"])), "weather": up(c["weather"]),
            "surface": up(c["surface"]), "route": c["route"], "reference_marker": c["reference_marker"]}


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, boxes: dict) -> dict:
    """Crashes for a corridor anywhere in New York: NYC open data in the five boroughs; elsewhere the DMV cases whose
    reference marker lands in the box (s, w, n, e). A DMV case with no marker gives only a town and can't be placed:
    it is counted in `cleaning`, not returned."""
    from . import ny_nyc
    out, missing, cleaning = [], set(), {}
    nyc = [f for f in county_fips if f in NYC_FIPS]
    if nyc:
        got = ny_nyc.fetch_contract(box, nyc, years, cache_dir)
        out += got["crashes"]
        missing |= set(got["years_missing"])
        cleaning |= got["cleaning"]
    rest = [f for f in county_fips if f not in NYC_FIPS]
    if rest:
        s, w, n, e = box
        fips = {boxes[f]["name"].removesuffix(" County").upper(): f for f in rest}
        yrs = [y for y in years if y in DMV_YEARS]
        missing |= {y for y in years if y not in DMV_YEARS}
        if yrs:
            base = (f"year in ({', '.join(repr(str(y)) for y in yrs)}) AND "
                    f"county_name in ({', '.join(repr(k) for k in fips)})")
            rows = fetch_cases(base + " AND dot_reference_marker_location IS NOT NULL", cache_dir)
            marks = marker_points(panel(r.get("dot_reference_marker_location")) for r in rows)
            placed = [c for c in ((crash_record(r, marks), r) for r in rows)
                      if c[0]["lat"] is not None and s <= c[0]["lat"] <= n and w <= c[0]["lon"] <= e]
            out += [contract_record(c, r, fips[(c["county_code"] or "").upper()]) for c, r in placed if c["severity"]]
            town = _get(CASES, {"$select": "count(*) AS n", "$where": base + " AND dot_reference_marker_location IS NULL"})
            cleaning |= {"dmv_with_marker_in_counties": len(rows), "dmv_marker_unmatched": sum(
                1 for r in rows if panel(r.get("dot_reference_marker_location")) not in marks),
                "dmv_town_only_not_placed": int(town[0]["n"]) if town else None}
    return {"crashes": out, "years_missing": sorted(missing), "cleaning": cleaning}
