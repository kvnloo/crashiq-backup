"""#246 D1 freeway placement by the report (user decision in principle 2026-10-23, docs/03; worked examples in
knowledge/methods/freeway-crashes.md). The OSM fixtures are cut from the local OSM extract (2026-10-18) around each
crash; truth as the user set it: A computed (200 ft S of the Artesia crossing, NB lanes), B the user's pin, C the
officer's GPS (record 1428399)."""

import json
import math

import pytest

from crashiq import freeway

from conftest import FIXTURES


def ft(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 364_000, (a[1] - b[1]) * 364_000 * math.cos(math.radians(a[0])))


def raw(name):
    return json.loads((FIXTURES / f"overpass_d1_{name}.json").read_text())


A = {"primary_road": "I-405 N/B (SAN DIEGO FREEWAY)", "secondary_road": "ARTESIA BLVD.", "offset_ft": 200,
     "offset_dir": "S", "is_freeway": True}          # 1456564 Lawndale
B = {"primary_road": "NB I5 OFF RAMP", "secondary_road": "FLORA ST", "offset_ft": 10, "offset_dir": "N",
     "is_freeway": True}                             # 2327267 Stockton
C = {"primary_road": "I-680 S/B TO SR-4", "secondary_road": "SR-4", "offset_ft": 1320, "offset_dir": "N",
     "is_freeway": True}                             # 1428399 Martinez


def test_mainline_200_ft_south_of_the_crossing_on_the_northbound_lanes():
    r = raw("a_lawndale")
    s = freeway.place(r, A)
    assert s.kind == "mainline"
    net = freeway._Net(r)
    lanes, streets = net.lanes({"405"}, "N"), net.named("ARTESIA BLVD.")
    cross = [p for w in lanes for a, b in zip(w["nodes"], w["nodes"][1:]) for v in streets
             for c, d in zip(v["nodes"], v["nodes"][1:]) if (p := freeway._cross(net.xy[a], net.xy[b], net.xy[c], net.xy[d]))]
    mid = net.proj.to_ll(sum(p[0] for p in cross) / len(cross), sum(p[1] for p in cross) / len(cross))
    assert 180 <= ft((s.lat, s.lon), mid) <= 220 and s.lat < mid[0]               # south, as written (not north)
    on_nb = min(freeway._seg_point(net.proj.to_xy(s.lat, s.lon), net.xy[a], net.xy[b])[0]
                for w in lanes for a, b in zip(w["nodes"], w["nodes"][1:]))
    assert on_nb < 3                                                               # on the northbound lanes
    assert ft((s.lat, s.lon), (33.8732, -118.3433)) > 400                          # not the officer's NW-corner GPS


def test_ramp_at_the_terminal_on_the_reference_street():
    s = freeway.place(raw("b_stockton"), B)
    assert s.kind == "ramp" and ft((s.lat, s.lon), (37.957310, -121.311389)) < 100     # the user's pin


def test_connector_the_stated_distance_from_the_second_freeway_along_the_connector():
    s = freeway.place(raw("c_martinez"), C)
    assert s.kind == "connector" and ft((s.lat, s.lon), (37.9971, -122.0734)) < 400    # the officer's GPS


@pytest.mark.parametrize("crash", [
    {**A, "secondary_road": "NOWHERE AVE"},                     # reference street not on the map
    {**B, "primary_road": "NB I99 OFF RAMP"},                   # no such route here
    {**A, "is_freeway": False},                                 # a route-numbered city street, not the mainline
])
def test_nothing_found_is_never_a_guess(crash):
    assert freeway.place(raw("a_lawndale" if crash["primary_road"].startswith("I-405") else "b_stockton"), crash) is None


def test_reading_the_report():
    assert freeway.parse(A)["travel"] == "N" and freeway.parse(A)["dir"] == "S"
    assert freeway.parse(B)["kind"] == "ramp" and freeway.parse(B)["route"] == {"5"}
    p = freeway.parse(C)
    assert p["kind"] == "connector" and p["route"] == {"680"} and p["to"] == {"4"} and p["travel"] == "S"


def _result(*crashes):
    return {"cleaning": {}, "crashes": [{"crash_id": f"f{i}", "lat": None, "lon": None, "location_source": "unmatched",
                                         **c} for i, c in enumerate(crashes)]}


FWY_NET = {"line": [(33.8700, -118.3418), (33.8760, -118.3420)], "is_freeway": True}


