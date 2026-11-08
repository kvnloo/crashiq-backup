"""State packs (#19): the registry, the reader contract checker and the cited methods files."""

import dataclasses

import pytest

from crashiq import packs

GOOD = {"crash_id": "1", "report_version": 0, "deleted": False, "preliminary": False, "date": "2024-05-01",
        "year": 2024, "hour": 8, "lat": 37.54, "lon": -77.43, "primary_road": "W BROAD ST", "secondary_road": None,
        "offset_ft": None, "offset_dir": None, "city": "RICHMOND", "county_fips": "51760", "state": "VA",
        "is_freeway": False, "killed": 0, "injured": 1, "severity": "B", "ped": False, "bike": False,
        "ebike": False, "escooter": False, "motorcycle": False, "heavy_truck": False, "parties": [],
        "collision_type": "REAR END"}
FAKE = packs.StatePack(code="VA", name="Virginia", fips="51", status="reader_only", source="x", source_short="x",
                       bounds=(36.5, -83.7, 39.5, -75.2), first_year=2017, methods=packs.REF / "methods_va.json")


def test_get_has_no_default():
    assert packs.get("CA").name == "California"
    with pytest.raises(KeyError):
        packs.get("ZZ")


def test_contract_accepts_a_good_crash_and_names_each_break():
    assert packs.check_crash(GOOD, FAKE) == []
    assert any("severity" in m for m in packs.check_crash({**GOOD, "severity": "X"}, FAKE))
    assert any("county_fips" in m for m in packs.check_crash({**GOOD, "county_fips": None}, FAKE))
    assert any("county_fips" in m for m in packs.check_crash({**GOOD, "county_fips": "06037"}, FAKE))
    assert any("outside" in m for m in packs.check_crash({**GOOD, "lat": 34.05, "lon": -118.24}, FAKE))
    noted = dataclasses.replace(FAKE, severity_note="no levels")
    assert any("no injury levels" in m for m in packs.check_crash(GOOD, noted))      # B from a K/U/O source


@pytest.mark.parametrize("path", sorted(packs.REF.glob("methods_*.json")), ids=lambda p: p.name)
def test_every_methods_file_is_cited_or_missing(path):
    import json
    m = json.loads(path.read_text())
    assert packs.check_methods(m, m["state"]) == []


def test_a_non_california_pack_may_not_cite_caltrans():
    import json
    m = json.loads((packs.REF / "methods_ca.json").read_text())
    assert any("not VA's" in p for p in packs.check_methods(m, "VA"))


def test_unverified_or_missing_values_are_never_used():
    pack = packs.get("CA")
    assert packs.value(pack, "min_years") is None                    # verified: false
    assert "not yet checked" in packs.why_missing(pack, "min_years")
    assert packs.value(pack, "spf_calibration") is None
    assert packs.value(pack, "crash_costs")["file"] == "crash_costs_ca.csv"


def test_setup_lists_ready_states_first():
    s = packs.states()
    assert s[0] == {"code": "CA", "name": "California", "ready": True}
    assert all(not x["ready"] for x in s[1:]) and [x["name"] for x in s[1:]] == sorted(x["name"] for x in s[1:])
