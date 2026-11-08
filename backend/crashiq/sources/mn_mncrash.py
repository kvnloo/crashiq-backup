"""Minnesota crash source: DPS MNCrash Public Crash Data Portal (mncrash.state.mn.us, "Analyze Data"), no login.

One row per crash, 2016 to now (the current year is preliminary), from Minnesota's statutory crash system of
record. The portal is an ASP.NET WebForms page (EasyQuery): there is no API, so the reader does what a person does
with the browser, in four postbacks: date operator "custom period", the map rectangle (NAD83 / UTM 15N, EPSG:26915)
plus the two dates, Search, then Export as CSV (a zip with one CSV). The export has 17 columns: ACN (crash id),
Local ID, Crash Date (local time), Roadway (officer text, "HENNEPIN AVE  at 9TH ST N" / "... near ..."), City,
Township, County, Tribal Nation, Agency, Crash Severity (KABCO words), Number of Fatalities, Number of Injuries,
Latitude, Longitude, and alcohol / distraction / speed flags. It has no crash type, light, weather, surface or
road-user details (research_notes/mn-2026-11-08/mn-import.md).

The portal sends its certificate without the Sectigo intermediate, so the reader adds that one public CA
certificate to the default trust store (verification stays on).

Licence: no licence or terms of use on the portal; public data under the Minnesota Government Data Practices Act
(Minn. Stat. ch. 13; crash reports Minn. Stat. 169.09). Read through the MN state pack (statepacks/mn.py, #19).
"""

from __future__ import annotations

import csv
import hashlib
import html
import http.cookiejar
import io
import json
import math
import re
import ssl
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

URL = "https://mncrash.state.mn.us/Pages/AdHocSearch.aspx"
MN_LAT, MN_LON = (43.4, 49.5), (-97.3, -89.4)      # Minnesota's extent with a small margin
SEVERITY_ORDER = "KABCUO"
SEVERITY = {"Fatal Crash": "K", "Suspected Serious Injury Crash": "A", "Suspected Minor Injury Crash": "B",
            "Possible Injury Crash": "C", "Property Damage Only Crash": "O"}
COLUMNS = 17                                        # the export's header width
ROADWAY = 3                                         # the one free-text column; an unquoted comma there splits it
# DATE_ROW: the query panel's one standing condition, "Crash Date of Crash (Required)"; e2 = its operator,
# operator 7 = "custom period", e3 / e5 = the from / to date boxes
DATE_OP, CUSTOM_PERIOD = "ctl00$ContentPlaceHolder$QueryPanel1$r1$e2", "7"
DATE_FROM = "ContentPlaceHolder_QueryPanel1_r1_e3_DatePanel_textbox"
DATE_TO = "ContentPlaceHolder_QueryPanel1_r1_e5_DatePanel_textbox"
MAP_ADD, MAP_FIELD = "ctl00$ContentPlaceHolder$lbAddMapCriteria", "ctl00$ContentPlaceHolder$hdnMapCriteria"
# lblErr also carries this harmless note on any result over 1,000 rows; anything else there is a failure
NOTE_OK = "Please note"

