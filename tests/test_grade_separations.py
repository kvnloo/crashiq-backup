"""#67 / N7: roads passing over or under the corridor are not intersections, and their crashes don't count."""

from __future__ import annotations

import pytest

from crashiq import assign, export, grade, network

LON = -122.0
LINE = [(37.600, LON), (37.605, LON), (37.610, LON)]          # ~3,640 ft north-south


class OSM:
    """Tiny Overpass response builder: nodes by (lat, lon), ways by tags."""

    def __init__(self):
        self.els, self.ids = [], {}

    def node(self, lat, lon, **tags):
        key = (round(lat, 6), round(lon, 6))
        if key not in self.ids:
            self.ids[key] = len(self.ids) + 1
            self.els.append({"type": "node", "id": self.ids[key], "lat": lat, "lon": lon, "tags": tags})
        return self.ids[key]

    def way(self, pts, **tags):
        self.els.append({"type": "way", "id": 1000 + len(self.els), "nodes": [self.node(*p) for p in pts], "tags": tags})

    def corridor(self, name, highway="primary", lats=(37.598, 37.601, 37.603, 37.605, 37.607, 37.609, 37.612), **tags):
        self.way([(la, LON) for la in lats], name=name, highway=highway, **tags)

    def cross(self, lat, name, highway="residential", shared=True, **tags):
        """An east-west street at `lat`; shared=False means no node where it crosses the corridor."""
        pts = [(lat, LON - 0.002), (lat, LON + 0.002)]
        if shared:
            pts.insert(1, (lat, LON))
        self.way(pts, name=name, highway=highway, **tags)

    def osm(self):
        return {"elements": self.els}


def arterial_under_freeway():
    o = OSM()
    o.corridor("Main Street")
    o.cross(37.603, "Oak Avenue")                                                     # at grade
    o.cross(37.6062, "Nimitz Freeway", "motorway", shared=False, ref="I 880", bridge="yes", layer="1")   # SB
    o.cross(37.6066, "Nimitz Freeway", "motorway", shared=False, ref="I 880", bridge="yes", layer="1")   # NB
    o.way([(37.6060, LON + 0.0015), (37.607, LON)], highway="motorway_link")           # ramp terminal, at grade
    return o.osm()


def test_freeway_overpass_is_a_grade_separation_not_an_intersection():
    got = network.detect(arterial_under_freeway(), LINE)
    names = [i["name"] for i in got["intersections"]]
    assert "Oak Avenue" in names and not any("880" in n or "Nimitz" in n for n in names)
    assert "Unnamed road" in names                                  # the ramp terminal is a real at-grade junction
    gs = got["grade_separations"]
    assert len(gs) == 1                                              # two carriageways, one grade separation
    assert gs[0]["name"] == "Nimitz Freeway / I 880" and gs[0]["relation"] == "over"
    assert len(gs[0]["osm_way_ids"]) == 2 and gs[0]["station_ft"] == pytest.approx(2276, abs=60)


def test_arterial_bridge_over_a_local_street():
    o = OSM()
    o.corridor("Main Street", lats=(37.598, 37.603, 37.604, 37.612))
    o.corridor("Main Street", lats=(37.604, 37.606), bridge="yes", layer="1")      # the corridor's bridge span
    o.cross(37.605, "Elm Street", shared=False)
    o.cross(37.602, "Oak Avenue")
    got = network.detect(o.osm(), LINE)
    assert [g["name"] for g in got["grade_separations"]] == ["Elm Street"]
    assert got["grade_separations"][0]["relation"] == "under"
    assert "Elm Street" not in [i["name"] for i in got["intersections"]]


def diamond():
    o = OSM()
    o.corridor("Nimitz Freeway", "motorway", ref="I 880")
    o.cross(37.605, "Alvarado Boulevard", "primary", shared=False, bridge="yes", layer="1")
    for la in (37.6035, 37.6065):                                    # four ramps: freeway <-> Alvarado
        for dx in (-0.0004, 0.0004):
            o.way([(la, LON), (37.605, LON + dx * 3)], highway="motorway_link")
    return o.osm()


def test_diamond_interchange_on_a_freeway_corridor():
    got = network.detect(diamond(), LINE)
    assert got["corridor_highway"] == "motorway"
    assert got["intersections"] == []                                # ramp merges are not intersections
    assert [(g["name"], g["relation"]) for g in got["grade_separations"]] == [("Alvarado Boulevard", "over")]


# -- crash rules --------------------------------------------------------------------------------------------------
def _net(found, is_freeway=False):
    ints = [{**i, "is_study": True} for i in found["intersections"]]
    return {"line": LINE, "corridor_name": found["corridor_name"], "intersections": ints,
            "segments": network.segments(ints, found["length_ft"]), "grade_separations": found["grade_separations"],
            "is_freeway": is_freeway}


