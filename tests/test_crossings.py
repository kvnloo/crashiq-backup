"""Street x railway / trail crossings and distances along named paths (#318; user decision 2026-11-01). Synthetic."""

import pytest

from crashiq import crossings
from crashiq.names import street_key

# corridor: north-south along lon -118.300, from lat 34.000 to 34.020 (about 7,300 ft)
NET = {"line": [[34.000, -118.300], [34.020, -118.300]], "corridor_names": ["Main Street"]}
FT_LAT = 1 / 364000                                    # degrees of latitude per foot


def osm(*ways):
    els, nid = [], 1
    for wid, (tags, pts) in enumerate(ways, start=100):
        ids = []
        for lat, lon in pts:
            els.append({"type": "node", "id": nid, "lat": lat, "lon": lon})
            ids.append(nid)
            nid += 1
        els.append({"type": "way", "id": wid, "nodes": ids, "tags": tags})
    return {"elements": els}


RAIL = ({"railway": "rail"}, [(34.010, -118.320), (34.010, -118.280)])                 # crosses at 34.010
TRAIL = ({"highway": "cycleway", "name": "Pacific Electric Trail"}, [(34.005, -118.330), (34.005, -118.270)])
U_PATH = ({"highway": "path", "name": "Creek Path"},                                    # crosses twice
          [(34.002, -118.310), (34.002, -118.290), (34.018, -118.290), (34.018, -118.310)])


def crash(p, s, ft=None, d=None):
    return {"crash_id": "x", "primary_road": p, "secondary_road": s, "offset_ft": ft, "offset_dir": d}


@pytest.mark.parametrize("text, want", [
    ("RAIL ROAD", {"kind": "rail", "name": None}), ("RAILROAD TRACKS", {"kind": "rail", "name": None}),
    ("RR TRACKS", {"kind": "rail", "name": None}), ("UPRR", {"kind": "rail", "name": None}),
    ("PACIFIC ELECTRIC TRL", {"kind": "path", "name": "PACIFIC ELECTRIC"}),
    ("ESCONDIDO CREEK BIKE PATH", {"kind": "path", "name": "ESCONDIDO CREEK"}),
    ("SANTA ANA RIVER TRAIL", {"kind": "path", "name": "SANTA ANA RIVER"}),
])
def test_reads_railways_and_paths(text, want):
    assert crossings.read(text) == want


def test_streets_and_bike_lanes_are_not_crossing_features():
    for text in ("MAIN ST", "MAIN ST BIKE LANE", "RAILROAD AVE BIKE LANE", "OAK AVE"):
        assert crossings.read(text) is None, text
    assert street_key("MAIN ST BIKE LANE") == street_key("Main Street")              # the bike lane is the road


def test_places_at_the_one_crossing_of_the_corridor_and_the_railway():
    r = crossings.place(crash("MAIN ST", "RAIL ROAD"), NET, osm(RAIL, TRAIL))
    assert r["lat"] == pytest.approx(34.010, abs=1e-6) and r["lon"] == pytest.approx(-118.300, abs=1e-6)
    assert r["kind"] == "rail" and r["on_path"] is False and r["note"] == "where the corridor crosses a railway"


def test_a_named_path_matches_by_name():
    r = crossings.place(crash("MAIN ST", "PACIFIC ELECTRIC TRL"), NET, osm(RAIL, TRAIL))
    assert r["lat"] == pytest.approx(34.005, abs=1e-6) and r["kind"] == "path"
    assert crossings.place(crash("MAIN ST", "JUNIPER TRL"), NET, osm(RAIL, TRAIL)) == \
        {"why": "the corridor doesn't cross the Juniper path on the map"}


def test_two_crossings_go_to_review_never_the_nearest():
    assert crossings.place(crash("MAIN ST", "CREEK PATH"), NET, osm(U_PATH)) == \
        {"why": "the corridor crosses the Creek path in 2 places"}
    double = ({"railway": "rail"}, [(34.0101, -118.320), (34.0101, -118.280)])        # a second track 36 ft away
    assert "lat" in crossings.place(crash("MAIN ST", "RAILROAD"), NET, osm(RAIL, double))     # one crossing


def test_a_distance_is_walked_along_the_path_in_the_stated_direction():
    # the crash on the trail, 817 ft west of the corridor street, measured along the trail
    r = crossings.place(crash("PACIFIC ELECTRIC TRL", "MAIN ST", 817, "W"), NET, osm(TRAIL))
    assert r["lat"] == pytest.approx(34.005, abs=1e-6) and r["lon"] < -118.300
    feet_west = (-118.300 - r["lon"]) * 364000 * 0.8288                              # cos(34.005 deg)
    assert feet_west == pytest.approx(817, rel=0.01)
    assert r["on_path"] is True                                                       # the path is the primary road
    assert crossings.place(crash("PACIFIC ELECTRIC TRL", "MAIN ST", 817, "N"), NET, osm(TRAIL)) == \
        {"why": "817 ft N from the crossing doesn't follow the Pacific Electric path"}


# -- the pull and placement ---------------------------------------------------------------------------------------
def xc(cid, p, s, ft=None, d=None):
    return {**crash(p, s, ft, d), "crash_id": cid, "location_source": "unmatched", "review_reason": "crossing",
            "lat": None, "lon": None}


class DB:
    """fetch_overpass's cache, empty: the transport answers."""
    def one(self, *a):
        return None

    def execute(self, *a):
        return None


def transport(data):
    import json
    return lambda url, payload, timeout: json.dumps(data).encode()


def test_while_the_tiers_are_off_the_crossing_is_the_suggestion():
    from crashiq import locate, placement
    r = {"crashes": [xc("a", "MAIN ST", "RAIL ROAD"), xc("b", "MAIN ST", "CREEK PATH")], "cleaning": {}}
    counts = placement.place_crossings(DB(), NET, r, locate.Gate(auto_tiers=frozenset({"exact"})),
                                       transport(osm(RAIL, U_PATH)))
    a, b = r["crashes"]
    assert a["suggestion"]["tier"] == "crossing_rail" and a["lat"] is None and a["review_reason"] == "crossing"
    assert b["crossing"]["why"] == "the corridor crosses the Creek path in 2 places" and "suggestion" not in b
    assert counts["placed"] == 0 and counts["suggested"] == 1


def test_with_a_tier_on_it_places_and_a_crash_on_a_bike_only_path_is_placed_on_the_path():
    from crashiq import locate, placement
    r = {"crashes": [xc("a", "MAIN ST", "PACIFIC ELECTRIC TRL"), xc("b", "PACIFIC ELECTRIC TRL", "MAIN ST", 817, "W")],
         "cleaning": {}}
    placement.place_crossings(DB(), NET, r, locate.Gate(auto_tiers=frozenset({"exact", "crossing_path"})),
                              transport(osm(TRAIL)))
    a, b = r["crashes"]
    assert a["location_source"] == "crossing_path" and a["review_reason"] is None
    assert b["location_source"] == "crossing_path" and b["review_reason"] is None             # user 2a, 2026-11-01
    assert b["lon"] < -118.300                                                                # 817 ft W along the trail


def test_the_crossing_tiers_are_off_and_bike_only_path_crashes_go_on_the_path():
    from crashiq import locate, placement
    assert not {"crossing_rail", "crossing_path"} & locate.configured_tiers()
    assert placement.CROSSING_ON_PATH is True                         # the user's 2a (2026-11-01, #331): on the path
