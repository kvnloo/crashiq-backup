"""#97: the review list. The engineer places or excludes unplaced crashes; code still counts everything."""

from __future__ import annotations

import json

import pytest

from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]


def _no_gps_fixture() -> dict:
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                if str(r["Collision Id"]) in ("9200001", "9200005"):
                    r["SecondaryRoad"] = "NOT STATED"        # -> review list (#94)
    return d


@pytest.fixture
def sid(client):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(_no_gps_fixture())
    s = client.post("/api/studies", json={"name": "R", "mode": "profile"}).json()["id"]
    client.put(f"/api/studies/{s}/corridor", json={"line": LINE})
    client.post(f"/api/studies/{s}/crashes/pull")
    return s


def review(client, sid):
    return client.get(f"/api/studies/{sid}/review").json()


def decide(client, sid, **body):
    return client.post(f"/api/studies/{sid}/review/decisions", json=body)


def t1(client, sid, key):
    p = client.get(f"/api/studies/{sid}/profile").json()
    return next(r for r in p["tables"][0]["rows"] if r["key"] == key)["values"]["value"]


def test_unplaced_crashes_are_grouped_by_street_pair(client, sid):
    r = review(client, sid)
    g = next(g for g in r["groups"] if g["secondary"] == "NOT STATED")
    assert g["primary"] == "CRENSHAW BOULEVARD" and g["count"] == 2 and g["reasons"] == {"no_cross_street": 2}
    assert {c["crash_id"] for c in g["crashes"]} == {"9200001", "9200005"}
    assert r["open"] == t1(client, sid, "unplaced") and r["intersections"]


def test_place_at_an_intersection_counts_it_there_with_user_provenance(client, sid):
    it = review(client, sid)["intersections"][0]
    before = t1(client, sid, "crashes")
    r = decide(client, sid, crash_ids=["9200001"], action="place", method="intersection", location_id=it["id"]).json()
    assert r["decided"] == 1 and "9200001" not in {c["crash_id"] for g in r["review"]["groups"] for c in g["crashes"]}
    a = client.get(f"/api/studies/{sid}/assignment").json()
    row = next(x for x in a["assignments"] if x["crash_id"] == "9200001")
    assert (row["kind"], row["location_id"], row["location_provenance"]) == ("intersection", it["id"], "user")
    assert t1(client, sid, "crashes") == before + 1 and t1(client, sid, "user_placed") == 1
    out = review(client, sid)["decided"][0]["outcome"]
    assert (out["kind"], out["location"]) == ("intersection", it["name"])


def test_a_placement_off_the_corridor_shows_it_is_not_counted(client, sid):
    decide(client, sid, crash_ids=["9200005"], action="place", method="map", lat=33.9060, lon=-118.3200)   # ~600 ft off
    out = review(client, sid)["decided"][0]["outcome"]
    assert (out["kind"], out["rule"]) == ("excluded", "outside_buffer")


def test_place_on_the_map_is_assigned_by_the_normal_rules(client, sid):
    decide(client, sid, crash_ids=["9200005"], action="place", method="map", lat=33.9060, lon=-118.32662)
    row = next(x for x in client.get(f"/api/studies/{sid}/assignment").json()["assignments"]
               if x["crash_id"] == "9200005")
    assert row["kind"] == "segment" and row["location_provenance"] == "user"


def test_exclude_needs_a_reason_and_is_counted_under_its_rule(client, sid):
    assert decide(client, sid, crash_ids=["9200001"], action="exclude").status_code == 422
    decide(client, sid, crash_ids=["9200001"], action="exclude", reason="Parking lot, not the road")
    a = client.get(f"/api/studies/{sid}/assignment").json()
    assert a["excluded_by_rule"]["user_excluded"] == 1


def test_group_action_then_undo_restores_the_list(client, sid):
    g = next(g for g in review(client, sid)["groups"] if g["secondary"] == "NOT STATED")
    ids = [c["crash_id"] for c in g["crashes"]]
    open_before = review(client, sid)["open"]
    r = decide(client, sid, crash_ids=ids, action="exclude", reason="Unknown location").json()
    assert r["decided"] == 2 and r["review"]["open"] == open_before - 2 and r["review"]["can_undo"]
    u = client.post(f"/api/studies/{sid}/review/undo").json()
    assert u["crashes"] == 2 and u["review"]["open"] == open_before and not u["review"]["decided"]
    assert client.post(f"/api/studies/{sid}/review/undo").status_code == 409


def test_undo_restores_the_previous_decision_not_just_nothing(client, sid):
    decide(client, sid, crash_ids=["9200001"], action="exclude", reason="first")
    decide(client, sid, crash_ids=["9200001"], action="exclude", reason="second")
    client.post(f"/api/studies/{sid}/review/undo")
    d = review(client, sid)["decided"]
    assert [x["decision"]["reason"] for x in d] == ["first"]


def test_suggestion_group_action_skips_crashes_without_one(client, sid):
    r = decide(client, sid, crash_ids=["9200001"], action="place", method="suggestion")
    assert r.status_code == 422          # NOT STATED: the locator never suggested anything


def test_decisions_survive_a_re_pull(client, sid):
    decide(client, sid, crash_ids=["9200001"], action="exclude", reason="Parking lot")
    client.post(f"/api/studies/{sid}/crashes/pull?refresh=true")
    a = client.get(f"/api/studies/{sid}/assignment").json()
    assert a["excluded_by_rule"].get("user_excluded") == 1


def test_a_revised_report_comes_back_for_re_review(client, sid):
    decide(client, sid, crash_ids=["9200001"], action="exclude", reason="Parking lot")
    d = _no_gps_fixture()
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                if str(r["Collision Id"]) == "9200001":
                    r["Report Version"] = 7                   # CHP revised the report
    client.app.state.ckan = FakeCkan(d)
    client.post(f"/api/studies/{sid}/crashes/pull?refresh=true")
    item = next(c for g in review(client, sid)["groups"] for c in g["crashes"] if c["crash_id"] == "9200001")
    assert item["reason"] == "report_changed" and item["decision"]["action"] == "exclude"


def test_unknown_crash_ids_are_refused(client, sid):
    assert decide(client, sid, crash_ids=["nope"], action="exclude", reason="x").status_code == 404


def test_export_lists_the_decisions(client, sid):
    decide(client, sid, crash_ids=["9200001"], action="exclude", reason="Parking lot")
    from crashiq import export
    d = export.gather(client.app.state.db, sid)
    assert d["decisions"][0]["crash_id"] == "9200001" and d["decisions"][0]["reason"] == "Parking lot"
    assert "excluded by the engineer" in export.methodology(d)
