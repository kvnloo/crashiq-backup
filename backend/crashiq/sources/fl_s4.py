"""Florida crash source: Signal Four Analytics (S4, UF GeoPlan) crash-event rows -> the shared crash shape.

S4 is FDOT's crash database of record. Logins go to agencies and their approved consultants only, so the main use is
"bring your export": a user with access downloads the crash Event file (CSV) and CrashIQ reads it. The same columns
appear in S4 extracts that MPOs and counties republish as open ArcGIS layers (Palm Beach MPO `pal_crash_event`,
MetroPlan Orlando, City of Orlando, Hillsborough County), so `fetch_layer` reads those too (licence unclear: see
research_notes/fl-2026-11-07/fl-import.md before using one in the product).

Column names follow the S4 Data Dictionary (https://signal4analytics.com/assets/files/S4_Data_Dictionary.pdf, Event
elements E1-E119 and Mapped M9/M10). Republished layers spell them a few ways (ROAD_SYSTEM_IDENTIFER, names cut at 31
characters, CamelCase in Hillsborough's copy), so columns are matched by their letters only, against the candidates.
Not wired into the app (state-pack seam, issue #19).
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, Iterator

from .ca_ccrs import parse_dt

FL_LAT, FL_LON = (24.4, 31.1), (-87.7, -79.8)   # S4 dictionary E24/E25: 24.544110-31.000750, -87.634930 to -80.0x

COLS = {
    "report_number": ["REPORT_NUMBER", "HSMV_Report_Number", "ReportNumber"],
    "objectid": ["OBJECTID"],
    "datetime": ["CRASH_DATE_AND_TIME", "CrashDate", "Crash_Date"],
    "crash_time": ["Crash_Time"],
    "county": ["COUNTY_NAME", "County"],
    "city": ["CITY_NAME", "City"],
    "on_street": ["ON_STREET_ROAD_HIGHWAY", "CrashStreet", "Crash_Street"],
    "house_number": ["STREET_ADDRESS_NUMBER"],
    "feet": ["FEET_FROM_INTERSECTION", "OffsetDistance", "Offset_Distance"],
    "direction": ["DIRECTION_FROM_INTERSECTION", "OffsetDirection", "Offset_Direction"],
    "from_street": ["FROM_INTERSECTION_OF", "IntersectingStreet", "Intersecting_Street"],
    "milepost": ["MILEPOST_NUMBER"],
    "road_system": ["ROAD_SYSTEM_IDENTIFIER", "ROAD_SYSTEM_IDENTIFER", "RoadSystemIdentifier", "Road_Sys_Identifier"],
    "interchange": ["INTERCHANGE_FLAG"],
    "collision_type": ["TYPE_OF_IMPACT", "Manner_of_Collision"],
    "lighting": ["LIGHT_CONDITION", "LightCondition", "Light_Condition"],
    "weather": ["WEATHER_CONDITION", "WeatherCondition", "Weather_Condition"],
    "surface": ["ROAD_SURFACE_CONDITION", "RoadSurfaceCondition", "Road_Surf_Cond"],
    "hit_run": ["S4_IS_HIT_AND_RUN"],
    "ped": ["S4_IS_PEDESTRIAN_INVOLVED"],
    "bike": ["S4_IS_BICYCLIST_INVOLVED"],
    "severity": ["S4_CRASH_SEVERITY", "CrashSeverity", "Crash_Severity"],
    "severity_detail": ["S4_CRASH_SEVERITY_DETAIL"],
    "n_fatal": ["S4_FATALITY_COUNT", "Fatalities"],
    "n_incap": ["S4_INCAPACITATING_INJURY_COUNT", "S4_INCAPACITATING_INJURY_CNT", "IncapacitatingInjuries",
                "Incapacitating_Injuries"],
    "n_nonincap": ["S4_NON_INCAPACITATING_INJURY_COUNT", "S4_NON_INCAPACITATING_INJURY", "S4_NON_INCAPACITATING_INJURY_CO",
                   "Non_Incapacitating_Injuries"],
    "n_possible": ["S4_POSSIBLE_INJURY_COUNT", "Possible_Injuries"],
    "n_none": ["S4_NONE_INJURY_COUNT"],
    "n_injured": ["S4_INJURY_COUNT", "Injuries"],
    "s4_lat": ["S4_LATITUDE", "S4DecimalDegreesLatitude", "S4_Decimal_Degree_Latitude"],
    "s4_lon": ["S4_LONGITUDE", "S4DecimalDegreesLongitude", "S4_Decimal_Degree_Longitude"],
    "lat": ["LATITUDE"],        # officer-reported (E24); S4's mapped point (M9) is preferred
    "lon": ["LONGITUDE"],
}

# S4 Crash Severity Detail (E68) and the per-person Injury Severity (D41/P21/N27) -> KABCO. A non-traffic fatality
# (death from illness, suicide...) is "not reported as a fatality" (E68 comment), so it counts as no injury.
KABCO = {"FATALWITHIN30DAYS": "K", "FATAL": "K", "FATALITY": "K", "INCAPACITATINGINJURY": "A", "INCAPACITATING": "A",
         "SERIOUSINJURY": "A", "NONINCAPACITATINGINJURY": "B", "NONINCAPACITATING": "B", "POSSIBLEINJURY": "C",
         "POSSIBLE": "C", "NOINJURY": "O", "NONE": "O", "PROPERTYDAMAGEONLY": "O", "NONTRAFFICFATALITY": "O",
         "INJURY": "U"}     # E67 simplified "Injury" = B or C, level not given
SEVERITY_ORDER = "KABCUO"
FREEWAY_SYSTEMS = {"INTERSTATE", "TURNPIKETOLL"}
DIRS = {"N": "N", "S": "S", "E": "E", "W": "W"}


def _sq(v) -> str:
    return "".join(ch for ch in str(v if v is not None else "").upper() if ch.isalnum())


def kabco(v) -> str | None:
    s = str(v or "").strip()
    if len(s) > 4 and s[0].isdigit() and " - " in s:          # Hillsborough's copy: "3 - Non-Incapacitating Injury"
        s = s.split(" - ", 1)[1]
    return KABCO.get(_sq(s))


def resolve(header: Iterable[str]) -> dict[str, str]:
    """Logical name -> the file's column, matched on letters and digits only (first candidate that exists)."""
    by = {_sq(h): h for h in header}
    return {k: next(by[_sq(c)] for c in cands if _sq(c) in by) for k, cands in COLS.items()
            if any(_sq(c) in by for c in cands)}


