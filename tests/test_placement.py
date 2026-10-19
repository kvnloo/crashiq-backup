"""placement.place_unmatched: no-coordinate crashes placed by the PR #16 locator behind locate.Gate (#35, #39)."""

from __future__ import annotations

import json

import pytest

from crashiq import locate, placement
from crashiq import network as network_mod

from conftest import FIXTURES

OSM = json.loads((FIXTURES / "overpass_crenshaw.json").read_text())
NET = {"line": [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]}


def _crash(cid, pr, sr, **kw):
    return {"crash_id": cid, "primary_road": pr, "secondary_road": sr, "lat": None, "lon": None,
            "location_source": "unmatched", **kw}


@pytest.fixture
def result(monkeypatch):
    monkeypatch.setattr(network_mod, "fetch_overpass", lambda db, q: OSM)
    return {"cleaning": {}, "crashes": [
        _crash("a", "CRENSHAW BL", "MARINE AV"),                         # a real corridor intersection
        _crash("b", "CRENSHAW BL", "ZZYZX RD"),                          # no such cross street here
        _crash("c", "CRENSHAW BL", "W 190TH ST", exclude_rule="cross_street_not_on_corridor"),
        {"crash_id": "g", "lat": 33.9, "lon": -118.33, "location_source": "gps"}]}


def test_exact_match_is_placed_with_its_tier(result):
    counts = placement.place_unmatched(None, NET, result)
    a = result["crashes"][0]
    assert a["location_source"] == "exact" and a["lat"] is not None
    assert counts["placed"] == {"exact": 1}


def test_unknown_cross_street_stays_unmatched(result):
    placement.place_unmatched(None, NET, result)
    b = result["crashes"][1]
    assert b["location_source"] == "unmatched" and b["lat"] is None
    assert result["cleaning"]["placement"]["still_unplaced"] == 1


def test_excluded_and_gps_crashes_are_not_touched(result):
    counts = placement.place_unmatched(None, NET, result)
    c, g = result["crashes"][2], result["crashes"][3]
    assert c["lat"] is None and "suggestion" not in c and c["location_source"] == "unmatched"
    assert (g["lat"], g["location_source"]) == (33.9, "gps")
    assert counts["tried"] == 2


def test_gate_closed_keeps_a_suggestion_instead(result):
    counts = placement.place_unmatched(None, NET, result, gate=locate.Gate(auto_tiers=frozenset()))
    a = result["crashes"][0]
    assert a["location_source"] == "unmatched" and a["lat"] is None
    assert a["suggestion"]["tier"] == "exact" and a["suggestion"]["lat"] is not None
    assert (counts["suggested"], counts["placed"]) == (1, {})


def test_nothing_to_place_downloads_nothing(monkeypatch):
    def boom(db, q):
        raise AssertionError("no Overpass call when nothing is unmatched")
    monkeypatch.setattr(network_mod, "fetch_overpass", boom)
    r = {"cleaning": {}, "crashes": [{"crash_id": "g", "lat": 1, "lon": 1, "location_source": "gps"}]}
    assert placement.place_unmatched(None, NET, r)["tried"] == 0


def test_no_corridor_line_places_nothing(result):
    counts = placement.place_unmatched(None, {"line": []}, result)
    assert counts["placed"] == {} and all(c["lat"] is None for c in result["crashes"][:3])
