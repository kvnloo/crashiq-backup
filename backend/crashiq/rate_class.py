"""Which state-highway rate a crash counts in (#304; user decisions 2026-10-31 and 2026-11-01, docs/03 #297, #312).

Counting only: where a crash sits on the map never changes. Every placed crash on a rate corridor gets a class and the
reason, by rules in code:
- `ramp`: the report names a ramp; or reads "<route> <dir> TO <local street>" (the <dir> off-ramp to that street); or
  is a connector "<route> TO <route>" whose cross street is one of the two routes (ramps.report). Rated in T25.
- `mainline`: the primary road is the highway ("<route> TO <route>" with a local cross street included); or, on a
  conventional highway, the highway is the secondary road and the crash is at the intersection (`at_intersection`).
- `cross_street`: any other primary road (a cross street or a frontage road). On a freeway, always. In no rate.
Roads over or under a freeway (N7) are excluded before this, at assignment.

A mainline crash at a study intersection counts in a segment (answer 2a): the one on its GPS side, else the one after
the intersection in station order, else (the last intersection) the one before (`segment_for`).
"""

from __future__ import annotations

import re

from . import grade, ramps
from .names import bare_route, route_numbers, street_key
from .shs import corridor_routes

MAINLINE, RAMP, CROSS = "mainline", "ramp", "cross_street"
STATION_TIE_FT = 25.0       # a GPS this close to the intersection's station is at the station: its side is noise


def at_intersection(c: dict, radius_ft: float) -> bool:
    """A cross-street-primary crash is at the intersection when its distance is blank or within the study's
    intersection influence radius (user 2026-11-01: blank = 0; within the HSM influence area)."""
    d = c.get("offset_ft")
    return d is None or d <= radius_ft


def classify(c: dict, net: dict, radius_ft: float) -> tuple[str, str]:
    """(class, reason) for one crash on a state-highway corridor."""
    r = ramps.report(c)
    if r is not None:
        why = "freeway connector" if r.get("connector") else \
              "<route> <dir> TO <street>: the off-ramp" if r.get("to_street") else \
              "<route> <dir> FROM <street>: the on-ramp" if r.get("from_word") else \
              "<street> TO <route> <dir>: the on-ramp" if r.get("from_street") else "names a ramp"
        return RAMP, why
    keys = grade.corridor_keys(net)
    other = _other_route(c.get("primary_road"), net)
    if other:
        return CROSS, f"on another route's main lanes ({other})"
    if grade.names(c.get("primary_road"), keys) or \
            (route_numbers(c.get("primary_road")) | {bare_route(c.get("primary_road"))}) & corridor_routes(net):
        return MAINLINE, "on the highway"                    # by name, or by route number ("NORTHBOUND I-405 ...")
    if net.get("is_freeway"):
        return CROSS, "cross street on a freeway"
    if grade.names(c.get("secondary_road"), keys):
        return (MAINLINE, "at an intersection") if at_intersection(c, radius_ft) else \
               (CROSS, f"cross street, beyond {radius_ft:g} ft")
    return CROSS, "cross street or frontage road"


def _other_route(primary: str | None, net: dict) -> str | None:
    """"<route> TO <route>" with a local cross street is on the first route's main lanes (2026-10-25, placed like
    mainline on X): another route's when X isn't the corridor's ("I-110 S/B TO I-405 N/B" on I-405: "I-110")."""
    m = re.match(r"^(.+?)\s+TO\s+(.+)$", str(primary or "").upper())
    if not m or not route_numbers(m.group(1)) or not route_numbers(m.group(2)):
        return None
    if route_numbers(m.group(1)) & corridor_routes(net):
        return None
    k = street_key(m.group(1))
    return k.core.replace(" ", "-") if k and re.match(r"^(I|US|SR) \d+$", k.core) else m.group(1).strip()


def segment_for(it: dict, segments: list[dict], station_ft: float | None) -> str | None:
    """The segment an intersection's mainline crash counts in: the GPS side, else the one after, else the one before."""
    st = it["station_ft"]
    mid = lambda s: (s["from_station_ft"] + s["to_station_ft"]) / 2            # noqa: E731
    after = min((s for s in segments if mid(s) > st), key=lambda s: abs(s["from_station_ft"] - st), default=None)
    before = min((s for s in segments if mid(s) < st), key=lambda s: abs(s["to_station_ft"] - st), default=None)
    if station_ft is not None and station_ft < st - STATION_TIE_FT and before is not None:
        return before["id"]
    s = after or before
    return s["id"] if s else None