def _num(v) -> float | None:
    try:
        f = float(str(v).strip())
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and FL_LAT[0] <= lat <= FL_LAT[1] and FL_LON[0] <= lon <= FL_LON[1]


def _date(v, crash_time=None) -> tuple[str | None, int | None, int | None]:
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 1e11:     # ArcGIS date: epoch milliseconds
        # read as UTC = local wall time: Palm Beach MPO's earliest value is 2019-01-01 00:15 "UTC" in a layer of
        # 2019-2024 crashes, so publishers store Florida wall-clock time without a zone
        t = _dt.datetime.fromtimestamp(v / 1000, _dt.timezone.utc)
        return t.strftime("%Y-%m-%d"), t.year, t.hour
    date, year, hour = parse_dt(v)
    if hour is None and crash_time not in (None, ""):
        t = str(crash_time).strip().replace(":", "")[:4].zfill(4)
        hour = int(t[:2]) if t.isdigit() and int(t[:2]) < 24 else None
    return date, year, hour


def crash_record(raw: dict, cols: dict[str, str]) -> dict:
    """One S4 crash-event row -> the shared crash shape (keys as ca_ccrs.crash_record), plus per-person KABCO from the
    event file's injury counts and the crash severity in KABCUO."""
    g = lambda k: raw.get(cols[k]) if k in cols else None
    s = lambda k: (str(g(k)).strip() or None) if g(k) is not None else None
    n = lambda k: int(_num(g(k)) or 0)
    date, year, hour = _date(g("datetime"), g("crash_time"))
    lat, lon, src = _num(g("s4_lat")), _num(g("s4_lon")), "s4"
    if not plausible(lat, lon):
        lat, lon, src = _num(g("lat")), _num(g("lon")), "officer"
    has = plausible(lat, lon)
    on, frm, house = s("on_street"), s("from_street"), s("house_number")
    # a report with a house number and no cross street: "975 3RD ST" in secondary_road is what locate._house_address reads
    secondary = frm or (f"{house} {on}" if house and on and house[:1].isdigit() else None)
    persons = (["K"] * n("n_fatal") + ["A"] * n("n_incap") + ["B"] * n("n_nonincap") + ["C"] * n("n_possible"))
    sev = kabco(g("severity_detail")) or kabco(g("severity"))
    best = min(persons, key=SEVERITY_ORDER.index) if persons else None
    if best and (sev is None or SEVERITY_ORDER.index(best) < SEVERITY_ORDER.index(sev)):
        sev = best                                    # the counts outrank a stale label
    rid = s("report_number")
    feet = _num(g("feet"))
    return {
        "crash_id": rid or (f"objectid:{s('objectid')}" if s("objectid") else None),
        "report_number": rid,
        "date": date or "", "year": year, "hour": hour,
        "lat": lat if has else None, "lon": lon if has else None,
        "gps_source": src if has else None,
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "primary_road": on, "secondary_road": secondary,
        "house_number": house,
        "offset_ft": feet if feet else None,
        "offset_dir": DIRS.get((s("direction") or "")[:1].upper()),
        "milepost": s("milepost"),
        "city": s("city"), "county_code": s("county"),
        "road_system": s("road_system"),
        "is_freeway": _sq(g("road_system")) in FREEWAY_SYSTEMS,
        "collision_type": s("collision_type"), "lighting": s("lighting"), "weather": s("weather"),
        "surface": s("surface"),
        "hit_run": _sq(g("hit_run")) in ("Y", "YES", "TRUE", "1"),
        "ped": _sq(g("ped")) in ("Y", "YES", "TRUE", "1"),
        "bike": _sq(g("bike")) in ("Y", "YES", "TRUE", "1"),
        "killed": n("n_fatal"),
        "injured": n("n_injured") or n("n_incap") + n("n_nonincap") + n("n_possible"),
        "person_kabco": persons,
        "severity": sev,                              # None = no severity on the row; the caller counts those
    }


