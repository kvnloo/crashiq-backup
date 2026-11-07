"""#413 (user 2026-11-07, "Signalized ones only"): a driveway or access road (OSM `service`) meeting the corridor at a
traffic signal is a study intersection, named after the driveway when it has a name, else "Driveway (signal)". One
without a signal stays part of the segment. The driveways come from their own small Overpass query; when it can't be
answered the profile says signalized driveways weren't checked."""

import json

from crashiq import network, profile

n = lambda i, lat, lon, **tags: {"type": "node", "id": i, "lat": lat, "lon": lon, **({"tags": tags} if tags else {})}  # noqa: E731
LINE = [(34.000, -118.300), (34.020, -118.300)]
MAIN = {"elements": [n(1, 34.000, -118.300), n(2, 34.005, -118.300), n(3, 34.010, -118.300, highway="traffic_signals"),
                     n(4, 34.015, -118.300), n(5, 34.020, -118.300),
                     n(6, 34.000, -118.310), n(7, 34.000, -118.290), n(8, 34.020, -118.310), n(9, 34.020, -118.290),
                     {"type": "way", "id": 10, "nodes": [1, 2, 3, 4, 5], "tags": {"highway": "primary", "name": "Main Street"}},
                     {"type": "way", "id": 11, "nodes": [6, 1, 7], "tags": {"highway": "residential", "name": "1st Street"}},
                     {"type": "way", "id": 12, "nodes": [8, 5, 9], "tags": {"highway": "residential", "name": "9th Street"}}]}


def drive(name=None, at=3):
    lat = {3: 34.010, 2: 34.005}[at]
    tags = {"highway": "service", **({"name": name} if name else {})}
    return {"elements": [n(at, lat, -118.300), n(20, lat, -118.302), n(21, lat - 0.001, -118.303),
                         {"type": "way", "id": 30, "nodes": [at, 20, 21], "tags": tags}]}


def names(osm_drive):
    return [(i["name"], i["control"]) for i in network.detect(MAIN, LINE, driveways=osm_drive)["intersections"]]


def test_a_driveway_at_a_signal_is_a_study_intersection():
    assert names(drive()) == [("1st Street", "unknown"), ("Driveway (signal)", "signal"), ("9th Street", "unknown")]
    got = {i["name"]: i for i in network.detect(MAIN, LINE, driveways=drive())["intersections"]}
    assert got["Driveway (signal)"]["legs"] == 3 and got["Driveway (signal)"]["station_ft"] > 3000


def test_a_named_driveway_is_named_after_itself():
    assert names(drive("Corte Madera Town Center"))[1] == ("Corte Madera Town Center", "signal")


def test_a_driveway_without_a_signal_stays_on_the_segment():
    assert names(drive(at=2)) == [("1st Street", "unknown"), ("9th Street", "unknown")]


def test_without_the_driveway_query_detection_is_as_before():
    assert names(None) == names({"elements": []}) == [("1st Street", "unknown"), ("9th Street", "unknown")]


def test_the_driveway_query_asks_for_service_ways_at_signals_near_the_line():
    q = network.driveway_query(LINE)
    assert '["highway"="traffic_signals"]' in q and '["highway"="service"]' in q and q != network.overpass_query(LINE)


def _study(client, transport):
    client.app.state.overpass = transport
    sid = client.post("/api/studies", json={"name": "D", "mode": "tis"}).json()["id"]
    r = client.put(f"/api/studies/{sid}/corridor", json={"line": [list(p) for p in LINE]})
    assert r.status_code == 200, r.text
    return sid, r.json()


def test_the_corridor_records_that_driveways_were_checked(client):
    def transport(url, data, timeout):
        q = data.decode() if isinstance(data, bytes) else str(data)
        return json.dumps(drive() if "service" in q else MAIN).encode()
    _, net = _study(client, transport)
    assert net["driveways_checked"] is True
    assert "Driveway (signal)" in [i["name"] for i in net["intersections"]]


def test_when_the_driveway_query_fails_the_profile_says_so(client):
    import urllib.error

    def transport(url, data, timeout):
        q = data.decode() if isinstance(data, bytes) else str(data)
        if "service" in q:
            raise urllib.error.URLError("down")
        return json.dumps(MAIN).encode()
    client.app.state.overpass_retries = 0
    _, net = _study(client, transport)
    assert net["driveways_checked"] is False
    assert [i["name"] for i in net["intersections"]] == ["1st Street", "9th Street"]
    cav = profile.driveway_caveat(net)
    assert cav["key"] == "driveways_not_checked" and "Signalized driveways weren't checked" in cav["text"]
    assert profile.driveway_caveat({**net, "driveways_checked": True}) is None
    assert profile.driveway_caveat({"intersections": []}) is None            # a test or older net without the field


def test_a_driveway_intersection_is_marked_and_the_mark_is_stored(client):
    found = network.detect(MAIN, LINE, driveways=drive("Corte Madera Town Center"))
    assert [i["driveway"] for i in found["intersections"]] == [False, True, False]

    def transport(url, data, timeout):
        q = data.decode() if isinstance(data, bytes) else str(data)
        return json.dumps(drive("Corte Madera Town Center") if "service" in q else MAIN).encode()
    _, net = _study(client, transport)
    assert [(i["name"], i["driveway"]) for i in net["intersections"]] == [
        ("1st Street", False), ("Corte Madera Town Center", True), ("9th Street", False)]


def test_a_crash_at_a_named_driveway_is_placed_with_its_offset_and_the_caller_network_is_untouched():
    from crashiq import placement
    found = network.detect(MAIN, LINE, driveways=drive("Corte Madera Town Center"))
    net = {"line": LINE, **found}
    raw = json.loads(json.dumps(MAIN))
    crash = {"crash_id": "1", "primary_road": "CORTE MADERA TOWN CENTER", "secondary_road": "MAIN ST",
             "offset_ft": 0, "offset_dir": None, "location_source": "unmatched", "lat": None, "lon": None}
    off = {**crash, "crash_id": "2", "primary_road": "MAIN ST", "secondary_road": "CORTE MADERA TOWN CENTER",
           "offset_ft": 200, "offset_dir": "N"}
    placement.place_unmatched(None, net, {"crashes": [crash, off], "cleaning": {}}, raw=raw)
    assert crash["location_source"] == "exact" and abs(crash["lat"] - 34.010) < 1e-6   # the corridor named second
    assert off["location_source"] == "exact" and off["lat"] > 34.0105                  # 200 ft north along Main St
    assert raw == MAIN