# Sectigo Public Server Authentication CA EV E36 (issuer of mncrash.state.mn.us; valid to 2036-03-21; SHA-256
# FD:91:7B:0D:09:4F:AA:4D:B1:BB:AF:9E:D7:AC:55:BE:51:62:D9:71:C2:27:B3:4E:70:85:CA:53:7A:4A:4B:47), from
# http://crt.sectigo.com/SectigoPublicServerAuthenticationCAEVE36.crt
SECTIGO_E36 = """-----BEGIN CERTIFICATE-----
MIIDXjCCAuWgAwIBAgIQdfCDfT4iwr52uKvBJaBGbDAKBggqhkjOPQQDAzBfMQsw
CQYDVQQGEwJHQjEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMTYwNAYDVQQDEy1T
ZWN0aWdvIFB1YmxpYyBTZXJ2ZXIgQXV0aGVudGljYXRpb24gUm9vdCBFNDYwHhcN
MjEwMzIyMDAwMDAwWhcNMzYwMzIxMjM1OTU5WjBgMQswCQYDVQQGEwJHQjEYMBYG
A1UEChMPU2VjdGlnbyBMaW1pdGVkMTcwNQYDVQQDEy5TZWN0aWdvIFB1YmxpYyBT
ZXJ2ZXIgQXV0aGVudGljYXRpb24gQ0EgRVYgRTM2MFkwEwYHKoZIzj0CAQYIKoZI
zj0DAQcDQgAEIclecB70mupDsxx5Q+pE94vB8/gMU8oIh9y7pEQ6c0QxbPhINFQ/
/AaiQBw60d9K1wMMhqy/QRkJy8MiywuslaOCAYAwggF8MB8GA1UdIwQYMBaAFNEi
2kxZ8UtfJjiqndbu6w3D+6lhMB0GA1UdDgQWBBTicWbHOuUGtl2bQQoVai3FseY3
dDAOBgNVHQ8BAf8EBAMCAYYwEgYDVR0TAQH/BAgwBgEB/wIBADAdBgNVHSUEFjAU
BggrBgEFBQcDAQYIKwYBBQUHAwIwGgYDVR0gBBMwETAGBgRVHSAAMAcGBWeBDAEB
MFQGA1UdHwRNMEswSaBHoEWGQ2h0dHA6Ly9jcmwuc2VjdGlnby5jb20vU2VjdGln
b1B1YmxpY1NlcnZlckF1dGhlbnRpY2F0aW9uUm9vdEU0Ni5jcmwwgYQGCCsGAQUF
BwEBBHgwdjBPBggrBgEFBQcwAoZDaHR0cDovL2NydC5zZWN0aWdvLmNvbS9TZWN0
aWdvUHVibGljU2VydmVyQXV0aGVudGljYXRpb25Sb290RTQ2LnA3YzAjBggrBgEF
BQcwAYYXaHR0cDovL29jc3Auc2VjdGlnby5jb20wCgYIKoZIzj0EAwMDZwAwZAIw
VtVm5z312gdibMeVJaC/LfWrobVfLPCiT0aXGrfMg/jc/9k+i1obrebeCiZtSnGO
AjAyI28uokQqX0U3YJym7XbDb13u5EiUEJk2DQnoYyVUTr28vG1V+wPuBVCqOMi/
Ov8=
-----END CERTIFICATE-----
"""

# Minnesota's 87 counties as MNCrash names them -> FIPS (Census, alphabetical, odd numbers 001-173)
COUNTIES = [
    "Aitkin", "Anoka", "Becker", "Beltrami", "Benton", "Big Stone", "Blue Earth", "Brown", "Carlton", "Carver",
    "Cass", "Chippewa", "Chisago", "Clay", "Clearwater", "Cook", "Cottonwood", "Crow Wing", "Dakota", "Dodge",
    "Douglas", "Faribault", "Fillmore", "Freeborn", "Goodhue", "Grant", "Hennepin", "Houston", "Hubbard", "Isanti",
    "Itasca", "Jackson", "Kanabec", "Kandiyohi", "Kittson", "Koochiching", "Lac qui Parle", "Lake",
    "Lake of the Woods", "Le Sueur", "Lincoln", "Lyon", "McLeod", "Mahnomen", "Marshall", "Martin", "Meeker",
    "Mille Lacs", "Morrison", "Mower", "Murray", "Nicollet", "Nobles", "Norman", "Olmsted", "Otter Tail",
    "Pennington", "Pine", "Pipestone", "Polk", "Pope", "Ramsey", "Red Lake", "Redwood", "Renville", "Rice", "Rock",
    "Roseau", "St. Louis", "Scott", "Sherburne", "Sibley", "Stearns", "Steele", "Stevens", "Swift", "Todd",
    "Traverse", "Wabasha", "Wadena", "Waseca", "Washington", "Watonwan", "Wilkin", "Winona", "Wright",
    "Yellow Medicine"]
