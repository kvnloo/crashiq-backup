"""C4 in the app: place crashes that came without coordinates, using the locator validated in PR #16.

Runs right after a crash pull, on the corridor's own OpenStreetMap data (the cached Overpass response, so no
new download). Each crash keeps its provenance: placed ones get the tier (`exact`, ...), the rest stay
`unmatched` with the locator's suggestion for the review list, and crashes whose cross street isn't on the
corridor at all are marked `outside_corridor` (counted as excluded, not as unplaced).

Auto-placement follows `locate.Gate()` (default: only tiers proven >= 98% on held-out data, i.e. `exact`).
The user decides any change to the gate (docs/03, PR #16 decision 2).
"""

from __future__ import annotations

from . import locate, osm
from . import network as network_mod
from .db import Database
from .names import same_core, street_key


def place_unmatched(db: Database, net: dict, result: dict, gate: locate.Gate | None = None) -> dict:
    gate = gate or locate.Gate()
    todo = [c for c in result["crashes"] if c.get("location_source") == "unmatched"]
    counts = {"tried": len(todo), "placed": {}, "suggested": 0, "outside_corridor": 0, "still_unplaced": 0}
    if todo:
        raw = network_mod.fetch_overpass(db, network_mod.overpass_query([tuple(p) for p in net["line"]]))
        onet = osm.Network(raw)
        corridor = street_key(net.get("corridor_name"))
        for c in todo:
            pl = locate.place(onet, c)
            if gate.auto(pl):
                c["lat"], c["lon"], c["location_source"] = pl.lat, pl.lon, pl.tier
                counts["placed"][pl.tier] = counts["placed"].get(pl.tier, 0) + 1
                continue
            if pl.lat is not None:
                c["suggestion"] = {"tier": pl.tier, "lat": pl.lat, "lon": pl.lon}
                counts["suggested"] += 1
            if _cross_street_off_corridor(onet, c, corridor):
                c["outside_corridor"] = True
                counts["outside_corridor"] += 1
            else:
                counts["still_unplaced"] += 1
    result["cleaning"]["placement"] = counts
    return counts


def _cross_street_off_corridor(onet: osm.Network, crash: dict, corridor) -> bool:
    """True when the report's other street doesn't appear anywhere on the corridor's street map."""
    keys = [street_key(crash.get("primary_road")), street_key(crash.get("secondary_road"))]
    others = [k for k in keys if k and not (corridor and same_core(k, corridor))]
    if not others:
        return False
    return not any(same_core(k, s) for k in others for s in onet.streets)
