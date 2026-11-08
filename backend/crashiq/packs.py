"""State packs (#19, docs/state-pack-design.md): everything that differs by state, in one registry.

A study belongs to one state (`study.state`, picked first on Setup, default 'CA' from the DB column); `get()` is the
one lookup and has no default, so nothing falls back to California. California keeps today's code path (`fetch` is
None: `crashes.pull()` reads CCRS); any other state's reader is called through `crashes.pull_reader()` and returns
crash dicts in the contract `check_crash()` enforces.

Methods (rates, costs, screening) live in data/reference/methods_<st>.json as cited data: every value names its
manual and page, or says why it's missing (`check_methods`). A non-CA pack may cite only its own state's or US
manuals: never Caltrans.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

from .settings import ROOT

REF = ROOT / "data" / "reference"
CACHE = Path(os.getenv("CRASHIQ_STATES_DIR", ROOT / "data" / "cache" / "states"))   # readers' raw pulls, never committed


@dataclass(frozen=True)
class StatePack:
    code: str                         # "CA"
    name: str                         # "California": the Setup dropdown and every "in <state>" sentence
    fips: str                         # "06"
    status: str                       # "active" (offered to users) | "reader_only" (tests and Tester runs only)
    source: str                       # credit line on exports and the pull summary
    source_short: str                 # "CCRS": Setup's one-line intro and the screens' "pull from" wording
    bounds: tuple                     # (s, w, n, e): a corridor with no point inside isn't in this state
    first_year: int                   # first year the reader has
    methods: Path                     # data/reference/methods_<st>.json
    fetch: Callable | None = None     # reader: fetch(box, county_fips, years, cache_dir) -> dict; None = CCRS pull()
    county_boxes: Path | None = None  # TIGER counties (5-digit FIPS -> padded box); None = CA's own file
    final_lag_months: int = 18        # when a year counts as final
    legal: str = ""                   # notice on every export page (23 USC 407 ...)
    severity_note: str | None = None  # set when the source has no A/B/C level: KSI outputs carry it
    data_notes: tuple = ()            # what the source lacks, said once in the profile and the export
    caltrans: bool = False            # Caltrans services (postmiles, AADT, ramps, rate groups, NAD, FARS store)


CA_SOURCE = "Crash data: CCRS, California Highway Patrol (data.ca.gov, public domain)."

PACKS: dict[str, StatePack] = {
    "CA": StatePack(code="CA", name="California", fips="06", status="active", source=CA_SOURCE, source_short="CCRS",
                    bounds=(32.4, -124.6, 42.1, -114.0), first_year=2016, methods=REF / "methods_ca.json",
                    caltrans=True),
}
# VDOT's Full Crash terms, quoted (research_notes/va-2026-11-07/va-import.md §1a)
VA_LEGAL = ("VDOT: \"under Title 23 United State Code – Section 407, this crash information cannot be used in discovery or "
            "as evidence …\" Users shall comply with the Federal Drivers Privacy Protection Act and DMV's rules on "
            "disclosure or dissemination (VDOT Full Crash terms).")


def _va_fetch(box, county_fips, years, cache_dir):
    from .sources import va_vdot
    return va_vdot.fetch_contract(box, county_fips, years, cache_dir)


PACKS["VA"] = StatePack(
    code="VA", name="Virginia", fips="51", status="active",
    source="Crash data: VDOT Full Crash, Virginia Roads (DMV TREDS records; no open licence, VDOT terms, 23 USC 407).",
    source_short="VDOT Full Crash", bounds=(36.5, -83.7, 39.5, -75.2), first_year=2017,
    methods=REF / "methods_va.json", fetch=_va_fetch, county_boxes=REF / "county_boxes_va.json", legal=VA_LEGAL,
    data_notes=("Virginia's public crash layer has one street field and no cross street, and no driver or vehicle "
                "records: road-user movements and collision diagrams are empty, and a crash without GPS can't be placed "
                "(about 60 of 1.18 million statewide).",
                "Primary collision factor, DUI and speed rows are blank: Virginia's public layer has no violation codes."))

def _ma_fetch(box, county_fips, years, cache_dir):
    from .sources import ma_impact
    boxes = json.loads((REF / "county_boxes_ma.json").read_text())["counties"]
    return ma_impact.fetch_contract(box, county_fips, years, cache_dir, boxes)


PACKS["MA"] = StatePack(
    code="MA", name="Massachusetts", fips="25", status="active",
    source="Crash data: MassDOT IMPACT open data (crash and person layers; 2002-2019 public domain, 2020 on under "
           "MassDOT's disclaimer).",
    source_short="MassDOT IMPACT", bounds=(41.2, -73.6, 42.9, -69.9), first_year=2002,
    methods=REF / "methods_ma.json", fetch=_ma_fetch, county_boxes=REF / "county_boxes_ma.json",
    # MassDOT's open-year disclaimer, quoted (research_notes/ma-2026-11-07/ma-import.md § licence)
    legal=("MassDOT: \"MassDOT makes no representation as to the accuracy… not an official record… any crash records or "
           "data provided for the years after 2020 are subject to change… open years' of crash data are for "
           "informational purposes only and should not be used for analysis… (see 23 USC, Section 407)\""),
    data_notes=("MassDOT's crash data in CrashIQ has no driver or vehicle records yet: road-user movements, motorcycle, "
                "heavy-truck and e-bike counts and collision diagrams are empty.",
                "Primary collision factor, DUI and speed rows are blank: MassDOT's crash layer has no violation codes."))

def _wa_fetch(box, county_fips, years, cache_dir):
    from .sources import wa_wsdot
    boxes = json.loads((REF / "county_boxes_wa.json").read_text())["counties"]
    return wa_wsdot.fetch_contract(box, county_fips, years, cache_dir, boxes)


# WSDOT's standard disclaimer, quoted (Safety Analysis Guide, Aug 2024, §6.3.1, PDF p. 14-15): "must be in the footer"
WA_LEGAL = ("Under 23 U.S. Code § 148 and 23 U.S. Code § 407, safety data, reports, surveys, schedules, lists compiled or "
            "collected for the purpose of identifying, evaluating, or planning the safety enhancement of potential crash "
            "sites, hazardous roadway conditions, or railway-highway crossings are not subject to discovery or admitted "
            "into evidence in a Federal or State court proceeding or considered for other purposes in any action for "
            "damages arising from any occurrence at a location mentioned or addressed in such reports, surveys, "
            "schedules, lists, or data.")

PACKS["WA"] = StatePack(
    code="WA", name="Washington", fips="53", status="active",
    source="Crash data: WSDOT Crash Data Portal (public record-level data, statewide; no published reuse licence); "
           "inside Seattle, street names and crash details from SDOT Collisions (City of Seattle open data).",
    source_short="WSDOT Crash Data Portal", bounds=(45.5, -124.9, 49.1, -116.8), first_year=2016,   # "10 full years"
    methods=REF / "methods_wa.json", fetch=_wa_fetch, county_boxes=REF / "county_boxes_wa.json", legal=WA_LEGAL,
    data_notes=("WSDOT's public portal gives each crash's point and severity but no street names, crash type, light, "
                "road users or people counts; inside Seattle CrashIQ adds them from SDOT's feed by report number. "
                "Elsewhere in Washington those tables are blank, and people killed and injured aren't counted.",
                "WSDOT's 'Unknown' injury is counted as injury, level not reported (U), pending a decision.",
                "Crashes WSDOT files under 'State Route' count as freeway crashes, so an arterial that is a state route "
                "(SR 99 Aurora Ave) loses them: check such corridors by hand.",
                "Primary collision factor, DUI and speed rows are blank: WSDOT's portal has no violation codes."))

def _or_fetch(box, county_fips, years, cache_dir):
    from .sources import or_odot
    boxes = json.loads((REF / "county_boxes_or.json").read_text())["counties"]
    return or_odot.fetch_contract(box, county_fips, years, cache_dir, boxes)


PACKS["OR"] = StatePack(
    code="OR", name="Oregon", fips="41", status="active",
    source="Crash data: ODOT Crash Data System, through ODOT's public ArcGIS crash layer (2019-2024; no published "
           "reuse licence).",
    source_short="ODOT Crash Data System", bounds=(41.9, -124.8, 46.3, -116.4), first_year=2019,
    methods=REF / "methods_or.json", fetch=_or_fetch, county_boxes=REF / "county_boxes_or.json",
    # ODOT's Crash Data Disclaimers (rev. 4-2026), quoted (research_notes/or-2026-11-07/or-import.md)
    legal=("ODOT: \"The ODOT CAR Unit releases crash data to local and federal governments, private consultants, "
           "engineering firms, universities, law enforcement agencies, and the public. As a result of this data sharing, "
           "ODOT makes no guarantee, and expressly disclaims liability, regarding the content, usage, and interpretation "
           "of crash data re-released by our customers.\""),
    data_notes=("CrashIQ reads Oregon from ODOT's public crash layer, which covers 2019-2024 only; earlier years are "
                "in ODOT's yearly Access files, not read yet. The layer has no driver or vehicle records: road-user "
                "movements and collision diagrams are empty.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't read ODOT's cause codes yet."))

# researched, no pack yet: listed greyed out on Setup (docs/state-pack-design.md § State picker)
COMING = {"TX": "Texas", "FL": "Florida", "IL": "Illinois",
          "DC": "District of Columbia", "NY": "New York"}


def get(code: str) -> StatePack:
    """The pack of a state code; KeyError for anything not registered (never a California fallback)."""
    return PACKS[code]


def for_study(study: dict) -> StatePack:
    return get(study.get("state") or "CA")      # a study row always has state (DB default 'CA'); dicts in tests may not


def states() -> list[dict]:
    """Setup's dropdown: ready states first, then the coming ones, both alphabetical."""
    ready = sorted((p for p in PACKS.values() if p.status == "active"), key=lambda p: p.name)
    later = sorted([(p.name, p.code) for p in PACKS.values() if p.status != "active"]
                   + [(n, c) for c, n in COMING.items() if c not in PACKS])
    return [{"code": p.code, "name": p.name, "ready": True} for p in ready] + \
           [{"code": c, "name": n, "ready": False} for n, c in later]