FIPS = {n.upper(): f"27{2 * i + 1:03d}" for i, n in enumerate(COUNTIES)}
FIPS["SAINT LOUIS"] = FIPS["ST LOUIS"] = FIPS["ST. LOUIS"]
# "HENNEPIN AVE  at 9TH ST N", "MNTH 65  near 496TH", "ISTH 694 EB @ VICTORIA AVE": street, then the cross street
PAIR = re.compile(r"\s+(?:at|AT|near|NEAR|@)\s+|\s*@\s*")
# MnDOT route codes -> the names TIGER/OSM carry, so the shared street matcher (names.street_key) reads them:
# ISTH 94 = I-94, USTH 169 = US Hwy 169, MNTH 13 = State Hwy 13, CSAH 81 / CR 81 = Co Rd 81 (TIGER's form)
ROUTES = [(re.compile(r"\bISTH\s*-?\s*(?=\d)"), "I-"), (re.compile(r"\bUSTH\s*-?\s*(?=\d)"), "US HWY "),
          (re.compile(r"\bMNTH\s*-?\s*(?=\d)"), "STATE HWY "),
          (re.compile(r"\b(?:CSAH|CR|CNTY RD|COUNTY RD|COUNTY ROAD)\s*-?\s*(?=\d)"), "CO RD ")]
BOUND = re.compile(r"^(?:NB|SB|EB|WB)\s+")
FREEWAY = re.compile(r"^(?:(?:NB|SB|EB|WB)\s*)?(?:ISTH|I-|I |INTERSTATE)\s*\d")   # Interstates only: MNCrash gives no road class


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and MN_LAT[0] <= lat <= MN_LAT[1] and MN_LON[0] <= lon <= MN_LON[1])


def utm15(lat: float, lon: float) -> tuple[float, float]:
    """Lat/lon (NAD83 ~ WGS84 here) -> UTM zone 15N metres, Snyder's series (well under 1 m inside Minnesota)."""
    a, f, k0 = 6378137.0, 1 / 298.257222101, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    phi, lam = math.radians(lat), math.radians(lon + 93.0)
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    t, c, A = math.tan(phi) ** 2, ep2 * math.cos(phi) ** 2, math.cos(phi) * lam
    m = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi)
             - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    x = k0 * n * (A + (1 - t + c) * A ** 3 / 6 + (5 - 18 * t + t * t + 72 * c - 58 * ep2) * A ** 5 / 120) + 500000.0
    y = k0 * (m + n * math.tan(phi) * (A * A / 2 + (5 - t + 9 * c + 4 * c * c) * A ** 4 / 24
                                        + (61 - 58 * t + t * t + 600 * c - 330 * ep2) * A ** 6 / 720))
    return x, y


def extent(box) -> dict:
    """The (s, w, n, e) box as the portal's map rectangle: UTM 15N, covering all four corners."""
    s, w, n, e = box
    xs, ys = zip(*(utm15(la, lo) for la in (s, n) for lo in (w, e)))
    return {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys), "spatialReference": {"wkid": 26915}}


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def severity(sev: str, killed: int, injured: int) -> str:
    """MNCrash's KABCO word; a blank (about 2.7% of 2024) falls back to the counts: K if killed, U if injured, else O."""
    if sev in SEVERITY:
        return SEVERITY[sev]
    return "K" if killed else "U" if injured else "O"


def route_names(raw: str) -> str:
    raw = BOUND.sub("", raw)                            # "SB ISTH 35E": the direction is not part of the name
    for rx, name in ROUTES:
        raw = rx.sub(name, raw)
    return raw


def split_road(raw: str) -> tuple[str | None, str | None]:
    parts = [route_names(p.strip()) for p in PAIR.split(raw or "", maxsplit=1)]
    prim = parts[0] or None
    return prim, (parts[1] or None) if len(parts) > 1 else None


