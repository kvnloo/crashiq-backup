import json
import urllib.error

import pytest

from crashiq import network
from crashiq.geo import FT_PER_MI

from test_geo import vincenty_ft

from conftest import FIXTURES

OSM = json.loads((FIXTURES / "overpass_crenshaw.json").read_text())
A, MID, B = (33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)
LINE = [A, MID, B]
EXPECTED = [  # name, cross-street latitude, control
    ("Marine Avenue", 33.8953, "signal"),
    ("West 147th Street", 33.8978, "stop"),
    ("West 144th Street", 33.8999, "unknown"),
    ("Rosecrans Avenue", 33.9016, "signal"),
    ("West 135th Street", 33.9093, "signal"),
    ("West 132nd Street", 33.9123, "signal"),
]


def test_detects_the_corridor_intersections_in_order():
    got = network.detect(OSM, LINE)
    assert got["corridor_name"] == "Crenshaw Boulevard"
    assert [(i["name"], i["control"]) for i in got["intersections"]] == [(n, c) for n, _, c in EXPECTED]
    for i, (_, lat, _) in zip(got["intersections"], EXPECTED):
        assert i["lat"] == pytest.approx(lat, abs=1e-6)               # pin sits on the cross street
        assert i["provenance"] == "auto" and i["osm_node_ids"]


def test_divided_road_gives_one_intersection_and_slip_lane_joins_it():
    got = {i["name"]: i for i in network.detect(OSM, LINE)["intersections"]}
    assert len(got["Marine Avenue"]["osm_node_ids"]) == 2               # NB + SB carriageway nodes
    assert len(got["West 147th Street"]["osm_node_ids"]) == 1           # T from the west only
    assert len(got["Rosecrans Avenue"]["osm_node_ids"]) == 3            # + the unnamed slip lane node


def test_outside_the_limits_is_excluded():
    names = [i["name"] for i in network.detect(OSM, LINE)["intersections"]]
    assert "West 153rd Street" not in names and "West 131st Street" not in names


def test_reversed_line_reverses_order():
    names = [i["name"] for i in network.detect(OSM, LINE[::-1])["intersections"]]
    assert names == [n for n, _, _ in EXPECTED][::-1]


def test_segment_lengths_match_hand_computed():
    got = network.detect(OSM, LINE)
    segs = network.segments(got["intersections"], got["length_ft"])
    # A coincides with Marine and B with 132nd (within 50 ft), so no stub segments
    assert [s["from_id"] for s in segs][0].startswith("osm-")
    assert len(segs) == len(EXPECTED) - 1
    for s, (_, lat1, _), (_, lat2, _) in zip(segs, EXPECTED, EXPECTED[1:]):
        hand = vincenty_ft((lat1, -118.32662), (lat2, -118.32662))
        assert s["length_ft"] == pytest.approx(hand, rel=2e-3)
        assert s["length_mi"] == pytest.approx(s["length_ft"] / FT_PER_MI, abs=1e-4)


def test_unflagged_intersection_merges_its_segments():
    got = network.detect(OSM, LINE)
    ints = got["intersections"]
    ints[2]["is_study"] = False                                         # 144th St not a study intersection
    segs = network.segments(ints, got["length_ft"])
    assert len(segs) == len(EXPECTED) - 2
    assert segs[1]["name"] == "West 147th Street – Rosecrans Avenue"


def test_stub_segments_when_limits_are_away_from_intersections():
    ints = [{"id": "x", "name": "X", "station_ft": 500.0, "is_study": True}]
    segs = network.segments(ints, 1200.0)
    assert [(s["from_id"], s["to_id"], s["length_ft"]) for s in segs] == [("A", "x", 500.0), ("x", "B", 700.0)]


