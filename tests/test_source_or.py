"""Oregon ODOT CDS reader (states brief 2026-11-07): the decode-DB tables and the public ArcGIS layer, offline from
tests/fixtures/or_odot/ (40 real Multnomah 2024 crashes; recorder: tests/fixtures/make_or_odot.py)."""

import json

import pytest

from crashiq.sources import or_odot

from conftest import FIXTURES

D = FIXTURES / "or_odot"


def _replay():
    rec = json.loads((D / "layer.json").read_text())
    calls = iter(rec["calls"])

    def get(url, params):
        call = next(calls)
        assert url == or_odot.LAYER + "/query" and params == call["params"]
        return call["body"]
    return rec["where"], get


@pytest.fixture(scope="module")
def decode():
    return {c["crash_id"]: c for c in or_odot.read_decode(D / "CRASH.csv", D / "PARTIC.csv")}


def test_person_kabco_matches_odots_crash_kabco(decode):
    where, get = _replay()
    layer = or_odot.fetch_layer(where, get=get)
    assert len(decode) == len(layer) == 40
    assert {c["severity"] for c in decode.values()} >= {"K", "O"}
    for c in layer:                                   # two published products of one CDS year agree, crash by crash
        d = decode[c["crash_id"]]
        assert d["severity"] == c["severity"] == c["odot_kabco"]
        assert (d["date"], d["hour"], d["killed"], d["collision_type"], d["primary_road"], d["secondary_road"], d["lat"]) == \
               (c["date"], c["hour"], c["killed"], c["collision_type"], c["primary_road"], c["secondary_road"], c["lat"])
        assert d["persons"] and not c["persons"]      # participants only in the decode DB


def test_location_fields(decode):
    cs = list(decode.values())
    unloc = [c for c in cs if c["unlocated"]]
    assert unloc and all(c["lat"] is None and c["lon"] is None for c in unloc)   # ODOT's default point is dropped
    assert all(or_odot.plausible(c["lat"], c["lon"]) for c in cs if not c["unlocated"])
    assert any(c["is_freeway"] and c["route"] for c in cs)
    off = [c for c in cs if c["offset_dir"]]
    assert any(c["offset_dir"] in ("N", "E", "S", "W") and c["offset_ft"] > 0 for c in off)
    assert all(c["offset_dir"] in or_odot.COMPASS.values() for c in off)            # CN / UN codes give no direction
    assert all(c["date"].startswith("2024-") and c["county"] == "Multnomah" for c in cs)


def _row(**kw):
    base = {"CRASH_ID": "1", "CRASH_YR_NO": "2024", "CRASH_MO_NO": "3", "CRASH_DAY_NO": "9", "LAT_DD": "45.5",
            "LONGTD_DD": "-122.6", "UNLOCT_FLG": "0", "TOT_FATAL_CNT": "0", "TOT_INJ_LVL_A_CNT": "0",
            "TOT_INJ_LVL_B_CNT": "0", "TOT_INJ_LVL_C_CNT": "0"}
    return or_odot.crash_record({**base, **kw})


def test_severity_rules():
    pdo = _row(CRASH_SVRTY_CD="5")
    assert or_odot.severity(pdo, ["O", "O"]) == "O"
    assert or_odot.severity(pdo, [None, "A", "C"]) == "A"
    assert or_odot.severity(_row(CRASH_SVRTY_CD="4"), ["O", None]) == "U"    # injury crash, no level coded
    assert or_odot.severity(_row(TOT_INJ_LVL_B_CNT="1"), ["O"]) == "B"       # counts are a floor
    assert or_odot.INJ_KABCO.get("5") is None                                # died before the crash: not counted


def test_hours_and_dates():
    assert _row(CRASH_HR_NO="00")["hour"] == 0 and _row(CRASH_HR_NO="99")["hour"] is None
    assert _row(CRASH_HR_LONG_DESC="12:00 AM (Midnight) to 12")["hour"] == 0
    assert _row(CRASH_HR_LONG_DESC="12:00 PM (Noon) to 12:59 ")["hour"] == 12
    assert _row(CRASH_HR_LONG_DESC="Unknown Time")["hour"] is None
    assert _row()["date"] == "2024-03-09"
    assert _row(LAT_DD="0", LONGTD_DD="0")["bad_coords"] and _row(UNLOCT_FLG="True")["lat"] is None


def test_contract_rows_pass_the_pack_checker(tmp_path):
    # #19: the OR pack reads the public layer: box OR (unlocated in the corridor's counties), years 2019-2024
    import json
    from crashiq import packs
    rec = json.loads((D / "layer.json").read_text())["calls"]
    asked = []

    def get(url, params):
        asked.append(params)
        return rec[0]["body"] if params.get("returnIdsOnly") else rec[1]["body"]
    boxes = json.loads((packs.REF / "county_boxes_or.json").read_text())["counties"]
    got = or_odot.fetch_contract((45.4, -122.8, 45.6, -122.3), ["41051"], [2018, 2024], tmp_path, boxes, get)
    assert "CRASH_YR_NO IN ('2024')" in asked[0]["where"] and "CNTY_NM IN ('Multnomah')" in asked[0]["where"]
    assert got["years_missing"] == [2018] and got["crashes"]
    assert all(packs.check_crash(c, packs.get("OR")) == [] for c in got["crashes"])
    assert got["cleaning"]["unlocated"] >= 1 and all(c["county_fips"] == "41051" for c in got["crashes"])
    assert "BROADSIDE" in {c["collision_type"] for c in got["crashes"]}
