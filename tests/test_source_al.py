"""Alabama: CARE eCrash reader (sources/al_care.py) and its plug-in pack, offline on a recorded fixture of 149 live rows
(Jefferson County: normal 2024 rows and shifted 2025 rows, by severity and manner, plus ped, bike, motorcycle, CMV,
interstate, no-point and Unknown-severity rows), recorded 2026-11-08."""

import io
import json
import re
import urllib.parse
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import al_care

from conftest import FIXTURES

ROWS = [f["attributes"] for f in json.loads((FIXTURES / "al_care.json").read_text())["features"]]
PACK = packs.get("AL")


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "al" not in packs.PLUGIN_ERRORS and PACK.name == "Alabama" and PACK.status == "reader_only"
    assert packs.value(PACK, "crash_costs")["K"] == 1571053 and packs.value(PACK, "statewide_rates") is None
    assert packs.check_methods(packs.methods(PACK), "AL") == []


def test_known_rows_pass_the_contract_normal_and_shifted():
    recs = [al_care.contract_record(a) for a in ROWS]
    good = [c for c in recs if c["severity"]]
    assert all(packs.check_crash(c, PACK) == [] for c in good)
    for flag in (False, True):
        part = [c for c in good if c["shifted_row"] is flag]
        assert {"K", "A", "B", "C", "O"} <= {c["severity"] for c in part}, flag
        assert {c["county_fips"] for c in part} == {"01073"} and {c["year"] for c in part} == {2025 if flag else 2024}
    assert any(c["severity"] is None for c in recs)                       # CARE's "Unknown" stays uncounted


def test_shifted_row_is_read_from_where_care_put_each_value():
    a = next(r for r in ROWS if al_care.shifted(r))
    assert re.fullmatch(r"\d{4}", a["County"]) and a["NumMajInj"] == "Jefferson"
    assert a["CrashSev"] not in al_care.SEVERITY and a["ManrCrs"] in al_care.SEVERITY
    c = al_care.contract_record(a)
    assert c["severity"] == al_care.SEVERITY[a["ManrCrs"]] and c["county_code"] == "Jefferson"
    normal = next(r for r in ROWS if not al_care.shifted(r))
    assert al_care.repair(normal) is normal


def test_counts_words_dates_and_flags():
    assert al_care.count("2 Injuries") == 2 and al_care.count("No Fatalities") == 0
    assert al_care.word("E Dark - Spot Illumination Both Sides of Roadway").startswith("Dark")
    recs = [al_care.contract_record(a) for a in ROWS]
    for c in recs:
        assert c["killed"] >= (c["severity"] == "K") and c["injured"] >= (c["severity"] in ("A", "B", "C"))
    # 2024-01-01 02:13 local is stored as 02:13Z; the date and hour must not move
    c = al_care.contract_record({**ROWS[0], "DateTime": 1704075180000})
    assert c["date"] == "2024-01-01" and c["hour"] == 2
    assert any(c["ped"] for c in recs) and any(c["bike"] for c in recs) and any(c["motorcycle"] for c in recs)
    assert any(c["heavy_truck"] for c in recs) and any(c["is_freeway"] for c in recs)
    types = Counter(c["collision_type"] for c in recs)
    assert "REAR END" in types and "BROADSIDE" in types
    nogps = [c for c in recs if c["lat"] is None]
    assert nogps and all(c["primary_road"] for c in nogps) and not any(c["bad_coords"] for c in nogps)
    assert al_care.FIPS[al_care._key("St Clair")] == "01115" and al_care.FIPS[al_care._key("Dekalb")] == "01049"


def test_fetch_contract_asks_box_and_county_no_point_rows_pages_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(al_care, "PAGE", 50)
    wheres = []

    def opener(req, timeout):
        q = urllib.parse.parse_qs(req.data.decode())
        where = q["where"][0]
        wheres.append(where)
        last = int(re.search(r"OBJECTID>(\d+)", where).group(1))
        nopoint = "Latitude <= 0" in where
        rows = [a for a in ROWS if (a["Latitude"] is None or a["Latitude"] <= 0) == nopoint]
        page = sorted((a for a in rows if a["OBJECTID"] > last), key=lambda a: a["OBJECTID"])[:50]
        return io.BytesIO(json.dumps({"features": [{"attributes": a} for a in page]}).encode())

    got = al_care.fetch_contract((33.3, -87.2, 33.8, -86.5), ["01073"], [2024, 2025], tmp_path, opener=opener)
    assert "(Year IN ('2024', '2025') OR County IN ('2024', '2025'))" in wheres[0]
    assert any("County IN ('Jefferson') OR NumMajInj IN ('Jefferson')" in w for w in wheres)
    assert got["cleaning"]["source_rows"] == len(ROWS) and got["cleaning"]["shifted_rows_repaired"] > 0
    assert got["years_missing"] == [] and all(packs.check_crash(c, PACK) == [] for c in got["crashes"])
    again = al_care.fetch_contract((33.3, -87.2, 33.8, -86.5), ["01073"], [2024, 2025], tmp_path, opener=None)
    assert again == got                                           # second call reads the cache, no network


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')   # noqa: E731
    with pytest.raises(RuntimeError):
        al_care.fetch_raw("nope", None, opener=err)
