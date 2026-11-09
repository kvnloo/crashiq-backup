"""Alabama crash source: the CARE eCrash map layer (University of Alabama CAPS for ALDOT / ALEA), an open ArcGIS
MapServer, no login.

One row per crash, 2020 to the current month (Alabama eCrash reports, every agency), crash-level KABCO (CrashSev,
e.g. "Suspected Minor Injury"), people killed and injured as text counts ("1 Fatality", "2 Injuries"), the officer's
street and cross street (StreetName, CrossStreet1), and a point on 86% of rows (officer GPS, or CARE's node, link or
route-milepost location; Latitude = -1 when none).

Shifted rows: from OBJECTID 746,179 on (227,676 rows at 2026-11-08: 1,699 late-loaded 2024 crashes, 2025 from
April, all of 2026) CARE loaded the text columns two places to the left: CrashSev holds the at-intersection flag and the
real severity sits in ManrCrs, County holds the year, NumMajInj the county. `repair` reads each field from where it
landed (measured on 300 rows against 300 normal ones, research_notes/al-2026-11-08/al-import.md § Shifted rows).
The point, street names, DateTime and ID columns are not shifted.

Licence: none published, and the layer has no description or copyright text. ALDOT's Safety Data Access Guidebook
says these data "are not to be shared with the public pursuant to Alabama Law and 23 U.S.C. §§148(h)(4) and 409",
and CAPS keeps location-specific data in a password-protected portal (al-import.md § Licence), so the pack is
reader_only until ALDOT/CAPS agree. Wired into the app through the AL state pack (statepacks/al.py) by `fetch_contract`.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAYER = "https://care-esriext.aladata.com/arcgis/rest/services/eCrash/Red/MapServer/0"
PAGE = 5000                                      # the layer's maxRecordCount
AL_LAT, AL_LON = (30.1, 35.1), (-88.6, -84.8)    # Alabama's extent with a small margin
REF = Path(__file__).resolve().parents[3] / "data" / "reference"

SEVERITY = {"Fatal Injury": "K", "Suspected Serious Injury": "A", "Suspected Minor Injury": "B",
            "Possible Injury": "C", "Property Damage Only": "O"}         # "Unknown" (2% of rows) stays None
# a shifted row's field -> where its value landed (two text columns to the left)
SHIFT = {"CrashSev": "ManrCrs", "ManrCrs": "DistToObj", "Lighting": "NHS", "Weather": "FXClass",
         "HwyClass": "DataSrc", "CUNonMot": "TruckBusSup", "CUType": "CMVInv", "CMVInv": "NumTrain",
         "CURdCond": "CURdBrdg", "NumKilled": "NumNonFat", "NumNonFat": "NumPed", "NumPed": "NumOcc",
         "NumByc": "NumNonOcc", "County": "NumMajInj", "City": "NumMinInj", "Year": "County"}
FIELDS = sorted(set(SHIFT) | set(SHIFT.values()) | {"OBJECTID", "ID", "DateTime", "Latitude", "Longitude",
                                                     "StreetName", "CrossStreet1", "Route", "Milepost"})
# CARE's words -> the CCRS words the profile and the collision diagram read; any other value keeps CARE's words
CCRS_TYPE = {"Rear End (front to rear)": "REAR END", "Side Impact (angled)": "BROADSIDE",
             "Side Impact (90 degrees)": "BROADSIDE", "Head-On (front to front only)": "HEAD-ON",
             "Sideswipe - Same Direction": "SIDE SWIPE", "Sideswipe - Opposite Direction": "SIDE SWIPE"}
CCRS_LIGHT = {"Dark - Roadway Not Lighted": "DARK - NO STREET LIGHTS",
              "Dark - Unknown Roadway Lighting": "DARK - UNKNOWN STREET LIGHTS"}


def _key(name: str) -> str:
    return re.sub(r"[^A-Z]", "", name.upper())     # "St. Clair" = "St Clair", "DeKalb" = "Dekalb"


NAME = {k: v["name"].removesuffix(" County") for k, v in
        json.loads((REF / "county_boxes_al.json").read_text())["counties"].items()}
FIPS = {_key(v): k for k, v in NAME.items()}


def shifted(a: dict) -> bool:
    return bool(re.fullmatch(r"\d{4}", str(a.get("County") or "")))


def repair(a: dict) -> dict:
    """The row with every field read from where CARE put it."""
    return {**a, **{k: a.get(v) for k, v in SHIFT.items()}} if shifted(a) else a


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and AL_LAT[0] <= lat <= AL_LAT[1] and AL_LON[0] <= lon <= AL_LON[1])


def count(text) -> int:
    """'2 Injuries' -> 2, 'No Fatalities' -> 0."""
    m = re.match(r"\s*(\d+)", str(text or ""))
    return int(m.group(1)) if m else 0


def word(v) -> str | None:
    """CARE marks eCrash-only values with a leading 'E ' ('E Dark - Spot Illumination ...'); drop it."""
    t = (str(v).strip() if v is not None else "") or None
    return t[2:] if t and t.startswith("E ") else t


def contract_record(raw: dict) -> dict:
    """One layer attributes dict -> the shared crash dict (packs.check_crash)."""
    a = repair(raw)
    lat, lon = a.get("Latitude"), a.get("Longitude")
    has = plausible(lat, lon)
    # DateTime is the local clock time stored as if UTC (2:13 AM crash = 02:13Z, Time "2:00 AM to 2:59 AM")
    when = datetime.fromtimestamp(a["DateTime"] / 1000, timezone.utc) if a.get("DateTime") is not None else None
    sev = SEVERITY.get(word(a.get("CrashSev")) or "")
    killed, hurt = count(a.get("NumKilled")), count(a.get("NumNonFat"))
    prim, sec = word(a.get("StreetName")), word(a.get("CrossStreet1"))
    light = word(a.get("Lighting")) or ""
    city = word(a.get("City"))
    return {"crash_id": str(a.get("ID") or a["OBJECTID"]), "report_version": 0, "deleted": False,
            "preliminary": bool(when and when.year >= datetime.now(timezone.utc).year),
            "date": when.date().isoformat() if when else "", "year": when.year if when else None,
            "hour": when.hour if when else None, "day_of_week": when.strftime("%A") if when else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and lat > 0 and not has,
            "primary_road": prim,
            "secondary_road": sec if sec and (sec or "").upper() != (prim or "").upper() else None,
            "offset_ft": None, "offset_dir": None,
            "city": None if not city or city.startswith("Rural ") else city.upper(),
            "county_code": word(a.get("County")), "county_fips": FIPS.get(_key(word(a.get("County")) or "")),
            "state": "AL", "is_freeway": word(a.get("HwyClass")) == "Interstate",
            # a K crash has at least one death and an A/B/C crash at least one injury, whatever the counts say
            "killed": max(killed, int(sev == "K")), "injured": max(hurt, int(sev in ("A", "B", "C"))),
            "severity": sev, "ped": count(a.get("NumPed")) > 0, "bike": count(a.get("NumByc")) > 0,
            "ebike": False, "escooter": False, "motorcycle": "Motorcycle" in (word(a.get("CUType")) or ""),
            "heavy_truck": word(a.get("CMVInv")) == "CMV is Involved", "parties": [],
            "collision_type": CCRS_TYPE.get(word(a.get("ManrCrs")), (word(a.get("ManrCrs")) or "").upper() or None),
            "lighting": (CCRS_LIGHT.get(light) or ("DARK - STREET LIGHTS" if light.startswith("Dark -") else
                                                    light.upper() or None)),
            "weather": (word(a.get("Weather")) or "").upper() or None,
            "surface": (word(a.get("CURdCond")) or "").upper() or None,
            "route": word(a.get("Route")), "milepost": a.get("Milepost"), "shifted_row": shifted(raw)}


def _get(where: str, last: int, opener) -> list[dict]:
    q = {"where": f"({where}) AND OBJECTID>{last}", "outFields": ",".join(FIELDS), "orderByFields": "OBJECTID",
         "resultRecordCount": PAGE, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(LAYER + "/query", data=urllib.parse.urlencode(q).encode(),
                                 headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=300) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"CARE eCrash query error: {body['error']}")
    return [f["attributes"] for f in body.get("features", [])]


def fetch_raw(where: str, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every row matching an ArcGIS `where`, paged by OBJECTID; cached as raw JSON per `where` when cache_dir is given."""
    cache = cache_dir / f"al_care_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json" if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    raw, last = [], 0
    while True:
        batch = _get(where, last, opener)
        raw += batch
        if len(batch) < PAGE:
            break
        last = batch[-1]["OBJECTID"]
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return raw


