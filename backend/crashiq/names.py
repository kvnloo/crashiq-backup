"""Street-name normalization for matching crash-report road names to OSM streets.

Officers write the same street many ways ("ALEMANY BL", "Alemany Boulevard", "07TH ST",
"MARINE AVE. (3100 BLOCK)", "I-280 S/B"). `street_key` reduces a name to a comparable
(core, suffix) pair. Aliases that rules can't derive live in data/aliases/*.csv, a versioned
file reviewed by the user, never in a prompt.
"""

from __future__ import annotations

import csv
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import NamedTuple

SUFFIX = {
    "STREET": "ST", "STR": "ST", "ST": "ST",
    "AVENUE": "AVE", "AVE": "AVE", "AV": "AVE", "AVN": "AVE",
    "BOULEVARD": "BLVD", "BLVD": "BLVD", "BL": "BLVD", "BLV": "BLVD",
    "DRIVE": "DR", "DR": "DR", "ROAD": "RD", "RD": "RD", "PLACE": "PL", "PL": "PL",
    "COURT": "CT", "CT": "CT", "TERRACE": "TER", "TER": "TER", "TERR": "TER",
    "WAY": "WAY", "WY": "WAY", "LANE": "LN", "LN": "LN", "ALLEY": "ALY", "ALY": "ALY",
    "HIGHWAY": "HWY", "HWY": "HWY", "HY": "HWY", "HIWAY": "HWY", "PARKWAY": "PKWY", "PKWY": "PKWY",
    "CIRCLE": "CIR", "CIR": "CIR", "EXPRESSWAY": "EXPY", "EXPY": "EXPY", "FREEWAY": "FWY", "FWY": "FWY", "FRWY": "FWY",
    "PLAZA": "PLZ", "PLZ": "PLZ", "SQUARE": "SQ", "SQ": "SQ", "WALK": "WALK", "TUNNEL": "TUNL",
}
DIRECTIONAL = {"N": "N", "NORTH": "N", "S": "S", "SOUTH": "S", "E": "E", "EAST": "E", "W": "W", "WEST": "W"}
ORDINAL_WORDS = {
    "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5, "SIXTH": 6, "SEVENTH": 7,
    "EIGHTH": 8, "NINTH": 9, "TENTH": 10, "ELEVENTH": 11, "TWELFTH": 12,
}
# Travel-direction and descriptive noise that never belongs to the street name.
NOISE = re.compile(
    r"\b(N/?B|S/?B|E/?B|W/?B|NORTHBOUND|SOUTHBOUND|EASTBOUND|WESTBOUND|BLOCK|BLK|"
    r"OFF[- ]?RAMP|ON[- ]?RAMP|RAMP|UNDERCROSSING|OVERCROSSING|U/C|O/C|OVERPASS|UNDERPASS|"
    r"PEDESTRIAN|ENTRANCE|EXIT|OF THE|THE|OF|AT|NEAR|AND)\b"
)
ROUTE = re.compile(r"^(I|US|SR|CA|STATE ROUTE|INTERSTATE|HWY|HIGHWAY|ROUTE|RT|RTE)[\s-]*(\d+)")


class StreetKey(NamedTuple):
    core: str          # e.g. "ALEMANY", "7TH", "US 101"
    suffix: str | None  # e.g. "BLVD"; None when not written


def _ordinal(n: int) -> str:
    tail = "TH" if 10 <= n % 100 <= 20 else {1: "ST", 2: "ND", 3: "RD"}.get(n % 10, "TH")
    return f"{n}{tail}"


_IMPL = None  # set by use(); None = our own rules


def use(name: str) -> None:
    """Pick the normalizer for the bake-off: ours | ours_usps | usaddress | libpostal (see normalizers.py)."""
    global _IMPL
    from .normalizers import IMPLS
    _IMPL = IMPLS[name]


# A route number anywhere in a road field: SR-1, RT 46, HWY 111, STATE ROUTE 1, "PCH - SR1", I-880 (#83). Three digits
# at most, so a ZIP code ("CA 90249") is never a route.
ROUTE_ANY = re.compile(r"\b(?:STATE ROUTE|INTERSTATE|HIGHWAY|ROUTE|HWY|RTE|RT|SR|CA|US|I)[\s-]*(\d{1,3})\b")
_ROUTE_KEY = re.compile(r"^(I|US|SR) (\d+)$")
ROUTE_SPELLINGS = {"SR": ("SR", "RT", "RTE", "HWY", "HIGHWAY", "ROUTE", "STATEROUTE", "CA"),
                   "I": ("I", "INTERSTATE"), "US": ("US", "HWY", "HIGHWAY")}


def route_number(k: StreetKey | None) -> str | None:
    """'1' for the key of SR 1 / CA 1 / RT 1; None for a named street."""
    m = _ROUTE_KEY.match(k.core) if k else None
    return str(int(m.group(2))) if m else None


