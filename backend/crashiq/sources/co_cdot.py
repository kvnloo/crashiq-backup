"""Colorado crash source: CDOT's Statewide Crash Data Listing, one Excel file per year, no login.

CDOT's crash-data page (LISTING_PAGE) links each year's listing as an OnBase "DocPop" document on oitco.hylandcloud.com,
served to anonymous visitors. One row per crash: CDOT's crash id (CUID), GPS (about 98% in 2024), the reported street
pair (Location 1 / Link / Location 2: "W 38TH AVE" AT "KIPLING ST", or 201 ft north of it as Link "00201FN"), city,
county, system (City Street, County Road, State Highway, Interstate Highway, Frontage Road), crash type, light, weather,
road condition, the first two traffic units' vehicle and non-motorist types, and the count of people at each KABCO
level (Injury 00 = O ... Injury 04 = K). Crash severity is the worst person's level.

Read here: the 2021-on layout (110 columns, data dictionary 2021-2026). 2007-2020 use another layout (84 columns, no
CUID) and aren't read yet; those years come back in `years_missing`.

Each year's file (~50 MB) is downloaded once, reduced to the columns below and cached as gzip JSON; the Excel file is
deleted. Licence: CDOT's page says only that the listings are "protected under 23 U.S.C. Section 407"; no reuse
grant (research_notes/co-2026-11-08/co-import.md). Wired into the app through statepacks/co.py.
"""

from __future__ import annotations

import gzip
import http.cookiejar
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

from crashiq.packs import REF

LISTING_PAGE = "https://www.codot.gov/safety/traffic-safety/data-analysis/crash-data"
ONBASE = "https://oitco.hylandcloud.com/cdotrmpop"
APPGUID = "7e6ad004-ac77-4ade-9b3f-3590b83c6d78"     # OnBase's public DocPop app id, set by its own page script
FIRST_YEAR = 2021                                     # first year in the layout read here
CO_LAT, CO_LON = (36.9, 41.1), (-109.1, -102.0)      # Colorado with a small margin
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) CrashIQ/0.1"

KEEP = ("CUID", "System Code", "Rd_Number", "Rd_Section", "Crash Date", "Crash Time", "Agency Id", "City", "County",
        "Latitude", "Longitude", "Location 1", "Link", "Location 2", "Road Description", "Crash Type", "MHE",
        "Number Killed", "Number Injured", "Injury 00", "Injury 01", "Injury 02", "Injury 03", "Injury 04",
        "Total Vehicles", "Road Condition", "Lighting Conditions", "Weather Condition", "TU-1 Type", "TU-2 Type",
        "TU-1 NM Type", "TU-2 NM Type", "TU-1 Hit And Run", "TU-2 Hit And Run", "TU-1 Alcohol Suspected",
        "TU-2 Alcohol Suspected", "Record Status", "Processing Status")

_boxes = json.loads((REF / "county_boxes_co.json").read_text())
FIPS = {v["name"].removesuffix(" County").upper(): k for k, v in _boxes["counties"].items()}

# CDOT crash type -> the CCRS words the profile and the collision diagram read; others keep CDOT's words, upper case
CCRS_TYPE = {"Rear-End": "REAR END", "Broadside": "BROADSIDE", "Approach Turn": "BROADSIDE",
             "Overtaking Turn": "SIDE SWIPE", "Sideswipe Same Direction": "SIDE SWIPE",
             "Sideswipe Opposite Direction": "SIDE SWIPE", "Head-On": "HEAD-ON", "Overturning/Rollover": "OVERTURNED",
             "Pedestrian": "VEHICLE/PEDESTRIAN"}
