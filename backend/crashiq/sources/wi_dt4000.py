"""Wisconsin crash source: WisDOT's open annual DT4000 crash extracts (Division of State Patrol crash system), no login.

WisDOT posts one zip per year on public Box.com links (wi-state-patrol.atlassian.net/wiki/spaces/OPENDATA, "Wisconsin
Motor Vehicle Crash Annual Data Sets", version 20230916-001): DT4000 2017-2022 so far, about 70-97 MB each, holding
crash, person, vehicle and object CSVs. The reader takes the crash file only (one row per crash, about 129,000 in
2022): GPS (LATDECDG/LONDECDG, 99.1% in 2022), the officer's on/at street or highway with distance and direction to
the intersection, the most severe injury in KABCO (INJSVR), and pedestrian / bicycle / motorcycle / truck flags.

Each year is downloaded once, cut to the columns below and cached gzipped (about 6 MB a year); the zip is deleted.
Years WisDOT hasn't posted (2023 on, as of 2026-11-08) are `years_missing`.

Licence: WisDOT says it is "making its annual motor vehicle crash data sets available as open data"; no licence text
(research_notes/wi-2026-11-08/wi-import.md). Read through the WI state pack (statepacks/wi.py, #19).
"""

from __future__ import annotations

import csv
import gzip
import io
import math
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

BOX = "https://wisdot.box.com/shared/static/{}.zip"
YEARS = {2017: "mpha5y6uqivbwykk76jznb9ojnlcnpsg", 2018: "gu1o556fz24zlz8zp0huhhva4mo5nib9",
         2019: "hcc85hy4tzh768v9u4b4ov0nbsge3h7q", 2020: "0ro1y4upd4bwp8xcmhfxxyyunh7xcxnf",
         2021: "nze1fgpp5uxe0go365u04zq2j3y9qrho", 2022: "d9t72ih7tko8w8nhx35t01aqdxppy5n5"}
KEEP = ("CRSHNMBR", "DOCTNMBR", "RECDSTAT", "CRSHDATE", "CRSHTIME", "CNTYFIPS", "MUNINAME", "MUNITYPE", "LATDECDG",
        "LONDECDG", "ONSTR", "ONHWY", "ONHWYSYS", "INTDIR", "INTDIS", "ATSTR", "ATHWY", "ATHWYSYS", "ATNMBR", "ATCODE",
        "HWYCLASS", "ACSCNTL", "INJSVR", "TOTINJ", "TOTFATL", "CRSHTYPE", "MNRCOLL", "LGTCOND", "WTCOND01", "RDCOND01",
        "PEDFLAG", "BIKEFLAG", "CYCLFLAG", "TRKFLAG", "AGCYNAME", "AGCYCASE")
WI_LAT, WI_LON = (42.4, 47.4), (-93.0, -86.2)       # Wisconsin's extent with a small margin
# DT4000 highway systems -> the names TIGER/OSM carry, so names.street_key reads them (CTH letters: "Co Rd PP")
HWY = {"IH": "I-{}", "USH": "US HWY {}", "STH": "STATE HWY {}", "CTH": "CO RD {}"}
# Data dictionary 202008 code lists, in the CCRS words the app already prints
COLLISION = {"102": "REAR END", "103": "HEAD-ON", "104": "OTHER", "105": "SIDE SWIPE", "106": "SIDE SWIPE",
             "107": "BROADSIDE", "108": "BROADSIDE", "998": "OTHER"}
FIXED = {str(c) for c in (*range(108, 128), 139, 140, 141, 142, 147)}   # CRSHTYPE: struck a fixed object
LIGHT = {"101": "DAYLIGHT", "102": "DUSK - DAWN", "103": "DUSK - DAWN", "104": "DARK - STREET LIGHTS",
         "105": "DARK - NO STREET LIGHTS", "106": "DARK - UNKNOWN STREET LIGHTS"}
WEATHER = {"101": "CLEAR", "102": "CLOUDY", "103": "RAINING", "104": "SNOWING", "105": "SNOWING", "106": "WIND",
           "107": "RAINING", "108": "FOG", "109": "FOG", "110": "SNOWING", "111": "WIND", "998": "OTHER"}
SURFACE = {"101": "DRY", "102": "WET", "103": "SNOWY OR ICY", "104": "SNOWY OR ICY", "105": "SNOWY OR ICY",
           "106": "WET", "107": "SLIPPERY", "108": "SLIPPERY", "109": "SLIPPERY", "110": "SLIPPERY", "998": "OTHER"}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and WI_LAT[0] <= lat <= WI_LAT[1] and WI_LON[0] <= lon <= WI_LON[1])


def road(street: str, hwy: str, system: str) -> str | None:
    """The officer's street name, else the highway ("STH 032" -> "STATE HWY 32", "CTH PP" -> "CO RD PP")."""
    if street.strip():
        return street.strip()
    hwy = hwy.strip()
    if not hwy:
        return None
    return HWY.get(system.strip(), "{}").format(hwy.lstrip("0") or hwy)


def severity(a: dict) -> str:
    """INJSVR is the crash's most severe injury in KABCO; blank = no injury (O), or U if WisDOT counts an injury."""
    s = (a.get("INJSVR") or "").strip()
    if s in ("K", "A", "B", "C", "O"):
        return s
    return "K" if _num(a.get("TOTFATL")) else "U" if _num(a.get("TOTINJ")) else "O"


def collision_type(a: dict) -> str | None:
    t = a.get("CRSHTYPE", "")
    if t == "104" or a.get("PEDFLAG") == "Y":          # a pedestrian anywhere in the crash, as CCRS's type G
        return "VEHICLE/PEDESTRIAN"
    if a.get("MNRCOLL") in COLLISION:
        return COLLISION[a["MNRCOLL"]]
    return "HIT OBJECT" if t in FIXED else "OVERTURNED" if t == "128" else "OTHER" if t else None


