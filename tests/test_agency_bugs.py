"""Fixes for CCRS recording habits found by the Tester's statewide agency profile (#73). Each test started as a
strict xfail in tests/tester/test_ccrs_agency_bugs.py (feat/73-statewide-test)."""

from __future__ import annotations

import copy
import json

from crashiq import crashes
from crashiq.names import same_core, street_key
from crashiq.sources.ckan import Ckan
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]
STUDY = {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}
CROSS = ("Marine Avenue", "West 144th Street", "Rosecrans Avenue")
NET_X = {"line": LINE, "corridor_name": "Crenshaw Boulevard",
         "intersections": [{"name": n, "is_study": True} for n in CROSS]}


def _fixture(no_gps: bool = False) -> dict:
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    if no_gps:
        for rid, t in d["tables"].items():
            if rid.startswith("cra-"):
                for r in t["rows"]:
                    r["Latitude"], r["Longitude"] = "", ""
    return d


def _row(d: dict, cid: int) -> tuple[list, dict]:
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                if r["Collision Id"] == cid:
                    return t["rows"], r
    raise KeyError(cid)


def _rename(d: dict, to: str) -> None:
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                for col in ("PrimaryRoad", "SecondaryRoad"):
                    if str(r.get(col) or "").upper().startswith("CRENSHAW"):
                        r[col] = to


# -- #80 hyphen in the corridor name ---------------------------------------------------------------------------
def test_hyphenated_corridor_name_finds_no_gps_reports():
    # Union City: OSM 'Alvarado-Niles Road', Union City PD (0% GPS) writes 'ALVARADO NILES RD'
    d = _fixture(no_gps=True)
    _rename(d, "ALVARADO NILES RD")
    out = crashes.pull(STUDY, {**NET_X, "corridor_name": "Alvarado-Niles Road"}, Ckan(FakeCkan(d)))
    assert {"9200001", "9200002", "9200003"} <= {c["crash_id"] for c in out["crashes"]}


def test_hyphen_written_in_the_report_matches_too():
    d = _fixture(no_gps=True)
    _rename(d, "ALVARADO-NILES RD")
    out = crashes.pull(STUDY, {**NET_X, "corridor_name": "Alvarado Niles Road"}, Ckan(FakeCkan(d)))
    assert {"9200001", "9200002", "9200003"} <= {c["crash_id"] for c in out["crashes"]}


def test_hyphen_is_a_space_in_street_keys_but_routes_keep_their_number():
    assert street_key("Alvarado-Niles Road") == street_key("ALVARADO NILES RD")
    assert same_core(street_key("ALVARADO-NILES"), street_key("Alvarado Niles Road"))
    assert street_key("I-880").core == "I 880" and street_key("SR-1").core == "SR 1"


# -- #81 one crash under two Collision Ids --------------------------------------------------------------------
def test_same_crash_filed_under_two_collision_ids_counts_once():
    # CHP 9630-2023-00084 = Collision Ids 1975974 and 1975975, same minute, I-10 E/B & BOB HOPE DR, same GPS.
    # The hand fixture has no Report Number column, so this also exercises the no-report-number rule.
    d = _fixture()
    rows, r = _row(d, 9200001)
    twin = copy.deepcopy(r)
    twin["Collision Id"], twin["Report Version"] = 9299999, 2      # the re-filed copy, a new id
    rows.append(twin)
    for rid, t in d["tables"].items():                             # a re-filed report carries its parties too
        if rid.startswith("par-"):
            t["rows"] += [{**p, "CollisionId": 9299999} for p in t["rows"] if p["CollisionId"] == 9200001]
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    ids = {c["crash_id"] for c in out["crashes"]}
    assert ids & {"9200001", "9299999"} == {"9299999"}             # the higher version is kept
    assert out["cleaning"]["same_crash_refiled_dropped"] == 1
    assert out["cleaning"]["same_crash_refiled"] == [{"kept": "9299999", "dropped": ["9200001"]}]


def test_same_report_number_on_a_different_crash_is_not_merged():
    # SFPD reuses report numbers for different crashes: same agency + number, different time/roads stay two crashes
    d = _fixture()
    rows, r = _row(d, 9200001)
    other = copy.deepcopy(r)
    other["Collision Id"] = 9299998
    other["SecondaryRoad"] = "ROSECRANS AV"
    rows.append(other)
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    assert {"9200001", "9299998"} <= {c["crash_id"] for c in out["crashes"]}
    assert out["cleaning"]["same_crash_refiled_dropped"] == 0


def test_look_alikes_without_a_report_number_that_differ_in_collision_type_are_both_kept():
    # PM review: same corner, same minute, no report number, but a different collision type = two real crashes
    d = _fixture()
    rows, r = _row(d, 9200001)
    other = copy.deepcopy(r)
    other["Collision Id"] = 9299997
    other["Collision Type Description"] = "REAR END" if r.get("Collision Type Description") != "REAR END" else "BROADSIDE"
    rows.append(other)
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    assert {"9200001", "9299997"} <= {c["crash_id"] for c in out["crashes"]}
    assert out["cleaning"]["same_crash_refiled_dropped"] == 0
    assert out["cleaning"]["possible_refile"] == [["9200001", "9299997"]]


