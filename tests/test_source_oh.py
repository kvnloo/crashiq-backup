"""Ohio: ODOT TIMS crash-layer reader (sources/oh_tims.py) and its plug-in pack, offline on a recorded fixture of 45
live rows (central Columbus, 2024: every severity, ped, bike, freeway, interstate/US/municipal/ramp NLFIDs), recorded
2026-11-08."""

import json
import re
import urllib.parse

import pytest

from crashiq import packs, study
from crashiq.sources import oh_tims

from conftest import FIXTURES

FX = json.loads((FIXTURES / "oh_tims.json").read_text())
ROWS = FX["rows"]
PACK = packs.get("OH")


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "oh" not in packs.PLUGIN_ERRORS and PACK.name == "Ohio" and PACK.status == "active"
    assert PACK.severity_note is None                                  # KABCO, all five levels
    assert packs.check_methods(packs.methods(PACK), "OH") == []
    assert packs.value(PACK, "crash_costs")["K"] == 2266992


def test_rows_pass_the_contract_with_kabco_severity():
    cs = [oh_tims.contract_record(r) for r in ROWS]
    assert all(packs.check_crash(c, PACK) == [] for c in cs)
    assert {c["severity"] for c in cs} == set("KABCO")
    for r, c in zip(ROWS, cs):
        assert c["severity"] == "KABCO"[r["CRASH_SEVERITY_CD"] - 1]
    assert oh_tims.contract_record({**ROWS[0], "CRASH_SEVERITY_CD": 9})["severity"] is None   # never guessed


def test_dates_points_flags_and_county():
    cs = [oh_tims.contract_record(r) for r in ROWS]
    assert all(c["date"] == "" and c["year"] == 2024 and 1 <= c["month"] <= 12 for c in cs)   # no day of month
    assert all(c["day_of_week"] in oh_tims.DOW.values() and (c["hour"] is None or 0 <= c["hour"] < 24) for c in cs)
    assert all(c["county_fips"] == "39049" and c["lat"] is not None for c in cs)
    assert any(c["ped"] for c in cs) and any(c["bike"] for c in cs)
    assert any(c["is_freeway"] for c in cs) and any(not c["is_freeway"] for c in cs)
    assert "BROADSIDE" in {c["collision_type"] for c in cs} or "REAR END" in {c["collision_type"] for c in cs}
    far = oh_tims.contract_record({**ROWS[0], "ODOT_LATITUDE_NBR": 34.0, "ODOT_LONGITUDE_NBR": -118.0})
    assert far["lat"] is None and far["bad_coords"]


def test_route_names_from_nlfid():
    assert oh_tims.route("SFRAIR00070**C") == "I-70"
    assert oh_tims.route("SFRAUS00023**C") == "US 23" and oh_tims.route("SHURSR00113**C") == "SR 113"
    assert oh_tims.route("MFRAMR01358**C") is None and oh_tims.route(None) is None    # inventory numbers aren't names


def test_county_codes_map_to_fips_in_name_order():
    boxes = json.loads(PACK.county_boxes.read_text())["counties"]
    assert len(oh_tims.FIPS) == 88 == len(boxes) and set(oh_tims.FIPS.values()) == set(boxes)
    for code, fips in oh_tims.FIPS.items():          # ODOT's code letters appear in order in the county's name
        assert re.search(".*".join(code), boxes[fips]["name"].upper()), (code, boxes[fips]["name"])
    assert oh_tims.FIPS["FRA"] == "39049" and oh_tims.FIPS["CUY"] == "39035" and oh_tims.FIPS["HAM"] == "39061"


def test_default_window_is_five_years_from_first_year():
    from datetime import date
    assert study.default_window(date(2026, 11, 8), PACK) == (2021, 2025)
    assert study.default_window(date(2026, 3, 1), PACK) == (2021, 2024)


class FakeTims:
    """TIMS's query endpoint answered from the fixture, PAGE rows at a time; 2020 has no service."""
    def __init__(self, page=20):
        self.calls, self.page = [], page

    def __call__(self, url):
        q = dict(urllib.parse.parse_qsl(url.split("?", 1)[1]))
        self.calls.append(q)
        if "/2020_" in url:
            return {"error": {"code": 404, "message": "Service not found", "details": []}}
        off, n = int(q["resultOffset"]), int(q["resultRecordCount"])
        rows = ROWS[off:off + min(n, self.page)]
        return {"features": [{"attributes": r} for r in rows],
                "exceededTransferLimit": off + len(rows) < len(ROWS)}


def test_fetch_contract_pages_marks_missing_years_and_caches(tmp_path):
    tims = FakeTims()
    got = oh_tims.fetch_contract(tuple(FX["box"]), ["39049"], [2020, 2024], tmp_path, get=tims)
    assert got["years_missing"] == [2020] and len(got["crashes"]) == len(ROWS)
    assert got["cleaning"]["source_rows"] == len(ROWS) and len(tims.calls) == 1 + 3      # 2020 + three pages
    assert "ODOT_LATITUDE_NBR >=" in tims.calls[-1]["where"]
    again = oh_tims.fetch_contract(tuple(FX["box"]), ["39049"], [2024], tmp_path, get=None)
    assert again["crashes"] == got["crashes"]                         # second call reads the cache, no network


def test_other_service_errors_are_raised():
    with pytest.raises(RuntimeError):
        oh_tims.query_year((40, -83, 40.1, -82.9), 2024, get=lambda u: {"error": {"code": 500, "message": "x"}})
