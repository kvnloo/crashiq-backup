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
    # CHP's own type abbreviations (alias batch A, user 2026-10-22, docs/03): general rules, every city
    "PW": "PKWY", "PY": "PKWY", "PKY": "PKWY", "EXPWY": "EXPY", "EXPRWY": "EXPY", "EX": "EXPY", "HW": "HWY",
    "TRAIL": "TRL", "TRL": "TRL", "TR": "TRL",
    # a trailing type word only (ARROW RT = Arrow Route); "RT 46" is a route number, read before this table
    "ROUTE": "RTE", "RTE": "RTE", "RT": "RTE",
}
# Words CHP shortens anywhere in a name (alias batch A): MARTIN LUTHER KING JR WY = Martin Luther King Junior Way
WORDS = {"JR": "JUNIOR", "CYN": "CANYON", "MTN": "MOUNTAIN", "HTS": "HEIGHTS"}
# A route tag after the name ("PACIFIC COAST HWY - SR1", "BEACH BL - SR39"): the route is read from the raw text
# (route_numbers), the name is what's left
ROUTE_TAIL = re.compile(r"\s+-\s*(?:SR|RT|RTE|HWY|US|I|CA)[\s-]*\d+\s*$")
DIRECTIONAL = {"N": "N", "NORTH": "N", "S": "S", "SOUTH": "S", "E": "E", "EAST": "E", "W": "W", "WEST": "W"}
ORDINAL_WORDS = {
    "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5, "SIXTH": 6, "SEVENTH": 7,
    "EIGHTH": 8, "NINTH": 9, "TENTH": 10, "ELEVENTH": 11, "TWELFTH": 12,
}
# Travel-direction and descriptive noise that never belongs to the street name.
# Abbreviations that start a name (#212); the spelled-out word is the key
LEADING = {"AVE": "AVENUE", "AV": "AVENUE", "AVN": "AVENUE", "BL": "BOULEVARD", "BLVD": "BOULEVARD",
           "ST": "SAINT", "MT": "MOUNT", "FT": "FORT"}