def rows(text: str) -> list[dict]:
    """The export CSV -> dicts by header. A Roadway with an unquoted comma (1 row of 63,643 in 2024) is joined back."""
    rd = csv.reader(io.StringIO(text.lstrip("\ufeff")))
    head = next(rd, None) or []
    out = []
    for r in rd:
        if not r:
            continue
        if len(r) > COLUMNS:
            extra = len(r) - COLUMNS
            r = r[:ROADWAY] + [",".join(r[ROADWAY:ROADWAY + extra + 1])] + r[ROADWAY + extra + 1:]
        out.append(dict(zip(head, r)))
    return out


def crash_record(a: dict) -> dict:
    """One export row -> the shared crash shape (the keys CCRS normalizes to)."""
    s = lambda v: (str(v).strip() or None) if v is not None else None
    lat, lon = _num(a.get("Latitude")), _num(a.get("Longitude"))
    has = plausible(lat, lon)
    try:
        dt = datetime.strptime((a.get("Crash Date") or "").strip(), "%m/%d/%Y %I:%M:%S %p")
    except ValueError:
        dt = None
    killed, injured = _int(a.get("Number of Fatalities")), _int(a.get("Number of Injuries"))
    reported = s(a.get("Crash Severity"))
    road = s(a.get("Roadway")) or ""
    prim, sec = split_road(road)
    county = (s(a.get("County")) or "").upper()
    return {
        "collision_id": s(a.get("ACN")),
        "report_number": s(a.get("Local ID")),
        "datetime": dt.strftime("%Y-%m-%dT%H:%M") if dt else None,
        "date": dt.date().isoformat() if dt else "",
        "year": dt.year if dt else None,
        "hour": dt.hour if dt else None,
        "lat": lat if has else None,
        "lon": lon if has else None,
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "road_text": road or None,
        "primary_road": prim,
        "secondary_road": sec,
        "city_name": s(a.get("City")),
        "township": s(a.get("Township")),
        "county_name": county or None,
        "county_fips": FIPS.get(county),
        "agency": s(a.get("Agency")),
        "killed": killed,
        "injured": injured,
        "severity": severity(reported or "", killed, injured),
        "severity_reported": reported,
        "severity_blank": reported not in SEVERITY,
        "is_freeway": bool(FREEWAY.match(road.upper())),
        "alcohol": s(a.get("Alcohol Related")) == "Yes",
        "distraction": s(a.get("Distraction Related")) == "Yes",
        "speed": s(a.get("Speed Related")) == "Yes",
    }


# -- the portal ---------------------------------------------------------------------------------------------------
def _opener():
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cadata=SECTIGO_E36)
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
                                     urllib.request.HTTPSHandler(context=ctx))
    return op.open


def _fields(page: str) -> dict:
    """What the browser posts for this form: hidden/text inputs, checked boxes ('on' without a value), textareas."""
    out = {"__LASTFOCUS": ""}
    for m in re.finditer(r"<input[^>]+>", page):
        t = m.group(0)
        name = re.search(r'name="([^"]+)"', t)
        typ = (re.search(r'type="([^"]+)"', t) or [None, "text"])[1]
        if not name or typ in ("submit", "image", "button") or (typ in ("checkbox", "radio") and "checked" not in t):
            continue
        val = re.search(r'value="([^"]*)"', t)
        out[html.unescape(name.group(1))] = html.unescape(val.group(1)) if val else ("on" if typ == "checkbox" else "")
    for m in re.finditer(r'<textarea[^>]*name="([^"]+)"[^>]*>(.*?)</textarea>', page, re.S):
        out[html.unescape(m.group(1))] = html.unescape(m.group(2)).lstrip("\r\n")
    return out


def _post(opener, page: str, target: str = "", extra: dict | None = None, arg: str = ""):
    f = {**_fields(page), "__EVENTTARGET": target, "__EVENTARGUMENT": arg, **(extra or {})}
    req = urllib.request.Request(URL, data=urllib.parse.urlencode(f).encode(), headers={"User-Agent": "CrashIQ/0.1"})
    return opener(req, timeout=300)


def _page(resp) -> str:
    page = resp.read().decode("utf-8", "replace")
    err = re.search(r'id="ContentPlaceHolder_lblErr"[^>]*>([^<]*)<', page)
    if err and err.group(1).strip() and not err.group(1).strip().startswith(NOTE_OK):
        raise RuntimeError(f"MNCrash portal: {html.unescape(err.group(1).strip())}")
    return page