OBJECT = ("Fence", "Sign", "Curb", "Concrete Highway Barrier", "Light Pole/Utility Pole", "Guardrail Face",
          "Embankment", "Tree", "Ditch", "Large Rocks or Boulder", "Other Fixed Object (Describe in Narrative)",
          "Cable Rail", "Guardrail End", "Wall or Building", "Traffic Signal Pole", "Electical/Utility Box",
          "Bridge Structure", "Culvert", "Mailbox", "Delineator/Milepost", "Crash Cushion/Traffic Barrel",
          "Barricade", "Bridge Rail", "Bridge Pier or Abutment", "Fire Hydrant", "Rock Fall/Landslide")
TRUCK = ("Medium/Heavy Trucks, GVWR/GCWR 16,001 or over", "Medium/Heavy Trucks, GVWR/GCWR 10,001 or Over")
LINK_FT = re.compile(r"^(\d+)F([NSEW])$")
LINK_MI = re.compile(r"^(\d*\.?\d+)M([NSEW])$")
LINK_DIR = re.compile(r"^J?([NSEW])/?O$")            # "SO", "S/O", "JSO": south of, no distance


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and CO_LAT[0] <= lat <= CO_LAT[1] and CO_LON[0] <= lon <= CO_LON[1])


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v) -> int:
    return int(_num(v) or 0)


def offset(link: str | None) -> tuple[float | None, str | None]:
    """CDOT's Link field -> (feet, N/S/E/W) from Location 2; (None, None) for AT, NEAR, FROM and diagonals."""
    s = (link or "").strip().upper()
    if m := LINK_FT.match(s):
        return float(m.group(1)), m.group(2)
    if m := LINK_MI.match(s):
        return round(float(m.group(1)) * 5280), m.group(2)
    if m := LINK_DIR.match(s):
        return None, m.group(1)
    return None, None


def severity(a: dict) -> str | None:
    """Worst person's KABCO level from CDOT's per-level counts (Injury 04 = K ... Injury 00 = O)."""
    if _int(a.get("Injury 04")) or _int(a.get("Number Killed")):
        return "K"
    for col, sev in (("Injury 03", "A"), ("Injury 02", "B"), ("Injury 01", "C")):
        if _int(a.get(col)):
            return sev
    if _int(a.get("Number Injured")):
        return "U"                              # injured count with no level (not seen in 2021-2024)
    return "O" if a.get("Injury 00") is not None else None