def test_no_gps_freeway_crashes_are_placed_approximately_by_default():
    # user decision 2026-10-24 (#255): on, as provenance approximate (+-0.5 mi)
    from crashiq import locate, placement
    assert "freeway_offset" in locate.configured_tiers()
    r = _result(A)
    placement.place_unmatched(None, FWY_NET, r, raw=raw("a_lawndale"))
    c = r["crashes"][0]
    assert c["location_source"] == "approximate"
    assert c["approximate"] == {"method": "freeway_offset", "kind": "mainline", "plus_minus_mi": 0.5}


def test_with_the_gate_off_it_stays_a_suggestion():
    from crashiq import locate, placement
    r = _result(A)
    placement.place_unmatched(None, FWY_NET, r, raw=raw("a_lawndale"), gate=locate.Gate(auto_tiers=frozenset({"exact"})))
    c = r["crashes"][0]
    assert c["location_source"] == "unmatched" and c["suggestion"]["tier"] == "freeway_offset"


def test_officer_gps_that_fits_the_named_roads_is_never_moved_by_the_report():
    # user decision 2026-10-25 (docs/03, replacing 2026-10-23 "the report beats the GPS"): the GPS is kept
    from crashiq import placement
    assert not hasattr(placement, "MOVE_GPS")
    gps = {**A, "crash_id": "g", "lat": 33.8732, "lon": -118.3433, "location_source": "gps"}   # the NW-corner GPS
    r = _result(A)
    r["crashes"].append(gps)
    counts = placement.place_unmatched(None, FWY_NET, r, raw=raw("a_lawndale"))
    assert r["crashes"][0]["location_source"] == "approximate"                  # no GPS: placed by the report
    g = r["crashes"][1]
    assert (g["location_source"], g["lat"], g["lon"]) == ("gps", 33.8732, -118.3433) and "gps_as_reported" not in g
    assert "freeway_gps_moved" not in counts


def test_arterial_corridors_are_untouched():
    from crashiq import locate, placement
    gate = locate.Gate(auto_tiers=frozenset({"exact", "unique_pair", "freeway_offset"}))
    r = _result(A)
    placement.place_unmatched(None, {**FWY_NET, "is_freeway": False}, r, raw=raw("a_lawndale"), gate=gate)
    c = r["crashes"][0]
    assert c["location_source"] != "freeway_offset" and (c.get("suggestion") or {}).get("tier") != "freeway_offset"


def test_a_crash_the_street_locator_places_keeps_that_placement(monkeypatch):
    # PM review of #252: freeway.place must not pre-empt locate.place; with the gate off, a freeway crash that
    # exact / unique_pair places today stays placed
    from crashiq import locate, placement
    monkeypatch.setattr(locate, "place", lambda net, c, **kw: locate.Placement("exact", 33.87, -118.34, 1))
    called = []
    monkeypatch.setattr(freeway, "place", lambda raw, c: called.append(c) or None)
    r = _result(A)
    placement.place_unmatched(None, FWY_NET, r, raw=raw("a_lawndale"))
    assert r["crashes"][0]["location_source"] == "exact" and not called


# #259: the reference street often doesn't touch the lanes on the map (an overpass drawn without a crossing segment);
# Tester's d1_compare (run 10) found the app missing 1,602 crashes the reference method places, for that reason.
def _net(streets):
    """Westbound I-80 lanes along lat 37.9; `streets` are named ways, each a list of (lat, lon)."""
    els, nid = [], [0]

    def way(pts, tags):
        ids = []
        for lat, lon in pts:
            nid[0] += 1
            els.append({"type": "node", "id": nid[0], "lat": lat, "lon": lon})
            ids.append(nid[0])
        els.append({"type": "way", "id": 1000 + len(els), "nodes": ids, "tags": tags})

    way([(37.9, -122.28 + i * -0.002) for i in range(31)], {"highway": "motorway", "ref": "I 80", "oneway": "yes"})
    for name, pts in streets:
        way(pts, {"highway": "secondary", "name": name})
    return {"elements": els}


W = {"primary_road": "I-80 W/B", "secondary_road": "BUCHANAN ST", "offset_ft": 0, "offset_dir": "", "is_freeway": True}
GAP = 0.0004                                                      # ~145 ft either side of the lanes


def test_a_street_drawn_short_of_the_lanes_still_meets_them():
    over = [("Buchanan Street", [(37.89, -122.30), (37.9 - GAP, -122.30)]),
            ("Buchanan Street", [(37.9 + GAP, -122.30), (37.91, -122.30)])]
    s = freeway.place(_net(over), W)
    assert s is not None and ft((s.lat, s.lon), (37.9, -122.30)) < 60