def read_csv(path: Path) -> Iterator[dict]:
    """Stream an S4 Event export (CSV); one crash per row."""
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        r = csv.DictReader(f)
        cols = resolve(r.fieldnames or [])
        missing = [k for k in ("datetime", "on_street", "severity") if k not in cols]
        if missing:
            raise ValueError(f"not an S4 crash-event file: no column for {missing}")
        for row in r:
            yield crash_record(row, cols)


def read_features(features: list[dict]) -> list[dict]:
    """ArcGIS query features (attributes, optional point geometry in WGS84) -> crashes. The layer geometry is S4's
    mapped point when the attribute columns lack S4_LATITUDE (City of Orlando's copy)."""
    if not features:
        return []
    use_geo = "s4_lat" not in resolve(features[0]["attributes"])
    rows = []
    for f in features:
        a, geo = dict(f["attributes"]), f.get("geometry") or {}
        if use_geo:
            a["S4_LATITUDE"], a["S4_LONGITUDE"] = geo.get("y"), geo.get("x")
        rows.append(a)
    cols = resolve(rows[0])
    return [crash_record(a, cols) for a in rows]


def _post(url: str, params: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), headers={"User-Agent": "CrashIQ/0.1"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = json.load(r)
            if "error" in body:
                raise RuntimeError(f"ArcGIS error: {body['error']}")
            return body
        except (OSError, RuntimeError):
            if attempt == 3:
                raise
            time.sleep(3 * 2 ** attempt)
    raise AssertionError


def fetch_layer(layer_url: str, where: str = "1=1", chunk: int = 500) -> list[dict]:
    """Every feature of an open ArcGIS layer matching `where`, paged by object id (WGS84)."""
    ids = sorted(_post(layer_url + "/query", {"where": where, "returnIdsOnly": "true", "f": "json"})["objectIds"] or [])
    feats = []
    for i in range(0, len(ids), chunk):
        feats += _post(layer_url + "/query", {"objectIds": ",".join(map(str, ids[i:i + chunk])), "outFields": "*",
                                              "outSR": 4326, "f": "json"})["features"]
    return read_features(feats)