def in_bounds(pack: StatePack, lat: float, lon: float) -> bool:
    s, w, n, e = pack.bounds
    return s <= lat <= n and w <= lon <= e


# -- reader contract ---------------------------------------------------------------------------------------------
SEVERITIES = set("KABCUO")
CONTRACT_KEYS = ("crash_id", "report_version", "deleted", "preliminary", "date", "year", "hour", "lat", "lon",
                 "primary_road", "secondary_road", "offset_ft", "offset_dir", "city", "county_fips", "state",
                 "is_freeway", "killed", "injured", "severity", "ped", "bike", "ebike", "escooter", "motorcycle",
                 "heavy_truck", "parties", "collision_type")


def check_crash(c: dict, pack: StatePack) -> list[str]:
    """Why a reader's crash breaks the contract (docs/state-pack-design.md § Reader contract); [] = fine."""
    bad = [f"missing {k}" for k in CONTRACT_KEYS if k not in c]
    if c.get("severity") not in SEVERITIES:
        bad.append(f"severity {c.get('severity')!r} is not one of KABCUO")
    if not (isinstance(c.get("county_fips"), str) and len(c["county_fips"]) == 5
            and c["county_fips"].startswith(pack.fips)):
        bad.append(f"county_fips {c.get('county_fips')!r} is not a 5-digit {pack.code} county")
    if c.get("state") != pack.code:
        bad.append(f"state {c.get('state')!r} is not {pack.code}")
    if c.get("lat") is not None and not in_bounds(pack, c["lat"], c.get("lon") or 0):
        bad.append("point outside the state box")
    if pack.severity_note and c.get("severity") in ("A", "B", "C"):
        bad.append(f"severity {c['severity']} from a source with no injury levels")
    return bad