# -- #82 'NOT STATED' cross street ----------------------------------------------------------------------------
def _no_cross(value):
    d = _fixture(no_gps=True)
    _, r = _row(d, 9200001)                     # CRENSHAW BL & W 144TH ST, no GPS
    r["SecondaryRoad"] = value
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    return out, next(c for c in out["crashes"] if c["crash_id"] == "9200001")


def test_cross_street_not_stated_is_not_called_a_side_street():
    # CCRS 2024: SecondaryRoad 'NOT STATED' on 4,649 rows (Santa Monica PD 16% of street crashes). User 2026-10-19
    # (#94): on the corridor, place unknown -> the review list, not excluded
    out, c = _no_cross("NOT STATED")
    assert c.get("exclude_rule") is None and c["review_reason"] == "no_cross_street"
    assert c["location_source"] == "unmatched" and c["lat"] is None
    assert out["cleaning"]["no_coords_no_cross_street"] == 1


def test_blank_and_junk_cross_streets_go_to_review_too():
    for v in ("", None, "X", "UNK"):
        c = _no_cross(v)[1]
        assert c.get("exclude_rule") is None and c["review_reason"] == "no_cross_street", v


def test_no_cross_street_is_unplaced_under_its_reason_and_in_no_location():
    from crashiq import assign
    out, c = _no_cross("NOT STATED")
    net = {**NET_X, "segments": [], "intersections": []}
    a = assign.assign([c], net, 250.0, 100.0)
    assert (a["counts"]["unmatched"], a["unmatched_by_rule"]) == (1, {"no_cross_street": 1})
    assert a["by_location"] == {}


def test_gps_crash_with_not_stated_is_assigned_by_its_gps():
    d = _fixture()                                  # GPS kept
    _, r = _row(d, 9000045)
    r["SecondaryRoad"] = "NOT STATED"
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    c = next(c for c in out["crashes"] if c["crash_id"] == "9000045")
    assert c["location_source"] == "gps" and not c.get("review_reason") and not c.get("exclude_rule")


def test_private_property_has_its_own_reason():
    assert _no_cross("PRIVATE PROPERTY")[1].get("exclude_rule") == "private_property"


def test_a_real_side_street_is_still_a_side_street():
    assert _no_cross("W 190TH ST")[1].get("exclude_rule") == "cross_street_not_on_corridor"


# -- #83 route numbers on a state-highway corridor -------------------------------------------------------------
def _state_route_osm() -> dict:
    """A corridor that is a state highway in OSM: name 'Pacific Coast Highway', ref 'CA 1', three cross streets."""
    lats = [LINE[0][0] + i * (LINE[-1][0] - LINE[0][0]) / 20 for i in range(21)]
    lon = LINE[0][1]
    nodes = [{"type": "node", "id": i + 1, "lat": la, "lon": lon} for i, la in enumerate(lats)]
    ways = [{"type": "way", "id": 100, "nodes": [n["id"] for n in nodes],
             "tags": {"highway": "primary", "name": "Pacific Coast Highway", "ref": "CA 1"}}]
    for k, (name, i) in enumerate(zip(CROSS, (3, 10, 17))):
        a, b = 1000 + 2 * k, 1001 + 2 * k
        nodes += [{"type": "node", "id": a, "lat": lats[i], "lon": lon - 0.003},
                  {"type": "node", "id": b, "lat": lats[i], "lon": lon + 0.003}]
        ways.append({"type": "way", "id": 200 + k, "nodes": [a, i + 1, b],
                     "tags": {"highway": "secondary", "name": name}})
    return {"elements": nodes + ways}


def _route_pull(spelling: str):
    from crashiq import network
    net = network.detect(_state_route_osm(), LINE)
    for i in net["intersections"]:
        i["is_study"] = True
    d = _fixture(no_gps=True)
    _rename(d, "PACIFIC COAST HWY")
    _, r = _row(d, 9200001)
    r["PrimaryRoad"] = spelling                  # same corner, written by route number
    return crashes.pull(STUDY, {**net, "line": LINE}, Ckan(FakeCkan(d)))


def test_no_gps_crash_written_by_route_number_is_found():
    # Laguna Beach PD (0% GPS) writes 26% of road fields as route numbers ('SR-1', 'PCH - SR1')
    for spelling in ("SR-1", "RT 1", "HWY 1", "STATE ROUTE 1", "PCH - SR1", "CA-1"):
        ids = {c["crash_id"] for c in _route_pull(spelling)["crashes"]}
        assert {"9200002", "9200003"} <= ids, spelling           # control: name-written crashes
        assert "9200001" in ids, spelling


def test_another_route_number_is_not_the_corridor():
    for spelling in ("SR-10", "RT 101", "I-110"):
        assert "9200001" not in {c["crash_id"] for c in _route_pull(spelling)["crashes"]}, spelling


def test_route_numbers_are_read_anywhere_but_zip_codes_are_not_routes():
    from crashiq.names import route_numbers
    assert route_numbers("PCH - SR1") == {"1"} and route_numbers("RT 046") == {"46"}
    assert route_numbers("14605 CRENSHAW BLVD.- GARDENA- CA 90249") == set()
