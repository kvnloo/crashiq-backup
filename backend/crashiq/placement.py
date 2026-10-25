"""C4 in the app: place crashes that came without coordinates, using the locator validated in PR #16.

Runs right after a crash pull, on the corridor's own OpenStreetMap data (the cached Overpass response, so no new
download). The pull already keeps only no-coordinate reports on the study stretch (#48). Placed crashes get the tier
as provenance (`exact`, ...); the rest stay `unmatched` with the locator's suggestion for the review list.
Auto-placement follows `locate.Gate()` (the tiers in config/placement.json: `exact` and `unique_pair`);
any change to the gate is the user's decision (docs/03, PR #16 decision 2).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import fars, freeway, gps_rules, grade, locate, osm
from . import network as network_mod
from . import union as union_mod
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


def place_fatal_from_fars(db: Database | None, net: dict, result: dict, overpass=None, tiger=None) -> dict:
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
        if src not in ("unmatched", "gps", "gps_dms_corrected", "gps_sign_corrected", "gps_offset_applied"):
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
                or fars.on_named_roads(network_mod.roads_near(db, p[0], p[1], radius_m, overpass)
                                       + union_mod.tiger_roads_near(tiger, p[0], p[1], radius_m), c)):
            counts["point_not_on_named_road"] += 1
            c["fars_hint"] = {"fars_case": fars.case_key(row["year"], row["st_case"]), "lat": p[0], "lon": p[1],
                              "miles_from_corridor": round(line.project(p[0], p[1]).offset_ft / 5280, 1)}
            continue
        c.update(lat=p[0], lon=p[1], location_source="fars", fars_case=fars.case_key(row["year"], row["st_case"]),
                 review_reason=None, suggestion=None,
                 gps_replaced=[c["lat"], c["lon"]] if src != "unmatched" else None)
        counts["placed"] += 1
    return counts


# moving officer GPS that disagrees with the report (D1 rule 4) has its own switch, off until the user confirms it (#255)
MOVE_GPS = bool(json.loads((Path(__file__).parent / "config" / "placement.json").read_text()).get("freeway_move_gps"))
APPROX_MI = json.loads((Path(__file__).parent / "config" / "placement.json").read_text()).get("approximate_mi", 0.5)
GPS_LIKE = ("gps", "gps_dms_corrected", "gps_sign_corrected", "gps_offset_applied")


def _freeway_gps(raw: dict, crashes: list[dict]) -> int:
    """The report beats the officer's GPS on a freeway when they disagree (#246, docs/03 D1 rule 4): a GPS point more
    than the GPS-check distance from the spot the report describes moves there; the GPS stays as provenance.
    Only when config/placement.json freeway_move_gps is on (#255: off until the user confirms)."""
    from .assign import GPS_CHECK_FT
    from .osm import metres
    moved = 0
    for c in crashes:
        sp = freeway.place(raw, c)
        if sp is None:
            continue
        # the spot already includes the stated distance: GPS within the check distance of it agrees (Tester, D1 step 2)
        if metres((c["lat"], c["lon"]), (sp.lat, sp.lon)) * 3.28084 > GPS_CHECK_FT:
            c["gps_as_reported"] = [c["lat"], c["lon"]]
            c.update(lat=sp.lat, lon=sp.lon, location_source="freeway_offset", freeway_spot=sp.kind)
            moved += 1
    return moved


def place_unmatched(db: Database, net: dict, result: dict, gate: locate.Gate | None = None, overpass=None,
                    raw: dict | None = None, tiger=None) -> dict:
    gate = gate or locate.Gate()
    # no cross street (#94): nothing for the locator to work with; the engineer places it from the review list
    todo = [c for c in result["crashes"] if c.get("location_source") == "unmatched" and not c.get("exclude_rule")
            and not c.get("review_reason")]
    counts = {"tried": len(todo), "placed": {}, "suggested": 0, "still_unplaced": 0}
    # GPS snapped to the named intersection while the report states an offset (#218): the offset wins
    offset_cands = [c for c in result["crashes"] if c.get("location_source") in ("gps", "gps_dms_corrected", "gps_sign_corrected")
                    and (c.get("offset_ft") or 0) > gps_rules.CONFIG["offset_min_ft"] and c.get("offset_dir")]
    # freeway crashes on a freeway corridor (#246, D1): placed by the report; GPS that disagrees with it is moved, gated
    fwy = bool(net.get("is_freeway"))
    fwy_gps = [c for c in result["crashes"] if fwy and c.get("is_freeway") and not c.get("exclude_rule")
               and c.get("location_source") in GPS_LIKE and c.get("lat") is not None] if MOVE_GPS else []
    onet = None
    if (todo or offset_cands or fwy_gps) and net.get("line"):
        if raw is None:                   # OSM only (the caller passes the OSM + TIGER network when it has one, #229)
            raw = network_mod.fetch_overpass(db, network_mod.overpass_query([tuple(p) for p in net["line"]]))
        onet = osm.Network(raw)
    result["cleaning"]["gps_offset_applied"] = gps_rules.apply_offsets(onet, net, offset_cands) if onet else 0
    counts["freeway_gps_moved"] = _freeway_gps(raw, fwy_gps) if fwy_gps else 0
    if todo and onet is not None:
        for c in todo:
            pl = locate.place(onet, c)
            # the street-name locator first: a freeway crash it places today keeps that placement (PM review of #252);
            # the report's freeway description is tried only when the locator doesn't auto-place
            sp = freeway.place(raw, c) if fwy and c.get("is_freeway") and not gate.auto(pl) else None
            if sp:
                pl = locate.Placement("freeway_offset", sp.lat, sp.lon, note=f"{sp.kind}: {sp.note}")
            if gate.auto(pl):
                c["lat"], c["lon"], c["location_source"] = pl.lat, pl.lon, pl.tier
                counts["placed"][pl.tier] = counts["placed"].get(pl.tier, 0) + 1
                if pl.tier == "freeway_offset":
                    # no usable GPS, placed by the report's freeway description: approximate (user 2026-10-24, #255),
                    # never at an intersection, labelled everywhere
                    c["location_source"] = "approximate"
                    c["approximate"] = {"method": "freeway_offset", "kind": pl.note.split(":", 1)[0],
                                        "plus_minus_mi": APPROX_MI}
                if pl.tiger:              # a street name or road only TIGER/Line has (#229): visible on the crash
                    c["placed_on"] = "tiger"
                    counts["placed_on_tiger"] = counts.get("placed_on_tiger", 0) + 1
                continue
            if pl.lat is not None:
                c["suggestion"] = {"tier": pl.tier, "lat": pl.lat, "lon": pl.lon, **({"tiger": True} if pl.tiger else {}),
                                   **({"tiger_road": True} if pl.tiger_road else {})}
                counts["suggested"] += 1
            counts["still_unplaced"] += 1
    # FARS only after the locator: a fatal crash it placed exactly has a usable location (#191)
    result["cleaning"]["fars"] = place_fatal_from_fars(db, net, result, overpass, tiger)
    result["cleaning"]["placement"] = counts
    return counts
