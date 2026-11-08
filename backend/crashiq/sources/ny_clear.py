"""New York CLEAR / ALIS crash export reader (Part B: "upload your export"). Read-only, no network.

CLEAR (NYSDOT's crash system) is open only to NY government staff and their consultants; everyone else gets the same
exports by FOIL. NYSDOT publishes no data dictionary for the export, so the column map comes from two exports NYSDOT
handed out that are posted publicly (checked 2026-11-07):
  - "NYSDOT Accident Data Spreadsheet" (human headers: Case Num, Comp Ref Marker, Comp X, Severity, On Street ...),
    e.g. NY DPS case file Appendix 16-B (documents.dps.ny.gov, DocRefId B0793CF9-89AB-415D-AB4E-FC6C77A25F90).
  - the same crash table as a shapefile/DBF (10-character names: CASE_NUM, COMP_REF_M, COMPX, DMV_ACCD_C, CLOSESTCRO
    ...), e.g. Town of Gardiner Int_Route-44-Route-7.xlsx (gardinerdems4586.live-website.com, 2021).
  ALIS "Simple Query Reports" (dot.ny.gov highway-repository/SimpleQuery_Reports.pdf) lists the same crash fields and
  says Comp X/Y are UTM zone 18 and "Number of Serious Injuries" is KABCO "A".
Both samples are ALIS-era (2015-2019). A CLEAR-era export may rename columns: `read` reports which logical fields it
could not find, so a new layout is a one-line addition to COLS, not a new reader.
Standalone: not wired into the app (state-pack seam, issue #19).
"""

from __future__ import annotations

import csv
import math
from datetime import date, datetime
from pathlib import Path

from .ca_ccrs import _norm_col

# logical field -> header candidates (human spreadsheet first, then the DBF name; matched ignoring case/punctuation)
COLS = {
    "case_number": ["Case Num", "CASE_NUM", "Case Number"],
    "case_year": ["Case Year", "CASE_YR", "Year"],
    "county": ["COMP_COUNT", "County", "County Name"],   # an export joined to road inventory also has County = ULS
    "municipality": ["Comp Muni", "COMP_MUNI", "Municipality"],
    "muni_type": ["Muni Type", "COMP_MUNI_"],
    "reference_marker": ["Comp Ref Marker", "COMP_REF_M", "Reference Marker"],
    "at_intersection": ["At Intersection", "ATINTERSEC"],
    "x": ["Comp X", "COMPX"],
    "y": ["Comp Y", "COMPY"],
    "lat": ["Latitude", "LAT"],                      # not in either sample; a CLEAR export may carry it
    "lon": ["Longitude", "LON", "LONG"],
    "date": ["Accd Date", "ACC_DATE", "ACCD_DTE", "Crash Date"],
    "time": ["Accd Time", "ACCD_TME", "Crash Time"],
    "severity": ["Severity", "DMV_ACCD_C", "Crash Severity"],
    "injuries": ["Num Of Injuries", "NUM_OF_INJ"],
    "serious": ["Num Serious Injuries", "NUM_OF_SER"],
    "fatalities": ["Num Of Fatalities", "NUM_OF_FAT"],
    "vehicles": ["Num Of Vehicles", "NUM_OF_VEH"],
    "accident_type": ["Accd Type", "ACCD_TYP"],
    "collision_type": ["Collision Type", "COLLISION_"],
    "traffic_control": ["Traffic Control", "TRAF_CNTL"],
    "lighting": ["Light Condition", "LIGHT_COND"],
    "weather": ["Weather", "WEATHER"],
    "surface": ["Road Surf Cond", "ROAD_SURF_"],
    "ped_location": ["Ped Loc", "PED_LOC"],
    "ped_action": ["Ped Action", "PED_ACTN"],
    "day_of_week": ["Day_Of_Week", "DAYOFWEEK", "Day Of Week"],
    "on_street": ["On Street", "ON_STREET"],
    "cross_street": ["Closest Cross Street", "CLOSESTCRO", "Cross Street"],
    "parking_lot": ["Parking Lot Ind", "PARKINGLOT"],
    "kabco": ["KABCO"],                              # added by some analysts; used when present
}
REQUIRED = ("case_number", "date", "severity")