def test_a_street_meeting_the_lanes_in_two_places_a_mile_apart_is_not_guessed():
    two = [("Buchanan Street", [(37.89, -122.30), (37.91, -122.30)]),
           ("Buchanan Street", [(37.89, -122.3183), (37.91, -122.3183)])]          # ~1 mi further west
    assert freeway.place(_net(two), W) is None


def test_a_street_farther_than_300_ft_from_the_lanes_does_not_meet_them():
    far = [("Buchanan Street", [(37.89, -122.30), (37.9 - 0.0011, -122.30)])]    # ~400 ft short
    assert freeway.place(_net(far), W) is None


def test_a_connector_crash_is_held_for_review_with_its_suggestion():
    # user decision 2026-10-25 (#259): connectors ("X TO Y") go to review; mainline and ramps stay approximate
    from crashiq import placement
    r = _result(C, B)
    placement.place_unmatched(None, FWY_NET, r, raw={"elements": raw("c_martinez")["elements"]
                                                      + raw("b_stockton")["elements"]})
    conn, ramp = r["crashes"]
    assert conn["location_source"] == "unmatched" and "approximate" not in conn
    assert conn["suggestion"]["tier"] == "freeway_offset" and conn["suggestion"]["freeway_kind"] == "connector"
    assert ramp["location_source"] == "approximate" and ramp["approximate"]["kind"] == "ramp"


# #259, user worked example 2026-10-25: an "X TO Y" report naming a local cross street is measured from that street's
# crossing of X, on X's lanes (record 4630945; the officer's GPS matches the user's reading)
E = {"primary_road": "SR-60 W/B (POF) TO I-10 (SMF)", "secondary_road": "EUCLID AVENUE", "offset_ft": 55,
     "offset_dir": "W", "is_freeway": True}          # 4630945 Los Angeles


def test_a_connector_report_naming_a_local_street_is_placed_on_the_first_route_from_its_crossing():
    s = freeway.place(raw("e_euclid"), E)
    assert s.kind == "mainline" and s.report == "connector_local"
    assert ft((s.lat, s.lon), (34.028450, -118.209045)) < 100                     # the officer's GPS
    assert ft((s.lat, s.lon), (34.031930, -118.222612)) > 2640                    # not the old SR-60/I-10 join spot


def test_what_a_connector_report_is_measured_from():
    assert freeway.parse(E)["from"] == "street"
    assert freeway.parse(C)["from"] == "y"                                        # Martinez: SR-4 is Y
    o = freeway.parse({"primary_road": "I-15 N/B TO I-10 W/B", "secondary_road": "I-15", "offset_ft": 1000,
                       "offset_dir": "W", "is_freeway": True})                     # 1392922 Ontario: I-15 is X
    assert o["from"] == "x" and o["to_travel"] == "W"


def test_a_connector_report_on_a_local_street_is_placed_approximately_like_mainline():
    # user decision 2026-10-25 (docs/03): only true connectors (cross street = X or Y) are held for review
    from crashiq import placement
    assert placement.FWY_AUTO_KINDS == {"mainline", "ramp", "connector_local"}
    r = _result(E)
    placement.place_unmatched(None, FWY_NET, r, raw=raw("e_euclid"))
    c = r["crashes"][0]
    assert c["location_source"] == "approximate" and c["approximate"]["kind"] == "mainline"
    assert ft((c["lat"], c["lon"]), (34.028450, -118.209045)) < 400                # the officer's GPS


def test_a_long_offset_follows_the_freeway_round_a_bend():
    # #259: the walk used to stop where the road turned away from the stated direction, leaving long offsets short
    els, nid = [], [0]

    def way(pts, tags):
        ids = []
        for lat, lon in pts:
            nid[0] += 1
            els.append({"type": "node", "id": nid[0], "lat": lat, "lon": lon})
            ids.append(nid[0])
        els.append({"type": "way", "id": 1000 + len(els), "nodes": ids, "tags": tags})

    # southbound lanes: 0.5 mi south from the street, then bending west for 1 mi
    south = [(37.9 - i * 0.00145, -122.30) for i in range(6)]
    west = [(south[-1][0], -122.30 - i * 0.0036) for i in range(1, 6)]
    way(south + west, {"highway": "motorway", "ref": "I 80", "oneway": "yes"})
    way([(37.9, -122.31), (37.9, -122.29)], {"highway": "secondary", "name": "Buchanan Street"})
    s = freeway.place({"elements": els}, {"primary_road": "I-80 S/B", "secondary_road": "BUCHANAN ST",
                                          "offset_ft": 5280, "offset_dir": "S", "is_freeway": True})
    want = (south[-1][0], -122.30 - 2640 / (364_000 * math.cos(math.radians(37.9))))   # 0.5 mi on past the bend
    assert ft((s.lat, s.lon), want) < 100