# -- Overpass fetch: cache, retry, clear failures (no network) -------------------------------------
def test_fetch_caches_and_retries(db):
    calls = []

    def flaky(url, data, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError(url, 504, "Gateway Timeout", {}, None)
        return json.dumps(OSM).encode()

    q = network.overpass_query(LINE)
    out = network.fetch_overpass(db, q, transport=flaky, sleep=lambda s: None)
    assert len(out["elements"]) == len(OSM["elements"]) and len(calls) == 2
    network.fetch_overpass(db, q, transport=flaky, sleep=lambda s: None)
    assert len(calls) == 2                                               # served from SQLite


def test_fetch_failure_raises_never_empty(db):
    def down(url, data, timeout):
        raise urllib.error.URLError("unreachable")

    with pytest.raises(network.NetworkError, match="OpenStreetMap"):
        network.fetch_overpass(db, "q", transport=down, retries=2, sleep=lambda s: None)
    assert db.one("SELECT COUNT(*) AS n FROM http_cache")["n"] == 0


def test_overpass_runtime_error_remark_is_a_failure(db):
    def timeout_remark(url, data, timeout):
        return json.dumps({"elements": [], "remark": "runtime error: Query timed out"}).encode()

    with pytest.raises(network.NetworkError):
        network.fetch_overpass(db, "q", transport=timeout_remark, retries=0, sleep=lambda s: None)


# -- API: save, edit, recompute -----------------------------------------------------------------------
@pytest.fixture
def sid(client):
    client.app.state.overpass = lambda url, data, timeout: json.dumps(OSM).encode()
    return client.post("/api/studies", json={"name": "Crenshaw", "mode": "profile"}).json()["id"]


def test_api_corridor_round_trip_and_edits(client, sid):
    net = client.put(f"/api/studies/{sid}/corridor", json={"line": LINE}).json()
    assert [i["name"] for i in net["intersections"]] == [n for n, _, _ in EXPECTED]
    assert net["radius_ft"] == 250 and net["buffer_ft"] == 100 and len(net["segments"]) == 5
    first = net["intersections"][0]["id"]

    net = client.patch(f"/api/studies/{sid}/intersections/{first}", json={"name": "Marine Ave"}).json()
    renamed = net["intersections"][0]
    assert renamed["name"] == "Marine Ave" and renamed["name_source"] == "user" and renamed["provenance"] == "auto"

    net = client.post(f"/api/studies/{sid}/intersections",
                      json={"lat": 33.9060, "lon": -118.32662, "name": "Mall driveway"}).json()
    added = [i for i in net["intersections"] if i["name"] == "Mall driveway"][0]
    assert added["provenance"] == "manual" and len(net["segments"]) == 6
    names = [i["name"] for i in net["intersections"]]
    assert names.index("Mall driveway") == names.index("Rosecrans Avenue") + 1   # ordered by station

    net = client.delete(f"/api/studies/{sid}/intersections/{added['id']}").json()
    assert len(net["segments"]) == 5
    seg = net["segments"][0]["id"]
    net = client.patch(f"/api/studies/{sid}/segments/{seg}", json={"aadt": 32000}).json()
    assert net["segments"][0]["aadt"] == 32000

    assert client.get(f"/api/studies/{sid}/network").json()["intersections"][0]["name"] == "Marine Ave"
    cleared = client.delete(f"/api/studies/{sid}/corridor").json()
    assert cleared["line"] is None and cleared["intersections"] == []


def test_api_overpass_down_returns_502_with_message(client, sid):
    def down(url, data, timeout):
        raise urllib.error.URLError("unreachable")
    client.app.state.overpass = down
    client.app.state.overpass_retries = 0
    r = client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    assert r.status_code == 502 and "OpenStreetMap" in r.json()["detail"]


def test_a_line_outside_the_studys_state_is_refused_before_overpass(client, sid):
    client.app.state.overpass = lambda *a, **k: (_ for _ in ()).throw(AssertionError("no Overpass call"))
    r = client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.45, -112.07], [33.46, -112.07]]})   # Phoenix
    assert r.status_code == 400 and r.json()["detail"] == ("This line isn't in California. Start a new study and "
                                                          "pick the state it's in.")


def test_api_rejects_bad_edits(client, sid):
    assert client.post(f"/api/studies/{sid}/intersections", json={"lat": 33.9, "lon": -118.3}).status_code == 409
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    far = client.post(f"/api/studies/{sid}/intersections", json={"lat": 33.95, "lon": -118.32662, "name": "x"})
    assert far.status_code == 422
    assert client.patch(f"/api/studies/{sid}/intersections/nope", json={"name": "x"}).status_code == 404
    assert client.patch(f"/api/studies/{sid}", json={"radius_ft": 5}).status_code == 422
    assert client.patch(f"/api/studies/{sid}", json={"radius_ft": 300, "buffer_ft": 75}).json()["radius_ft"] == 300


def test_empty_overpass_answer_is_retried_and_never_cached(db):
    # #84 (Tester #73): overpass-api.de answered 0 elements, no remark, 7 times in 14 calls; it was cached forever
    empty = b'{"version": 0.6, "osm3s": {}, "elements": []}'
    q = network.overpass_query([(37.5976, -122.0583), (37.5926, -122.0410)])
    with pytest.raises(network.NetworkError, match="no streets"):
        network.fetch_overpass(db, q, transport=lambda url, data, timeout: empty, retries=0, sleep=lambda s: None)
    assert db.one("SELECT 1 FROM http_cache WHERE source = 'overpass'") is None
    answers = iter([empty, json.dumps(OSM).encode()])                       # empty once, then the real map
    got = network.fetch_overpass(db, q, transport=lambda url, data, timeout: next(answers), retries=1,
                                 sleep=lambda s: None)
    assert got["elements"] and db.one("SELECT 1 FROM http_cache WHERE source = 'overpass'")


