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
# quadrant prefixes and suffixes (Portland's SE POWELL BLVD, DC's GEORGIA AVE NW): spelled out leading, dropped trailing (#19)
QUADRANT = {"NE": "NORTHEAST", "NW": "NORTHWEST", "SE": "SOUTHEAST", "SW": "SOUTHWEST",
            **{w: w for w in ("NORTHEAST", "NORTHWEST", "SOUTHEAST", "SOUTHWEST")}}
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
# Another state's own route prefix is a state route too (#19 state packs): CT 187, AR 10, MS 25, KY1747, PA 611, MN 55,
# and Minnesota's trunk-highway codes (ISTH 94 = I 94, USTH 169 = US 169, MNTH 13 = SR 13). Left out: CO ("CO 81" is as
# often a county road as Colorado 81) and the codes that are English words a report writes before a number (IN, OR,
# ME, OK, HI, DE, LA, ID, AL, MA: "IN 200 BLOCK"), NE (the quadrant: "NE 45TH ST") and MI (miles); those states'
# readers write their routes as SR n.
STATE_ROUTE_PREFIXES = ("AK", "AZ", "AR", "CT", "FL", "GA", "IL", "IA", "KS", "KY", "MD", "MN", "MS", "MO", "MT",
                        "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "PA", "RI", "SC", "SD", "TN", "TX", "UT",
                        "VT", "VA", "WA", "WV", "WI", "WY", "MNTH")
_STATES_RX = "|".join(STATE_ROUTE_PREFIXES)
ROUTE = re.compile(r"^(STATE HWY|STATE HIGHWAY|STATE RTE|STATE ROUTE|US HWY|US HIGHWAY|US ROUTE|ISTH|USTH|I|US|SR|CA|"
                   r"INTERSTATE|HWY|HIGHWAY|ROUTE|RT|RTE|" + _STATES_RX + r")[\s-]*(\d+)")
# a travel direction written before the route ("SB I-35E", "NB US 52") hides it from ROUTE
_LEAD_TRAVEL = re.compile(r"^(?:[NSEW]/?B|NORTHBOUND|SOUTHBOUND|EASTBOUND|WESTBOUND)\s+(?=\S)")


class StreetKey(NamedTuple):
    core: str          # e.g. "ALEMANY", "7TH", "US 101"
    suffix: str | None  # e.g. "BLVD"; None when not written


# Street types a bare number can stand before: NYC writes "E 26 ST", "4508 2 AVE", "63 DR"; TIGER and OSM write the
# ordinal ("E 26th St", "2nd Ave", "63rd Dr"). Only these, so "HWY 1", "AVENUE 26" and "PIER 39 WAY" never change (#19).
NUMBERED_TYPES = {"ST", "STREET", "AVE", "AVENUE", "AV", "RD", "ROAD", "PL", "PLACE", "DR", "DRIVE", "CT", "COURT",
                  "TER", "TERRACE", "LN", "LANE"}
# Abbreviated names a source spells as initials (Seattle: M L KING JR WAY S = Martin Luther King Jr Way S)
PHRASES = ((re.compile(r"\bM L KING\b"), "MARTIN LUTHER KING"),)


def _numbered(toks: list[str]) -> list[str]:
    """[EAST, 26, ST] -> [EAST, 26TH, ST]; [4508, 2, AVE] -> [2ND, AVE] (the leading number is the house number)."""
    j = len(toks) - 2 if len(toks) > 2 and toks[-1] in DIRECTIONAL else len(toks) - 1   # 26 ST W
    if j < 1 or toks[j] not in NUMBERED_TYPES or not re.fullmatch(r"\d{1,3}", toks[j - 1]):
        return toks
    head = toks[:j - 1]
    if head and not (len(head) == 1 and (head[0] in ("NORTH", "SOUTH", "EAST", "WEST") or head[0].isdigit())):
        return toks                                  # more words before the number: a name, not a numbered street
    head = [] if head and head[0].isdigit() else head
    return head + [_ordinal(int(toks[j - 1]))] + toks[j:]


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
ROUTE_ANY = re.compile(r"\b(?:STATE ROUTE|INTERSTATE|HIGHWAY|ROUTE|HWY|RTE|RT|SR|CA|US|I|ISTH|USTH|" + _STATES_RX
                       + r")[\s-]*(\d{1,3})\b")