def utm18_to_latlon(x: float, y: float) -> tuple[float, float]:
    """UTM zone 18N (GRS80/NAD83, metres) -> (lat, lon) in degrees. Snyder 1987, USGS PP 1395, eq. 8-18 ff."""
    a, f, k0 = 6378137.0, 1 / 298.257222101, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    p = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
         + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    c1, t1 = ep2 * math.cos(p) ** 2, math.tan(p) ** 2
    n1 = a / math.sqrt(1 - e2 * math.sin(p) ** 2)
    r1 = a * (1 - e2) / (1 - e2 * math.sin(p) ** 2) ** 1.5
    d = (x - 500000.0) / (n1 * k0)
    lat = p - (n1 * math.tan(p) / r1) * (d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24
                                         + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = (d - (1 + 2 * t1 + c1) * d ** 3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120
           ) / math.cos(p)
    return math.degrees(lat), -75.0 + math.degrees(lon)


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", "")) if v not in (None, "") else None
    except ValueError:
        return None


def _date(v) -> str | None:
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    s = str(v or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _time(v) -> str | None:
    s = str(v or "").strip().lower().replace(" ", "")
    for fmt in ("%I:%M%p", "%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%H:%M")
        except ValueError:
            pass
    return None


def severity(sev_text, fatalities, serious, injuries, kabco_col=None) -> str:
    """KABCUO: the export's KABCO column when given; else K from fatalities, A from serious ('A') injuries, U for other
    injuries (B/C not split in the export), O otherwise."""
    k = str(kabco_col or "").strip().upper()
    if k in tuple("KABCO"):
        return k
    if (fatalities or 0) > 0 or "FATAL" in str(sev_text or "").upper():
        return "K"
    if (serious or 0) > 0:
        return "A"
    if (injuries or 0) > 0 or "INJURY" in str(sev_text or "").upper():
        return "U"
    return "O"


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and 40.4 < lat < 45.1 and -79.8 < lon < -71.8   # New York State box


def crash_record(raw: dict, cols: dict[str, dict]) -> dict:
    g = lambda k: raw.get(cols[k]["id"]) if k in cols else None
    s = lambda k: (str(g(k)).strip() or None) if g(k) is not None else None
    lat, lon = _num(g("lat")), _num(g("lon"))
    method = "export_latlon"
    if not plausible(lat, lon):
        x, y = _num(g("x")), _num(g("y"))
        lat, lon = utm18_to_latlon(x, y) if x and y else (None, None)
        method = "export_utm18"
    ok = plausible(lat, lon)
    killed, serious, injured = (int(_num(g(k)) or 0) for k in ("fatalities", "serious", "injuries"))
    d, t = _date(g("date")), _time(g("time"))
    rm = s("reference_marker")
    return {
        "collision_id": s("case_number"),
        "datetime": f"{d or ''} {t or ''}".strip(),
        "date": d,
        "year": int(d[:4]) if d else None,
        "lat": lat if ok else None,
        "lon": lon if ok else None,
        "location_method": method if ok else None,
        "reference_marker": rm.rjust(12) if rm else None,
        "primary_road": s("on_street"),
        "secondary_road": s("cross_street"),
        "at_intersection": (s("at_intersection") or "").upper() == "Y",
        "city_name": s("municipality"),
        "county_code": s("county"),
        "killed": killed,
        "injured": injured,                   # all injuries; `serious_injured` of them are KABCO A
        "serious_injured": serious,
        "severity": severity(s("severity"), killed, serious, injured, s("kabco")),
        "severity_raw": s("severity"),
        "non_reportable": "NON-REPORTABLE" in (s("severity") or "").upper(),
        "collision_type": s("collision_type"),
        "accident_type": s("accident_type"),
        "lighting": s("lighting"),
        "weather": s("weather"),
        "surface": s("surface"),
        "traffic_control": s("traffic_control"),
        "ped_action": s("ped_action"),
        "vehicles": int(_num(g("vehicles")) or 0) or None,
        "parking_lot": (s("parking_lot") or "").upper() == "Y",
        "is_freeway": None,                   # not in the export; join the reference marker to RDM functional class
    }


def _rows(path: Path) -> list[list]:
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        return [list(r) for ws in wb.worksheets for r in ws.iter_rows(values_only=True)]
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.reader(fh))


def resolve(header: list[str]) -> tuple[dict[str, dict], list[str]]:
    """Logical field -> {"id": header}. An exact header (any case) wins over a punctuation-blind match, because DBF
    names collide once squeezed: COMP_MUNI (the town) and COMP_MUNI_ (its type code) are both 'compmuni'."""
    exact = {h.strip().upper(): h for h in header if h}
    loose = {}
    for h in header:
        if h:
            loose.setdefault(_norm_col(h), h)
    cols, missing = {}, []
    for logical, cands in COLS.items():
        hit = next((exact[c.upper()] for c in cands if c.upper() in exact), None) or \
            next((loose[_norm_col(c)] for c in cands if _norm_col(c) in loose), None)
        if hit:
            cols[logical] = {"id": hit}
        else:
            missing.append(logical)
    return cols, missing


def read(path: Path | str) -> tuple[list[dict], list[str]]:
    """Crashes from a CLEAR/ALIS crash-level export (.csv or .xlsx). Returns (crashes, logical fields not found).
    The header is the first row naming a case-number column (exports often start with title rows)."""
    rows = _rows(Path(path))
    case_heads = {_norm_col(c) for c in COLS["case_number"]}
    for i, r in enumerate(rows):
        if any(_norm_col(str(v or "")) in case_heads for v in r):
            header = [str(v).strip() if v is not None else "" for v in r]
            break
    else:
        raise ValueError(f"{path}: no header row with a case number column ({', '.join(COLS['case_number'])})")
    cols, missing = resolve(header)
    lacking = [k for k in REQUIRED if k not in cols]
    if lacking:
        raise ValueError(f"{path}: export lacks required columns {lacking}")
    out = []
    for r in rows[i + 1:]:
        raw = dict(zip(header, r))
        if str(raw.get(cols["case_number"]["id"]) or "").strip():
            out.append(crash_record(raw, cols))
    return out, missing