def contract_record(a: dict) -> dict:
    lat, lon = _num(a.get("LATDECDG")), _num(a.get("LONDECDG"))
    has = plausible(lat, lon)
    try:
        m, d, y = (int(x) for x in a["CRSHDATE"].split("/"))
        dt = date(y, m, d)
    except (KeyError, ValueError):
        dt = None
    t = (a.get("CRSHTIME") or "").strip()
    dist = _num(a.get("INTDIS"))
    fips = (a.get("CNTYFIPS") or "").strip()
    return {"crash_id": a["CRSHNMBR"], "report_version": 0, "deleted": a.get("RECDSTAT") == "D",
            "preliminary": False,                       # the annual extracts are WisDOT's final files
            "date": dt.isoformat() if dt else "", "year": dt.year if dt else None,
            "hour": int(t[:-2]) if t.isdigit() and len(t) >= 3 and int(t[:-2]) < 24 else None,
            "day_of_week": dt.strftime("%A") if dt else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": road(a.get("ONSTR", ""), a.get("ONHWY", ""), a.get("ONHWYSYS", "")),
            "secondary_road": road(a.get("ATSTR", ""), a.get("ATHWY", ""), a.get("ATHWYSYS", "")),
            "offset_ft": round(dist * 5280) if dist else None, "offset_dir": (a.get("INTDIR") or "").strip() or None,
            "house_number": a.get("ATNMBR") if a.get("ATCODE") == "101" else None,   # 101 = house number
            "city": (a.get("MUNINAME") or "UNINCORPORATED").strip().upper(), "county_code": fips[2:] or None,
            "county_fips": fips if len(fips) == 5 and fips.startswith("55") else None, "state": "WI",
            "is_freeway": a.get("ACSCNTL") == "101" or a.get("ONHWYSYS") == "IH",   # full access control
            "killed": int(_num(a.get("TOTFATL")) or 0), "injured": int(_num(a.get("TOTINJ")) or 0),
            "severity": severity(a), "ped": a.get("PEDFLAG") == "Y", "bike": a.get("BIKEFLAG") == "Y",
            "ebike": False, "escooter": False, "motorcycle": a.get("CYCLFLAG") == "Y",
            "heavy_truck": a.get("TRKFLAG") == "Y", "parties": [], "collision_type": collision_type(a),
            "agency": (a.get("AGCYNAME") or "").strip() or None, "report_number": (a.get("AGCYCASE") or "").strip() or None,
            "lighting": LIGHT.get(a.get("LGTCOND")), "weather": WEATHER.get(a.get("WTCOND01")),
            "surface": SURFACE.get(a.get("RDCOND01"))}


def compact(zip_path: Path, out: Path) -> None:
    """The year's zip -> its crash CSV cut to KEEP, gzipped."""
    with zipfile.ZipFile(zip_path) as z:
        # 2020-2022: dt4000/WI_annual_dt4000_<y>_crash.csv; 2017-2019: WIN_annual_dt4000_<y>_crash.csv at the root
        names = [n for n in z.namelist() if "_dt4000_" in n and n.lower().endswith("_crash.csv")]
        if len(names) != 1:
            raise RuntimeError(f"WisDOT crash file {zip_path.name}: no single DT4000 crash CSV in the zip")
        name = names[0]
        src = csv.DictReader(io.TextIOWrapper(z.open(name), encoding="latin-1", newline=""))
        lost = set(KEEP) - set(src.fieldnames or [])
        if lost:
            raise RuntimeError(f"WisDOT crash file {name}: columns missing {sorted(lost)}")
        tmp = out.with_suffix(".part")
        with gzip.open(tmp, "wt", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, KEEP, extrasaction="ignore")
            w.writeheader()
            w.writerows(src)
        tmp.replace(out)


def year_file(year: int, cache_dir: Path, opener=urllib.request.urlopen) -> Path:
    out = cache_dir / f"wi_dt4000_{year}.csv.gz"
    if out.exists():
        return out
    cache_dir.mkdir(parents=True, exist_ok=True)
    zp = cache_dir / f"wi_dt4000_{year}.zip"
    try:
        with opener(urllib.request.Request(BOX.format(YEARS[year]), headers={"User-Agent": "CrashIQ/0.1"}),
                    timeout=600) as r, open(zp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        if not zipfile.is_zipfile(zp):
            raise RuntimeError(f"WisDOT crash file {year}: the Box link did not return a zip")
        compact(zp, out)
    finally:
        zp.unlink(missing_ok=True)
    return out


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path,
                   opener=urllib.request.urlopen) -> dict:
    """Crashes with a point in the box, plus the no-GPS crashes of those counties (placed from street names)."""
    s, w, n, e = box
    out, missing = [], []
    clean = {"source_rows": 0, "no_county": 0, "no_gps_in_counties": 0, "severity_blank_from_counts": 0}
    for y in years:
        if y not in YEARS:
            missing.append(y)
            continue
        with gzip.open(year_file(y, cache_dir, opener), "rt", encoding="utf-8", newline="") as f:
            for a in csv.DictReader(f):
                clean["source_rows"] += 1
                r = contract_record(a)
                inside = r["lat"] is not None and s <= r["lat"] <= n and w <= r["lon"] <= e
                if not (inside or (r["lat"] is None and r["county_fips"] in county_fips)):
                    continue
                if not r["county_fips"]:
                    clean["no_county"] += 1
                    continue
                clean["no_gps_in_counties"] += r["lat"] is None
                clean["severity_blank_from_counts"] += not (a.get("INJSVR") or "").strip()
                out.append(r)
    return {"crashes": out, "years_missing": missing, "cleaning": clean}
