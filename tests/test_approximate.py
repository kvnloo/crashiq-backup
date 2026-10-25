"""#255 (user decision 2026-10-24): freeway crashes with no usable GPS are placed approximately (+-0.5 mi) by the
report. They never count at an intersection, so intersection tables and collision diagrams leave them out, and the
profile says how many; segment and corridor counts include them, labelled."""

from crashiq import assign, findings, network as network_mod
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]
ROSECRANS = (33.9016, -118.32662)          # study intersection osm-1023


def _net(client):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "X", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    return sid, network_mod.network(client.app.state.db, sid)


def test_an_approximate_crash_at_an_intersection_counts_on_the_segment(client):
    _, net = _net(client)
    c = {"crash_id": "a1", "lat": ROSECRANS[0], "lon": ROSECRANS[1], "location_source": "approximate",
         "primary_road": "CRENSHAW BLVD", "secondary_road": "ROSECRANS AV"}
    g = {**c, "crash_id": "g1", "location_source": "gps"}
    out = assign.assign([c, g], net, 250, 100)
    by = {a["crash_id"]: a for a in out["assignments"]}
    assert by["a1"]["kind"] == "segment" and by["g1"]["kind"] == "intersection"
    assert out["approximate"] == 1


def test_findings_say_so_without_a_number():
    prof = {"signals": [{"row": "r", "pattern": "p", "noun": "Rear-end crashes", "location": "Segment A-B",
                         "location_id": "seg:1", "filter": {}, "kind": "segment"}],
            "approximate_locations": ["seg:1"], "tables": [{"id": "T1", "rows": [{"key": "crashes", "values": {"value": 100}}]}]}
    t12 = {"id": "T12", "rows": [{"key": "r", "values": {"target_crashes": 4, "location_crashes": 6, "share_pct": 66.7,
                                                          "reference_share_pct": 30.0, "reference": "corridor segments",
                                                          "strength": "Moderate", "probability": 0.9, "method": "m",
                                                          "excess_pct": 36.7, "reference_crashes": 10}}]}
    f = findings.screen_findings(prof, [t12])[0]
    assert f.text.endswith("Some crashes here are freeway crashes placed approximately from the report (no usable GPS).")
    assert not any(ch.isdigit() for ch in f.text.split("Some crashes here")[1])        # nothing the validator can't cite


def test_the_profile_says_how_many_the_precise_point_analyses_leave_out(client):
    from crashiq import crashes, profile, study
    sid, net = _net(client)
    db = client.app.state.db
    client.post(f"/api/studies/{sid}/crashes/pull")
    pull = crashes.get_cached(db, sid)
    pull["crashes"].append({**pull["crashes"][0], "crash_id": "a1", "lat": ROSECRANS[0], "lon": ROSECRANS[1],
                            "location_source": "approximate", "exclude_rule": None,
                            "approximate": {"method": "freeway_offset", "kind": "mainline", "plus_minus_mi": 0.5}})
    st = study.require(db, sid)
    a = assign.assign(pull["crashes"], net, st["radius_ft"], st["buffer_ft"])
    p = profile.build(st, net, pull, a)
    cav = next(c for c in p["caveats"] if c["key"] == "approximate_freeway")
    assert cav["count"] == 1 and "intersection tables and collision diagrams leave them out" in cav["text"]
    t1 = {r["key"]: r["values"]["value"] for r in p["tables"][0]["rows"]}
    assert t1["located_freeway"] == 1 and p["location_provenance"].get("approximate") == 1
    assert p["approximate_locations"] and all(lid.startswith("seg") for lid in p["approximate_locations"])
