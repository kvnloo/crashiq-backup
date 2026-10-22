"""C4 in the app: place crashes that came without coordinates, using the locator validated in PR #16.

Runs right after a crash pull, on the corridor's own OpenStreetMap data (the cached Overpass response, so no new
download). The pull already keeps only no-coordinate reports on the study stretch (#48). Placed crashes get the tier
as provenance (`exact`, ...); the rest stay `unmatched` with the locator's suggestion for the review list.
Auto-placement follows `locate.Gate()` (default: only tiers proven >= 98% on held-out data, i.e. `exact`);
any change to the gate is the user's decision (docs/03, PR #16 decision 2).
"""

from __future__ import annotations

from . import fars, grade, locate, osm
from . import network as network_mod
from .db import Database


def _at_named_intersection(c: dict, net: dict) -> bool:
    """The point is within the GPS-check distance (+ offset) of the study intersection the report names: there both of
    its roads meet, so it fits both (#195)."""
    import math

    from .assign import GPS_CHECK_FT, _stated_intersection
    from .geo import Polyline
    studies = [i for i in net.get("intersections", []) if i.get("is_study") and i.get("lat") is not None]
    st = _stated_intersection(c, studies, grade.corridor_keys(net)) if studies else None
    if st is None:
        return False
    line = Polyline([tuple(q) for q in net["line"]])
    (x, y), (sx, sy) = line.proj.to_xy(c["lat"], c["lon"]), line.proj.to_xy(st["lat"], st["lon"])
    return math.hypot(x - sx, y - sy) <= GPS_CHECK_FT + (c.get("offset_ft") or 0.0)


def _gps_usable(c: dict, net: dict) -> bool:
    """The GPS check the assignment itself applies (#191, Atwater): GPS is unusable only when the assignment would drop
    it as on another street (`not_on_corridor_street`) or flag it far from the intersection the report names. A
    stricter test (the report must name the corridor) moved GPS that the assignment accepts."""
    from .assign import assign
    if not net.get("intersections") and not net.get("segments"):
        from .crashes import point_fits_streets
        return point_fits_streets(c, net)
    x = assign([c], net, net.get("radius_ft", 250), net.get("buffer_ft", 100))["assignments"][0]
    return x.get("rule") != "not_on_corridor_street" and not x.get("gps_check")


def place_fatal_from_fars(db: Database | None, net: dict, result: dict, overpass=None) -> dict:
    """Fatal crashes first (#174, user decision 2026-10-21): a fatal crash with no usable location (no GPS and no
    placement by the street-name locator, or GPS the assignment rejects or flags) takes its linked FARS point like GPS
    when the point lies on a road the report names
    (within the GPS-check distance + the report's offset); assignment then decides: on the study stretch it's
    placed, elsewhere it's excluded and listed as `fars_off_corridor` with its distance (PM review of #182). A point on
    none of the report's roads isn't used; the crash keeps its place on the review list with a `fars_hint`."""
    from .assign import GPS_CHECK_FT
    from .geo import Polyline
    counts = {"tried": 0, "placed": 0, "point_not_on_named_road": 0, "no_point": 0, "ambiguous": 0, "unlinked": 0,
              "no_fars_year": 0}
    if db is None or not net.get("line"):
        return counts
    try:
        loaded = fars.years_loaded(db)
    except Exception:  # noqa: BLE001 - a database without the store (older schema in a test double) means no FARS
        loaded = []
    if not loaded:
        return counts
    line = Polyline([tuple(p) for p in net["line"]])
    for c in result["crashes"]:
        if (c.get("killed") or 0) <= 0 or c.get("exclude_rule"):
            continue
        src = c.get("location_source")
        if src not in ("unmatched", "gps", "gps_dms_corrected"):
            continue                       # placed by the locator (exact) or by hand: a usable location (#191)
        if src != "unmatched" and (c.get("lat") is None or _gps_usable(c, net)):
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
        radius_m = (GPS_CHECK_FT + (c.get("offset_ft") or 0.0)) / 3.28084
        if not (_at_named_intersection(trial, net)
                or fars.on_named_roads(network_mod.roads_near(db, p[0], p[1], radius_m, overpass), c)):
            counts["point_not_on_named_road"] += 1
            c["fars_hint"] = {"fars_case": fars.case_key(row["year"], row["st_case"]), "lat": p[0], "lon": p[1],
                              "miles_from_corridor": round(line.project(p[0], p[1]).offset_ft / 5280, 1)}
            continue
        c.update(lat=p[0], lon=p[1], location_source="fars", fars_case=fars.case_key(row["year"], row["st_case"]),
                 review_reason=None, suggestion=None,
                 gps_replaced=[c["lat"], c["lon"]] if src != "unmatched" else None)
        counts["placed"] += 1
    return counts


def place_unmatched(db: Database, net: dict, result: dict, gate: locate.Gate | None = None, overpass=None) -> dict:
    gate = gate or locate.Gate()
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
    # FARS only after the locator: a fatal crash it placed exactly has a usable location (#191)
    result["cleaning"]["fars"] = place_fatal_from_fars(db, net, result, overpass)
    result["cleaning"]["placement"] = counts
    return counts
