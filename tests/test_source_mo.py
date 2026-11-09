"""Missouri: MSHP STARS crash layer reader (sources/mo_mshp.py) and its plug-in pack, offline on a recorded fixture
(Jackson County 2023: one row per severity x light x At/After/Before, plus ped, bike, freeway, no-GPS, parking-lot and
ramp / reference-point rows), recorded 2026-11-08 by research_notes/mo-2026-11-08/mo_pull.py."""

import json

from crashiq import packs
from crashiq.sources import mo_mshp as mo

from conftest import FIXTURES

FX = json.loads((FIXTURES / "mo_mshp.json").read_text())
ROWS = FX["rows"]
PACK = packs.get("MO")


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "mo" not in packs.PLUGIN_ERRORS and PACK.name == "Missouri" and PACK.status == "active"
    assert PACK.severity_note is None and packs.value(PACK, "crash_costs") is None
    assert packs.check_methods(packs.methods(PACK), "MO") == []
    assert len(mo.FIPS) == 115 and mo.FIPS["JACKSON"] == "29095" and mo.FIPS["ST. LOUIS CITY"] == "29510"
    assert mo.FIPS["ST. LOUIS"] == "29189"


def test_rows_pass_the_contract_and_severity_is_k_a_u_o():
    cs = [mo.contract_record(a) for a in ROWS]
    assert all(packs.check_crash(c, PACK) == [] for c in cs)
    assert {c["severity"] for c in cs} == set("KAUO")
    for a, c in zip(ROWS, cs):
        want = ("K" if a["SEVERITY"] == "Fatal" else "A" if a["DIS_INJ"] else
                "U" if a["SEVERITY"] == "Personal Injury" else "O")
        assert c["severity"] == want
    assert any(c["lat"] is None for c in cs) and any(c["ped"] for c in cs) and any(c["bike"] for c in cs)
    assert any(c["is_freeway"] for c in cs) and any(not c["is_freeway"] for c in cs)


def test_roads_are_read_the_way_the_locator_reads_them():
    assert mo.road("CST DALE AVE") == "DALE AVE" and mo.road("CRD PINK HILL RD") == "PINK HILL RD"
    assert mo.road("IS 70") == "I 70" and mo.road("MO 78") == "MO 78" and mo.road("RT J") == "RT J"
    assert mo.road("PP PARKING LOT AT 353 S KIRKWOOD RD") is None and mo.road("  ") is None
    c = mo.contract_record({**ROWS[0], "ON_STREET": "US 36", "AT_STREET": "RP 7610"})
    assert c["primary_road"] == "US 36" and c["secondary_road"] is None
    c = mo.contract_record({**ROWS[0], "ON_STREET": "IS 70", "AT_STREET": "ERM WEST IS 70 MILE 1070"})
    assert c["secondary_road"] is None and c["is_freeway"]


def test_offset_after_is_along_the_roadway_direction_before_is_against_it():
    base = {**ROWS[0], "DIST_FEET": 200}
    assert mo.offset({**base, "INTER_LOC": "A ", "DIRECTION": "S "}) == (200, "S")
    assert mo.offset({**base, "INTER_LOC": "B ", "DIRECTION": "S "}) == (200, "N")
    assert mo.offset({**base, "INTER_LOC": "AT", "DIRECTION": "E "}) == (None, None)
    assert mo.offset({**base, "INTER_LOC": "A ", "DIRECTION": "NA"}) == (None, None)
    assert mo.offset({**base, "INTER_LOC": "A ", "DIRECTION": "E ", "DIST_FEET": 0}) == (None, None)


def test_dates_ids_and_points():
    cs = [mo.contract_record(a) for a in ROWS]
    assert all(c["date"].startswith("2023-") and c["year"] == 2023 for c in cs)
    assert len({c["crash_id"] for c in cs}) == len(cs)
    far = mo.contract_record({**ROWS[0], "GPS_LAT": 34.0, "GPS_LONG": -118.0})
    assert far["lat"] is None and far["bad_coords"]
    zero = mo.contract_record({**ROWS[0], "GPS_LAT": 0.0, "GPS_LONG": 0.0})
    assert zero["lat"] is None and not zero["bad_coords"]


class FakeLayer:
    def __init__(self):
        self.calls = []

    def __call__(self, url, params):
        self.calls.append(params)
        if params.get("returnIdsOnly"):
            return {"objectIds": [r["OBJECTID"] for r in ROWS]}
        want = set(map(int, params["objectIds"].split(",")))
        return {"features": [{"attributes": r} for r in ROWS if r["OBJECTID"] in want]}


def test_fetch_contract_asks_for_the_box_plus_no_gps_rows_in_the_counties_and_caches(tmp_path):
    fake = FakeLayer()
    got = mo.fetch_contract(FX["box"], ["29095"], [2012, 2023], tmp_path, get=fake)
    q = fake.calls[0]["where"]
    assert "ACC_DATE >= '2023-01-01 00:00:00'" in q and "COUNTY IN ('JACKSON')" in q and "GPS_LAT IS NULL" in q
    assert got["years_missing"] == [2012] and len(got["crashes"]) == len(ROWS)
    assert got["cleaning"]["no_gps"] == sum(not mo.plausible(r["GPS_LAT"], r["GPS_LONG"]) for r in ROWS)
    assert mo.fetch_contract(FX["box"], ["29095"], [2012, 2023], tmp_path, get=None) == got     # cached
    assert "O''FALLON" in mo.where(FX["box"], 2023, ["O'FALLON"])
