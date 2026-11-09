"""Pennsylvania crash source: PennDOT's public crash data (PennDOT GIS Open Data, the "Crash Data Download" map),
one zip of CSV tables per county and year, no login.

Each zip holds 8 tables keyed by CRN (Crash Record Number); this reader uses three: CRASH (one row per reportable
crash, PennDOT GPS in DEC_LATITUDE/DEC_LONGITUDE on 99.5-99.9% of 2021-2025 rows, crash-level KABCO in
MAX_SEVERITY_LEVEL), ROADWAY (the street name of every road the crash involves, ordered by RDWY_SEQ_NUM: the first
is the primary road, the first different name the cross street) and FLAGS (pedestrian, bicycle, motorcycle, heavy
truck, hit-and-run). Codes are decoded from PennDOT's Crash Data Dictionary (06-26 edition, Column Codes).

The public files carry the crash month, day of week and hour but never the day (PennDOT keeps it out as data that
could identify people), so `date` is empty and `month` is kept.

Licence: none published; PennDOT's portal states a disclaimer only (research_notes/pa-2026-11-08/pa-import.md).
Wired into the app by the PA state pack (statepacks/pa.py, #19) through `fetch_contract`.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from ..names import _ordinal
from ..settings import ROOT

BASE = "https://gis.penndot.pa.gov/gishub/crashZip/County/{name}/{name}_{year}.zip"
PA_LAT, PA_LON = (39.7, 42.3), (-80.6, -74.6)     # Pennsylvania's extent with a small margin
REF = ROOT / "data" / "reference"

# PennDOT county code (CRASH.COUNTY) -> (name used in the download URL, county FIPS); PennDOT opendata/countyboundary
COUNTY = {
    "01": ("ADAMS", "42001"), "02": ("ALLEGHENY", "42003"), "03": ("ARMSTRONG", "42005"), "04": ("BEAVER", "42007"),
    "05": ("BEDFORD", "42009"), "06": ("BERKS", "42011"), "07": ("BLAIR", "42013"), "08": ("BRADFORD", "42015"),
    "09": ("BUCKS", "42017"), "10": ("BUTLER", "42019"), "11": ("CAMBRIA", "42021"), "12": ("CAMERON", "42023"),
    "13": ("CARBON", "42025"), "14": ("CENTRE", "42027"), "15": ("CHESTER", "42029"), "16": ("CLARION", "42031"),
    "17": ("CLEARFIELD", "42033"), "18": ("CLINTON", "42035"), "19": ("COLUMBIA", "42037"),
    "20": ("CRAWFORD", "42039"), "21": ("CUMBERLAND", "42041"), "22": ("DAUPHIN", "42043"),
    "23": ("DELAWARE", "42045"), "24": ("ELK", "42047"), "25": ("ERIE", "42049"), "26": ("FAYETTE", "42051"),
    "27": ("FOREST", "42053"), "28": ("FRANKLIN", "42055"), "29": ("FULTON", "42057"), "30": ("GREENE", "42059"),
    "31": ("HUNTINGDON", "42061"), "32": ("INDIANA", "42063"), "33": ("JEFFERSON", "42065"),
    "34": ("JUNIATA", "42067"), "35": ("LACKAWANNA", "42069"), "36": ("LANCASTER", "42071"),
    "37": ("LAWRENCE", "42073"), "38": ("LEBANON", "42075"), "39": ("LEHIGH", "42077"), "40": ("LUZERNE", "42079"),
    "41": ("LYCOMING", "42081"), "42": ("MCKEAN", "42083"), "43": ("MERCER", "42085"), "44": ("MIFFLIN", "42087"),
    "45": ("MONROE", "42089"), "46": ("MONTGOMERY", "42091"), "47": ("MONTOUR", "42093"),
    "48": ("NORTHAMPTON", "42095"), "49": ("NORTHUMBERLAND", "42097"), "50": ("PERRY", "42099"),
    "51": ("PIKE", "42103"), "52": ("POTTER", "42105"), "53": ("SCHUYLKILL", "42107"), "54": ("SNYDER", "42109"),
    "55": ("SOMERSET", "42111"), "56": ("SULLIVAN", "42113"), "57": ("SUSQUEHANNA", "42115"), "58": ("TIOGA", "42117"),
    "59": ("UNION", "42119"), "60": ("VENANGO", "42121"), "61": ("WARREN", "42123"), "62": ("WASHINGTON", "42125"),
    "63": ("WAYNE", "42127"), "64": ("WESTMORELAND", "42129"), "65": ("WYOMING", "42131"), "66": ("YORK", "42133"),
    "67": ("PHILADELPHIA", "42101"),
}
BY_FIPS = {f: (code, name) for code, (name, f) in COUNTY.items()}

# MAX_SEVERITY_LEVEL -> KABCUO. 8 = injury, unknown severity and 9 = unknown if injured both go to U: PennDOT's own
# Crash Facts 2025 (p. 8) counts both among its injury crashes (its 19,979 'possible injury' = C + 8 + 9), never PDO.
# 5 = died before the crash (not a crash death) -> O. The pull log counts the 9s.
SEVERITY = {"0": "O", "1": "K", "2": "A", "3": "B", "4": "C", "5": "O", "8": "U", "9": "U"}
# COLLISION_TYPE -> CCRS words where they mean the same; others keep PennDOT's words
COLLISION = {"0": "NON-COLLISION", "1": "REAR END", "2": "HEAD-ON", "3": "BACKING", "4": "BROADSIDE",
             "5": "SIDE SWIPE", "6": "SIDE SWIPE", "7": "HIT OBJECT", "8": "HIT NON-MOTORIST", "9": "OTHER",
             "98": "OTHER", "99": "NOT STATED"}
LIGHT = {"1": "DAYLIGHT", "2": "DARK - NO STREET LIGHTS", "3": "DARK - STREET LIGHTS", "4": "DUSK - DAWN",
         "5": "DUSK - DAWN", "6": "DARK - UNKNOWN STREET LIGHTS", "8": "OTHER", "9": "NOT STATED"}
WEATHER = {"1": "BLOWING SAND, SOIL, DIRT", "2": "BLOWING SNOW", "3": "CLEAR", "4": "CLOUDY", "5": "FOG, SMOG, SMOKE",
           "6": "FREEZING RAIN OR FREEZING DRIZZLE", "7": "RAINING", "8": "SEVERE CROSSWINDS", "9": "SLEET OR HAIL",
           "10": "SNOWING", "11": "SMOG OR SMOKE", "98": "OTHER", "99": "NOT STATED"}
SURFACE = {"1": "DRY", "2": "ICE/FROST", "3": "MUD, DIRT, GRAVEL", "4": "OIL", "5": "SAND", "6": "SLUSH", "7": "SNOWY",
           "8": "WATER (STANDING OR MOVING)", "9": "WET", "22": "MUD, SAND, DIRT, OIL", "98": "OTHER", "99": "NOT STATED"}
DOW = {"1": "Sunday", "2": "Monday", "3": "Tuesday", "4": "Wednesday", "5": "Thursday", "6": "Friday", "7": "Saturday"}
# PennDOT's two-letter suffixes street_key doesn't read (AV, BL, EX, PY, HW, WY already work): shared-fixes.md
SUFFIX = {"PK": "PIKE", "CR": "CIR", "TE": "TER", "BR": "BRIDGE"}
# PennDOT spells numbered streets out (SIXTYTHIRD ST, FIFTY-FIFTH ST; ~7% of Philadelphia's street rows); TIGER and
# OSM write 63RD. street_key reads only FIRST..TWELFTH (shared-fixes.md item 2), so the reader writes the number.
ORD = {w: i for i, w in enumerate("FIRST SECOND THIRD FOURTH FIFTH SIXTH SEVENTH EIGHTH NINTH TENTH ELEVENTH TWELFTH "
                                  "THIRTEENTH FOURTEENTH FIFTEENTH SIXTEENTH SEVENTEENTH EIGHTEENTH NINETEENTH".split(), 1)}
TENS = {w: 10 * i for i, w in enumerate("TWENTY THIRTY FORTY FIFTY SIXTY SEVENTY EIGHTY NINETY".split(), 2)}
ORD |= {w[:-1] + "IETH": n for w, n in TENS.items()}                        # TWENTIETH .. NINETIETH
_SPELLED = re.compile(f"({'|'.join(TENS)})-?({'|'.join(list(ORD)[:9])})")   # TWENTYFIRST, FIFTY-FIFTH


def code(v) -> str | None:
    """'4.0', '04', ' 4' -> '4'; text codes stay as they are; blank -> None."""
    s = (v or "").strip()
    if not s:
        return None
    try:
        return str(int(float(s)))
    except ValueError:
        return s


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and PA_LAT[0] <= lat <= PA_LAT[1] and PA_LON[0] <= lon <= PA_LON[1])


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v) -> int:
    n = _num(v)
    return int(n) if n is not None else 0


def _number(tok: str) -> str:
    """SIXTYTHIRD -> 63RD, TWELFTH -> 12TH; any other word stays."""
    m = _SPELLED.fullmatch(tok)
    n = TENS[m[1]] + ORD[m[2]] if m else ORD.get(tok)
    return _ordinal(n) if n else tok


def street(name: str | None) -> str | None:
    s = " ".join(_number(t) for t in (name or "").upper().split())
    if not s:
        return None
    head, _, last = s.rpartition(" ")
    return f"{head} {SUFFIX[last]}" if head and last in SUFFIX else s


def roads(rows: list[dict]) -> tuple[str | None, str | None, dict | None]:
    """ROADWAY rows of one crash -> (primary street, cross street, the primary's row)."""
    rows = sorted(rows, key=lambda r: _int(r.get("RDWY_SEQ_NUM")))
    named = [(street(r.get("STREET_NAME")), r) for r in rows if street(r.get("STREET_NAME"))]
    if not named:
        return None, None, rows[0] if rows else None
    prim, row = named[0]
    sec = next((n for n, _ in named if n != prim), None)
    return prim, sec, row


def crash_record(c: dict, rdwy: list[dict], flags: dict | None, munis: dict) -> dict:
    """One CRASH row + its ROADWAY rows + its FLAGS row -> the shared crash shape (packs.check_crash)."""
    f = flags or {}
    flag = lambda k: code(f.get(k)) == "1"
    lat, lon = _num(c.get("DEC_LATITUDE")), _num(c.get("DEC_LONGITUDE"))
    has = plausible(lat, lon)
    year = _int(c.get("CRASH_YEAR")) or None
    hour = _int(c.get("HOUR_OF_DAY")) if code(c.get("HOUR_OF_DAY")) not in (None, "99") else None
    hour = hour if hour is not None and 0 <= hour <= 23 else None
    county = (c.get("COUNTY") or "").strip().zfill(2)
    prim, sec, row = roads(rdwy)
    reported = code(c.get("MAX_SEVERITY_LEVEL"))
    sev = SEVERITY.get(reported or "", "O")
    ctype = code(c.get("COLLISION_TYPE"))
    ped = flag("PEDESTRIAN")
    return {
        "crash_id": str(c["CRN"]).strip(), "report_version": 0, "deleted": False,
        "preliminary": False,                    # PennDOT posts a year once it is closed (the June after)
        "date": "",                              # the public files have no day of the month
        "month": _int(c.get("CRASH_MONTH")) or None, "year": year, "hour": hour,
        "day_of_week": DOW.get(code(c.get("DAY_OF_WEEK")) or ""),
        "lat": lat if has else None, "lon": lon if has else None,
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "primary_road": prim, "secondary_road": sec, "offset_ft": None, "offset_dir": None,
        "city": munis.get((c.get("MUNICIPALITY") or "").strip()), "county_code": county,
        "county_fips": COUNTY.get(county, (None, None))[1], "state": "PA",
        "is_freeway": bool(row) and code(row.get("ACCESS_CTRL")) == "1",       # limited access
        "killed": _int(c.get("FATAL_COUNT")), "injured": _int(c.get("TOT_INJ_COUNT")),
        "severity": sev, "severity_reported": reported,
        "ped": ped, "bike": flag("BICYCLE"), "ebike": False, "escooter": False,
        "motorcycle": flag("MOTORCYCLE"), "heavy_truck": flag("HVY_TRUCK_RELATED"), "hit_run": flag("HIT_RUN"),
        "parties": [],
        "collision_type": "VEHICLE/PEDESTRIAN" if ctype == "8" and ped
        else COLLISION.get(ctype or "", f"code {ctype}" if ctype else None),
        "lighting": LIGHT.get(code(c.get("ILLUMINATION")) or ""),
        "weather": WEATHER.get(code(c.get("WEATHER1")) or ""),
        "surface": SURFACE.get(code(c.get("ROAD_CONDITION")) or ""),
        "intersect_type": code(c.get("INTERSECT_TYPE")),
        "route": (row or {}).get("ROUTE") or None, "segment": code((row or {}).get("SEGMENT")),
    }


def _table(z: zipfile.ZipFile, name: str):
    """A table's rows, streamed: county zips name it CRASH_<COUNTY>_<YEAR>.csv, statewide ones CRASH_<YEAR>.csv."""
    member = next((n for n in z.namelist() if n.upper().startswith(name + "_")), None)
    if member is None:
        raise RuntimeError(f"PennDOT zip has no {name} table: {z.namelist()}")
    return csv.DictReader(io.TextIOWrapper(z.open(member), encoding="latin-1", newline=""))


def read_zip(path: Path, keep, munis: dict) -> list[dict]:
    """Crash records of one PennDOT zip whose CRASH row passes keep(row)."""
    with zipfile.ZipFile(path) as z:
        crashes = {r["CRN"]: r for r in _table(z, "CRASH") if keep(r)}
        rdwy = defaultdict(list)
        for r in _table(z, "ROADWAY"):
            if r["CRN"] in crashes:
                rdwy[r["CRN"]].append(r)
        flags = {r["CRN"]: r for r in _table(z, "FLAGS") if r["CRN"] in crashes}
    return [crash_record(c, rdwy[k], flags.get(k), munis) for k, c in crashes.items()]


def download(county: str, year: int, cache_dir: Path, opener=urllib.request.urlopen) -> Path | None:
    """The county-year zip (cached; ~1-3 MB), or None when PennDOT hasn't posted that year (404)."""
    path = cache_dir / f"pa_{county}_{year}.zip"
    if path.exists():
        return path
    req = urllib.request.Request(BASE.format(name=county, year=year), headers={"User-Agent": "CrashIQ/0.1"})
    try:
        with opener(req, timeout=300) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(body)
    zipfile.ZipFile(tmp).testzip()               # a cut-off download never lands in the cache
    tmp.replace(path)
    return path


def municipalities() -> dict:
    return json.loads((REF / "pa_municipalities.json").read_text())["municipalities"]


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path,
                   opener=urllib.request.urlopen) -> dict:
    """Every crash of those counties and years with a point in the box (s, w, n, e), plus the county's crashes with
    no point (the core sorts those by street name)."""
    s, w, n, e = box
    munis = municipalities()

    def keep(r):
        la, lo = _num(r.get("DEC_LATITUDE")), _num(r.get("DEC_LONGITUDE"))
        return not plausible(la, lo) or (s <= la <= n and w <= lo <= e)

    out, have = [], set()
    for fips in county_fips:
        if fips not in BY_FIPS:
            continue                             # a box that pokes into a neighbouring state
        for y in years:
            path = download(BY_FIPS[fips][1], y, Path(cache_dir), opener)
            if path is None:
                continue
            have.add(y)
            out += read_zip(path, keep, munis)
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(out),
                         "unknown_if_injured_counted_U": sum(c["severity_reported"] == "9" for c in out),
                         "no_gps": sum(c["lat"] is None for c in out)}}