def _crash(cid, lat, pr, sr, **kw):
    return {"crash_id": cid, "lat": lat, "lon": LON + 0.0001, "primary_road": pr, "secondary_road": sr,
            "location_source": "gps", **kw}


def _rules(net, crashes, include_freeway=False):
    a = assign.assign(crashes, net, 250.0, 100.0, include_freeway)
    return {x["crash_id"]: (x["kind"], x["rule"]) for x in a["assignments"]}, a


def test_arterial_crashes_under_a_freeway():
    net = _net(network.detect(arterial_under_freeway(), LINE))
    crashes = [
        _crash("bridge", 37.6064, "NIMITZ FWY", "MAIN ST"),                  # on the overpass, CHP not IsFreeway
        _crash("fwy", 37.6064, "I-880", "MAIN ST", is_freeway=True),         # freeway mainline: the #34 rule
        _crash("under", 37.6064, "MAIN ST", "RT 880"),                       # on Main St under the bridge: counts
        _crash("oak", 37.6031, "MAIN ST", "OAK AV"),
    ]
    got, a = _rules(net, crashes)
    assert got["bridge"] == ("excluded", "grade_separated_crossing")
    assert got["fwy"] == ("excluded", "freeway")
    assert got["under"][0] in ("segment", "intersection") and got["oak"][0] == "intersection"
    assert a["excluded_by_rule"] == {"grade_separated_crossing": 1, "freeway": 1}


def test_ramp_terminal_switch_keeps_ramp_crashes_but_not_the_mainline():
    net = _net(network.detect(arterial_under_freeway(), LINE))
    crashes = [_crash("ramp", 37.6058, "I-880 NB OFF RAMP", "MAIN ST", is_freeway=True),
               _crash("fwy", 37.6064, "I-880", "MAIN ST", is_freeway=True)]
    got, _ = _rules(net, crashes, include_freeway=True)
    assert got["ramp"][0] in ("segment", "intersection")
    assert got["fwy"] == ("excluded", "grade_separated_crossing")


def test_freeway_corridor_counts_only_freeway_crashes():
    net = _net(network.detect(diamond(), LINE), is_freeway=True)
    crashes = [
        _crash("main", 37.6020, "I-880", "ALVARADO BL", is_freeway=True),
        _crash("cross", 37.6050, "ALVARADO BL", "I-880"),                    # on the overcrossing
        _crash("term", 37.6050, "I-880 SB OFF RAMP", "ALVARADO BL"),         # ramp terminal on the local street
        _crash("ramp", 37.6040, "I-880 SB OFF RAMP", "ALVARADO BL", is_freeway=True),
    ]
    got, _ = _rules(net, crashes)
    assert got["main"] == ("segment", "corridor_buffer")
    assert got["cross"] == ("excluded", "grade_separated_crossing")
    assert got["term"] == ("excluded", "not_on_freeway")
    assert got["ramp"] == ("excluded", "ramp")
    got, _ = _rules(net, crashes, include_freeway=True)            # switch on: ramps count
    assert got["ramp"][0] == "segment"


def test_route_numbers_match_across_kinds():
    k = grade.keys_of(["Nimitz Freeway / I 880"])
    assert grade.names("RT 880", k) and grade.names("SR-880", k) and grade.names("I-880", k)
    assert not grade.names("RT 238", k)
    assert grade.names("NIMITZ FRWY", k) and grade.names("NIMITZ FWY", k)      # CHP spellings of Freeway


def test_methods_text_says_how_grade_separations_are_handled():
    d = {"study": {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100},
         "assignment": {"excluded_by_rule": {"grade_separated_crossing": 2}, "counts": {"unmatched": 0}}}
    text = export.methodology(d)
    assert "passing over or under" in text and "2 on a road passing over or under the corridor" in text


def test_grade_separations_are_stored_and_backfilled_from_the_cache(client, db):
    import json
    client.app.state.overpass = lambda url, data, timeout: json.dumps(arterial_under_freeway()).encode()
    sid = client.post("/api/studies", json={"name": "GS", "mode": "tis"}).json()["id"]
    net = client.put(f"/api/studies/{sid}/corridor", json={"line": LINE}).json()
    assert [g["name"] for g in net["grade_separations"]] == ["Nimitz Freeway / I 880"]
    assert net["is_freeway"] is False
    # a corridor saved before #67 has no stored grade separations: filled from the cached OSM response
    db.execute("UPDATE corridor SET grade_separations_json = NULL, corridor_highway = NULL WHERE study_id = ?", (sid,))
    client.app.state.overpass = lambda url, data, timeout: pytest.fail("no new download")
    again = client.get(f"/api/studies/{sid}/network").json()
    assert [g["name"] for g in again["grade_separations"]] == ["Nimitz Freeway / I 880"]
    assert again["corridor_highway"] == "primary"
