"""C4 in the app: place crashes that came without coordinates, using the locator validated in PR #16.

Runs right after a crash pull, on the corridor's own OpenStreetMap data (the cached Overpass response, so no new
download). The pull already keeps only no-coordinate reports on the study stretch (#48). Placed crashes get the tier
as provenance (`exact`, ...); the rest stay `unmatched` with the locator's suggestion for the review list.
Auto-placement follows `locate.Gate()` (default: only tiers proven >= 98% on held-out data, i.e. `exact`);
any change to the gate is the user's decision (docs/03, PR #16 decision 2).
"""

from __future__ import annotations

from . import fars, locate, osm
from . import network as network_mod
from .db import Database


def place_fatal_from_fars(db: Database | None, net: dict, result: dict) -> dict:
    """Fatal crashes first (#174, user decision 2026-10-21): a fatal crash with no usable location (no GPS, or GPS that
    fails the street check) takes its linked FARS point when that point fits the report's streets; provenance `fars`.
    Anything else stays as it was (review list, or its own GPS)."""
    from .crashes import point_fits_streets
    counts = {"tried": 0, "placed": 0, "linked_point_off_streets": 0, "no_point": 0, "ambiguous": 0, "unlinked": 0,
              "no_fars_year": 0}
    if db is None or not net.get("line"):
        return counts
    try:
        loaded = fars.years_loaded(db)
    except Exception:  # noqa: BLE001 - a database without the store (older schema in a test double) means no FARS
        loaded = []
    if not loaded:
        return counts
    for c in result["crashes"]:
        if (c.get("killed") or 0) <= 0 or c.get("exclude_rule"):
            continue
        src = c.get("location_source")
        if src not in ("unmatched", "gps", "gps_dms_corrected"):
            continue
        if src != "unmatched" and (c.get("lat") is None or point_fits_streets(c, net)):
            continue                                       # its own GPS checks out
        counts["tried"] += 1
        status, row = fars.link(db, c)
        if status != "linked":
            counts[status] += 1
            continue
        p = fars.point(db, row)
        if p is None:
            counts["no_point"] += 1
            continue
        trial = {**c, "lat": p[0], "lon": p[1]}
        if not point_fits_streets(trial, net):
            counts["linked_point_off_streets"] += 1
            continue
        c.update(lat=p[0], lon=p[1], location_source="fars", fars_case=fars.case_key(row["year"], row["st_case"]),
                 review_reason=None, suggestion=None,
                 gps_replaced=[c["lat"], c["lon"]] if src != "unmatched" else None)
        counts["placed"] += 1
    return counts


def place_unmatched(db: Database, net: dict, result: dict, gate: locate.Gate | None = None) -> dict:
    gate = gate or locate.Gate()
    result["cleaning"]["fars"] = place_fatal_from_fars(db, net, result)
    # no cross street (#94): nothing for the locator to work with; the engineer places it from the review list
    todo = [c for c in result["crashes"] if c.get("location_source") == "unmatched" and not c.get("exclude_rule")
            and not c.get("review_reason")]
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
