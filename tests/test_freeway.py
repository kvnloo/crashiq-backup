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


def test_off_by_default_a_suggestion_on_a_freeway_corridor():
    from crashiq import locate, placement
    assert "freeway_offset" not in locate.configured_tiers()
    r = _result(A)
    placement.place_unmatched(None, FWY_NET, r, raw=raw("a_lawndale"))
    c = r["crashes"][0]
    assert c["location_source"] == "unmatched" and c["suggestion"]["tier"] == "freeway_offset"


def test_with_the_gate_on_it_places_and_the_report_beats_disagreeing_gps():
    from crashiq import locate, placement
    gate = locate.Gate(auto_tiers=frozenset({"exact", "unique_pair", "freeway_offset"}))
    gps = {**A, "crash_id": "g", "lat": 33.8732, "lon": -118.3433, "location_source": "gps"}   # the NW-corner GPS
    r = _result(A)
    r["crashes"].append(gps)
    counts = placement.place_unmatched(None, FWY_NET, r, raw=raw("a_lawndale"), gate=gate)
    assert r["crashes"][0]["location_source"] == "freeway_offset"
    g = r["crashes"][1]
    assert g["location_source"] == "freeway_offset" and g["gps_as_reported"] == [33.8732, -118.3433]
    assert counts["freeway_gps_moved"] == 1


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
