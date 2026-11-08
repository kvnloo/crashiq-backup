"""Oregon: ODOT Crash Data System (CDS), statewide, every public road. Open downloads, no login (checked 2026-11-07).

Two readers of the same CDS CRASH columns:
- `read_decode(crash_csv, partic_csv)`: the yearly Decode Database (crash, vehicle and participant tables, linked by
  CRASH_ID), from https://www.oregon.gov/odot/Data/Pages/CrashDataProducts.aspx
  (e.g. Crash Data Products/Statewide_Crashes_2024_DecodeDB.zip, an Access .mdb). Export its CRASH and PARTIC tables
  to CSV first, e.g. `mdb-export Statewide_Crashes_2024_Decode.mdb CRASH > CRASH.csv` (mdbtools). Per-person KABCO.
- `fetch_layer(where)`: ODOT's public ArcGIS layer behind the Oregon Transportation Safety Data Explorer, 2019-2024,
  crash level only (no participant table), with ODOT's own crash KABCO.
Field meanings: ODOT "Motor Vehicle Traffic Crash Analysis & Code Manual",
https://www.oregon.gov/odot/Data/documents/CDS_Code_Manual.pdf. The OR state pack (packs.py, #19) reads the ArcGIS layer through `fetch_contract`.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

LAYER = "https://gis.odot.state.or.us/arcgis1006/rest/services/agol/OTSDE_Crash/MapServer/0"
OR_LAT, OR_LON = (41.9, 46.3), (-124.8, -116.4)
SEVERITY_ORDER = "KABCUO"   # same as CCRS: U = injury crash with no person level coded, O = property damage only

# PARTIC.INJ_SVRTY_CD (code manual, injury severity): 1 K, 2 A, 3 B, 4 C, 9 no apparent injury, 7 no injury aged 0-4
# (retired 2018). 5 "died prior to crash" is not a crash injury.
INJ_KABCO = {"1": "K", "2": "A", "3": "B", "4": "C", "7": "O", "9": "O"}
COMPASS = {"1": "N", "2": "NE", "3": "E", "4": "SE", "5": "S", "6": "SW", "7": "W", "8": "NW"}  # 9 CN, 0 UN: none
# COLLIS_TYP_CD -> the layer's long text, so both readers give one vocabulary (decode DB lookup table COLLIS_TYP)
COLLISION = {"&": "Miscellaneous", "-": "Backing", "0": "Pedestrian", "1": "Angle", "2": "Head-On", "3": "Rear-End",
             "4": "Sideswipe - Meeting", "5": "Sideswipe - Overtaking", "6": "Turning Movement", "7": "Parking Maneuver",
             "8": "Non-collision", "9": "Fixed Object or Other Object"}
FREEWAY_FC = {"01", "02", "11", "12"}   # functional class: interstate, other freeway/expressway (rural, urban)
_HOUR = re.compile(r"^(\d{1,2}):\d{2}\s*([AP]M)", re.I)


def _s(v) -> str | None:
    return (str(v).strip() or None) if v is not None else None


def _num(v) -> float | None:
    try:
        return float(v) if _s(v) is not None else None
    except (TypeError, ValueError):
        return None


def _flag(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "t", "y", "yes")


def _g(r: dict, *names):
    """First present value: the decode DB and the ArcGIS layer name a few descriptions differently."""
    for n in names:
        if _s(r.get(n)) is not None:
            return r[n]
    return None


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and OR_LAT[0] <= lat <= OR_LAT[1] and OR_LON[0] <= lon <= OR_LON[1]


def _hour(r: dict) -> int | None:
    h = _num(r.get("CRASH_HR_NO"))
    if h is not None:
        return int(h) if 0 <= h <= 23 else None          # 99 = unknown
    m = _HOUR.match(str(r.get("CRASH_HR_LONG_DESC") or ""))
    return int(m[1]) % 12 + (12 if m[2].upper() == "PM" else 0) if m else None


def crash_record(r: dict) -> dict:
    """One CDS CRASH row (decode DB CSV or ArcGIS layer attributes) -> the shared crash shape, severity from counts."""
    y, mo, d = (int(_num(r.get(k)) or 0) for k in ("CRASH_YR_NO", "CRASH_MO_NO", "CRASH_DAY_NO"))
    lat, lon = _num(r.get("LAT_DD")), _num(r.get("LONGTD_DD"))
    unlocated = _flag(r.get("UNLOCT_FLG"))     # ODOT gives unlocatable crashes a default point; never use it
    has = not unlocated and plausible(lat, lon)
    primary = _s(r.get("ST_FULL_NM")) or _s(r.get("RECRE_RD_NM"))
    secondary = _s(r.get("ISECT_ST_FULL_NM")) or _s(r.get("ISECT_RECRE_RD_NM"))
    fc = _s(r.get("FC_CD"))
    counts = {k: int(_num(r.get(c)) or 0) for k, c in (("K", "TOT_FATAL_CNT"), ("A", "TOT_INJ_LVL_A_CNT"),
                                                       ("B", "TOT_INJ_LVL_B_CNT"), ("C", "TOT_INJ_LVL_C_CNT"))}
    injured = _num(r.get("TOT_INJ_CNT"))
    return {
        "crash_id": str(int(_num(r["CRASH_ID"]))),
        "date": f"{y:04d}-{mo:02d}-{d:02d}" if y and mo and d else "",
        "year": y or None,
        "hour": _hour(r),
        "lat": lat if has else None,
        "lon": lon if has else None,
        "unlocated": unlocated,
        "bad_coords": not unlocated and lat is not None and lon is not None and not has,
        "primary_road": primary,
        "secondary_road": secondary,
        "offset_ft": _num(r.get("FROM_ISECT_DSTNC_QTY")),
        "offset_dir": COMPASS.get(str(_s(r.get("CMPSS_DIR_CD")) or "")),
        "city": _s(r.get("CITY_SECT_NM")),               # city, or city section ("Portland NE")
        "county": _s(r.get("CNTY_NM")),
        "county_code": _s(r.get("CNTY_ID")),             # ODOT county number (1-36), decode DB only
        "route": _s(r.get("RTE_NM")),                    # e.g. I-205, OR-99E (state highways only)
        "highway_no": _s(r.get("HWY_NO")),
        "milepoint": _num(r.get("MP_NO")),
        "collision_type": _s(r.get("COLLIS_TYP_LONG_DESC")) or COLLISION.get(str(_s(r.get("COLLIS_TYP_CD")))),
        "killed": counts["K"],
        "injured": int(injured) if injured is not None else counts["A"] + counts["B"] + counts["C"],
        "severity_counts": counts,
        "lighting": _s(_g(r, "LGT_COND_LONG_DESC", "LGT_COND_SHORT_DESC")),
        "weather": _s(_g(r, "WTHR_COND_LONG_DESC", "WTHR_COND_SHORT_DESC")),
        "surface": _s(_g(r, "RD_SURF_MED_DESC", "RD_SURF_SHORT_DESC")),
        "hit_run": _flag(r.get("CRASH_HIT_RUN_FLG")),
        "is_freeway": fc in FREEWAY_FC if fc else bool(re.search(r"INTERSTATE|FREEWAY", str(r.get("FC_DESC") or ""))),
        "odot_kabco": _s(r.get("KABCO")),               # ArcGIS layer only
        "injury_crash": _s(r.get("CRASH_SVRTY_CD")) == "4" or _s(r.get("CRASH_SVRTY_LONG_DESC")) == "Non-Fatal Injury",
    }


def severity(crash: dict, persons: list[str | None]) -> str:
    """Most severe outcome: person KABCO, never below the crash's own K/A/B/C counts or ODOT's crash KABCO."""
    found = [k for k in persons if k] + [k for k, n in crash["severity_counts"].items() if n > 0]
    if crash.get("odot_kabco") in tuple(SEVERITY_ORDER):
        found.append(crash["odot_kabco"])
    best = min(found, key=SEVERITY_ORDER.index, default="O")
    return "U" if best == "O" and (crash["injured"] > 0 or crash["injury_crash"]) else best


def read_decode(crash_csv: Path, partic_csv: Path) -> list[dict]:
    """Every crash of a decode-DB year, with `persons` (one KABCO letter or None per participant) and `severity`."""
    persons: dict[str, list] = defaultdict(list)
    with open(partic_csv, newline="", encoding="utf-8-sig") as f:
        for p in csv.DictReader(f):
            persons[str(int(_num(p["CRASH_ID"])))].append(INJ_KABCO.get(str(_s(p.get("INJ_SVRTY_CD")) or "")))
    out = []
    with open(crash_csv, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            c = crash_record(r)
            c["persons"] = persons.get(c["crash_id"], [])
            c["severity"] = severity(c, c["persons"])
            out.append(c)
    return out


def _post(url: str, params: dict) -> dict:
    import httpx
    resp = httpx.post(url, data=params, headers={"User-Agent": "CrashIQ/0.1"}, timeout=120)  # id lists outgrow a GET URL
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:                    # ArcGIS reports query errors with HTTP 200
        raise RuntimeError(f"ODOT layer error: {body['error']}")
    return body


def fetch_layer(where: str, get=None, page: int = 2000) -> list[dict]:
    """Crashes on the public ArcGIS layer matching a SQL `where` (e.g. "CRASH_YR_NO='2024' AND CNTY_NM='Multnomah'"),
    paged by object id. `get(url, params) -> dict` is injectable for tests; default httpx with CrashIQ's user agent."""
    get = get or _post
    ids = sorted(get(LAYER + "/query", {"where": where, "returnIdsOnly": "true", "f": "json"})["objectIds"] or [])
    out = []
    for i in range(0, len(ids), page):
        body = get(LAYER + "/query", {"objectIds": ",".join(map(str, ids[i:i + page])), "outFields": "*",
                                      "returnGeometry": "false", "f": "json"})
        for feat in body["features"]:
            c = crash_record(feat["attributes"])
            c["persons"] = []
            c["severity"] = severity(c, [])
            out.append(c)
    return out


