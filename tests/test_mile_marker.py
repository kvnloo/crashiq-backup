"""'MILE MARKER x' crashes at that Caltrans postmile on the state route (#319; user decision 2026-11-01, docs/03), behind
a switch. Postmile points: the LA-405 fixture of #248 plus synthetic lines."""

import json

import pytest

from crashiq import mile_marker, postmile

from conftest import FIXTURES
from test_postmile import Get, points

PAGE = json.loads((FIXTURES / "postmiles_la405_artesia.json").read_text())


def feat(oid, route, county, pm, lat, lon, prefix="", align="Right", direction="NB"):
    return {"attributes": {"OBJECTID": oid, "Route": route, "RteSuffix": "", "County": county, "PMPrefix": prefix, "PM": pm,
                           "PMSuffix": "", "Odometer": None, "AlignCode": align, "Direction": direction},
            "geometry": {"x": lon, "y": lat}}


SYN = [  # route 96 in Siskiyou, north-south; route 2 in LA with an R-prefixed realignment at the same numbers 5.0-5.2
    *[feat(9000 + i, "96", "SIS", 95.0 + i / 10, 41.50 + i * 0.00145, -123.40) for i in range(6)],
    *[feat(9100 + i, "2", "LA", 5.0 + i / 10, 34.20, -118.20 + i * 0.00175, direction="EB") for i in range(3)],
    *[feat(9200 + i, "2", "LA", 5.0 + i / 10, 34.30, -118.10 + i * 0.00175, prefix="R", direction="EB") for i in range(3)],
]


@pytest.fixture
def cache(tmp_path):
    return postmile.PostmileCache(tmp_path / "pm", get=Get([{"features": PAGE["features"] + SYN}]), background=False)


@pytest.mark.parametrize("text, want", [
    ("MILE MARKER 28.86", (None, 28.86)), ("MM 28.86", (None, 28.86)), ("MILEPOST 28.86", (None, 28.86)),
    ("PM 28.86", (None, 28.86)), ("M/M 28.86", (None, 28.86)), ("MILE MARKER R12.3", ("R", 12.3)),
    ("MILE POST #95", (None, 95.0)), ("MILEMARKER 7", (None, 7.0)),
])
def test_reads_the_mile_marker_wording(text, want):
    assert mile_marker.marker(text) == want


def test_other_text_is_not_a_mile_marker():
    for text in ("MAIN ST", "PMB 12", "HAMPTON RD", "SUMMIT 2", "MILE SQUARE RD"):
        assert mile_marker.marker(text) is None, text


def test_a_postmile_on_the_route_in_the_county_gives_its_point(cache):
    pm, lat, lon = points("405", "NB")[10]
    p = cache.at("405", "LA", pm)
    assert abs(p["lat"] - lat) < 3e-4 and abs(p["lon"] - lon) < 3e-4          # both sides of the freeway averaged
    q = cache.at("96", "SIS", 95.25)
    assert q["lat"] == pytest.approx(41.50 + 2.5 * 0.00145, abs=1e-6) and q["lon"] == pytest.approx(-123.40)


def test_off_the_route_or_county_or_two_places_is_no_point(cache):
    assert cache.at("96", "SIS", 120.0) is None                               # past the route's end
    assert cache.at("96", "HUM", 95.2) is None                                # another county
    assert cache.at("2", "LA", 5.1) is None                                   # 5.1 and R5.1: two places
    assert cache.at("2", "LA", 5.1, "R")["lat"] == pytest.approx(34.30)       # the prefix settles it


def crash(p, s, county=47, ft=None, d=None):
    return {"crash_id": "m1", "primary_road": p, "secondary_road": s, "county_code": county, "offset_ft": ft, "offset_dir": d}


def test_places_at_the_postmile_on_the_named_route(cache):
    r = mile_marker.place(crash("STATE HIGHWAY 96", "MILE MARKER 95.20"), cache, {"96"})
    assert r["lat"] == pytest.approx(41.50 + 2 * 0.00145, abs=1e-6) and r["note"] == "SIS-96 PM 95.200"