def test_an_empty_map_cached_before_the_fix_is_downloaded_again(db):
    import hashlib
    q = network.overpass_query([(37.5976, -122.0583), (37.5926, -122.0410)])
    db.execute("INSERT INTO http_cache (key, source, body) VALUES (?, 'overpass', ?)",
               ("overpass:" + hashlib.sha1(q.encode()).hexdigest(), '{"elements": []}'))
    got = network.fetch_overpass(db, q, transport=lambda url, data, timeout: json.dumps(OSM).encode(),
                                 sleep=lambda s: None)
    assert got["elements"]


def test_corridor_cities_from_osm_boundaries(tmp_path):
    # #142: one `is_in` per point along the line and both buffer edges; a point in no city = unincorporated county
    from crashiq.db import Database
    db = Database(tmp_path / "t.sqlite")
    line = [(33.89, -118.33), (33.91, -118.33)]
    pts = network.city_points(line, 100)
    assert len(pts) % 3 == 0 and len(pts) >= 3 * 2

    def transport(url, data, timeout):
        els = []
        for i, (lat, _) in enumerate(pts):
            els.append({"type": "pt", "id": i + 1, "tags": {"idx": str(i)}})
            els.append({"type": "area", "id": 1, "tags": {"admin_level": "6", "name": "Los Angeles County"}})
            if lat < 33.90:
                els.append({"type": "area", "id": 2, "tags": {"admin_level": "8", "name": "Hawthorne"}})
        return json.dumps({"elements": els}).encode()
    got = network.corridor_cities(db, line, 100, transport)
    assert got == {"cities": ["Hawthorne"], "outside": True, "counties": ["Los Angeles County"]}
    assert network.corridor_cities(db, [(34.0, -118.0), (34.01, -118.0)], 100,
                                   lambda u, d, t: json.dumps({"elements": [{"type": "node", "id": 1}]}).encode()) is None


def test_a_short_piece_of_the_corridor_street_is_not_an_intersection():
    """A crossover or short bent piece of the corridor street meeting it mid-block made an "Unnamed road" stop
    (Crenshaw, Sherman Way, Camino Capistrano, 2026-11-03). Only the real cross streets count."""
    n = lambda i, lat, lon: {"type": "node", "id": i, "lat": lat, "lon": lon}  # noqa: E731
    els = [n(1, 34.000, -118.300), n(8, 34.003, -118.300), n(2, 34.005, -118.300), n(3, 34.010, -118.300),
           n(4, 34.020, -118.300),
           n(5, 34.0051, -118.2999),                                      # crossover to the other carriageway
           n(6, 34.010, -118.310), n(7, 34.010, -118.290), n(9, 34.003, -118.310), n(10, 34.003, -118.290),
           {"type": "way", "id": 10, "nodes": [1, 8, 2, 3, 4], "tags": {"highway": "primary", "name": "Main Street"}},
           {"type": "way", "id": 11, "nodes": [2, 5], "tags": {"highway": "primary", "name": "Main Street"}},
           {"type": "way", "id": 12, "nodes": [6, 3, 7], "tags": {"highway": "residential", "name": "1st Street"}},
           {"type": "way", "id": 13, "nodes": [9, 8, 10], "tags": {"highway": "residential", "name": "2nd Street"}}]
    net = network.detect({"elements": els}, [(34.000, -118.300), (34.020, -118.300)])
    assert [i["name"] for i in net["intersections"]] == ["2nd Street", "1st Street"]


def test_the_corridor_street_bending_away_at_a_drawn_end_stays_the_terminus():
    """#391: Country Club Dr, Palm Desert (Tester's frozen corridor, OSM as cached). At the west end the street bends
    away towards Cook St, which is past the 40 ft map query; that piece's meeting is the terminus, and the Cook St
    crashes count there. The other carriageway joining 158 ft in is mid-block: no stop."""
    osm = json.loads((FIXTURES / "live" / "overpass_palmdesert.json").read_text())
    line = [tuple(p) for p in json.loads((FIXTURES / "live" / "line_palmdesert.json").read_text())]
    got = [(i["name"], round(i["station_ft"])) for i in network.detect(osm, line)["intersections"]]
    assert got == [("Unnamed road", 0), ("The Lakes Drive", 1702), ("El Dorado Drive", 5081), ("Unnamed road", 5312)]