def contract_record(a: dict, preliminary: bool = False) -> dict:
    """One listing row (KEEP columns) -> the shared crash dict (packs.check_crash)."""
    s = lambda v: (str(v).strip() or None) if v is not None else None                  # noqa: E731
    lat, lon = _num(a.get("Latitude")), _num(a.get("Longitude"))
    has = plausible(lat, lon)
    d = a.get("Crash Date")
    d = date.fromisoformat(d[:10]) if isinstance(d, str) else (d.date() if isinstance(d, datetime) else d)
    hour = int(t[:2]) if (t := s(a.get("Crash Time"))) and t[:2].isdigit() else None
    sev = severity(a)
    loc2 = s(a.get("Location 2"))
    ft, dr = offset(a.get("Link"))
    if loc2 and loc2.upper().startswith("MM "):                 # state-highway mile marker, not a cross street
        loc2, ft, dr = None, None, None
    tu = {s(a.get("TU-1 Type")), s(a.get("TU-2 Type"))}
    nm = {s(a.get("TU-1 NM Type")), s(a.get("TU-2 NM Type"))}
    ctype = s(a.get("Crash Type"))
    county = s(a.get("County"))
    return {"crash_id": str(a["CUID"]), "report_version": 0, "deleted": False, "preliminary": preliminary,
            "date": d.isoformat() if d else "", "year": d.year if d else None, "hour": hour,
            "day_of_week": d.strftime("%A") if d else None,
            "lat": lat if has else None, "lon": lon if has else None,
            "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
            "primary_road": s(a.get("Location 1")), "secondary_road": loc2, "offset_ft": ft, "offset_dir": dr,
            "city": s(a.get("City")) or "UNINCORPORATED", "county_code": county,
            "county_fips": FIPS.get((county or "").upper()), "state": "CO",
            "is_freeway": s(a.get("System Code")) == "Interstate Highway",
            "killed": max(_int(a.get("Number Killed")), _int(a.get("Injury 04")), int(sev == "K")),
            "injured": max(_int(a.get("Number Injured")), sum(_int(a.get(f"Injury 0{i}")) for i in (1, 2, 3)),
                           int(sev in ("A", "B", "C", "U"))),
            "severity": sev,
            "ped": ctype == "Pedestrian" or bool(nm & {"Pedestrian", "Other Pedestrian", "Wheelchair"}),
            "bike": ctype == "Bicycle/Motorized Bicycle" or bool(nm & {"Bicyclist", "Other Bicyclist/Cyclist"}),
            "ebike": False, "escooter": "Scooter" in nm, "motorcycle": "Motorcycle" in tu,
            "heavy_truck": bool(tu & set(TRUCK)), "parties": [],
            "collision_type": (CCRS_TYPE.get(ctype) or ("VEHICLE/PEDESTRIAN" if ctype == "Bicycle/Motorized Bicycle"
                               else "HIT OBJECT" if ctype in OBJECT else ctype.upper() if ctype else None)),
            "lighting": s(a.get("Lighting Conditions")), "weather": s(a.get("Weather Condition")),
            "surface": s(a.get("Road Condition")), "agency": s(a.get("Agency Id")),
            "hit_run": a.get("TU-1 Hit And Run") is True or a.get("TU-2 Hit And Run") is True,
            "report_number": None, "route_id": s(a.get("Rd_Number")) if s(a.get("System Code")) != "City Street" else None,
            "road_description": s(a.get("Road Description")),
            "alcohol_suspected": any((s(a.get(f"TU-{i} Alcohol Suspected")) or "").startswith("Yes") for i in (1, 2))}


# -- download ------------------------------------------------------------------------------------------------------
def docids(opener=urllib.request.urlopen) -> dict[int, str]:
    """{year: OnBase docid} from the links on CDOT's crash-data page (link text ' 2024', a space or a no-break one)."""
    req = urllib.request.Request(LISTING_PAGE, headers={"User-Agent": UA})
    with opener(req, timeout=60) as r:
        page = r.read().decode("utf-8", "replace")
    return {int(y): d for d, y in re.findall(r'docid=(\d+)"[^>]*?text="\s?(\d{4})"', page)}


def download(docid: str, out: Path) -> None:
    """One DocPop document to a file: docpop -> PdfPop (form post, OBToken) -> ViewDocumentEx -> the file itself.
    Anonymous; the steps are OnBase's own page flow (scratch notes in research_notes/co-2026-11-08/co-import.md)."""
    cj = http.cookiejar.CookieJar()
    cj.set_cookie(http.cookiejar.Cookie(0, "appguid", APPGUID, None, False, "oitco.hylandcloud.com", False, False,
                                        "/", True, True, None, False, None, None, {}))
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA)]

    def get(url, data=None, ref=None, to=None):
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None)
        if ref:
            req.add_header("Referer", ref)
        with op.open(req, timeout=900) as r:
            if to is None:
                return r.read().decode("utf-8", "replace")
            with open(to, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)

    h = get(f"{ONBASE}/docpop/docpop.aspx?clienttype=html&docid={docid}")
    form = dict(re.findall(r'name="([^"]+)"[^>]*value="([^"]*)"', h))
    form.update(languageParam="en-US", darkmode="false", contentmode="false", browserIdentifier="x1")
    tok = re.findall(r'id="OBToken" value="([^"]+)"', get(f"{ONBASE}/docpop/PdfPop.aspx", form))
    if not tok:     # OnBase served its Sign In page instead of the anonymous viewer (seen 2026-11-08 after 4 downloads)
        raise RuntimeError(f"CDOT listing {docid}: OnBase asked for a sign-in instead of serving the file")
    tok = tok[-1]
    h = get(f"{ONBASE}/docpop/PdfPop.aspx", dict(clienttype="html", docid=docid, contentmode="false",
                                                  shouldInitializeDesktopHost="True", fromLogin="", OBToken=tok))
    dsc = re.search(r'(https://[^"]+DocumentSelectContainer\.aspx[^"]+)', h).group(1)
    get(dsc)
    view = f"{ONBASE}/ViewDocumentEx.aspx?OBToken={tok}&docid={docid}"
    p = json.loads(re.search(r"window.initializationParams = (\{.*?\});", get(view, ref=dsc)).group(1))
    get(p["startframesrc"] + p["endframesrc"] + f"&OBToken={tok}" + p["fileextensionsrc"], ref=view, to=out)
    if out.read_bytes()[:2] != b"PK":
        raise RuntimeError(f"CDOT listing {docid}: OnBase sent something other than an Excel file")