def test_a_stated_offset_moves_along_the_route_in_its_direction(cache):
    base = mile_marker.place(crash("STATE HIGHWAY 96", "MILE MARKER 95.20"), cache, {"96"})
    north = mile_marker.place(crash("STATE HIGHWAY 96", "MILE MARKER 95.20", ft=528, d="N"), cache, {"96"})
    south = mile_marker.place(crash("STATE HIGHWAY 96", "MILE MARKER 95.20", ft=528, d="S"), cache, {"96"})
    assert north["lat"] == pytest.approx(base["lat"] + 0.00145, abs=1e-6)    # 0.1 mi north = the next tenth point
    assert south["lat"] == pytest.approx(base["lat"] - 0.00145, abs=1e-6)
    tiny = mile_marker.place(crash("STATE HIGHWAY 96", "MILE MARKER 95.20", ft=5, d="S"), cache, {"96"})
    assert tiny["lat"] == base["lat"] and tiny["note"] == base["note"]       # 5 ft: within the marker's precision


def test_no_route_or_no_point_says_why(cache):
    assert mile_marker.place(crash("ANGELES CREST HWY", "MILE MARKER 28.86", county=19), cache, set()) == \
        {"why": "no state route named"}
    assert mile_marker.place(crash("STATE HIGHWAY 96", "MILE MARKER 300"), cache, {"96"}) == \
        {"why": "postmile 300.000 isn't on route 96 in SIS"}
    assert mile_marker.place(crash("SR-2", "MILE MARKER 5.1", county=19), cache, {"2"}) == \
        {"why": "postmile 5.100 is in more than one place on route 2 in LA"}


def test_the_route_comes_from_the_road_field_else_the_corridor():
    assert mile_marker.routes(crash("STATE HIGHWAY 96", "MM 95.2"), {"2"}) == {"96"}
    assert mile_marker.routes(crash("ANGELES CREST HWY", "MM 28.86"), {"2"}) == {"2"}    # the corridor's ref (OSM)


# -- the pull and placement ---------------------------------------------------------------------------------------
def test_a_mile_marker_beside_the_corridor_street_goes_to_its_own_review_reason():
    from crashiq import crashes
    assert crashes._mile_marker_on(["STATE HIGHWAY 96", "MILE MARKER 95.29"], [0]) == (None, 95.29)
    assert crashes._mile_marker_on(["MILE MARKER 95.29", "STATE HIGHWAY 96"], [1]) == (None, 95.29)
    assert crashes._mile_marker_on(["MAIN ST", "MILE MARKER 3"], []) is None              # not on the corridor
    assert crashes._mile_marker_on(["STATE HIGHWAY 96", "MAIN ST"], [0]) is None


def mm(cid, pm="MILE MARKER 95.20", county=47):
    return {"crash_id": cid, "primary_road": "STATE HIGHWAY 96", "secondary_road": pm, "county_code": county,
            "location_source": "unmatched", "review_reason": "mile_marker", "lat": None, "lon": None}


def test_while_the_tier_is_off_the_postmile_point_is_the_suggestion(cache):
    from crashiq import locate, placement
    r = {"crashes": [mm("a"), mm("b", "MILE MARKER 300")], "cleaning": {}}
    counts = placement.place_mile_markers({"corridor_names": ["CA 96"]}, r, locate.Gate(auto_tiers=frozenset({"exact"})), cache)
    a, b = r["crashes"]
    assert a["review_reason"] == "mile_marker" and a["suggestion"]["tier"] == "postmile" and a["lat"] is None
    assert a["suggestion"]["note"] == "SIS-96 PM 95.200"
    assert b["mile_marker"]["why"] == "postmile 300.000 isn't on route 96 in SIS" and "suggestion" not in b
    assert counts == {"tried": 2, "placed": 0, "suggested": 1, "no_point": {"postmile 300.000 isn't on route 96 in SIS": 1}}


def test_with_the_tier_on_it_places_with_provenance_postmile(cache):
    from crashiq import locate, placement
    r = {"crashes": [mm("a")], "cleaning": {}}
    placement.place_mile_markers({"corridor_names": ["CA 96"]}, r, locate.Gate(auto_tiers=frozenset({"exact", "postmile"})), cache)
    c = r["crashes"][0]
    assert c["location_source"] == "postmile" and c["review_reason"] is None and c["lat"] == pytest.approx(41.5029, abs=1e-4)


def test_the_postmile_tier_is_off_by_default():
    from crashiq import locate
    assert "postmile" not in locate.configured_tiers()