def route_numbers(raw: str | None) -> set[str]:
    return {str(int(m.group(1))) for m in ROUTE_ANY.finditer(str(raw or "").upper())}


def street_key(raw: str | None, aliases: dict[str, str] | None = None) -> StreetKey | None:
    if aliases and raw:
        k = re.sub(r"\s+", " ", re.sub(r"[.,#'\"]", " ", raw.upper())).strip()
        raw = aliases.get(k, raw)
    return _IMPL(raw) if _IMPL else _street_key_ours(raw)


def _street_key_ours(raw: str | None, aliases: dict[str, str] | None = None) -> StreetKey | None:
    if not raw:
        return None
    s = raw.upper()
    s = re.sub(r"\(.*?\)", " ", s)              # "(3100 BLOCK)"
    s = re.sub(r"[.,#'\"]", " ", s).replace("&", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if aliases and s in aliases:
        s = aliases[s]
    route = ROUTE.match(s)
    if route:
        kind = {"INTERSTATE": "I", "STATE ROUTE": "SR", "CA": "SR", "HWY": "SR", "HIGHWAY": "SR", "ROUTE": "SR", "RT": "SR", "RTE": "SR"}.get(route.group(1), route.group(1))
        return StreetKey(f"{kind} {int(route.group(2))}", None)
    s = re.sub(r"^\d+\s+(?=[A-Z])", "", s)       # house number "3144 W 147TH ST"
    s = NOISE.sub(" ", s)
    s = s.replace("/", " ").replace("-", " ")    # Alvarado-Niles Road = ALVARADO NILES RD (#80); routes matched above
    toks = [t for t in s.split() if t]
    if not toks:
        return None
    if len(toks) > 1 and toks[0] in DIRECTIONAL:  # keep it ("SOUTH VAN NESS" is its own street), spelled out
        toks[0] = {"N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST"}[DIRECTIONAL[toks[0]]]
    toks = [str(int(t[:-2])) + t[-2:] if re.fullmatch(r"0\d+(ST|ND|RD|TH)", t) else t for t in toks]  # 07TH -> 7TH
    toks = [_ordinal(ORDINAL_WORDS[t]) if t in ORDINAL_WORDS else t for t in toks]
    suffix = None
    if len(toks) > 1 and toks[-1] in SUFFIX:
        suffix = SUFFIX[toks.pop()]
    elif len(toks) > 1 and toks[-1] in DIRECTIONAL:  # trailing directional
        toks.pop()
        if len(toks) > 1 and toks[-1] in SUFFIX:
            suffix = SUFFIX[toks.pop()]
    core = " ".join(toks)
    return StreetKey(core, suffix) if core else None


def same_street(a: StreetKey, b: StreetKey) -> bool:
    """Exact tier: same core (spaces ignored, so BAY SHORE == BAYSHORE), suffixes compatible."""
    if a.core.replace(" ", "") != b.core.replace(" ", ""):
        return False
    return a.suffix is None or b.suffix is None or a.suffix == b.suffix


_LEAD_DIR = re.compile(r"^(NORTH|SOUTH|EAST|WEST) ")


def drop_directional(k: StreetKey) -> StreetKey:
    return StreetKey(_LEAD_DIR.sub("", k.core), k.suffix)


def same_core(a: StreetKey, b: StreetKey) -> bool:
    """Relaxed tier: same core, any suffix (GEARY ST for GEARY BLVD); a leading directional may be
    missing on one side only (W 147TH ST vs 147TH ST). A freeway is never relaxed to a street of another kind:
    HARBOR FWY (I-110) is not HARBOR BLVD (before #67 FWY wasn't a suffix, so these never matched)."""
    if (a.suffix == "FWY") != (b.suffix == "FWY") and a.suffix and b.suffix:
        return False
    ca, cb = a.core.replace(" ", ""), b.core.replace(" ", "")
    if ca == cb:
        return True
    da, db = drop_directional(a).core.replace(" ", ""), drop_directional(b).core.replace(" ", "")
    return (da == cb and da != ca) or (db == ca and db != cb)


def similarity(a: StreetKey, b: StreetKey) -> float:
    """Fuzzy tier score in [0, 1] on the core; a suffix conflict costs 0.1."""
    r = SequenceMatcher(None, a.core.replace(" ", ""), b.core.replace(" ", "")).ratio()
    if a.suffix and b.suffix and a.suffix != b.suffix:
        r -= 0.1
    return r


def load_aliases(path: Path) -> dict[str, str]:
    """raw (upper, punctuation-stripped) -> replacement, from a reviewed CSV with header raw,replacement."""
    if not path.exists():
        return {}
    with path.open() as f:
        return {row["raw"].strip().upper(): row["replacement"].strip().upper() for row in csv.DictReader(f)}
