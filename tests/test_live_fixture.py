"""Pulls replayed from LIVE data.ca.gov responses (recorded by backend/scripts/record_live_fixture.py, 2026-10-19).

The hand-built fixture uses the data dictionary's wording; these are the real rows, so they catch differences between
what CHP documents and what it publishes (#75: injury codes)."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from crashiq import crashes, nad, network, placement
from crashiq.names import street_key
from crashiq.sources.ckan import Ckan
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LIVE = FIXTURES / "live"
STUDY = {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}


class FixtureAddrfeat:
    """The ADDRFEAT points of the three off-stretch Crenshaw house addresses (#410), recorded in a fixture."""
    def __init__(self):
        self.pts = {(p["number"], p["street"]): p for p in
                    json.loads((LIVE / "address_points_crenshaw.json").read_text())["points"]}

    def lookup(self, county, number, k):
        p = next((p for (n, s), p in self.pts.items() if n == number and street_key(s) == k), None)
        return p and {"lat": p["lat"], "lon": p["lon"]}


@pytest.fixture(scope="module")
def crenshaw(tmp_path_factory):
    line = [tuple(p) for p in json.loads((LIVE / "line_crenshaw.json").read_text())]
    found = network.detect(json.loads((LIVE / "overpass_crenshaw.json").read_text()), line)
    net = {"line": line, **found, "intersections": [{**i, "is_study": True} for i in found["intersections"]]}
    result = crashes.pull(STUDY, net, Ckan(FakeCkan(LIVE / "ckan_crenshaw.json"), retries=0))
    # the house-address step of placement, as the app's pull runs it (#410); NAD has no LA County, so ADDRFEAT only
    house = [c for c in result["crashes"] if c.get("review_reason") == "house_address" and not c.get("exclude_rule")]
    # 1210 Crenshaw (Torrance) from the LA County list, which matches in the crash's city (#416)
    import csv
    tmp = tmp_path_factory.mktemp("addr")
    cams = json.loads((LIVE / "address_points_crenshaw.json").read_text())["la_county_cams"]["rows"]
    with (tmp / "addr_ca_los_angeles.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["County", "Add_Number", "StNam_Full", "Inc_Muni", "Post_City", "Latitude", "Longitude", "Source"])
        w.writerows(r + ["Los Angeles County GIS (CAMS) address points"] for r in cams)
    addresses = nad.Addresses(nad.NadIndex(tmp / "nad_ca.sqlite", tmp / "nad_ca_r24.csv"), FixtureAddrfeat())
    for c in house:
        placement.place_address(c, addresses, line)
    return result


def test_live_injury_codes_give_real_severity_levels(crenshaw):
    sev = Counter(c["severity"] for c in crenshaw["crashes"])
    assert sev["A"] > 0 and sev["B"] > 0 and sev["C"] > 0          # #75: was 0 / 0 / 0
    assert crenshaw["cleaning"]["unknown_injury_values"] == []
    # U is only "injured, but no injury row says how badly", which is rare once the codes map
    assert sev["U"] < 0.05 * sum(sev[k] for k in "KABCU")


def test_live_severity_on_the_study_stretch(crenshaw):
    # Crenshaw Blvd, Marine Ave -> W 132nd St, 2021-2025, crashes on the stretch (side-street reports excluded)
    sev = Counter(c["severity"] for c in crenshaw["crashes"] if not c.get("exclude_rule"))
    # 4 GPS rows > 650 ft from the line dropped (#54); 16 no-cross-street reports now on the review list (#94);
    # 4 house addresses on Crenshaw written in both fields ("CRENSHAW BL" | "CRENSHAW BL 24413") were excluded as an
    # off-corridor cross street: now D5, placed at a NAD point or reviewed (#283); 3 PRIVATE PROPERTY reports with a
    # house address on Crenshaw (11312, 11306, 1210; one B, C, O each) are D5 too (#397), and their addresses are off
    # the stretch: outside the study limits (#410)
    assert dict(sev) == {"K": 1, "A": 6, "B": 48, "C": 82, "O": 196}


def test_house_addresses_off_the_study_stretch_are_outside_the_limits(crenshaw):
    """#410 (user 2026-11-07, "Exclude: outside limits"): 11312 and 11306 Crenshaw are ~1.35 mi north of the
    stretch, 1210 Crenshaw (Torrance) ~4 mi south (Tester on #402). Excluded with the reason, not sent to review."""
    by_id = {c["crash_id"]: c for c in crenshaw["crashes"]}
    for cid in ("2000932", "2138243", "2301460"):
        c = by_id[cid]
        assert c["exclude_rule"] == "outside_study_limits" and not c.get("review_reason"), c
    assert by_id["2000932"]["address_point"]["tier"] == "address_tiger"            # 11312: ADDRFEAT, 61 ft off the line
    p = by_id["2301460"]["address_point"]                                           # 1210, Torrance: ~617 ft off
    assert p["tier"] == "address_point" and p["source"] == "Los Angeles County GIS (CAMS) address points"
    assert p["lat"] < 33.9                                       # the Torrance point, not the Los Angeles (90019) one


def test_live_replay_returns_every_recorded_crash(crenshaw):
    # #53: with typed columns the replay finds the no-coordinate reports too (was 314 of 1602 untyped)
    # one LAPD crash is in CCRS twice (Collision Ids 4364159 v1 and 4369588 v4, Crenshaw Bl & 66th St, #81);
    # 4 GPS rows more than 650 ft from the line stop before the lookups (#54)
    cl = crenshaw["cleaning"]
    assert len(crenshaw["crashes"]) + cl["same_crash_refiled_dropped"] + cl["gps_beyond_margin_dropped"] == 1602
    assert cl["same_crash_refiled"] == [{"kept": "4369588", "dropped": ["4364159"]}]
