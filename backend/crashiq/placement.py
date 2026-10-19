"""C4 in the app: place crashes that came without coordinates, using the locator validated in PR #16.

Runs right after a crash pull, on the corridor's own OpenStreetMap data (the cached Overpass response, so no new
download). The pull already keeps only no-coordinate reports on the study stretch (#48). Placed crashes get the tier
as provenance (`exact`, ...); the rest stay `unmatched` with the locator's suggestion for the review list.
Auto-placement follows `locate.Gate()` (default: only tiers proven >= 98% on held-out data, i.e. `exact`);
any change to the gate is the user's decision (docs/03, PR #16 decision 2).
"""

from __future__ import annotations

from . import locate, osm
from . import network as network_mod
from .db import Database


def place_unmatched(db: Database, net: dict, result: dict, gate: locate.Gate | None = None) -> dict:
    gate = gate or locate.Gate()
    todo = [c for c in result["crashes"] if c.get("location_source") == "unmatched" and not c.get("exclude_rule")]
    counts = {"tried": len(todo), "placed": {}, "suggested": 0, "still_unplaced": 0}
    if todo and net.get("line"):
        raw = network_mod.fetch_overpass(db, network_mod.overpass_query([tuple(p) for p in net["line"]]))
        onet = osm.Network(raw)
        for c in todo:
            pl = locate.place(onet, c)
            if gate.auto(pl):
                c["lat"], c["lon"], c["location_source"] = pl.lat, pl.lon, pl.tier
                counts["placed"][pl.tier] = counts["placed"].get(pl.tier, 0) + 1
                continue
            if pl.lat is not None:
                c["suggestion"] = {"tier": pl.tier, "lat": pl.lat, "lon": pl.lon}
                counts["suggested"] += 1
            counts["still_unplaced"] += 1
    result["cleaning"]["placement"] = counts
    return counts
