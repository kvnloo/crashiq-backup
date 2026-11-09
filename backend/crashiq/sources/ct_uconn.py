"""Connecticut crash source: the Connecticut Crash Data Repository's public ArcGIS MapServer (UConn CTSRC, CTDOT),
no login.

Three point layers share CrashID: Crash (0), Person (1) and Vehicle (2). Every crash has a point (100% of 2024 inside
the state, research_notes/ct-2026-11-08), crash-level KABCO (MostSevereInjury, always the worst person's
InjuryStatus), the officer's road and intersecting road (about 25% have one), town, route class, collision manner,
light, weather and surface. 2015 to now, refreshed nightly; PDO about 3 months behind, fatal 3-6 months (CTCDR notes).
Person and vehicle rows carry their crash's point, so all three are asked for by the same box.

Licence: none published. CTCDR: "query, analyze and print/export the data for research and informational purposes";
"exempt from discovery or admission under 23 U.S.C. 409". Wired in by the CT state pack (statepacks/ct.py).
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SERVICE = "https://gis.cti.uconn.edu/arcgis/rest/services/Crash_Dashboards/ConnecticutCrash/MapServer"
LAYERS = {"crash": 0, "person": 1, "vehicle": 2}
PAGE = 2000                                      # the service's maxRecordCount
_TZ = ZoneInfo("America/New_York")               # CrashDate is a UTC instant; CrashTimeHour is local
CT_BOUNDS = (40.9, -73.8, 42.1, -71.7)

# CTCDR town -> 2022 planning region FIPS (Census TIGERweb county subdivisions, 2026-11-08). Mashantucket (the
# Mashantucket Pequot reservation) is not a town; it lies in Ledyard, so it takes Ledyard's region.
TOWN_FIPS = {
    "Andover": "09110", "Ansonia": "09140", "Ashford": "09150", "Avon": "09110", "Barkhamsted": "09160",
    "Beacon Falls": "09140", "Berlin": "09110", "Bethany": "09170", "Bethel": "09190", "Bethlehem": "09140",
    "Bloomfield": "09110", "Bolton": "09110", "Bozrah": "09180", "Branford": "09170", "Bridgeport": "09120",
    "Bridgewater": "09190", "Bristol": "09140", "Brookfield": "09190", "Brooklyn": "09150", "Burlington": "09160",
    "Canaan": "09160", "Canterbury": "09150", "Canton": "09110", "Chaplin": "09150", "Cheshire": "09140",
    "Chester": "09130", "Clinton": "09130", "Colchester": "09180", "Colebrook": "09160", "Columbia": "09110",
    "Cornwall": "09160", "Coventry": "09110", "Cromwell": "09130", "Danbury": "09190", "Darien": "09190",
    "Deep River": "09130", "Derby": "09140", "Durham": "09130", "East Granby": "09110", "East Haddam": "09130",
    "East Hampton": "09130", "East Hartford": "09110", "East Haven": "09170", "East Lyme": "09180",
    "East Windsor": "09110", "Eastford": "09150", "Easton": "09120", "Ellington": "09110", "Enfield": "09110",
    "Essex": "09130", "Fairfield": "09120", "Farmington": "09110", "Franklin": "09180", "Glastonbury": "09110",
    "Goshen": "09160", "Granby": "09110", "Greenwich": "09190", "Griswold": "09180", "Groton": "09180",
    "Guilford": "09170", "Haddam": "09130", "Hamden": "09170", "Hampton": "09150", "Hartford": "09110",
    "Hartland": "09160", "Harwinton": "09160", "Hebron": "09110", "Kent": "09160", "Killingly": "09150",
    "Killingworth": "09130", "Lebanon": "09180", "Ledyard": "09180", "Lisbon": "09180", "Litchfield": "09160",
    "Lyme": "09130", "Madison": "09170", "Manchester": "09110", "Mansfield": "09110", "Marlborough": "09110",
    "Mashantucket": "09180", "Meriden": "09170", "Middlebury": "09140", "Middlefield": "09130", "Middletown": "09130",
    "Milford": "09170", "Monroe": "09120", "Montville": "09180", "Morris": "09160", "Naugatuck": "09140",
    "New Britain": "09110", "New Canaan": "09190", "New Fairfield": "09190", "New Hartford": "09160",
    "New Haven": "09170", "New London": "09180", "New Milford": "09190", "Newington": "09110", "Newtown": "09190",
    "Norfolk": "09160", "North Branford": "09170", "North Canaan": "09160", "North Haven": "09170",
    "North Stonington": "09180", "Norwalk": "09190", "Norwich": "09180", "Old Lyme": "09130", "Old Saybrook": "09130",
    "Orange": "09170", "Oxford": "09140", "Plainfield": "09150", "Plainville": "09110", "Plymouth": "09140",
    "Pomfret": "09150", "Portland": "09130", "Preston": "09180", "Prospect": "09140", "Putnam": "09150",
    "Redding": "09190", "Ridgefield": "09190", "Rocky Hill": "09110", "Roxbury": "09160", "Salem": "09180",
    "Salisbury": "09160", "Scotland": "09150", "Seymour": "09140", "Sharon": "09160", "Shelton": "09140",
    "Sherman": "09190", "Simsbury": "09110", "Somers": "09110", "South Windsor": "09110", "Southbury": "09140",
    "Southington": "09110", "Sprague": "09180", "Stafford": "09110", "Stamford": "09190", "Sterling": "09150",
    "Stonington": "09180", "Stratford": "09120", "Suffield": "09110", "Thomaston": "09140", "Thompson": "09150",
    "Tolland": "09110", "Torrington": "09160", "Trumbull": "09120", "Union": "09150", "Vernon": "09110",
    "Voluntown": "09150", "Wallingford": "09170", "Warren": "09160", "Washington": "09160", "Waterbury": "09140",
    "Waterford": "09180", "Watertown": "09140", "West Hartford": "09110", "West Haven": "09170", "Westbrook": "09130",
    "Weston": "09190", "Westport": "09190", "Wethersfield": "09110", "Willington": "09110", "Wilton": "09190",
    "Winchester": "09160", "Windham": "09180", "Windsor": "09110", "Windsor Locks": "09110", "Wolcott": "09140",
    "Woodbridge": "09170", "Woodbury": "09140", "Woodstock": "09150",
}

LEVEL = re.compile(r"\(([KABCO])\)")             # "Suspected Serious Injury (A)" -> A
# CTCDR words -> the CCRS words the profile and the collision diagram read; any other value keeps CTCDR's words
CCRS_TYPE = {"Front to rear": "REAR END", "Angle": "BROADSIDE", "Front to front": "HEAD-ON",
             "Sideswipe, same direction": "SIDE SWIPE", "Sideswipe, opposite direction": "SIDE SWIPE"}
CCRS_LIGHT = {"Dark-Lighted": "DARK - STREET LIGHTS", "Dark-Not Lighted": "DARK - NO STREET LIGHTS",
              "Dark-Unknown Lighting": "DARK - UNKNOWN STREET LIGHTS"}
PED_TYPES = ("Pedestrian", "Other Pedestrian")   # PersonType prefixes
BIKE_TYPES = ("Bicyclist", "Other Cyclist")
MOTORCYCLE = {"Motorcycle", "Moped"}
HEAVY = {"Medium / Heavy Trucks (more than 10,000 lbs (4,536 kg))"}
ROUTE = re.compile(r"^(\d+[A-Z]?)-[NSEW]$")     # "84-W", "187-N": a state-maintained route and its direction
ROUTE_FORM = {"Interstate": "I {}", "USRoute": "US {}", "State": "CT {}"}
# the intersecting road has no route class: Connecticut's Interstates and US routes by number, anything else a CT route
CT_INTERSTATES = {"84", "91", "95", "291", "384", "395", "691"}
CT_US_ROUTES = {"1", "5", "6", "7", "44", "202"}
TOWN_NO = re.compile(r"\s+NO\s+\d+$")            # "MAIN ST NO 1": CTDOT's suffix for a town's same-named streets


def level(v) -> str | None:
    m = LEVEL.search(v or "")
    return m.group(1) if m else None


def road(name, route_class) -> str | None:
    """The officer's road in a form the corridor-street check reads: "84-W" + Interstate -> "I 84", "187-N" + State ->
    "CT 187" (OSM's ref for Connecticut routes), "MAIN ST NO 1" -> "MAIN ST". With no route class (the intersecting
    road) the number decides: "44-E" -> "US 44". Ramps ("91-S-165A (EXIT 33)") stay as written."""
    s = (name or "").strip().upper()
    if not s:
        return None
    m = ROUTE.match(s)
    if m and route_class is None:
        n = m.group(1)
        route_class = "Interstate" if n in CT_INTERSTATES else "USRoute" if n in CT_US_ROUTES else "State"
    if m and route_class in ROUTE_FORM:
        return ROUTE_FORM[route_class].format(m.group(1))
    return TOWN_NO.sub("", s)


def severity(a: dict, people: list[dict]) -> str:
    """The crash's KABCO (MostSevereInjury, else the worst person); U when CTCDR calls it an injury crash with no level."""
    lv = level(a.get("MostSevereInjury")) or min((level(p.get("InjuryStatus")) or "O" for p in people),
                                                 key="KABCO".index, default=None)
    if lv:
        return lv
    sev = a.get("CrashSeverity") or ""
    return "K" if sev.startswith("Fatal") else "U" if sev.startswith("Injury") else "O"


