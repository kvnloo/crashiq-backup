"""#229 OSM + TIGER/Line street network: a TIGER segment along an OSM way only adds names; elsewhere it is a new way,
joined to the OSM network; provenance per way and name; the locator uses either name and tags TIGER-only matches."""

from crashiq import locate, union
from crashiq.osm import Network

# OSM: Main Street east-west (nodes 1-2-3, ~90 m apart), Oak Avenue crossing at node 2. No Elm Street in OSM.
OSM = {"elements": [
    {"type": "node", "id": 1, "lat": 34.0000, "lon": -118.0010},
    {"type": "node", "id": 2, "lat": 34.0000, "lon": -118.0000},
    {"type": "node", "id": 3, "lat": 34.0000, "lon": -117.9990},
    {"type": "node", "id": 4, "lat": 34.0010, "lon": -118.0000},
    {"type": "node", "id": 5, "lat": 33.9990, "lon": -118.0000},
    {"type": "way", "id": 10, "nodes": [1, 2, 3], "tags": {"name": "Main Street", "highway": "secondary"}},
    {"type": "way", "id": 11, "nodes": [5, 2, 4], "tags": {"name": "Oak Avenue", "highway": "residential"}},
]}
LINE = [(34.0, -118.0010), (34.0, -117.9990)]


def edge(tlid, names, pts, tnidf=1, tnidt=2):
    return {"tlid": tlid, "mtfcc": "S1400", "names": names, "pts": pts, "tnidf": tnidf, "tnidt": tnidt}


def crash(p, s):
    return {"primary_road": p, "secondary_road": s, "offset_ft": None, "offset_dir": None}


def test_a_street_only_in_tiger_is_matched_where_it_meets_the_corridor():
    # Elm Street, TIGER only: from Main Street's node 3 north
    els, counts = union.union(OSM, [edge(501, ["Elm St"], [(34.0, -117.9990), (34.0010, -117.9990)], 7, 8)], LINE, 40)
    net = Network(els)
    p = locate.place(net, crash("MAIN ST", "ELM ST"))
    assert p.tier == "exact" and p.node == 3 and p.tiger
    assert counts == {"tiger_segments": 1, "added_from_tiger": 1}
    assert locate.place(Network(OSM), crash("MAIN ST", "ELM ST")).tier == "review"      # OSM alone can't
    assert not locate.place(net, crash("MAIN ST", "OAK AVE")).tiger                      # OSM streets stay OSM


def test_a_tiger_street_meeting_the_corridor_between_osm_nodes_is_spliced_in():
    # Birch Street, TIGER only, ends on Main Street halfway between nodes 2 and 3 (OSM has no corner there)
    mid = (34.0, -117.9995)
    els, counts = union.union(OSM, [edge(502, ["Birch St"], [mid, (34.0010, -117.9995)], 9, 10)], LINE, 40)
    net = Network(els)
    p = locate.place(net, crash("MAIN ST", "BIRCH ST"))
    assert p.tier == "exact" and abs(p.lon - mid[1]) < 1e-6 and p.tiger
    assert counts["joined_by_splice"] == 1
    main = next(e for e in els["elements"] if e.get("id") == 10)
    assert len(main["nodes"]) == 4 and main["nodes"][0] == 1 and main["nodes"][-1] == 3   # in order along the way


def test_a_tiger_copy_of_an_osm_street_is_not_added_twice():
    # TIGER's Main St, 3 m north of OSM's: the same street
    els, counts = union.union(OSM, [edge(503, ["Main St"], [(34.00003, -118.0010), (34.00003, -117.9990)])], LINE, 40)
    assert counts == {"tiger_segments": 1, "coincide_with_osm": 1}
    assert sum(e["type"] == "way" for e in els["elements"]) == 2
    main = next(e for e in els["elements"] if e.get("id") == 10)
    assert main["tags"]["crashiq:source"] == "both"
    net = Network(els)
    assert locate.place(net, crash("MAIN ST", "OAK AVE")).node == 2


def test_an_osm_name_and_a_tiger_name_on_one_way_both_match():
    # TIGER calls Main Street "State Hwy 39" and "Old Mill Rd": either name finds the same corner
    els, _ = union.union(OSM, [edge(504, ["Old Mill Rd", "State Hwy 39"], [(34.00002, -118.0010), (34.00002, -117.9990)])],
                         LINE, 40)
    net = Network(els)
    for name in ("MAIN ST", "OLD MILL RD", "SR 39"):
        p = locate.place(net, crash(name, "OAK AVE"))
        assert p.node == 2, name
    assert not locate.place(net, crash("MAIN ST", "OAK AVE")).tiger
    assert locate.place(net, crash("OLD MILL RD", "OAK AVE")).tiger                     # name only TIGER has
    assert net.key_source[next(k for k in net.streets if k.core == "OLD MILL")] == {"tiger"}


def test_tiger_far_from_the_corridor_is_left_out():
    far = edge(505, ["Pine St"], [(34.01, -118.0), (34.011, -118.0)])
    els, counts = union.union(OSM, [far], LINE, 40)
    assert counts == {} and sum(e["type"] == "way" for e in els["elements"]) == 2


def test_a_cross_street_beside_a_divided_roads_far_carriageway_doesnt_name_it():
    # SF validation: TIGER's Masonic Ave (one centerline through Geary's median) ran within 12 m of Geary's far
    # carriageway for a few samples; Geary's way took the name and Geary "met" Masonic all along it
    d = 0.00012                                            # ~13 m: Geary's carriageways either side of the median
    osm = {"elements": [
        {"type": "node", "id": 1, "lat": 37.7830 + d, "lon": -122.4480}, {"type": "node", "id": 2, "lat": 37.7830 + d, "lon": -122.4460},
        {"type": "node", "id": 3, "lat": 37.7830 + d, "lon": -122.4440},
        {"type": "node", "id": 4, "lat": 37.7830 - d, "lon": -122.4480}, {"type": "node", "id": 5, "lat": 37.7830 - d, "lon": -122.4460},
        {"type": "node", "id": 6, "lat": 37.7830 - d, "lon": -122.4440},
        {"type": "node", "id": 7, "lat": 37.7850, "lon": -122.4460}, {"type": "node", "id": 8, "lat": 37.7810, "lon": -122.4460},
        {"type": "way", "id": 20, "nodes": [1, 2, 3], "tags": {"name": "Geary Boulevard"}},
        {"type": "way", "id": 21, "nodes": [6, 5, 4], "tags": {"name": "Geary Boulevard"}},
        {"type": "way", "id": 22, "nodes": [7, 2, 5, 8], "tags": {"name": "Masonic Avenue"}},
    ]}
    # short TIGER pieces (~40 m, an alley or a slip lane ends them): every sample left sits beside a carriageway
    # and TIGER's centerline 8 m east of OSM's: beside the carriageway, Geary's way is nearer than Masonic's own
    tiger = [edge(601, ["Masonic Ave"], [(37.7830, -122.44591), (37.78336, -122.44591)]),
             edge(602, ["Masonic Ave"], [(37.78264, -122.44591), (37.7830, -122.44591)])]
    els, counts = union.union(osm, tiger, [(37.783, -122.448), (37.783, -122.444)], 40)
    geary = [e for e in els["elements"] if e.get("id") in (20, 21)]
    assert all("Masonic" not in e["tags"].get("tiger:name", "") for e in geary)
    p = locate.place(Network(els), crash("MASONIC AV", "GEARY BL"))
    assert p.tier == "exact" and p.node in (2, 5)