def year_where(years: list[int]) -> str:
    """Normal rows carry the year in Year, shifted rows in County."""
    yrs = ", ".join(f"'{y}'" for y in years)
    return f"(Year IN ({yrs}) OR County IN ({yrs}))"


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years, plus the corridor counties' crashes with no
    point (14%; the app places those from their street names)."""
    s, w, n, e = box
    yw = year_where(years)
    raw = fetch_raw(f"Latitude >= {s:.6f} AND Latitude <= {n:.6f} AND Longitude >= {w:.6f} "
                    f"AND Longitude <= {e:.6f} AND {yw}", cache_dir, opener)
    # CARE writes "St Clair" and "Dekalb"; the layer's text compare ignores case, so drop the dots only
    cn = ", ".join(f"'{NAME[f].replace('.', '')}'" for f in county_fips if f in NAME)
    if cn:
        raw += fetch_raw(f"(Latitude IS NULL OR Latitude <= 0) AND {yw} AND (County IN ({cn}) OR "
                         f"NumMajInj IN ({cn}))", cache_dir, opener)
    rows = [contract_record(a) for a in raw]
    have = {r["year"] for r in rows}
    out = [r for r in rows if r["county_fips"] and r["severity"] and r["year"] in years]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "shifted_rows_repaired": sum(r["shifted_row"] for r in rows),
                         "no_county": sum(not r["county_fips"] for r in rows),
                         "no_severity": sum(not r["severity"] for r in rows)}}