def contract_record(a: dict, geom: dict | None, people: list[dict], vehicles: list[dict]) -> dict:
    """One Crash attributes dict (+ its point, persons and vehicles) -> the shared crash dict (packs.check_crash)."""
    t = datetime.fromtimestamp(a["CrashDate"] / 1000, _TZ) if a.get("CrashDate") is not None else None
    lat = lon = None
    if geom and isinstance(geom.get("x"), (int, float)) and isinstance(geom.get("y"), (int, float)):
        s, w, n, e = CT_BOUNDS
        if s <= geom["y"] <= n and w <= geom["x"] <= e:
            lat, lon = round(geom["y"], 7), round(geom["x"], 7)
    lv = [level(p.get("InjuryStatus")) for p in people]
    ptype = [p.get("PersonType") or "" for p in people]
    body = {v.get("VehicleBodyType") for v in vehicles}
    harm = a.get("FirstHarmfulEvent") or ""
    up = lambda v: v.upper() if v else None       # noqa: E731
    rc = a.get("RouteClass")
    return {
        "crash_id": str(a["CrashID"]), "report_version": 0, "deleted": False,
        "preliminary": bool(t and t.year >= datetime.now(_TZ).year),     # CTCDR: PDO ~3 months, fatal 3-6 months late
        "date": t.date().isoformat() if t else "", "year": t.year if t else None,
        "hour": t.hour if t else a.get("CrashTimeHour"), "day_of_week": t.strftime("%A") if t else a.get("DayofWeek"),
        "lat": lat, "lon": lon, "bad_coords": geom is not None and lat is None,
        "primary_road": road(a.get("NameOfRoadway"), rc), "secondary_road": road(a.get("NameOfIntersectingRoadway"), None),
        "offset_ft": None, "offset_dir": None,
        "city": up(a.get("CrashTownName")), "county_code": a.get("CrashTownName"),
        "county_fips": TOWN_FIPS.get(a.get("CrashTownName") or ""), "state": "CT",
        "is_freeway": rc == "Interstate",
        "killed": lv.count("K"), "injured": sum(x in ("A", "B", "C") for x in lv),
        "severity": severity(a, people),
        "ped": any(t_.startswith(PED_TYPES) for t_ in ptype) or harm == "Pedestrian",
        "bike": any(t_.startswith(BIKE_TYPES) for t_ in ptype) or harm == "Pedalcycle/Pedalcyclist",
        "ebike": False, "escooter": False,
        "motorcycle": bool(body & MOTORCYCLE), "heavy_truck": bool(body & HEAVY), "parties": [],
        "collision_type": CCRS_TYPE.get(a.get("MannerOfCrashCollisionImpact"), up(a.get("MannerOfCrashCollisionImpact"))),
        "lighting": CCRS_LIGHT.get(a.get("LightCondition"), up(a.get("LightCondition"))),
        "weather": up(a.get("WeatherCondition")), "surface": up(a.get("TrafficSurfaceCondition")),
        "route_class": rc, "road_as_reported": a.get("NameOfRoadway"),
        "location_type": a.get("CrashSpecificLocation"), "intersection_type": a.get("TypeOfIntersection"),
        "first_harmful_event": harm or None, "agency": a.get("LawEnforcementAgencyName"),
    }


