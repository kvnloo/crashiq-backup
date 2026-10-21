"""Tester: tests of the statewide harness's own checks (#73), not of the app.

- silent-drop check v3 (PM, PR #148): exact street match after normalising, and duplicate-aware.
- corridor list v2 (PM, PR #148): corridors re-picked from the parts of roads inside the city.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "statewide"))

import checks  # noqa: E402
import corridors  # noqa: E402

CORES = ("MIDDLEFIELD", ["SHORELINE", "RENGSTORFF"])


def test_v3_needs_the_exact_street_not_a_substring():
    core, cross = CORES
    assert checks.names_pair_v3("W MIDDLEFIELD RD", "SHORELINE BL", core, cross)
    assert checks.names_pair_v3("RENGSTORFF AV", "MIDDLEFIELD ROAD", core, cross)       # either road order
    assert not checks.names_pair_v3("OLD MIDDLEFIELD WY", "SHORELINE BL", core, cross)  # a different street
    assert not checks.names_pair_v3("MIDDLEFIELD RD", "N SHORELINE CT", "MIDDLEFIELD", ["SHORELINEX"])
    assert not checks.names_pair_v3("LINCOLNOCEAN AV", "SHORELINE BL", "LINCOLN", ["SHORELINE"])


def test_v3_respects_the_corridor_direction():
    assert not checks.names_pair_v3("W COLORADO BL", "LAKE AV", "COLORADO", ["LAKE"], corridor_dir="E")
    assert checks.names_pair_v3("COLORADO BL", "LAKE AV", "COLORADO", ["LAKE"], corridor_dir="E")


def test_v3_does_not_count_a_refiled_copy_whose_twin_was_pulled():
    expected = {"1", "2", "3"}
    got = {"1", "9"}
    refiled = [{"kept": "9", "dropped": ["2"]}]            # the app's #81 log: 2 is a later copy of 9
    assert checks.silent_drops_v3(expected, got, refiled) == ["3"]


def test_v3_still_counts_a_copy_when_its_twin_was_not_pulled():
    assert checks.silent_drops_v3({"2"}, set(), [{"kept": "9", "dropped": ["2"]}]) == ["2"]


BOX = [[(0.0, 0.0), (0.0, 0.03), (0.03, 0.03), (0.03, 0.0)]]      # ~3.3 km square


def _way(i, name, pts, hw="primary"):
    return {"type": "way", "id": i, "tags": {"name": name, "highway": hw},
            "geometry": [{"lat": a, "lon": b} for a, b in pts]}


def test_clip_keeps_only_runs_of_nodes_inside():
    w = _way(1, "A", [(0.01, -0.02), (0.01, -0.01), (0.01, 0.005), (0.01, 0.01), (0.01, 0.05), (0.01, 0.06)])
    out = checks.clip_inside({"elements": [w]}, BOX)["elements"]
    assert [[(g["lat"], g["lon"]) for g in x["geometry"]] for x in out] == [[(0.01, 0.005), (0.01, 0.01)]]


def test_inside_pick_prefers_the_road_that_runs_inside_the_city():
    # A: a long road that only clips the city's corner; B: a shorter road straight through the city.
    a = _way(1, "Long Road", [(0.001, -0.2 + k * 0.01) for k in range(25)])
    b = _way(2, "City Street", [(0.015, 0.001 + k * 0.002) for k in range(15)])
    roads = {"elements": [a, b]}
    assert corridors._pick_from(roads)["road"] == "Long Road"                      # v1 rule: any node inside
    picked = corridors._pick_from(checks.clip_inside(roads, BOX))
    assert picked["road"] == "City Street"
    assert checks.inside_share(picked["line"], BOX) == 100.0


def test_series_v2_swaps_only_the_repicked_cities():
    import run_history
    v1 = [{"city": "A", "county": "1", "result": "pass"}, {"city": "B", "county": "2", "result": "fail"}]
    v2 = [{"city": "B", "county": "2", "result": "warn", "corridor_list": "v2"}]
    assert [r["result"] for r in run_history.series_v2(v1, v2)] == ["pass", "warn"]
    assert run_history.HISTORY_V2 != run_history.HISTORY
