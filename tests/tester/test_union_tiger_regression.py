"""Tester (run 9): the OSM + TIGER network must not lose a placement OSM alone makes. A TIGER copy of an OSM street
that the union doesn't recognize as the same street (here ~37 m off) joins the cross street near the OSM intersection;
the locator then picks a node whose street is "only on TIGER" and the gate holds a crash OSM places exactly.
Strict xfail until fixed (see the issue linked in the PR)."""
import pytest

from crashiq import locate, osm, union

OSM = {"elements": [
    {"type": "node", "id": 1, "lat": 34.0, "lon": -118.002}, {"type": "node", "id": 5, "lat": 34.0, "lon": -118.0},
    {"type": "node", "id": 2, "lat": 34.0, "lon": -117.998}, {"type": "node", "id": 3, "lat": 33.998, "lon": -118.0},
    {"type": "node", "id": 4, "lat": 34.002, "lon": -118.0},
    {"type": "way", "id": 10, "nodes": [1, 5, 2], "tags": {"name": "Main Street", "highway": "secondary"}},
    {"type": "way", "id": 11, "nodes": [3, 5, 4], "tags": {"name": "Oak Avenue", "highway": "residential"}}]}
TIGER_COPY = [{"tlid": 1, "names": ["Oak Ave"], "pts": [[33.998, -117.9996], [34.0, -117.9996]],
               "tnidf": 900, "tnidt": 901}]
CRASH = {"primary_road": "MAIN ST", "secondary_road": "OAK AV"}


def test_osm_alone_places_it():
    assert locate.Gate().auto(locate.place(osm.Network(OSM), CRASH))


@pytest.mark.xfail(strict=True, reason="union regression: a TIGER copy near an OSM street makes the placement tiger_road")
def test_union_keeps_the_osm_placement():
    raw, _ = union.union(OSM, TIGER_COPY, None, 0)
    pl = locate.place(osm.Network(raw), CRASH)
    assert locate.Gate().auto(pl)
    assert pl.node == 5
