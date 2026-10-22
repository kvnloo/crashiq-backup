"""#203 unique_pair tier: the report's two streets, allowing only what it leaves out (a leading or trailing direction,
a suffix), meet at exactly one intersection. Auto-places only when the gate allows it (default: off, a suggestion)."""

from crashiq import locate, placement
from crashiq import network as network_mod
from crashiq.names import directions
from crashiq.osm import Network

# Lancaster's grid in miniature: Avenue J is West Avenue J west of Division Street and East Avenue J east of it;
# 20th Street West crosses West Avenue J (node 2), 20th Street East crosses East Avenue J (node 4).
LANCASTER = {"elements": [
    {"type": "node", "id": 1, "lat": 34.6900, "lon": -118.1700},
    {"type": "node", "id": 2, "lat": 34.6900, "lon": -118.1650},
    {"type": "node", "id": 3, "lat": 34.6900, "lon": -118.1360},
    {"type": "node", "id": 4, "lat": 34.6900, "lon": -118.1000},
    {"type": "node", "id": 5, "lat": 34.6950, "lon": -118.1650},
    {"type": "node", "id": 6, "lat": 34.6850, "lon": -118.1650},
    {"type": "node", "id": 7, "lat": 34.6950, "lon": -118.1000},
    {"type": "node", "id": 8, "lat": 34.6850, "lon": -118.1000},
    {"type": "node", "id": 9, "lat": 34.6950, "lon": -118.1360},
    {"type": "way", "id": 10, "nodes": [1, 2, 3], "tags": {"name": "West Avenue J"}},
    {"type": "way", "id": 11, "nodes": [3, 4], "tags": {"name": "East Avenue J"}},
    {"type": "way", "id": 12, "nodes": [5, 2, 6], "tags": {"name": "20th Street West"}},
    {"type": "way", "id": 13, "nodes": [7, 4, 8], "tags": {"name": "20th Street East"}},
    {"type": "way", "id": 14, "nodes": [9, 3], "tags": {"name": "Division Street"}},
]}
NET = Network(LANCASTER)


def crash(p, s, cid="x"):
    return {"crash_id": cid, "primary_road": p, "secondary_road": s, "offset_ft": None, "offset_dir": None,
            "lat": None, "lon": None, "location_source": "unmatched"}


def test_avenue_j_and_20th_st_west_can_only_be_one_corner():
    p = locate.place(NET, crash("AVENUE J", "20TH ST W"))
    assert p.tier == "unique_pair" and p.node == 2
    assert locate.place(NET, crash("20TH STREET WEST", "AVENUE J")).node == 2   # either order


def test_east_or_west_left_open_on_both_streets_is_not_unique():
    p = locate.place(NET, crash("AVENUE J", "20TH ST"))
    assert p.tier == "review" and "more than one place" in p.note                 # unchanged: two candidates


def test_a_direction_the_report_writes_must_match():
    assert locate.place(NET, crash("AVENUE J", "20TH ST N")).tier != "unique_pair"   # no 20th Street North here


def test_exact_placements_are_unchanged():
    p = locate.place(NET, crash("WEST AVENUE J", "20TH ST W"))
    assert p.tier == "exact" and p.node == 2
    assert locate.place(NET, crash("DIVISION ST", "W AVENUE J")).tier == "exact"


def test_directions_as_written():
    assert directions("20TH ST W") == (None, "W")
    assert directions("W AVENUE J") == ("W", None)
    assert directions("20th Street East") == (None, "E")
    assert directions("N ST") == ("N", None) and directions("AVENUE J") == (None, None)
    assert directions("RT 14") == (None, None)


def _pull(monkeypatch, *crashes):
    monkeypatch.setattr(network_mod, "fetch_overpass", lambda db, q: LANCASTER)
    return {"cleaning": {}, "crashes": list(crashes)}


def test_gate_off_by_default_leaves_a_one_click_suggestion(monkeypatch):
    assert locate.configured_tiers() == frozenset({"exact"})                       # until #201 and the user's OK
    r = _pull(monkeypatch, crash("AVENUE J", "20TH ST W"))
    counts = placement.place_unmatched(None, {"line": [(34.69, -118.17), (34.69, -118.10)]}, r)
    c = r["crashes"][0]
    assert c["location_source"] == "unmatched" and c["lat"] is None
    assert c["suggestion"]["tier"] == "unique_pair" and (c["suggestion"]["lat"], c["suggestion"]["lon"]) == NET.coord[2]
    assert counts["placed"] == {} and counts["suggested"] == 1


def test_gate_on_places_it_with_its_provenance(monkeypatch):
    r = _pull(monkeypatch, crash("AVENUE J", "20TH ST W"))
    gate = locate.Gate(auto_tiers=frozenset({"exact", "unique_pair"}))
    counts = placement.place_unmatched(None, {"line": [(34.69, -118.17), (34.69, -118.10)]}, r, gate=gate)
    c = r["crashes"][0]
    assert c["location_source"] == "unique_pair" and (c["lat"], c["lon"]) == NET.coord[2]
    assert counts["placed"] == {"unique_pair": 1}


def test_exact_never_lands_on_the_opposite_stated_direction():
    # #205: the exact key drops a trailing direction, so 20TH ST W matched 20th Street East at East Avenue J
    p = locate.place(NET, crash("E AVENUE J", "20TH ST W"))
    assert p.node != 4
    assert p.tier == "review"            # East Ave J never meets 20th St West: a person decides
    assert locate.place(NET, crash("E AVENUE J", "20TH ST")).node == 4               # no direction stated: as before
    assert locate.place(NET, crash("E AVENUE J", "20TH ST E")).tier == "exact"


def test_near_tier_still_works_with_a_stated_direction():
    # 20th Street West stops 20 m short of West Avenue J (no shared node): near picks Avenue J's closest node, which
    # 20th Street West doesn't pass through, so its stated W can't be checked there and mustn't block it
    net = Network({"elements": [
        {"type": "node", "id": 1, "lat": 34.6900, "lon": -118.1700}, {"type": "node", "id": 2, "lat": 34.6900, "lon": -118.1650},
        {"type": "node", "id": 3, "lat": 34.6950, "lon": -118.1650}, {"type": "node", "id": 4, "lat": 34.6902, "lon": -118.1650},
        {"type": "way", "id": 10, "nodes": [1, 2], "tags": {"name": "West Avenue J"}},
        {"type": "way", "id": 12, "nodes": [3, 4], "tags": {"name": "20th Street West"}}]})
    p = locate.place(net, crash("WEST AVENUE J", "20TH ST W"))
    assert p.tier == "near" and p.node == 2
