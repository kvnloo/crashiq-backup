"""Nebraska: NDOT NTIP crash-map reader (sources/ne_ntip.py), offline on a recorded fixture: the 160 live 2024
crashes in a box around W Dodge Rd and 72nd St, Omaha, and the keys the map's filters return, recorded 2026-11-08."""

import io
import json
import urllib.parse
from collections import Counter

from crashiq import packs
from crashiq.sources import ne_ntip

from conftest import FIXTURES

GOT = json.loads((FIXTURES / "ne_ntip_dodge_72nd_2024.json").read_text())
FLAGS = {k: set(v) for k, v in GOT["flags"].items()}


def test_every_reportable_crash_maps_to_the_contract():
    pack = packs.get("NE")
    got = [ne_ntip.crash_record(c, FLAGS) for c in GOT["rows"]]
    kept = [c for c in got if c]
    assert len(kept) == len(GOT["rows"]) - sum(c["s"] in ("06", "96") for c in GOT["rows"]) == 120
    assert all(packs.check_crash(c, pack) == [] for c in kept)
    assert {c["county_fips"] for c in kept} == {"31055"}                         # Douglas
    assert Counter(c["severity"] for c in kept) == {"O": 69, "B": 24, "C": 23, "A": 4}
    assert sum(c["motorcycle"] for c in kept) == 5


def test_location_sentences():
    loc = ne_ntip.location
    assert loc("INT-ROSE BLUMKIN DRIVE (5031) & 72ND STREET (5037)") == {
        "primary_road": "ROSE BLUMKIN DRIVE", "secondary_road": "72ND STREET", "offset_dir": None, "intersection": True}
    assert loc("LEAVENWORTH STREET (5044) E OF 60TH STREET (5043)")["offset_dir"] == "E"
    assert loc("204TH STREET (006) S OF W CENTER ROAD (275) NEAR OMAHA")["secondary_road"] == "W CENTER ROAD"
    assert loc("52ND STREET (5049) NEAR AMES AVENUE (5080)")["secondary_road"] == "AMES AVENUE"
    assert loc("INT-IDA STREET (5168) N OF N-133 (133)")["secondary_road"] == "NE 133"
    assert loc("I-80 (080)") == {"primary_road": "I-80", "secondary_road": None, "offset_dir": None,
                                 "intersection": False}


def test_time_and_bad_points():
    c = ne_ntip.crash_record({**GOT["rows"][0], "s": "05", "d": "12/31/2024", "t": "11:55 PM"}, FLAGS)
    assert (c["date"], c["hour"], c["year"]) == ("2024-12-31", 23, 2024)
    far = ne_ntip.crash_record({**GOT["rows"][0], "s": "05", "a": 34.0, "o": -118.0}, FLAGS)
    assert far["lat"] is None and far["bad_coords"]


def test_fetch_contract_posts_the_box_asks_each_filter_and_caches(tmp_path):
    seen = []

    def opener(req, timeout):
        form = urllib.parse.parse_qs(req.data.decode())
        seen.append(form)
        assert req.headers["User-agent"] == "CrashIQ/0.1" and req.get_method() == "POST"
        flag = next((f for f, q in ne_ntip.FLAGS.items() if set(q) <= set(form)), None)
        rows = GOT["rows"] if flag is None else [c for c in GOT["rows"] if c["k"] in FLAGS[flag]]
        return io.BytesIO(json.dumps({"CoordGroups": [{"Crashes": rows}]}).encode())

    box = (41.255, -96.035, 41.268, -96.015)
    got = ne_ntip.fetch_contract(box, ["31055"], [2020, 2024], tmp_path, opener=opener)
    assert len(seen) == 5 and seen[0]["fromDate"] == ["01/01/2024"] and seen[0]["minLat"] == ["41.255"]
    assert seen[4]["roadClass"] == ["1", "2"]
    assert got["years_missing"] == [2020] and len(got["crashes"]) == 120
    assert got["cleaning"]["non_reportable_left_out"] == 40
    again = ne_ntip.fetch_contract(box, ["31055"], [2024], tmp_path, opener=None)      # cached: no network
    assert len(again["crashes"]) == 120


def test_pack_is_reader_only_and_its_methods_are_cited():
    pack = packs.get("NE")
    assert pack.status == "reader_only" and pack.first_year == 2021
    assert packs.check_methods(packs.methods(pack), "NE") == []
    assert packs.value(pack, "crash_costs") is None and "per person" in packs.why_missing(pack, "crash_costs")
    assert len(json.loads(pack.county_boxes.read_text())["counties"]) == 93
