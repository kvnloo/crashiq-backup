"""Alternative street-name normalizers for the bake-off (user, 2026-10-18: "use public tools, compare").

Each returns the same StreetKey(core, suffix) as `names.street_key`, so the locator and the hidden-GPS test run
unchanged. Activate one with `names.use(<name>)` before building the street network.

  ours        names.street_key as written (baseline)
  ours_usps   ours, with the official USPS Pub 28 suffix table (via usaddress-scourgify) added
  usaddress   usaddress CRF parser for the parts + USPS table (replaces our tokenizer)
  libpostal   libpostal expand_address (statistical normalizer trained on OSM/OpenAddresses)
"""

from __future__ import annotations

from functools import lru_cache

from . import names
from .names import StreetKey

_DIR_LONG = {"N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST", "NORTH": "NORTH", "SOUTH": "SOUTH",
             "EAST": "EAST", "WEST": "WEST", "NE": "NORTHEAST", "NW": "NORTHWEST", "SE": "SOUTHEAST", "SW": "SOUTHWEST"}


@lru_cache(maxsize=1)
def usps_suffixes() -> dict[str, str]:
    """USPS Pub 28 street types (scourgify) mapped onto our canonical forms, ours winning on conflicts."""
    from scourgify.address_constants import STREET_TYPE_ABBREVIATIONS
    ours = dict(names.SUFFIX)
    canon = {v: v for v in ours.values()}
    merged = {}
    for longhand, usps in STREET_TYPE_ABBREVIATIONS.items():
        merged[longhand.upper()] = canon.get(usps.upper(), usps.upper())
    merged.update(ours)
    return merged


@lru_cache(maxsize=200_000)
def ours_usps(raw: str | None) -> StreetKey | None:
    saved = names.SUFFIX
    try:
        names.SUFFIX = usps_suffixes()
        return names._street_key_ours(raw)
    finally:
        names.SUFFIX = saved


@lru_cache(maxsize=200_000)
def usaddress_key(raw: str | None) -> StreetKey | None:
    if not raw or not raw.strip():
        return None
    route = names._street_key_ours(raw)          # keep route handling (I-280, RT 101) identical across arms
    if route and route.core.split()[0] in ("I", "US", "SR") and route.suffix is None and route.core.split()[-1].isdigit():
        return route
    import usaddress
    try:
        parts, _ = usaddress.tag("1 " + raw.upper().replace(".", " "))
    except usaddress.RepeatedLabelError:
        return names._street_key_ours(raw)
    core = parts.get("StreetName", "").strip()
    pre = parts.get("StreetNamePreDirectional", "").strip().upper()
    if pre in _DIR_LONG:
        core = f"{_DIR_LONG[pre]} {core}".strip()
    typ = parts.get("StreetNamePostType", "").strip().upper()
    suffix = usps_suffixes().get(typ) if typ else None
    if not core:
        return None
    core = " ".join(t.lstrip("0") if t[:1] == "0" and t[1:2].isdigit() else t for t in core.split())
    ordinal_words = {k: names._ordinal(v) for k, v in names.ORDINAL_WORDS.items()}
    core = " ".join(ordinal_words.get(t, t) for t in core.split())
    return StreetKey(core, suffix)


@lru_cache(maxsize=200_000)
def libpostal_key(raw: str | None) -> StreetKey | None:
    if not raw or not raw.strip():
        return None
    from postal.expand import expand_address
    exps = expand_address(raw.upper().replace("/", " "))  # libpostal ranks its own expansions; keep its first
    if not exps:
        return None
    suffixes = usps_suffixes()
    # libpostal's top expansion can read ST as "Saint" (MISSION ST -> "mission saint"); prefer the highest-ranked
    # expansion that ends in a street type, which is what a crash report's street field is.
    typed = [e for e in exps if len(e.split()) > 1 and e.split()[-1].upper() in suffixes]
    toks = (typed or exps)[0].upper().split()
    suffix = suffixes.get(toks[-1]) if len(toks) > 1 and toks[-1] in suffixes else None
    if suffix:
        toks = toks[:-1]
    return StreetKey(" ".join(toks), suffix) if toks else None


IMPLS = {"ours": None, "ours_usps": ours_usps, "usaddress": usaddress_key, "libpostal": libpostal_key}
