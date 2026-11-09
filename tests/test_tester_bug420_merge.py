"""Tester (on #420, head c2d0517): an unnamed signalized driveway chains two separate intersections into one.
Frozen run: 14 pairs merged, e.g. Hayward (a signal 188 ft from Jefferson St becomes part of the stop-controlled
Jefferson St), Long Beach (a stop 356 ft past E Wardlow Rd), Albany (Washington Av signal + stop 183 ft apart).
Step 4 of detect clusters a node with no cross-street name onto any neighbour within CLUSTER_FT, so a driveway node at
the signal bridges the gap. Where the second intersection was at A or B, the study's end moves (Compton, La Puente)."""

from crashiq import network

from test_driveways import LINE


_FT = 1 / 364000            # degrees of latitude per foot, near 34° N


def _n(i, lat, lon, **tags):
    return {"type": "node", "id": i, "lat": lat, "lon": lon, **({"tags": tags} if tags else {})}


def test_an_unnamed_driveway_at_a_signal_does_not_merge_its_neighbours():
    s, u, d = 34.010, 34.010 + 240 * _FT, 34.010 + 110 * _FT     # Oak St signal; an unnamed street 240 ft on; driveway
    osm = {"elements": [_n(1, 34.000, -118.300), _n(3, s, -118.300, highway="traffic_signals"), _n(40, d, -118.300),
                        _n(41, u, -118.300), _n(5, 34.020, -118.300),
                        _n(6, 34.000, -118.310), _n(7, 34.000, -118.290), _n(8, 34.020, -118.310), _n(9, 34.020, -118.290),
                        _n(60, s, -118.302), _n(61, s, -118.298), _n(62, u, -118.302), _n(63, u, -118.298),
                        {"type": "way", "id": 10, "nodes": [1, 3, 40, 41, 5], "tags": {"highway": "primary", "name": "Main Street"}},
                        {"type": "way", "id": 11, "nodes": [6, 1, 7], "tags": {"highway": "residential", "name": "1st Street"}},
                        {"type": "way", "id": 12, "nodes": [8, 5, 9], "tags": {"highway": "residential", "name": "9th Street"}},
                        {"type": "way", "id": 13, "nodes": [60, 3, 61], "tags": {"highway": "residential", "name": "Oak Street"}},
                        {"type": "way", "id": 14, "nodes": [62, 41, 63], "tags": {"highway": "residential"}}]}
    drive = {"elements": [_n(40, d, -118.300), _n(70, d, -118.302),
                          {"type": "way", "id": 30, "nodes": [40, 70], "tags": {"highway": "service"}}]}
    before = [i["name"] for i in network.detect(osm, LINE)["intersections"]]
    assert before == ["1st Street", "Oak Street", "Unnamed road", "9th Street"]
    after = [i["name"] for i in network.detect(osm, LINE, driveways=drive)["intersections"]]
    assert "Unnamed road" in after, after               # c2d0517: merged into "Oak Street"