def _get(layer: int, q: dict, last: int, opener) -> list[dict]:
    q = {**q, "where": f"({q['where']}) AND OBJECTID>{last}", "outFields": "*", "orderByFields": "OBJECTID",
         "resultRecordCount": PAGE, "outSR": 4326, "f": "json"}
    req = urllib.request.Request(f"{SERVICE}/{layer}/query?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"CTCDR crash layer query error: {body['error']}")
    return body.get("features", [])


def fetch(where: str, box=None, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> dict:
    """Every crash, person and vehicle feature matching `where` (and inside box (s, w, n, e) if given), paged by
    OBJECTID. Cached as raw JSON per query when cache_dir is given."""
    q = {"where": where}
    if box:
        s, w, n, e = box
        q.update(geometry=f"{w:.6f},{s:.6f},{e:.6f},{n:.6f}", geometryType="esriGeometryEnvelope", inSR=4326,
                 spatialRel="esriSpatialRelIntersects")
    key = hashlib.sha1(json.dumps(q, sort_keys=True).encode()).hexdigest()[:10]
    cache = cache_dir / f"ct_uconn_{key}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    raw = {}
    for name, layer in LAYERS.items():
        rows, last = [], 0
        while True:
            batch = _get(layer, q, last, opener)
            rows += batch
            if len(batch) < PAGE:
                break
            last = batch[-1]["attributes"]["OBJECTID"]
        raw[name] = rows
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return raw


def records(raw: dict) -> list[dict]:
    people, vehicles = {}, {}
    for f in raw.get("person", []):
        people.setdefault(f["attributes"]["CrashID"], []).append(f["attributes"])
    for f in raw.get("vehicle", []):
        vehicles.setdefault(f["attributes"]["CrashID"], []).append(f["attributes"])
    return [contract_record(f["attributes"], f.get("geometry"), people.get(f["attributes"]["CrashID"], []),
                            vehicles.get(f["attributes"]["CrashID"], [])) for f in raw.get("crash", [])]


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years, with its people and vehicles."""
    where = f"CrashDateYear IN ({', '.join(str(int(y)) for y in years)})"
    raw = fetch(where, box, cache_dir, opener)
    rows = records(raw)
    have = {r["year"] for r in rows}
    out = [r for r in rows if r["county_fips"]]
    with_people = {p["attributes"]["CrashID"] for p in raw.get("person", [])}
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "no_town": len(rows) - len(out),
                         "persons_read": len(raw.get("person", [])), "vehicles_read": len(raw.get("vehicle", [])),
                         "no_person_rows": sum(f["attributes"]["CrashID"] not in with_people
                                               for f in raw.get("crash", []))}}