# -- methods -----------------------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def methods(pack: StatePack) -> dict:
    m = json.loads(pack.methods.read_text())
    problems = check_methods(m, pack.code)
    if problems:
        raise ValueError(f"{pack.methods.name}: " + "; ".join(problems))
    return m


def check_methods(m: dict, code: str) -> list[str]:
    """Every value is cited (manual + page, the manual titled with edition and url) or missing ("missing": why).
    A manual is the state's own or national (US, with the user's decision); never another state's."""
    out = []
    manuals = m.get("manuals", {})
    for slug, man in manuals.items():
        if man.get("jurisdiction") not in (code, "US"):
            out.append(f"manual {slug} is {man.get('jurisdiction')}'s, not {code}'s or national")
        if man.get("jurisdiction") == "US" and not man.get("decided"):
            out.append(f"national manual {slug} has no 'decided' line")
        for k in ("title", "edition", "url"):
            if not man.get(k):
                out.append(f"manual {slug} has no {k}")
    for key, v in m.get("values", {}).items():
        if "missing" in v:
            continue
        if v.get("manual") not in manuals or not v.get("page"):
            out.append(f"{key}: neither cited (manual + page) nor missing")
        elif v.get("verified") and not manuals[v["manual"]].get("sha256"):
            out.append(f"{key}: verified against {v['manual']}, which has no sha256")
    return out


def value(pack: StatePack, key: str) -> dict | None:
    """A cited, verified methods value, or None (missing, unverified): the caller leaves that part out and says why."""
    v = methods(pack)["values"].get(key) or {}
    return v if v and "missing" not in v and v.get("verified", True) else None


def why_missing(pack: StatePack, key: str) -> str:
    v = methods(pack)["values"].get(key) or {}
    if "missing" in v:
        return v["missing"]
    return f"found in research, not yet checked against {v.get('manual')}" if v else "not looked up"


def cite(pack: StatePack, key: str) -> str:
    """'<title> (<publisher>, <edition>), <page>' for a value's source line."""
    v = methods(pack)["values"][key]
    man = methods(pack)["manuals"][v["manual"]]
    return f"{man['title']} ({', '.join(x for x in (man.get('publisher'), man['edition']) if x)}), {v['page']}"