def test_a_reference_road_that_is_another_freeway_meets_the_route_where_their_lanes_cross():
    # #259: 214 of Tester's run-10 crashes name another freeway as the reference road ("I-80 W/B" / "I-580")
    g = _net([])
    g["elements"] += [{"type": "node", "id": 9001, "lat": 37.89, "lon": -122.30},
                      {"type": "node", "id": 9002, "lat": 37.91, "lon": -122.30},
                      {"type": "way", "id": 9100, "nodes": [9001, 9002], "tags": {"highway": "motorway", "ref": "I 580"}}]
    s = freeway.place(g, {**W, "secondary_road": "I-580"})
    assert s is not None and ft((s.lat, s.lon), (37.9, -122.30)) < 60


def test_the_walk_starts_on_the_lanes_when_the_crossings_middle_is_between_them():
    # #259: two carriageways (no travel direction stated): the crossings' middle lies between them, off both
    g = _net([("Buchanan Street", [(37.89, -122.30), (37.91, -122.30)])])
    g["elements"] += [{"type": "node", "id": 9001, "lat": 37.9006, "lon": -122.24},
                      {"type": "node", "id": 9002, "lat": 37.9006, "lon": -122.34},
                      {"type": "way", "id": 9100, "nodes": [9001, 9002], "tags": {"highway": "motorway", "ref": "I 80"}}]
    s = freeway.place(g, {**W, "primary_road": "I-80", "offset_ft": 2000, "offset_dir": "W"})
    assert s is not None and ft((s.lat, s.lon), (37.9, -122.30)) > 1900


@pytest.mark.parametrize("crash, fixture", [
    # user ruling 2026-10-25: on the connector, the stated 1,000 ft unreliable, the officer's GPS right
    ({"primary_road": "I-15 N/B TO I-10 W/B", "secondary_road": "I-15", "offset_ft": 1000, "offset_dir": "W",
      "is_freeway": True}, "f_ontario"),                                         # 1392922 Ontario (cross street = X)
    ({"primary_road": "SR-91 W/B TO I-110 S/B", "secondary_road": "I-110", "offset_ft": 192, "offset_dir": "W",
      "is_freeway": True}, "g_harbor"),                                          # 1818216 Los Angeles (cross street = Y)
])
def test_connector_crashes_without_gps_go_to_review_never_an_automatic_spot(crash, fixture):
    from crashiq import placement
    r = _result(crash)
    placement.place_unmatched(None, FWY_NET, r, raw=raw(fixture))
    c = r["crashes"][0]
    assert c["location_source"] == "unmatched" and c["lat"] is None and "approximate" not in c
    assert (c.get("suggestion") or {}).get("freeway_kind", "connector") == "connector"


def test_a_fars_point_that_fits_the_named_roads_beats_the_approximate_freeway_spot(tmp_path):
    # #280 (Tester, re-measure of #278): fatal freeway crashes with no usable GPS lost their FARS point to the
    # approximate spot. Fatal first (2026-10-21); FARS fills when it fits the named roads (2026-10-22)
    import json as _json
    from crashiq import placement
    from test_fars import _db, _fars_row

    def roads(url, data, timeout):          # the roads at the FARS point: the I-405 and Artesia Blvd
        return _json.dumps({"elements": [{"type": "way", "id": 1, "nodes": [], "tags": {"highway": "motorway",
                                          "ref": "I 405", "name": "San Diego Freeway"}},
                                         {"type": "way", "id": 2, "nodes": [], "tags": {"highway": "primary",
                                          "name": "Artesia Boulevard"}}]}).encode()

    fatal = {**A, "killed": 1, "severity": "K", "county_code": "19", "reported_at": "2023-03-04T02:15:00"}
    r = _result(fatal)
    db = _db(tmp_path, [_fars_row(fatal, 33.8728, -118.3426)])
    counts = placement.place_unmatched(db, FWY_NET, r, raw=raw("a_lawndale"), overpass=roads)
    assert counts["placed"].get("freeway_offset") == 0 and counts["approximate_replaced_by_fars"] == 1
    c = r["crashes"][0]
    assert c["location_source"] == "fars" and (c["lat"], c["lon"]) == (33.8728, -118.3426)
    assert "approximate" not in c and c["fars_case"].endswith("-60077")
