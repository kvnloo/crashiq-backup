"""North Dakota: NDDOT crash layer reader (sources/nd_nddot.py), offline on a recorded fixture: 38 live rows of the
public layer (2024 Fargo crashes by KABCO level, pedestrian and interstate rows, Burleigh non-collision rows, and the
two rows whose hour is '24' or '6-'), cut to the columns the reader reads, recorded 2026-11-08."""

import json
from collections import Counter
from datetime import date

from crashiq import packs, study
from crashiq.sources import nd_nddot

from conftest import FIXTURES

FIX = json.loads((FIXTURES / "nd_nddot_sample.json").read_text())
ROWS = FIX["rows"]


def test_every_row_maps_to_the_contract():
    pack = packs.get("ND")
    crashes = [nd_nddot.contract_record(a) for a in ROWS]
    assert len(crashes) == 38
    assert all(packs.check_crash(c, pack) == [] for c in crashes)
    assert all(c["lat"] is not None and c["primary_road"] is None for c in crashes)
    assert Counter(c["county_fips"] for c in crashes) == {"38017": 33, "38015": 3, "38089": 1, "38105": 1}


def test_kabco_and_codes():
    crashes = {c["crash_id"]: c for c in map(nd_nddot.contract_record, ROWS)}
    assert Counter(c["severity"] for c in crashes.values()) == {"O": 17, "B": 7, "C": 7, "A": 5, "K": 2}
    k = crashes["ID1155269"]
    assert (k["severity"], k["killed"], k["motorcycle"], k["date"], k["hour"]) == ("K", 1, True, "2024-06-29", 20)
    assert k["collision_type"] == "UTILITY POLE/LIGHT SUPPORT"       # non-collision crash: its first harmful event
    assert {i: c["collision_type"] for i, c in crashes.items() if c["ped"]} == {
        "ID1150908": "VEHICLE/PEDESTRIAN", "ID1148282": "VEHICLE/PEDESTRIAN", "ID1150925": "OTHER NON-MOTORIST"}
    assert [c["hour"] for c in crashes.values() if c["crash_id"] in ("ID1035079", "ID1043218")] == [None, None]
    blank = dict(ROWS[0], Crash_Severity_KABCO="", Crash_Severity_ID="3")
    assert nd_nddot.contract_record(blank)["severity"] == "B"          # the numeric id when the text is blank


def test_fetch_contract_queries_once_and_caches(tmp_path):
    calls = []

    def get(url, params):
        calls.append(params)
        if params.get("returnIdsOnly"):
            return {"objectIds": [r["ID"] for r in ROWS]}
        want = set(map(int, params["objectIds"].split(",")))
        return {"features": [{"attributes": r} for r in ROWS if r["ID"] in want]}

    box = (46.75, -96.95, 46.95, -96.75)                           # Fargo
    got = nd_nddot.fetch_contract(box, ["38017"], [2023, 2024, 2026], tmp_path, get=get)
    assert "crash_yr IN ('2023', '2024')" in calls[0]["where"] and "latitude >= 46.750000" in calls[0]["where"]
    assert got["years_missing"] == [2026] and len(got["crashes"]) == 38 and len(calls) == 2
    again = nd_nddot.fetch_contract(box, ["38017"], [2023, 2024, 2026], tmp_path, get=None)   # cached: no network
    assert len(again["crashes"]) == 38
    assert nd_nddot.fetch_contract(box, ["38017"], [2016], tmp_path, get=get)["years_missing"] == [2016]


def test_pack_is_registered_and_its_methods_are_cited():
    pack = packs.get("ND")
    assert pack.status == "active" and "ND" not in packs.PLUGIN_ERRORS.values()
    assert packs.check_methods(packs.methods(pack), "ND") == []
    assert packs.value(pack, "crash_costs") is None and packs.value(pack, "min_years")["value"] == 3
    assert len(json.loads(pack.county_boxes.read_text())["counties"]) == 53
    assert study.default_window(date(2026, 11, 8), pack) == (2020, 2024)
