"""N7 / #67: crashes on roads that pass over or under the corridor, and the freeway-corridor rules.

CCRS PrimaryRoad is the road the crash happened on, SecondaryRoad the reference street (CHP 555 convention).
- A crash ON a grade-separated crossing road (PrimaryRoad names it, not the corridor) is excluded with rule
  `grade_separated_crossing`: that road never meets the corridor.
- A crash on the corridor that only uses the crossing as its reference point ("UNION CITY BL 200 FT N OF I-880")
  is on the corridor and stays in: it is a segment crash unless it falls within the radius of a real intersection.
- Freeway corridor (OSM highway=motorway): only CHP IsFreeway crashes count. Others (the crossing road, ramp
  terminals on local streets) are excluded as `not_on_freeway`; ramp crashes as `ramp` unless the study's
  ramp/freeway include switch is on (#34 item 9).
"""

from __future__ import annotations

import re

from .names import StreetKey, same_core, street_key

_ROUTE = re.compile(r"^(I|US|SR) (\d+)$")
_RAMP = re.compile(r"\b(RAMP|RAMPS|ONR|OFR|ON-RAMP|OFF-RAMP|CONNECTOR)\b")


def _route_no(k: StreetKey) -> str | None:
    m = _ROUTE.match(k.core)
    return m.group(2) if m else None


def same_road(a: StreetKey, b: StreetKey) -> bool:
    """Street-key match, plus route numbers across kinds (CHP writes I-880 as RT 880 or SR 880)."""
    if same_core(a, b):
        return True
    ra, rb = _route_no(a), _route_no(b)
    return ra is not None and ra == rb


def keys_of(names: list[str]) -> list[StreetKey]:
    out = []
    for n in names:
        for part in str(n or "").split("/"):
            k = street_key(part)
            if k and k.core != "UNNAMED ROAD":
                out.append(k)
    return out


def crossing_keys(net: dict) -> list[StreetKey]:
    return keys_of([g.get("name") for g in net.get("grade_separations") or []])


def names(raw: str | None, keys: list[StreetKey]) -> bool:
    k = street_key(raw)
    return bool(k) and any(same_road(k, x) for x in keys)


def on_crossing_road(crash: dict, corridor: list[StreetKey], crossings: list[StreetKey]) -> bool:
    """The crash happened on a road that passes over or under the corridor (not on the corridor itself)."""
    pr = crash.get("primary_road")
    if is_ramp(crash):          # ramps are the freeway rules' business (#34 item 9 switch), not a crossing road
        return False
    return bool(crossings) and names(pr, crossings) and not names(pr, corridor)


def is_ramp(crash: dict) -> bool:
    return any(_RAMP.search(str(crash.get(f) or "").upper()) for f in ("primary_road", "secondary_road"))


def freeway_rule(crash: dict, include_ramps: bool) -> str | None:
    """Exclusion rule for a crash on a freeway corridor, or None when it counts."""
    if not crash.get("is_freeway"):
        return "not_on_freeway"
    if is_ramp(crash) and not include_ramps:
        return "ramp"
    return None