def read_xlsx(path: Path) -> list[dict]:
    """The KEEP columns of every row (streamed; ~100k rows, ~1.5 min a year)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    rows = wb.worksheets[0].iter_rows(values_only=True)
    head = [" ".join(str(h).split()) if h is not None else "" for h in next(rows)]
    if "CUID" not in head:
        raise ValueError(f"{path.name}: not the 2021-on CDOT layout (no CUID column)")
    ix = {k: head.index(k) for k in KEEP if k in head}
    out = []
    for r in rows:
        if r[ix["CUID"]] is None:
            continue
        a = {k: r[i] for k, i in ix.items()}
        if isinstance(a.get("Crash Date"), datetime):
            a["Crash Date"] = a["Crash Date"].date().isoformat()
        out.append(a)
    wb.close()
    return out


def year_rows(year: int, docid: str, cache_dir: Path) -> list[dict]:
    """A year's reduced rows, from cache (keyed by docid: a re-issued listing gets a new download)."""
    cache = cache_dir / f"co_cdot_{year}_{docid}.json.gz"
    if cache.exists():
        return json.loads(gzip.decompress(cache.read_bytes()))
    cache_dir.mkdir(parents=True, exist_ok=True)
    xlsx = cache_dir / f"co_cdot_{year}_{docid}.xlsx"
    try:
        if not xlsx.exists():
            download(docid, xlsx)
        rows = read_xlsx(xlsx)
        cache.write_bytes(gzip.compress(json.dumps(rows, default=str).encode()))
    finally:
        xlsx.unlink(missing_ok=True)
    return rows


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, ids: dict | None = None) -> dict:
    """Every crash with GPS in the box, plus every crash without usable GPS in those counties, in those years.
    Years before 2021 or not on CDOT's page are missing; the newest listed year is preliminary (CDOT's words)."""
    ids = docids() if ids is None else ids
    s, w, n, e = box
    newest = max(ids)
    out, cleaning, missing = [], {"source_rows": 0, "no_county": 0, "no_severity": 0, "no_gps_kept": 0}, []
    for y in years:
        if y < FIRST_YEAR or y not in ids:
            missing.append(y)
            continue
        try:
            rows = year_rows(y, ids[y], cache_dir)
        except (OSError, RuntimeError) as e:          # a year that won't download is missing, never half-counted
            missing.append(y)
            cleaning.setdefault("download_failed", {})[y] = str(e)[:200]
            continue
        for a in rows:
            cleaning["source_rows"] += 1
            c = contract_record(a, preliminary=y == newest)
            if not c["county_fips"]:
                cleaning["no_county"] += 1
                continue
            if not c["severity"]:
                cleaning["no_severity"] += 1
                continue
            if c["lat"] is not None:
                if s <= c["lat"] <= n and w <= c["lon"] <= e:
                    out.append(c)
            elif c["county_fips"] in county_fips:
                cleaning["no_gps_kept"] += 1
                out.append(c)
    return {"crashes": out, "years_missing": missing, "cleaning": cleaning}
