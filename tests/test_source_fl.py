"""Florida readers (offline): S4 crash events (open MPO copy + a spec-built export CSV) and FLHSMV Crash Facts."""

import json
from collections import Counter
from pathlib import Path

import pytest

from crashiq.sources import fl_flhsmv, fl_s4

FX = Path(__file__).parent / "fixtures" / "fl"


def test_s4_kabco_map_follows_the_dictionary():
    # S4 Data Dictionary E68 + FDOT Safety Crash Data Guidance KABCO table
    assert [fl_s4.kabco(v) for v in ("Fatal (within 30 days)", "Incapacitating Injury", "Non-Incapacitating Injury",
                                     "Possible Injury", "No Injury", "Non-Traffic Fatality")] == list("KABCOO")
    assert fl_s4.kabco("3 - Non-Incapacitating Injury") == "B"      # Hillsborough's coded copy
    assert fl_s4.kabco("Injury") == "U" and fl_s4.kabco("Serious Injury") == "A" and fl_s4.kabco("??") is None


def test_s4_columns_resolve_across_spellings():
    cols = fl_s4.resolve(["REPORT_NUMBER", "ROAD_SYSTEM_IDENTIFER", "S4_INCAPACITATING_INJURY_CNT", "On Street, Road, Highway"])
    assert cols == {"report_number": "REPORT_NUMBER", "road_system": "ROAD_SYSTEM_IDENTIFER",
                    "n_incap": "S4_INCAPACITATING_INJURY_CNT", "on_street": "On Street, Road, Highway"}


def test_s4_open_layer_fixture():
    feats = json.loads((FX / "s4_palm_beach_2024.json").read_text())["features"]
    crashes = fl_s4.read_features(feats)
    assert len(crashes) == 100
    assert Counter(c["severity"] for c in crashes) == {"O": 76, "C": 10, "A": 6, "K": 4, "B": 4}
    assert all(c["lat"] is not None and c["gps_source"] == "s4" for c in crashes)
    assert all(c["year"] == 2024 and c["date"].startswith("2024-") for c in crashes)   # epoch ms read as wall time
    first = crashes[0]
    assert (first["primary_road"], first["secondary_road"], first["offset_ft"], first["offset_dir"]) == \
        ("N MILITARY TRL", "LILLIAN AVE", 234.0, "S")
    assert first["severity"] == "K" and first["killed"] == 1 and first["ped"] and first["crash_id"] == "objectid:238064"
    for c in crashes:   # crash severity is never milder than its worst person
        if c["person_kabco"]:
            assert fl_s4.SEVERITY_ORDER.index(c["severity"]) <= min(map(fl_s4.SEVERITY_ORDER.index, c["person_kabco"]))


def test_s4_export_csv_from_spec():
    k, fwy, house, zero = list(fl_s4.read_csv(FX / "s4_export_synthetic.csv"))
    assert (k["crash_id"], k["date"], k["hour"], k["severity"], k["person_kabco"]) == \
        ("90000001", "2024-03-14", 17, "K", ["K", "A"])
    assert k["lat"] == 26.712455 and k["gps_source"] == "s4"        # S4's mapped point wins over the officer's
    assert fwy["is_freeway"] and fwy["severity"] == "C" and fwy["injured"] == 2
    assert house["secondary_road"] == "1423 N DIXIE HWY" and house["lat"] is None and house["hit_run"]
    assert zero["lat"] is None and not zero["bad_coords"]           # 0/0 is "no GPS", not a bad point


def test_s4_rejects_other_files(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        list(fl_s4.read_csv(p))


def test_flhsmv_crash_facts_fixture():
    crashes = {c["crash_id"]: c for c in fl_flhsmv.read(FX / "flhsmv_crashfacts_palm_beach_2025.csv")}
    assert len(crashes) == 96
    assert Counter(c["severity"] for c in crashes.values()) == {"O": 58, None: 20, "C": 7, "K": 6, "B": 4, "A": 1}
    assert sum(c["lat"] is not None for c in crashes.values()) == 53
    assert all(c["primary_road"] is None for c in crashes.values())          # no street names in this file
    two_dead = crashes["9898982"]
    assert two_dead["killed"] == 2 and two_dead["person_kabco"] == ["K", "K"]
    no_row = crashes["9853790"]                      # fatal by the crash's max severity, the person has no row
    assert no_row["severity"] == "K" and no_row["killed"] == 1
    assert crashes["10128818"]["hit_run"] and crashes["10128818"]["vehicles"] == 2


def test_flhsmv_filters():
    assert list(fl_flhsmv.read(FX / "flhsmv_crashfacts_palm_beach_2025.csv", county="MIAMI-DADE")) == []
    assert len(list(fl_flhsmv.read(FX / "flhsmv_crashfacts_palm_beach_2025.csv", county="palm beach", years={2025}))) == 96
