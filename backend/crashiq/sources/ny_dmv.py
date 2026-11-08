"""New York statewide crash source: NYS DMV crash cases on data.ny.gov (OPEN-NY terms), placed by reference marker.

- Cases: https://data.ny.gov/resource/e8ky-4vqe ("Four Year Window", 2021-2024 as of 2026-11-07). No coordinates, no
  street names, no case number. About 36% of crashes carry `dot_reference_marker_location` (state highways).
- Persons (ir4y-sesj) and vehicles (xe9x-a24f) have no key back to the case, so crash severity comes from
  `accident_descriptor` only: Fatal -> K, injury -> U (level not given), property damage -> O.
- Placement: the reference marker is joined to NYSDOT's public marker layer (Roadway FeatureServer layer 0). Markers
  are posted every 0.1 mi, so a matched crash sits within about 0.05 mi of the marker, along the route, side unknown.
Standalone: not wired into the app (state-pack seam, issue #19).
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
