"""Virginia crash source: VDOT "Full Crash" on Virginia Roads (DMV TREDS data), an open ArcGIS layer, no login.

One row per crash, 2017 to now (preliminary for the latest months), VDOT-located GPS on all but about 60 of 1.18M
crashes, crash-level KABCO (CRASH_SEVERITY) and per-crash counts of K, A, B and C people. There is ONE street field
(ROUTE_OR_STREET_NM, the officer's text) and no cross street, so `secondary_road` is always None; the VDOT LRS
route, milepost, node and node offset are kept as they are. Codes are decoded with the maps measured in
research_notes/va-2026-11-07 (VDOT codes joined to the DMV datathon's text, 16,693 crashes, every code 100% one text).

Licence: no open licence; VDOT's disclaimer, 23 USC 407 and DPPA terms apply (see va-import.md). Wired into the app
through the VA state pack (packs.py, #19) by `fetch_contract`.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import from_epoch

LAYER = "https://services.arcgis.com/p5v98VHDX9Atv3l7/arcgis/rest/services/Full_Crash/FeatureServer/0"
PAGE = 2000                                    # the layer's maxRecordCount
SEVERITY_ORDER = "KABCUO"                      # same order as CCRS: U = injured, level not reported
VA_LAT, VA_LON = (36.5, 39.5), (-83.7, -75.2)  # Virginia's extent with a small margin
_TZ = ZoneInfo("America/New_York")             # CRASH_DT is local midnight sent as UTC epoch ms

COLLISION = {"1": "Rear End", "2": "Angle", "3": "Head On", "4": "Sideswipe - Same Direction",
             "5": "Sideswipe - Opposite Direction", "6": "Fixed Object in Road", "7": "Train", "8": "Non-Collision",
             "9": "Fixed Object - Off Road", "10": "Deer", "11": "Other Animal", "12": "Pedestrian",
             "13": "Bicyclist", "14": "Motorcyclist", "15": "Backed Into", "16": "Other"}
WEATHER = {"1": "No Adverse Condition (Clear/Cloud)", "3": "Fog", "4": "Mist", "5": "Rain", "6": "Snow",
           "7": "Sleet/Hail", "8": "Smoke/Dust", "9": "Other", "10": "Blowing Sand, Soil, Dirt, or Snow",
           "11": "Severe Crosswinds"}
LIGHT = {"1": "Dawn", "2": "Daylight", "3": "Dusk", "4": "Darkness - Road Lighted", "5": "Darkness - Road Not Lighted",
         "6": "Darkness - Unknown Road Lighting", "7": "Unknown"}
SURFACE = {"1": "Dry", "2": "Wet", "3": "Snowy", "4": "Icy", "5": "Muddy", "6": "Oil/Other Fluids", "7": "Other",
           "8": "Natural Debris", "9": "Water (Standing, Moving)", "10": "Slush", "11": "Sand, Dirt, Gravel"}
INTERSECTION = {"1": "Not at Intersection", "2": "Two Approaches", "3": "Three Approaches", "4": "Four Approaches",
                "5": "Five-Point, or More", "6": "Roundabout"}
FREEWAY_FUN = {"INT", "OFE"}                   # functional class: Interstate, Other Freeways and Expressways

# VDOT jurisdiction code (JURIS_CODE / PHYSICAL_JURIS, leading zeros dropped as in the crash layer) -> (name, county
# FIPS). From VDOT's VA_Jurisdictions layer (2026-11-07); a town carries its county's FIPS. Code 141 (867 crashes)
# is not in that layer and stays unnamed.
JURIS = {
    "0": ("Arlington County", "51013"), "1": ("Accomack County", "51001"), "2": ("Albemarle County", "51003"),
    "3": ("Alleghany County", "51005"), "4": ("Amelia County", "51007"), "5": ("Amherst County", "51009"),
    "6": ("Appomattox County", "51011"), "7": ("Augusta County", "51015"), "8": ("Bath County", "51017"),
    "9": ("Bedford County", "51019"), "10": ("Bland County", "51021"), "11": ("Botetourt County", "51023"),
    "12": ("Brunswick County", "51025"), "13": ("Buchanan County", "51027"), "14": ("Buckingham County", "51029"),
    "15": ("Campbell County", "51031"), "16": ("Caroline County", "51033"), "17": ("Carroll County", "51035"),
    "18": ("Charles City County", "51036"), "19": ("Charlotte County", "51037"),
    "20": ("Chesterfield County", "51041"), "21": ("Clarke County", "51043"), "22": ("Craig County", "51045"),
    "23": ("Culpeper County", "51047"), "24": ("Cumberland County", "51049"), "25": ("Dickenson County", "51051"),
    "26": ("Dinwiddie County", "51053"), "28": ("Essex County", "51057"), "29": ("Fairfax County", "51059"),
    "30": ("Fauquier County", "51061"), "31": ("Floyd County", "51063"), "32": ("Fluvanna County", "51065"),
    "33": ("Franklin County", "51067"), "34": ("Frederick County", "51069"), "35": ("Giles County", "51071"),
    "36": ("Gloucester County", "51073"), "37": ("Goochland County", "51075"), "38": ("Grayson County", "51077"),
    "39": ("Greene County", "51079"), "40": ("Greensville County", "51081"), "41": ("Halifax County", "51083"),
    "42": ("Hanover County", "51085"), "43": ("Henrico County", "51087"), "44": ("Henry County", "51089"),
    "45": ("Highland County", "51091"), "46": ("Isle of Wight County", "51093"), "47": ("James City County", "51095"),
    "48": ("King George County", "51099"), "49": ("King and Queen County", "51097"),
    "50": ("King William County", "51101"), "51": ("Lancaster County", "51103"), "52": ("Lee County", "51105"),
    "53": ("Loudoun County", "51107"), "54": ("Louisa County", "51109"), "55": ("Lunenburg County", "51111"),
    "56": ("Madison County", "51113"), "57": ("Mathews County", "51115"), "58": ("Mecklenburg County", "51117"),
    "59": ("Middlesex County", "51119"), "60": ("Montgomery County", "51121"), "62": ("Nelson County", "51125"),
    "63": ("New Kent County", "51127"), "65": ("Northampton County", "51131"),
    "66": ("Northumberland County", "51133"), "67": ("Nottoway County", "51135"), "68": ("Orange County", "51137"),
    "69": ("Page County", "51139"), "70": ("Patrick County", "51141"), "71": ("Pittsylvania County", "51143"),
    "72": ("Powhatan County", "51145"), "73": ("Prince Edward County", "51147"),
    "74": ("Prince George County", "51149"), "76": ("Prince William County", "51153"),
    "77": ("Pulaski County", "51155"), "78": ("Rappahannock County", "51157"), "79": ("Richmond County", "51159"),
    "80": ("Roanoke County", "51161"), "81": ("Rockbridge County", "51163"), "82": ("Rockingham County", "51165"),
    "83": ("Russell County", "51167"), "84": ("Scott County", "51169"), "85": ("Shenandoah County", "51171"),
    "86": ("Smyth County", "51173"), "87": ("Southampton County", "51175"), "88": ("Spotsylvania County", "51177"),
    "89": ("Stafford County", "51179"), "90": ("Surry County", "51181"), "91": ("Sussex County", "51183"),
    "92": ("Tazewell County", "51185"), "93": ("Warren County", "51187"), "95": ("Washington County", "51191"),
    "96": ("Westmoreland County", "51193"), "97": ("Wise County", "51195"), "98": ("Wythe County", "51197"),
    "99": ("York County", "51199"), "100": ("Alexandria City", "51510"), "101": ("Big Stone Gap town", "51195"),
    "102": ("Bristol City", "51520"), "103": ("Buena Vista City", "51530"), "104": ("Charlottesville City", "51540"),
    "105": ("Clifton Forge town", "51005"), "106": ("Colonial Heights City", "51570"),
    "107": ("Covington City", "51580"), "108": ("Danville City", "51590"), "109": ("Emporia City", "51595"),
    "110": ("Falls Church City", "51610"), "111": ("Fredericksburg City", "51630"),
    "112": ("Front Royal town", "51187"), "113": ("Galax City", "51640"), "114": ("Hampton City", "51650"),
    "115": ("Harrisonburg City", "51660"), "116": ("Hopewell City", "51670"), "117": ("Lexington City", "51678"),
    "118": ("Lynchburg City", "51680"), "119": ("Marion town", "51173"), "120": ("Martinsville City", "51690"),
    "121": ("Newport News City", "51700"), "122": ("Norfolk City", "51710"), "123": ("Petersburg City", "51730"),
    "124": ("Portsmouth City", "51740"), "125": ("Pulaski town", "51155"), "126": ("Radford City", "51750"),
    "127": ("Richmond City", "51760"), "128": ("Roanoke City", "51770"), "129": ("Salem City", "51775"),
    "130": ("South Boston town", "51083"), "131": ("Chesapeake City", "51550"), "132": ("Staunton City", "51790"),
    "133": ("Suffolk City", "51800"), "134": ("Virginia Beach City", "51810"), "136": ("Waynesboro City", "51820"),
    "137": ("Williamsburg City", "51830"), "138": ("Winchester City", "51840"), "139": ("Wytheville town", "51197"),
    "140": ("Abingdon town", "51191"), "142": ("Blackstone town", "51135"), "143": ("Bluefield town", "51185"),
    "144": ("Farmville town", "51147"), "145": ("Franklin City", "51620"), "146": ("Norton City", "51720"),
    "147": ("Poquoson City", "51735"), "148": ("Richlands town", "51185"), "149": ("Vinton town", "51161"),
    "150": ("Blacksburg town", "51121"), "151": ("Fairfax City", "51600"), "152": ("Manassas Park City", "51685"),
    "153": ("Vienna town", "51059"), "154": ("Christiansburg town", "51121"), "155": ("Manassas City", "51683"),
    "156": ("Warrenton town", "51061"), "157": ("Rocky Mount town", "51067"), "158": ("Tazewell town", "51185"),
    "159": ("Luray town", "51139"), "160": ("Accomac town", "51001"), "161": ("Alberta town", "51025"),
    "162": ("Altavista town", "51143"), "163": ("Amherst town", "51009"), "164": ("Appalachia town", "51195"),
    "165": ("Appomattox town", "51011"), "166": ("Ashland town", "51085"), "167": ("Belle Haven town", "51001"),
    "168": ("Berryville town", "51043"), "169": ("Bloxom town", "51001"), "170": ("Boones Mill town", "51067"),
    "171": ("Bowling Green town", "51033"), "172": ("Boyce town", "51043"), "173": ("Boydton town", "51117"),
    "174": ("Boykins town", "51175"), "175": ("Branchville town", "51175"), "176": ("Bridgewater town", "51165"),
    "177": ("Broadway town", "51165"), "178": ("Brodnax town", "51025"), "179": ("Brookneal town", "51031"),
    "180": ("Buchanan town", "51023"), "181": ("Burkeville town", "51135"), "182": ("Cape Charles town", "51131"),
    "183": ("Capron town", "51175"), "184": ("Cedar Bluff town", "51185"),
    "185": ("Charlotte Court House town", "51037"), "186": ("Chase City town", "51117"),
    "187": ("Chatham town", "51143"), "188": ("Cheriton town", "51131"), "189": ("Chilhowie town", "51173"),
    "190": ("Chincoteague town", "51001"), "191": ("Claremont town", "51181"), "192": ("Clarksville town", "51117"),
    "193": ("Cleveland town", "51167"), "194": ("Clifton town", "51059"), "195": ("Clinchport town", "51169"),
    "196": ("Clintwood town", "51051"), "198": ("Coeburn town", "51195"), "199": ("Colonial Beach town", "51193"),
    "200": ("Columbia town", "51065"), "201": ("Courtland town", "51175"), "202": ("Craigsville town", "51015"),
    "203": ("Crewe town", "51135"), "204": ("Culpeper town", "51047"), "205": ("Damascus town", "51191"),
    "206": ("Dayton town", "51165"), "207": ("Dendron town", "51181"), "208": ("Dillwyn town", "51029"),
    "209": ("Drakes Branch town", "51037"), "210": ("Dublin town", "51155"), "211": ("Duffield town", "51169"),
    "212": ("Dumfries town", "51153"), "213": ("Dungannon town", "51169"), "214": ("Eastville town", "51131"),
    "215": ("Edinburg town", "51171"), "216": ("Elkton town", "51165"), "217": ("Exmore Town", "51131"),
    "218": ("Fincastle town", "51023"), "219": ("Floyd town", "51063"), "220": ("Fries town", "51077"),
    "221": ("Gate City town", "51169"), "222": ("Glade Spring town", "51191"), "223": ("Glasgow town", "51163"),
    "224": ("Glen Lyn town", "51071"), "225": ("Gordonsville town", "51137"), "226": ("Goshen town", "51163"),
    "227": ("Gretna town", "51143"), "228": ("Grottoes town", "51165"), "229": ("Grundy town", "51027"),
    "230": ("Halifax town", "51083"), "231": ("Hallwood town", "51001"), "232": ("Hamilton town", "51107"),
    "233": ("Haymarket town", "51153"), "234": ("Haysi town", "51051"), "235": ("Herndon town", "51059"),
    "236": ("Hillsboro town", "51107"), "237": ("Hillsville town", "51035"), "239": ("Honaker town", "51167"),
    "240": ("Independence town", "51077"), "241": ("Iron Gate town", "51005"), "242": ("Irvington town", "51103"),
    "243": ("Ivor town", "51175"), "244": ("Jarratt town", "51081"), "245": ("Jonesville town", "51105"),
    "246": ("Keller town", "51001"), "247": ("Kenbridge town", "51111"), "248": ("Keysville town", "51037"),
    "249": ("Kilmarnock town", "51103"), "250": ("La Crosse town", "51117"), "251": ("Lawrenceville town", "51025"),
    "252": ("Lebanon town", "51167"), "253": ("Leesburg town", "51107"), "254": ("Louisa town", "51109"),
    "255": ("Lovettsville town", "51107"), "256": ("Madison town", "51113"), "257": ("McKenney town", "51053"),
    "258": ("Melfa town", "51001"), "259": ("Middleburg town", "51107"), "260": ("Middletown town", "51069"),
    "261": ("Mineral town", "51109"), "262": ("Monterey town", "51091"), "263": ("Montross town", "51193"),
    "264": ("Mount Crawford town", "51165"), "265": ("Mount Jackson town", "51171"), "266": ("Narrows town", "51071"),
    "267": ("Nassawadox town", "51131"), "268": ("New Castle town", "51045"), "269": ("New Market town", "51171"),
    "270": ("Newsoms town", "51175"), "271": ("Nickelsville town", "51169"), "272": ("Occoquan town", "51153"),
    "273": ("Onancock town", "51001"), "274": ("Onley town", "51001"), "275": ("Orange town", "51137"),
    "276": ("Painter town", "51001"), "277": ("Pamplin City town", "51011"), "278": ("Parksley town", "51001"),
    "279": ("Pearisburg town", "51071"), "280": ("Pembroke town", "51071"), "281": ("Pennington Gap town", "51105"),
    "282": ("Phenix town", "51037"), "283": ("Pocahontas town", "51185"), "284": ("Port Royal town", "51033"),
    "285": ("Pound town", "51195"), "286": ("Purcellville town", "51107"), "287": ("Quantico town", "51153"),
    "288": ("Remington town", "51061"), "289": ("Rich Creek town", "51071"), "290": ("Ridgeway town", "51089"),
    "291": ("Round Hill town", "51107"), "292": ("Rural Retreat town", "51197"), "293": ("St. Charles town", "51105"),
    "294": ("St. Paul town", "51195"), "295": ("Saltville town", "51173"), "296": ("Saxis town", "51001"),
    "297": ("Scottsburg town", "51083"), "298": ("Scottsville town", "51003"), "299": ("Shenandoah town", "51139"),
    "300": ("Smithfield town", "51093"), "301": ("South Hill town", "51117"), "302": ("Stanardsville town", "51079"),
    "303": ("Stanley town", "51139"), "304": ("Stephens City town", "51069"), "305": ("Stony Creek town", "51183"),
    "306": ("Strasburg town", "51171"), "307": ("Stuart town", "51141"), "308": ("Surry town", "51181"),
    "309": ("Tangier town", "51001"), "310": ("Tappahannock town", "51057"), "311": ("The Plains town", "51061"),
    "312": ("Timberville town", "51165"), "313": ("Toms Brook town", "51171"), "314": ("Troutdale town", "51077"),
    "315": ("Troutville town", "51023"), "316": ("Urbanna town", "51119"), "317": ("Victoria town", "51111"),
    "318": ("Virgilina town", "51083"), "319": ("Wachapreague town", "51001"), "320": ("Wakefield town", "51183"),
    "321": ("Warsaw town", "51159"), "322": ("Washington town", "51157"), "323": ("Waverly town", "51183"),
    "324": ("Weber City town", "51169"), "325": ("West Point town", "51101"), "327": ("White Stone town", "51103"),
    "328": ("Windsor town", "51093"), "329": ("Wise town", "51195"), "330": ("Woodstock town", "51171"),
    "331": ("Hurt town", "51143"), "339": ("Clinchco town", "51051"), "515": ("Bedford town", "51141"),
}


def plausible(lat, lon) -> bool:
    return (lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon)
            and VA_LAT[0] <= lat <= VA_LAT[1] and VA_LON[0] <= lon <= VA_LON[1])


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _decode(table: dict, v):
    if v is None or str(v).strip() == "":
        return None
    return table.get(str(v).strip(), f"code {str(v).strip()}")   # an unmapped code stays visible, never dropped


def severity(a: dict) -> str:
    """Most severe outcome from the people counts; U when people are injured but none has a KABC level."""
    for k in "KABC":
        if _int(a.get(f"{k}_PEOPLE")):
            return k
    return "U" if _int(a.get("PERSONS_INJURED")) else "O"


def crash_record(a: dict) -> dict:
    """One Full Crash attributes dict -> the shared crash shape (the keys CCRS normalizes to)."""
    s = lambda v: (str(v).strip() or None) if v is not None else None
    lat, lon = a.get("LAT"), a.get("LON")
    has = plausible(lat, lon)
    date = from_epoch(a["CRASH_DT"] / 1000, _TZ).date() if a.get("CRASH_DT") is not None else None
    tm = a.get("CRASH_MILITARY_TM")
    hour = tm // 100 if isinstance(tm, int) and 0 <= tm <= 2359 and tm % 100 < 60 else None
    juris = s(a.get("PHYSICAL_JURIS")) or s(a.get("JURIS_CODE"))
    name, fips = JURIS.get(juris or "", (None, None))
    persons = [k for k in "KABC" for _ in range(_int(a.get(f"{k}_PEOPLE")))]
    sev, reported = severity(a), s(a.get("CRASH_SEVERITY"))
    return {
        "collision_id": str(a["DOCUMENT_NBR"]),
        "report_number": s(a.get("LOCAL_CASE_CD")),
        "datetime": f"{date.isoformat()}T{tm // 100:02d}:{tm % 100:02d}" if date and hour is not None
        else (date.isoformat() if date else None),
        "date": date.isoformat() if date else "",
        "year": date.year if date else None,
        "hour": hour,
        "lat": lat if has else None,
        "lon": lon if has else None,
        "bad_coords": lat is not None and lon is not None and (lat, lon) != (0, 0) and not has,
        "primary_road": s(a.get("ROUTE_OR_STREET_NM")),
        "secondary_road": None,                  # the public layer has no cross street
        "sec_distance": None,
        "sec_direction": None,
        "city_name": name,
        "county_code": juris,                    # VDOT jurisdiction code, as CCRS keeps its own county code
        "county_fips": fips,
        "killed": _int(a.get("K_PEOPLE")),
        "injured": _int(a.get("PERSONS_INJURED")),
        "person_kabco": persons,                 # one entry per K/A/B/C person, from the crash's counts
        "severity": sev,
        "severity_reported": reported,
        "severity_mismatch": reported is not None and reported != sev,
        "collision_type": _decode(COLLISION, a.get("COLLISION_TYPE")),
        "lighting": _decode(LIGHT, a.get("LIGHT_CONDITION")),
        "weather": _decode(WEATHER, a.get("WEATHER_CONDITION")),
        "surface": _decode(SURFACE, a.get("ROADWAY_SURFACE_COND")),
        "intersection_type": _decode(INTERSECTION, a.get("INTERSECTION_TYPE")),
        "is_freeway": s(a.get("FUN")) in FREEWAY_FUN,
        "ped": s(a.get("PED_NONPED")) == "1",
        "bike": s(a.get("BIKE_NONBIKE")) == "1",
        "motorcycle": s(a.get("MOTOR_NONMOTOR")) == "1",
        "heavy_truck": s(a.get("LGTRUCK_NONLGTRUCK")) == "1",
        "hit_run": s(a.get("HITRUN_NOT_HITRUN")) == "1",
        "route": s(a.get("RTE_NM")), "milepost": a.get("RNS_MP"),
        "node": s(a.get("NODE")), "node_offset": a.get("OFFSET"),
    }


def _get(where: str, last: int, opener) -> list[dict]:
    q = {"where": f"({where}) AND OBJECTID>{last}", "outFields": "*", "orderByFields": "OBJECTID",
         "resultRecordCount": PAGE, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(LAYER + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    with opener(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"VDOT Full Crash query error: {body['error']}")
    return [f["attributes"] for f in body.get("features", [])]


def fetch(where: str, cache_dir: Path | None = None, opener=urllib.request.urlopen) -> list[dict]:
    """Every crash matching an ArcGIS `where` (e.g. "CRASH_YEAR='2024' AND PHYSICAL_JURIS='127'"), paged by OBJECTID
    and normalized. Cached as raw JSON per `where` when cache_dir is given."""
    cache = cache_dir / f"va_vdot_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json" if cache_dir else None
    if cache and cache.exists():
        raw = json.loads(cache.read_text())
    else:
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
    return [crash_record(a) for a in raw]


# -- state-pack contract (#19, docs/state-pack-design.md § Reader contract) --------------------------------------
# VDOT words -> the CCRS words the profile and the collision diagram read; any other type keeps VDOT's own words
CCRS_TYPE = {"Rear End": "REAR END", "Angle": "BROADSIDE", "Head On": "HEAD-ON", "Sideswipe - Same Direction": "SIDE SWIPE",
             "Sideswipe - Opposite Direction": "SIDE SWIPE", "Fixed Object in Road": "HIT OBJECT",
             "Fixed Object - Off Road": "HIT OBJECT", "Pedestrian": "VEHICLE/PEDESTRIAN"}
CCRS_LIGHT = {"Darkness - Road Lighted": "DARK - STREET LIGHTS", "Darkness - Road Not Lighted": "DARK - NO STREET LIGHTS",
              "Darkness - Unknown Road Lighting": "DARK - UNKNOWN STREET LIGHTS"}


def contract_record(r: dict) -> dict:
    """One crash_record() -> the shared crash dict (packs.check_crash)."""
    d = datetime.fromisoformat(r["date"]).date() if r["date"] else None
    up = lambda v: v.upper() if v else None
    return {"crash_id": r["collision_id"], "report_version": 0, "deleted": False,
            "preliminary": bool(d and d.year >= datetime.now(_TZ).year),     # VDOT: the current year is preliminary
            "date": r["date"], "year": r["year"], "hour": r["hour"], "day_of_week": d.strftime("%A") if d else None,
            "lat": r["lat"], "lon": r["lon"], "bad_coords": r["bad_coords"],
            "primary_road": r["primary_road"], "secondary_road": None, "offset_ft": None, "offset_dir": None,
            "city": up(r["city_name"]), "county_code": r["county_code"], "county_fips": r["county_fips"], "state": "VA",
            "is_freeway": r["is_freeway"], "killed": r["killed"], "injured": r["injured"], "severity": r["severity"],
            "ped": r["ped"], "bike": r["bike"], "ebike": False, "escooter": False, "motorcycle": r["motorcycle"],
            "heavy_truck": r["heavy_truck"], "parties": [],
            "collision_type": CCRS_TYPE.get(r["collision_type"], up(r["collision_type"])),
            "lighting": CCRS_LIGHT.get(r["lighting"], up(r["lighting"])), "weather": up(r["weather"]),
            "surface": up(r["surface"]), "report_number": r["report_number"],
            "route": r["route"], "milepost": r["milepost"], "node": r["node"]}


def fetch_contract(box, county_fips: list[str], years: list[int], cache_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Every crash with a point in the box (s, w, n, e) in those years. The ~60 crashes of 1.18M with no point
    (research 2026-11-07) aren't read: the layer can't say where they are beyond the jurisdiction."""
    s, w, n, e = box
    yrs = ", ".join(f"'{y}'" for y in years)
    where = f"LAT >= {s:.6f} AND LAT <= {n:.6f} AND LON >= {w:.6f} AND LON <= {e:.6f} AND CRASH_YEAR IN ({yrs})"
    rows = fetch(where, cache_dir, opener)
    have = {r["year"] for r in rows}
    out = [contract_record(r) for r in rows if r["county_fips"]]
    return {"crashes": out, "years_missing": [y for y in years if y not in have],
            "cleaning": {"source_rows": len(rows), "no_jurisdiction": len(rows) - len(out),
                         "severity_differs_from_vdot": sum(r["severity_mismatch"] for r in rows),
                         "no_gps_not_read": "about 60 of 1.18M statewide crashes have no point; not read"}}