def export(box, first: str, last: str, opener=None) -> str:
    """The CSV text of every crash with a point in the box between two MM/DD/YYYY dates (inclusive)."""
    opener = opener or _opener()
    ua = {"User-Agent": "CrashIQ/0.1"}
    page = _page(opener(urllib.request.Request(URL, headers=ua), timeout=120))
    page = _page(_post(opener, page, DATE_OP, arg=CUSTOM_PERIOD))
    page = _page(_post(opener, page, MAP_ADD, {DATE_FROM: first, DATE_TO: last, MAP_FIELD: json.dumps(extent(box))}))
    page = _page(_post(opener, page, extra={"ctl00$ContentPlaceHolder$btnSearch": "Search"}))
    resp = _post(opener, page, extra={"ctl00$ContentPlaceHolder$btnExport": "Export",
                                      "ctl00$ContentPlaceHolder$rdoListExportOptions": "CSV"})
    body = resp.read()
    if not body.startswith(b"PK"):
        _page(io.BytesIO(body))                         # raises with the portal's own message when it has one
        raise RuntimeError("MNCrash portal: the export did not return a zip")
    z = zipfile.ZipFile(io.BytesIO(body))
    return z.read(z.namelist()[0]).decode("utf-8-sig", "replace")


def fetch(box, years: list[int], cache_dir: Path | None = None, opener=None) -> list[dict]:
    """Every crash with a point in the box in those calendar years, normalized; the raw CSV cached per query."""
    first, last = f"01/01/{min(years)}", f"12/31/{max(years)}"
    key = hashlib.sha1(json.dumps([list(box), first, last]).encode()).hexdigest()[:10]
    cache = cache_dir / f"mn_mncrash_{key}.csv" if cache_dir else None
    if cache and cache.exists():
        text = cache.read_text()
    else:
        text = export(box, first, last, opener)
        if cache:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache.write_text(text)
    return [crash_record(a) for a in rows(text)]


# -- state-pack contract (#19, docs/state-pack-design.md § Reader contract) --------------------------------------
def contract_record(r: dict) -> dict:
    d = datetime.fromisoformat(r["date"]).date() if r["date"] else None
    return {"crash_id": r["collision_id"], "report_version": 0, "deleted": False,
            "preliminary": bool(d and d.year >= datetime.now().year),        # the current year is still coming in
            "date": r["date"], "year": r["year"], "hour": r["hour"], "day_of_week": d.strftime("%A") if d else None,
            "lat": r["lat"], "lon": r["lon"], "bad_coords": r["bad_coords"],
            "primary_road": r["primary_road"], "secondary_road": r["secondary_road"], "offset_ft": None,
            "offset_dir": None, "city": (r["city_name"] or "UNINCORPORATED").upper(), "county_code": r["county_name"],
            "county_fips": r["county_fips"], "state": "MN", "is_freeway": r["is_freeway"], "killed": r["killed"],
            "injured": r["injured"], "severity": r["severity"], "ped": False, "bike": False, "ebike": False,
            "escooter": False, "motorcycle": False, "heavy_truck": False, "parties": [], "collision_type": None,
            "agency": r["agency"], "report_number": r["report_number"], "lighting": None, "weather": None,
            "surface": None}


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=None) -> dict:
    """Every crash with a point in the box in those years. The portal's map search only sees crashes with a point:
    4 of 63,643 in 2024 have none (research 2026-11-08), so the no-GPS path reads nothing here."""
    got = fetch(box, years, cache_dir, opener)
    have = {r["year"] for r in got}
    out = [contract_record(r) for r in got if r["county_fips"] and r["year"] in years]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(got), "no_county": sum(not r["county_fips"] for r in got),
                         "severity_blank_from_counts": sum(r["severity_blank"] for r in got),
                         "no_gps_not_read": "4 of 63,643 statewide crashes (2024) have no point; not read"}}
