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
# researched, no pack yet: listed greyed out on Setup (docs/state-pack-design.md § State picker)
COMING = {"TX": "Texas", "FL": "Florida", "IL": "Illinois", "MA": "Massachusetts", "WA": "Washington",
          "OR": "Oregon", "DC": "District of Columbia", "NY": "New York"}


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
