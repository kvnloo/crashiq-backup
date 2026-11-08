"""C4 in the app: place crashes that came without coordinates, using the locator validated in PR #16.

Runs right after a crash pull, on the corridor's own OpenStreetMap data (the cached Overpass response, so no new
download). The pull already keeps only no-coordinate reports on the study stretch (#48). Placed crashes get the tier
as provenance (`exact`, ...); the rest stay `unmatched` with the locator's suggestion for the review list.
Auto-placement follows `locate.Gate()` (the tiers in config/placement.json: `exact` and `unique_pair`);
any change to the gate is the user's decision (docs/03, PR #16 decision 2).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from . import fars, freeway, gps_rules, grade, locate, osm
from . import network as network_mod
from . import union as union_mod
from .db import Database
from .geo import Polyline


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


# Placements that are estimates, not points (docs/03): freeway reports (#255) and NAD address points (#283). They count
# on segments, never at an intersection, and a FARS point that fits the named roads replaces them (#280).
APPROX_SOURCES = ("approximate", "address_nad")


def place_address(c: dict, addresses, line: list | None = None) -> bool:
    """D5 (#283; user decision 2026-10-25): a house-address crash at its address point (NAD, or a county layer where
    NAD has none, #393), approximate ("usually within 400 ft"). The point is a building or a lot, set back from the
    street; the address is on the corridor street, so the crash goes on the corridor in front of it (#393: left where
    it was, a point more than the 100 ft buffer back was dropped as outside_buffer). A point more than
    nad.MAX_SETBACK_FT off the corridor isn't this street's frontage (a bad point, or the same number on a namesake
    street): no placement. Where there's no point, it stays on the review list with the TIGER address-range point
    as the suggestion. True when placed."""
    from . import nad
    from .names import street_key
    ha, k = c["house_address"], street_key(c["house_address"]["street"])
    pl = Polyline([tuple(x) for x in line]) if line else None
    p = addresses.nad.lookup(c.get("county_code"), c.get("city"), ha["number"], k) if addresses.nad else None
    # NAD and the county lists match only in the crash's city, on its street: their point shows the address is off
    # the stretch however far past an end it lies (user 2026-11-07, "Trust city lists"; #416)
    if p and _off_the_stretch(c, pl, {"tier": "address_point", "lat": p["lat"], "lon": p["lon"],
                                      "source": p.get("source") or nad.SOURCE}):
        return False
    if p and _far_off(pl, p):
        p = None                # on the stretch but not this street's frontage: not placed or suggested (#393)
    if p and p.get("source", nad.SOURCE) not in nad.auto_sources():
        c["suggestion"] = {"tier": "address_point", "lat": p["lat"], "lon": p["lon"], "source": p["source"]}
        return False
    lat, lon, setback = (p["lat"], p["lon"], None) if p else (None, None, None)
    if p and pl:                # on the stretch and within nad.MAX_SETBACK_FT (#416): in front of the address
        pr = pl.project(lat, lon)
        (lat, lon), setback = pl.point_at(pr.station_ft), round(pr.offset_ft)
    if p:
        c.update(lat=lat, lon=lon, location_source="address_nad", review_reason=None,
                 approximate={"method": "address_nad", "plus_minus_ft": nad.PLUS_MINUS_FT, "points": p["points"],
                              "source": p.get("source") or nad.SOURCE, "setback_ft": setback})
        return True
    t = addresses.addrfeat.lookup(c.get("county_code"), ha["number"], k) if addresses.addrfeat else None
    if t and not _far_off(pl, t) and not _off_the_stretch(c, pl, {"tier": "address_tiger", "lat": t["lat"],
                                                                   "lon": t["lon"]}):
        c["suggestion"] = {"tier": "address_tiger", "lat": t["lat"], "lon": t["lon"]}
    return False


def _far_off(pl: Polyline | None, point: dict) -> bool:
    """docs/03 (#393, user 2026-11-04 "yea 500 cut off"): a point more than nad.MAX_SETBACK_FT off the corridor isn't
    this street's frontage: not placed and not the suggestion. A TIGER ADDRFEAT point that far off isn't used at all,
    nor as evidence that the address is off the stretch: ADDRFEAT has no city filter, so it's usually the same number
    in another city (3 Maywood crashes; user 2026-11-07, "Trust city lists"; #416). Past A or B the distance is to
    the corridor line extended along its end segment, so a point just past an end on the corridor street counts."""
    from . import nad
    if pl is None:
        return False
    pr = pl.project(point["lat"], point["lon"])
    past = max(0.0, -pr.station_ext, pr.station_ext - pl.length_ft)        # along the extension past the end
    return math.sqrt(max(0.0, pr.offset_ft ** 2 - past ** 2)) > nad.MAX_SETBACK_FT


def _off_the_stretch(c: dict, pl: Polyline | None, point: dict) -> bool:
    """#410 (user 2026-11-07, "Exclude: outside limits"): a house address whose point lies past either end of the study
    line is outside the study limits, by the same test as every other crash (assign: station before A or past B). Any
    address list says so, a suggestion-only one or TIGER ADDRFEAT too: they're only too rough to place on the
    stretch. The crash is excluded with the point kept as its evidence; it doesn't go to review."""
    if pl is None:
        return False
    st = pl.project(point["lat"], point["lon"]).station_ext
    if 0 <= st <= pl.length_ft:
        return False
    c.update(exclude_rule="outside_study_limits", review_reason=None, address_point=point)
    return True


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
        if src not in ("unmatched", *APPROX_SOURCES, "gps", "gps_dms_corrected", "gps_sign_corrected",
                       "gps_offset_applied"):
            continue                       # placed by the locator (exact) or by hand: a usable location (#191)
        # an approximate freeway spot is an estimate: a FARS point that fits the named roads replaces it (#280)
        if src not in ("unmatched", *APPROX_SOURCES) and (c.get("lat") is None or _gps_usable(c, net)):
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
        trial_from = (c.get("lat"), c.get("lon"))
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
                 gps_replaced=[c["lat"], c["lon"]] if src not in ("unmatched", *APPROX_SOURCES) else None)
        if src in APPROX_SOURCES:
            c["approximate_replaced"] = {**c.pop("approximate"), "lat_lon": [trial_from[0], trial_from[1]]}
        counts["placed"] += 1
    return counts


APPROX_MI = json.loads((Path(__file__).parent / "config" / "placement.json").read_text()).get("approximate_mi", 0.5)
# the freeway descriptions that auto-place (user 2026-10-25, #259): true connectors ("X TO Y" whose cross street is
# X or Y) are held for review; an "X TO Y" naming a local street is placed on X's lanes like mainline
FWY_AUTO_KINDS = frozenset(json.loads((Path(__file__).parent / "config" / "placement.json").read_text())
                           .get("freeway_auto_kinds", ["mainline", "ramp", "connector_local"]))
def place_mile_markers(net: dict, result: dict, gate: locate.Gate, postmiles) -> dict:
    """#319 (user 2026-11-01): mile-marker crashes at their Caltrans postmile. Placed as `postmile` when that tier is
    on, else the point is the review list's suggestion; no point leaves the crash on the review list with the reason."""
    from . import mile_marker
    from .shs import corridor_routes
    todo = [c for c in result["crashes"] if c.get("review_reason") == "mile_marker" and not c.get("exclude_rule")]
    counts = {"tried": len(todo), "placed": 0, "suggested": 0, "no_point": {}}
    if not todo or postmiles is None:
        return counts
    rts = corridor_routes(net)
    for c in todo:
        r = mile_marker.place(c, postmiles, rts)
        if "why" in r:
            c["mile_marker"] = {**(c.get("mile_marker") or {}), "why": r["why"]}
            counts["no_point"][r["why"]] = counts["no_point"].get(r["why"], 0) + 1
        elif "postmile" in gate.auto_tiers:
            c.update(lat=r["lat"], lon=r["lon"], location_source="postmile", review_reason=None,
                     mile_marker={**(c.get("mile_marker") or {}), "placed_at": r["note"]})
            counts["placed"] += 1
        else:
            c["suggestion"] = {"tier": "postmile", "lat": r["lat"], "lon": r["lon"], "note": r["note"]}
            counts["suggested"] += 1
    return counts


CROSSING_ON_PATH = json.loads((Path(__file__).parent / "config" / "placement.json").read_text()).get("crossing_on_path", False)


def place_crossings(db: Database | None, net: dict, result: dict, gate: locate.Gate, overpass=None) -> dict:
    """#318 (user 2026-11-01): crashes at the corridor's crossing with a railway or a named trail or path. Placed as
    `crossing_rail` / `crossing_path` when that tier is on, else the spot is the review list's suggestion; two or more
    crossings, or none, leave the crash on the review list with the reason. A crash on a separate bike-only path
    (the path is its primary road) is placed on the path (`crossing_on_path`, user 2026-11-01)."""
    from . import crossings
    todo = [c for c in result["crashes"] if c.get("review_reason") == "crossing" and not c.get("exclude_rule")]
    counts = {"tried": len(todo), "placed": 0, "suggested": 0, "no_spot": {}}
    if not todo or db is None or not net.get("line"):
        return counts
    try:
        osm_x = network_mod.fetch_overpass(db, network_mod.crossing_query([tuple(p) for p in net["line"]]),
                                           transport=overpass, allow_empty=True)
    except network_mod.NetworkError as e:
        counts["error"] = str(e)
        return counts
    for c in todo:
        r = crossings.place(c, net, osm_x)
        if "why" in r:
            c["crossing"] = {**(c.get("crossing") or {}), "why": r["why"]}
            counts["no_spot"][r["why"]] = counts["no_spot"].get(r["why"], 0) + 1
            continue
        tier = f"crossing_{r['kind']}"
        if tier in gate.auto_tiers and (CROSSING_ON_PATH or not r["on_path"]):
            c.update(lat=r["lat"], lon=r["lon"], location_source=tier, review_reason=None,
                     crossing={**(c.get("crossing") or {}), "placed_at": r["note"]})
            counts["placed"] += 1
        else:
            c["suggestion"] = {"tier": tier, "lat": r["lat"], "lon": r["lon"], "note": r["note"],
                               **({"on_path": True} if r["on_path"] else {})}
            counts["suggested"] += 1
    return counts


def outside_corners(net: dict, cands: list[dict], raw: dict, gate: locate.Gate | None = None) -> dict:
    """#70: reports at a cross street that isn't one of the corridor's intersections, with a reported distance. The
    locator places each from that corner (auto-place tiers only) and the normal assignment decides: on a segment or at
    a study intersection, it is kept, with the corner and distance recorded; still off the stretch, it keeps
    `cross_street_not_on_corridor`."""
    from . import assign
    gate, onet, kept = gate or locate.Gate(), osm.Network(raw), 0
    for c in cands:
        pl = locate.place(onet, c)
        if not gate.auto(pl):
            continue
        trial = {**c, "lat": pl.lat, "lon": pl.lon, "location_source": pl.tier, "exclude_rule": None}
        if assign.assign([trial], net, net.get("radius_ft") or 250, net.get("buffer_ft") or 100)["assignments"][0]["kind"] \
                not in ("intersection", "segment"):
            continue
        kept += 1
        del c["exclude_rule"]
        c.update(lat=pl.lat, lon=pl.lon, location_source=pl.tier,
                 outside_corner={"cross_street": c.get("secondary_road"), "offset_ft": c.get("offset_ft"),
                                 "offset_dir": c.get("offset_dir")})
        if pl.tiger:
            c["placed_on"] = "tiger"
    return {"tried": len(cands), "kept": kept}


def with_driveways(raw: dict, net: dict) -> dict:
    """The locator's street network plus the named signalized driveways that are study intersections (#421). The street
    query has no `service` ways, so "PACIFIC COAST HWY / DOHENY PARK PLZ" found no Doheny Park Plaza and stayed
    unmatched. Each one is a short way by its name from its corridor nodes; no other driveway reaches the locator.
    The caller's network isn't changed."""
    have = {el["id"] for el in raw.get("elements", []) if el.get("type") == "node"}
    extra, nid = [], -1
    for i in net.get("intersections", []):
        if not i.get("driveway") or i.get("name") in ("Driveway (signal)", "Unnamed road", None):
            continue
        for n in i.get("osm_node_ids", []):
            if n in have:
                extra += [{"type": "node", "id": nid, "lat": i["lat"], "lon": i["lon"]},
                          {"type": "way", "id": nid, "nodes": [n, nid], "tags": {"highway": "service", "name": i["name"]}}]
                nid -= 1
    return {**raw, "elements": raw.get("elements", []) + extra} if extra else raw


def place_unmatched(db: Database, net: dict, result: dict, gate: locate.Gate | None = None, overpass=None,
                    raw: dict | None = None, tiger=None, postmiles=None, addresses=None) -> dict:
    gate = gate or locate.Gate()
    result["cleaning"]["mile_markers"] = place_mile_markers(net, result, gate, postmiles)
    result["cleaning"]["crossings"] = place_crossings(db, net, result, gate, overpass)
    # house addresses (D5, #283): NAD address point, else review with the TIGER suggestion; never the street locator
    house = [c for c in result["crashes"] if c.get("review_reason") == "house_address" and not c.get("exclude_rule")]
    by_nad = sum(place_address(c, addresses, net.get("line")) for c in house) if addresses is not None else 0
    # no cross street (#94): nothing for the locator to work with; the engineer places it from the review list
    todo = [c for c in result["crashes"] if c.get("location_source") == "unmatched" and not c.get("exclude_rule")
            and not c.get("review_reason")]
    counts = {"tried": len(todo), "placed": {}, "suggested": 0, "still_unplaced": 0}
    if house:
        counts["house_address"] = {"tried": len(house), "placed_nad": by_nad,
                                   "suggested_tiger": sum(1 for c in house if (c.get("suggestion") or {}).get("tier")
                                                          == "address_tiger")}
    # GPS snapped to the named intersection while the report states an offset (#218): the offset wins
    offset_cands = [c for c in result["crashes"] if c.get("location_source") in ("gps", "gps_dms_corrected", "gps_sign_corrected")
                    and (c.get("offset_ft") or 0) > gps_rules.CONFIG["offset_min_ft"] and c.get("offset_dir")]
    # freeway crashes on a freeway corridor (#246, D1): placed by the report when they have no usable GPS; officer GPS
    # that fits the named roads is kept (user 2026-10-25, docs/03; replaces "the report beats the GPS", 2026-10-23)
    fwy = bool(net.get("is_freeway"))
    onet = None
    if (todo or offset_cands) and net.get("line"):
        if raw is None:                   # OSM only (the caller passes the OSM + TIGER network when it has one, #229)
            raw = network_mod.fetch_overpass(db, network_mod.overpass_query([tuple(p) for p in net["line"]]))
        onet = osm.Network(with_driveways(raw, net))
    result["cleaning"]["gps_offset_applied"] = gps_rules.apply_offsets(onet, net, offset_cands) if onet else 0
    if todo and onet is not None:
        for c in todo:
            pl = locate.place(onet, c)
            # the street-name locator first: a freeway crash it places today keeps that placement (PM review of #252);
            # the report's freeway description is tried only when the locator doesn't auto-place
            sp = freeway.place(raw, c) if fwy and c.get("is_freeway") and not gate.auto(pl) else None
            if sp:
                pl = locate.Placement("freeway_offset", sp.lat, sp.lon, note=f"{sp.kind}: {sp.note}")
            if gate.auto(pl) and not (sp and sp.report not in FWY_AUTO_KINDS):
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
                                   **({"tiger_road": True} if pl.tiger_road else {}),
                                   **({"freeway_kind": sp.report, "freeway_spot": sp.kind} if sp else {})}
                counts["suggested"] += 1
            counts["still_unplaced"] += 1
    # FARS only after the locator: a fatal crash it placed exactly has a usable location (#191)
    result["cleaning"]["fars"] = place_fatal_from_fars(db, net, result, overpass, tiger)
    replaced = [c["approximate_replaced"]["method"] for c in result["crashes"] if c.get("approximate_replaced")]
    if replaced:                          # approximate spots FARS replaced (#280) are counted as FARS
        for m in replaced:
            if m == "address_nad":
                counts["house_address"]["placed_nad"] -= 1
            else:
                counts["placed"]["freeway_offset"] -= 1
        counts["approximate_replaced_by_fars"] = len(replaced)
    result["cleaning"]["placement"] = counts
    return counts