# -- state-pack contract (#19): the public ArcGIS layer, 2019-2024 (the yearly Access .mdb files need mdbtools) -----
LAYER_YEARS = range(2019, 2025)
CCRS_TYPE = {"REAR-END": "REAR END", "ANGLE": "BROADSIDE", "HEAD-ON": "HEAD-ON", "SIDESWIPE - MEETING": "SIDE SWIPE",
             "SIDESWIPE - OVERTAKING": "SIDE SWIPE", "PEDESTRIAN": "VEHICLE/PEDESTRIAN",
             "FIXED OBJECT OR OTHER OBJECT": "HIT OBJECT"}
CCRS_LIGHT = {"DARKNESS - WITH STREET LIGHTS": "DARK - STREET LIGHTS", "DARKNESS - NO STREET LIGHTS": "DARK - NO STREET LIGHTS"}


def contract_record(c: dict, a: dict, fips_by_county: dict[str, str]) -> dict:
    """One crash_record() (with its layer attributes `a`) -> the shared crash dict (packs.check_crash)."""
    import datetime as _dt
    up = lambda v: str(v).upper() if v else None
    d = _dt.date.fromisoformat(c["date"]) if c["date"] else None
    return {"crash_id": c["crash_id"], "report_version": 0, "deleted": False, "preliminary": False,
            "date": c["date"], "year": c["year"], "hour": c["hour"], "day_of_week": d.strftime("%A") if d else None,
            "lat": c["lat"], "lon": c["lon"], "bad_coords": c["bad_coords"], "primary_road": c["primary_road"],
            "secondary_road": c["secondary_road"], "offset_ft": c["offset_ft"] or None, "offset_dir": c["offset_dir"],
            "city": up(c["city"]), "county_code": c["county"],
            "county_fips": fips_by_county.get((c["county"] or "").upper()), "state": "OR",
            "is_freeway": c["is_freeway"], "killed": c["killed"], "injured": c["injured"], "severity": c["severity"],
            "ped": str(a.get("Ped_Pres_Flg")) == "1", "bike": str(a.get("Bike_Pres_Flg")) == "1", "ebike": False,
            "escooter": False, "motorcycle": str(a.get("MTCL_Flg")) == "1", "heavy_truck": bool(a.get("HeavyTruck")),
            "parties": [], "collision_type": CCRS_TYPE.get(up(c["collision_type"]) or "", up(c["collision_type"])),
            "lighting": CCRS_LIGHT.get(up(c["lighting"]) or "", up(c["lighting"])), "weather": up(c["weather"]),
            "surface": up(c["surface"]), "route": c["route"], "milepoint": c["milepoint"]}


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, boxes: dict, get=None) -> dict:
    """Crashes on the layer with a point in the box, plus the unlocated ones (ODOT's default point, dropped) in the
    corridor's counties; years outside 2019-2024 are missing (the layer has no others)."""
    import hashlib
    import json
    s, w, n, e = box
    names = {f: v["name"].removesuffix(" County") for f, v in boxes.items()}
    fips_by_county = {v.upper(): k for k, v in names.items()}
    yrs = [y for y in years if y in LAYER_YEARS]
    if not yrs:
        return {"crashes": [], "years_missing": list(years), "cleaning": {}}
    area = ", ".join(f"'{names[f]}'" for f in county_fips if f in names) or "''"
    where = (f"CRASH_YR_NO IN ({', '.join(repr(str(y)) for y in yrs)}) AND ((LAT_DD >= {s:.6f} AND LAT_DD <= {n:.6f} "
             f"AND LONGTD_DD >= {w:.6f} AND LONGTD_DD <= {e:.6f}) OR (UNLOCT_FLG = 1 AND CNTY_NM IN ({area})))")
    cache = cache_dir / f"or_odot_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json"
    if cache.exists():
        rows = json.loads(cache.read_text())
    else:
        rows = _attributes(where, get or _post)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows))
    out = []
    for a in rows:
        c = crash_record(a)
        c["severity"] = severity(c, [])
        out.append(contract_record(c, a, fips_by_county))
    have = {c["year"] for c in out}
    return {"crashes": [c for c in out if c["county_fips"]], "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "unlocated": sum(1 for c in out if c["lat"] is None),
                         "layer_years": f"{LAYER_YEARS.start}-{LAYER_YEARS.stop - 1}"}}


def _attributes(where: str, get, page: int = 2000) -> list[dict]:
    ids = sorted(get(LAYER + "/query", {"where": where, "returnIdsOnly": "true", "f": "json"})["objectIds"] or [])
    out = []
    for i in range(0, len(ids), page):
        body = get(LAYER + "/query", {"objectIds": ",".join(map(str, ids[i:i + page])), "outFields": "*",
                                      "returnGeometry": "false", "f": "json"})
        out += [f["attributes"] for f in body["features"]]
    return out
