"""Pulls replayed from LIVE data.ca.gov responses (recorded by backend/scripts/record_live_fixture.py, 2026-10-19).

The hand-built fixture uses the data dictionary's wording; these are the real rows, so they catch differences between
what CHP documents and what it publishes (#75: injury codes)."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from crashiq import crashes, network
from crashiq.sources.ckan import Ckan
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LIVE = FIXTURES / "live"
STUDY = {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}


@pytest.fixture(scope="module")
def crenshaw():
    line = [tuple(p) for p in json.loads((LIVE / "line_crenshaw.json").read_text())]
    found = network.detect(json.loads((LIVE / "overpass_crenshaw.json").read_text()), line)
    net = {"line": line, **found, "intersections": [{**i, "is_study": True} for i in found["intersections"]]}
    return crashes.pull(STUDY, net, Ckan(FakeCkan(LIVE / "ckan_crenshaw.json"), retries=0))


def test_live_injury_codes_give_real_severity_levels(crenshaw):
    sev = Counter(c["severity"] for c in crenshaw["crashes"])
    assert sev["A"] > 0 and sev["B"] > 0 and sev["C"] > 0          # #75: was 0 / 0 / 0
    assert crenshaw["cleaning"]["unknown_injury_values"] == []
    # U is only "injured, but no injury row says how badly", which is rare once the codes map
    assert sev["U"] < 0.05 * sum(sev[k] for k in "KABCU")


def test_live_severity_on_the_study_stretch(crenshaw):
    # Crenshaw Blvd, Marine Ave -> W 132nd St, 2021-2025, crashes on the stretch (side-street reports excluded)
    sev = Counter(c["severity"] for c in crenshaw["crashes"] if not c.get("exclude_rule"))
    assert dict(sev) == {"K": 1, "A": 6, "B": 44, "C": 78, "O": 184}   # 4 GPS rows > 650 ft from the line dropped (#54)


def test_live_replay_returns_every_recorded_crash(crenshaw):
    # #53: with typed columns the replay finds the no-coordinate reports too (was 314 of 1602 untyped)
    # one LAPD crash is in CCRS twice (Collision Ids 4364159 v1 and 4369588 v4, Crenshaw Bl & 66th St, #81);
    # 4 GPS rows more than 650 ft from the line stop before the lookups (#54)
    cl = crenshaw["cleaning"]
    assert len(crenshaw["crashes"]) + cl["same_crash_refiled_dropped"] + cl["gps_beyond_margin_dropped"] == 1602
    assert cl["same_crash_refiled"] == [{"kept": "4369588", "dropped": ["4364159"]}]
