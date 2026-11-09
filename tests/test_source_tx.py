"""TxDOT CRIS public-extract reader (crashiq.sources.tx_cris) on the synthetic fixture built from TxDOT's spec
(tests/fixtures/make_tx_cris_fixture.py). Offline."""

import shutil
from pathlib import Path

import pytest

from crashiq.sources import tx_cris

FIX = Path(__file__).parent / "fixtures" / "tx_cris"


@pytest.fixture(scope="module")
def crashes():
    return {c["collision_id"]: c for c in tx_cris.read_extract(FIX)}


def test_reads_every_crash_with_the_shared_keys(crashes):
    assert len(crashes) == 6
    shared = {"collision_id", "datetime", "lat", "lon", "primary_road", "secondary_road", "offset_ft", "offset_dir",
              "city_name", "county_code", "killed", "injured", "collision_type", "lighting", "weather", "surface",
              "is_freeway", "severity", "persons"}
    assert all(shared <= set(c) for c in crashes.values())


def test_off_system_street_pair_and_lookups(crashes):
    c = crashes["90000001"]
    assert (c["primary_road"], c["secondary_road"]) == ("E BELT LINE RD", "S HIGHLAND DR")
    assert c["datetime"] == "2025-03-14T14:50" and c["gps_source"] == "txdot_locator"
    assert (c["city_name"], c["county_name"]) == ("DALLAS", "DALLAS")
    assert c["collision_type"] == "ANGLE - ONE STRAIGHT-ONE LEFT TURN" and c["weather"] == "CLEAR"
    assert c["severity"] == "A"                               # driver A, passenger B: the worst person counts
    assert sorted(p["kabco"] for p in c["persons"]) == ["A", "B", "O"]   # primaryperson + person files both read


def test_on_system_reference_marker_and_locator_fields(crashes):
    c = crashes["90000002"]
    assert c["primary_road"] == "IH 35E"                      # highway system + number when the officer names no street
    assert c["offset_ft"] is None                             # the offset is from the marker, not the intersection
    assert (c["ref_marker"], c["ref_marker_offset_ft"], c["ref_marker_dir"]) == ("430", 0.3 * 5280, "N")
    assert (c["highway"], c["control"], c["section"], c["milepoint"]) == ("IH 35E", "196", "3", 2.345)
    assert c["is_freeway"] and c["aadt"] == 145111 and c["hour"] == 23
    assert c["severity"] == "K" and c["ped"]


def test_offset_from_intersection_and_officer_gps_fallback(crashes):
    c = crashes["90000003"]
    assert (c["offset_ft"], c["offset_dir"]) == (150.0, "W")
    assert c["gps_source"] == "officer" and c["lat"] == pytest.approx(32.92307423)
    assert c["motorcycle"] and c["severity"] == "C"


def test_severity_edges_and_bad_coordinates(crashes):
    assert crashes["90000004"]["severity"] == "O" and crashes["90000004"]["lat"] is None
    assert crashes["90000004"]["private_drive"]
    assert crashes["90000005"]["severity"] == "U"             # CRIS 0 UNKNOWN on the crash and the person
    assert crashes["90000006"]["severity"] == "B"             # no person rows: the crash-level code
    assert crashes["90000006"]["lat"] is None                 # 0/0 is not a place


def test_headers_in_any_case(tmp_path):
    for p in FIX.glob("*.csv"):
        lines = p.read_text().splitlines()
        (tmp_path / p.name).write_text("\n".join([lines[0].lower(), *lines[1:]]) + "\n")
    assert {c["collision_id"]: c["severity"] for c in tx_cris.read_extract(tmp_path)}["90000002"] == "K"


def test_reader_columns_exist_in_the_spec_headers():
    """Every crash/person column the reader reads is a column of TxDOT's spec (the fixture carries the spec's headers)."""
    head = {h.lower() for h in (FIX / next(p.name for p in FIX.glob("*_crash_*"))).read_text().splitlines()[0].split(",")}
    read = {"crash_id", "crash_date", "crash_time", "latitude", "longitude", "rpt_latitude", "rpt_longitude",
            "rpt_street_pfx", "rpt_street_name", "rpt_street_sfx", "rpt_sec_street_name", "rpt_hwy_num",
            "rpt_rdwy_sys_id", "rpt_sec_rdwy_sys_id", "rpt_ref_mark_offset_amt", "rpt_ref_mark_dist_uom",
            "rpt_ref_mark_dir", "rpt_ref_mark_nbr", "rpt_block_num", "at_intrsct_fl", "hwy_sys", "hwy_nbr", "control",
            "section", "milepoint", "dfo", "ref_mark_nbr", "ref_mark_displ", "street_name", "onsys_fl", "located_fl",
            "crash_sev_id", "death_cnt", "tot_injry_cnt", "fhe_collsn_id", "func_sys_id", "adt_curnt_amt", "cnty_id",
            "city_id", "private_dr_fl", "txdot_rptable_fl"}
    assert read <= head, read - head


def test_missing_crash_file_is_a_clear_error(tmp_path):
    shutil.copy(next(FIX.glob("*_person_*")), tmp_path)
    with pytest.raises(FileNotFoundError, match="unzip"):
        tx_cris.read_extract(tmp_path)