NOISE = re.compile(
    r"\b(N/?B|S/?B|E/?B|W/?B|NORTHBOUND|SOUTHBOUND|EASTBOUND|WESTBOUND|BLOCK|BLK|"
    r"OFF[- ]?RAMP|ON[- ]?RAMP|RAMP|UNDERCROSSING|OVERCROSSING|U/C|O/C|OVERPASS|UNDERPASS|"
    r"PEDESTRIAN|ENTRANCE|EXIT|BIKE LANE|OF THE|THE|OF|AT|NEAR|AND)\b"
)
# TIGER/Line writes State Hwy 39, State Rte 1, US Hwy 101, I- 5 (#229)
ROUTE = re.compile(r"^(STATE HWY|STATE HIGHWAY|STATE RTE|STATE ROUTE|US HWY|US HIGHWAY|US ROUTE|I|US|SR|CA|INTERSTATE|HWY|"
                   r"HIGHWAY|ROUTE|RT|RTE)[\s-]*(\d+)")


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
    s = re.sub(r"\(.*?\)", " ", s)              # "(3100 BLOCK)", "(N)"
    s = ROUTE_TAIL.sub("", s)
    s = re.sub(r"[.,#'\"]", " ", s).replace("&", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if aliases and s in aliases:
        s = aliases[s]
    route = ROUTE.match(s)
    if route:
        kind = {"INTERSTATE": "I", "STATE ROUTE": "SR", "CA": "SR", "HWY": "SR", "HIGHWAY": "SR", "ROUTE": "SR", "RT": "SR",
                "RTE": "SR", "STATE HWY": "SR", "STATE HIGHWAY": "SR", "STATE RTE": "SR", "US HWY": "US",
                "US HIGHWAY": "US", "US ROUTE": "US"}.get(route.group(1), route.group(1))
        return StreetKey(f"{kind} {int(route.group(2))}", None)
    numbered = bool(re.match(r"^\d+\s+(?=[A-Z])", s))
    s = re.sub(r"^\d+\s+(?=[A-Z])", "", s)       # house number "3144 W 147TH ST"
    # "Avenue of Flags", "Avenue of the Stars": OF belongs to the name here. CHP writes AVE OF, AV OF, and adds or drops
    # THE (Buellton: AVENUE OF FLAGS and AVENUE OF THE FLAGS), so THE is left out of the key (#154)
    s = re.sub(r"\b(?:AVENUE|AVE|AV) OF (?:THE )?", "AVENUE_OF_", s)
    s = NOISE.sub(" ", s).replace("_", " ")
    s = s.replace("/", " ").replace("-", " ")    # Alvarado-Niles Road = ALVARADO NILES RD (#80); routes matched above
    toks = [t for t in s.split() if t]
    if not toks:
        return None
    if len(toks) > 1 and toks[0] in DIRECTIONAL:  # keep it ("SOUTH VAN NESS" is its own street), spelled out
        toks[0] = {"N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST"}[DIRECTIONAL[toks[0]]]
    # a street type or title written first is the start of the name, not a suffix: AVE M = Avenue M, ST TROPEZ CT =
    # Saint Tropez Court, MT VERNON AVE = Mount Vernon Avenue (#212). Only when a name follows it: "W ST" is West
    # Street, and ST HWY is a highway
    i = 1 if len(toks) > 2 and toks[0] in ("NORTH", "SOUTH", "EAST", "WEST") else 0
    rest = toks[i + 1:]
    if (toks[i] in LEADING and rest and not (len(rest) == 1 and rest[0] in SUFFIX)
            and not (toks[i] == "ST" and rest[0] in ("HWY", "HIGHWAY", "RTE", "ROUTE", "RT"))
            and not (toks[i] == "FT" and (numbered or rest[0] in DIRECTIONAL))):   # 100 FT NORTH OF: feet
        toks[i] = LEADING[toks[i]]
    toks = [str(int(t[:-2])) + t[-2:] if re.fullmatch(r"0\d+(ST|ND|RD|TH)", t) else t for t in toks]  # 07TH -> 7TH
    toks = [_ordinal(ORDINAL_WORDS[t]) if t in ORDINAL_WORDS else t for t in toks]
    toks = [WORDS.get(t, t) for t in toks]
    suffix = None
    if len(toks) > 1 and toks[-1] in SUFFIX:
        suffix = SUFFIX[toks.pop()]
    elif len(toks) > 1 and toks[-1] in DIRECTIONAL:  # trailing directional
        toks.pop()
        if len(toks) > 1 and toks[-1] in SUFFIX:
            suffix = SUFFIX[toks.pop()]
    core = " ".join(toks)
    return StreetKey(core, suffix) if core else None


def directions(raw: str | None, aliases: dict[str, str] | None = None) -> tuple[str | None, str | None]:
    """(leading, trailing) direction as written: N, S, E, W or None. street_key keeps a leading one in the core and
    drops a trailing one ("20TH ST W" and "20th Street East" share a key), so the unique-pair tier reads them here
    (#203)."""
    if not raw:
        return None, None
    s = re.sub(r"\s+", " ", re.sub(r"[.,#'\"]", " ", raw.upper())).strip()
    if aliases and s in aliases:
        s = aliases[s]
    if ROUTE.match(s):
        return None, None
    toks = re.sub(r"\(.*?\)", " ", s).replace("&", " ").split()
    if len(toks) < 2:
        return None, None
    return DIRECTIONAL.get(toks[0]), (DIRECTIONAL.get(toks[-1]) if len(toks) > 2 or toks[0] not in DIRECTIONAL else None)


def _flat(core: str) -> str:
    """Core for comparison: spaces ignored (BAY SHORE == BAYSHORE), and an inner OF / OF THE too (AVENUE OF FLAGS ==
    AVENUE FLAGS, #154)."""
    return re.sub(r" OF (THE )?", " ", core).replace(" ", "")


def same_street(a: StreetKey, b: StreetKey) -> bool:
    """Exact tier: same core (spaces ignored, so BAY SHORE == BAYSHORE), suffixes compatible."""
    if _flat(a.core) != _flat(b.core):
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
    ca, cb = _flat(a.core), _flat(b.core)
    if ca == cb:
        return True
    da, db = _flat(drop_directional(a).core), _flat(drop_directional(b).core)
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