_ROUTE_KEY = re.compile(r"^(I|US|SR) (\d+)$")
ROUTE_SPELLINGS = {"SR": ("SR", "RT", "RTE", "HWY", "HIGHWAY", "ROUTE", "STATEROUTE", "CA", *STATE_ROUTE_PREFIXES),
                   "I": ("I", "INTERSTATE", "ISTH"), "US": ("US", "HWY", "HIGHWAY", "USTH")}


# A route written bare in a freeway report (#334): "405 SB", "405 SOUTHBOUND", "99 HWY", "101 FWY", and "1-15 S/B"
# (a "1-" typed for "I-" before an interstate number). Callers read it only for the corridor's own route or a report
# CHP marks as freeway; never a house number ("405 MAIN ST"), a numbered street ("405TH ST") or a number alone.
_BARE = re.compile(r"^\s*(1\s*-\s*)?(\d{1,3})\s+(?:[NSEW]\s*/?\s*B|NORTHBOUND|SOUTHBOUND|EASTBOUND|WESTBOUND|HWY|HIGHWAY|"
                   r"FWY|FREEWAY|FRWY)\b")
INTERSTATES = {"5", "8", "10", "15", "40", "80", "105", "110", "205", "210", "215", "238", "280", "380", "405", "505",
               "580", "605", "680", "710", "780", "805", "880", "980"}


def bare_route(raw: str | None) -> str | None:
    m = _BARE.match(str(raw or "").upper())
    if not m:
        return None
    n = str(int(m.group(2)))
    return None if m.group(1) and n not in INTERSTATES else n


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
    for rx, full in PHRASES:
        s = rx.sub(full, s)
    if aliases and s in aliases:
        s = aliases[s]
    route = ROUTE.match(_LEAD_TRAVEL.sub("", s))
    if route:
        kind = {"ISTH": "I", "USTH": "US", **dict.fromkeys(STATE_ROUTE_PREFIXES, "SR"), "INTERSTATE": "I", "STATE ROUTE": "SR", "CA": "SR", "HWY": "SR", "HIGHWAY": "SR", "ROUTE": "SR", "RT": "SR",
                "RTE": "SR", "STATE HWY": "SR", "STATE HIGHWAY": "SR", "STATE RTE": "SR", "US HWY": "US",
                "US HIGHWAY": "US", "US ROUTE": "US"}.get(route.group(1), route.group(1))
        return StreetKey(f"{kind} {int(route.group(2))}", None)
    # a bare numbered street ("63 DRIVE", "2 AVE N") is the street, not a house number before a type word (#19)
    bare = re.fullmatch(r"\d{1,3} (?:" + "|".join(NUMBERED_TYPES) + r")(?: [NSEW]| NORTH| SOUTH| EAST| WEST)?", s)
    numbered = bool(re.match(r"^\d+\s+(?=[A-Z])", s)) and not bare
    if not bare:
        s = re.sub(r"^\d+\s+(?=[A-Z])", "", s)   # house number "3144 W 147TH ST"
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
    elif len(toks) > 1 and toks[0] in QUADRANT:
        toks[0] = QUADRANT[toks[0]]
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
    toks = _numbered(toks)
    suffix = None
    if len(toks) > 1 and toks[-1] in SUFFIX:
        suffix = SUFFIX[toks.pop()]
    elif len(toks) > 1 and (toks[-1] in DIRECTIONAL or toks[-1] in QUADRANT):  # trailing directional
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
