"""Idaho: ITD crash-layer reader (sources/id_itd.py) and its plug-in pack, offline on a recorded fixture of 58 live
crashes and their 105 unit rows (Ada County 2022 by severity, road user and route system, 2008 rows with no point, and
2023 rows from the part-loaded year), recorded 2026-11-08."""

import io
import json
import re
import urllib.parse

import pytest

from crashiq import packs
from crashiq.sources import id_itd

from conftest import FIXTURES

FIX = json.loads((FIXTURES / "id_itd_crashes.json").read_text())
ROWS, UNITS = FIX["crashes"], FIX["units"]
PACK = packs.get("ID")
BY = {}
for u in UNITS:
    BY.setdefault(u["Serial_Number"], []).append(u)
RECS = [id_itd.contract_record(a, BY.get(a["Serial_Number"], [])) for a in ROWS]


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "id" not in packs.PLUGIN_ERRORS and PACK.name == "Idaho" and PACK.status == "active"
    assert packs.value(PACK, "crash_costs")["K"] == 14200000
    assert packs.value(PACK, "statewide_rates") is None


def test_rows_with_gps_pass_the_contract_and_severity_words_map():
    gps = [c for c in RECS if c["lat"] is not None]
    assert len(gps) >= 50 and all(packs.check_crash(c, PACK) == [] for c in gps)
    for a, c in zip(ROWS, RECS):
        assert c["severity"] == id_itd.SEVERITY[a["Severity"]]
        assert c["killed"] >= (c["severity"] == "K") and c["injured"] >= (c["severity"] in "ABC")
    assert id_itd.contract_record({**ROWS[0], "Severity": "Unknown"})["severity"] is None


def test_counties_by_name_and_wall_clock_dates():
    assert len(id_itd.FIPS) == 44 and id_itd.FIPS["Ada"] == "16001" and id_itd.FIPS["Nez Perce"] == "16069"
    assert all(c["county_fips"] == id_itd.FIPS[a["County"]] for a, c in zip(ROWS, RECS))
    # 2022-12-31 23:30 Idaho time arrives as 23:30 UTC; the date must not move
    c = id_itd.contract_record({**ROWS[0], "Accident_Date_Time": 1672529400000})
    assert c["date"] == "2022-12-31" and c["hour"] == 23 and c["year"] == 2022


def test_unit_flags_collision_type_freeway_and_no_street_names():
    for flag in ("ped", "bike", "motorcycle", "heavy_truck", "is_freeway"):
        assert any(c[flag] for c in RECS) and not all(c[flag] for c in RECS), flag
    assert {"REAR END", "BROADSIDE"} <= {c["collision_type"] for c in RECS}
    assert all(c["primary_road"] is None and c["secondary_road"] is None for c in RECS)
    nogps = [c for c in RECS if c["lat"] is None]
    assert len(nogps) == 3 and not any(c["bad_coords"] for c in nogps)
    far = id_itd.contract_record({**ROWS[0], "Latitude": "34.0", "Longitude": "-118.0"})
    assert far["lat"] is None and far["bad_coords"]


def _opener(page, urls):
    def opener(req, timeout):
        q = urllib.parse.unquote_plus(req.full_url)
        urls.append(q)
        if "outStatistics" in q:
            return io.BytesIO(json.dumps(FIX["max"]).encode())
        rows = UNITS if "/35/query" in q else ROWS
        last = int(re.search(r"OBJECTID>(\d+)", q).group(1))
        out = sorted((a for a in rows if a["OBJECTID"] > last), key=lambda a: a["OBJECTID"])[:page]
        return io.BytesIO(json.dumps({"features": [{"attributes": a} for a in out]}).encode())
    return opener


def test_last_full_year_drops_the_part_loaded_year():
    assert id_itd.last_full_year(_opener(0, [])) == 2022                       # newest crash 2023-10-01
    end = lambda d: lambda req, timeout: io.BytesIO(json.dumps({"features": [{"attributes": {"hi": d}}]}).encode())  # noqa: E731
    assert id_itd.last_full_year(end(1703980800000)) == 2023                   # 2023-12-31


def test_fetch_contract_sends_the_box_pages_both_layers_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(id_itd, "PAGE", 20)
    urls = []
    got = id_itd.fetch_contract((43.5, -116.4, 43.7, -116.1), ["16001"], [2022, 2023], tmp_path,
                                opener=_opener(20, urls))
    assert "geometry=-116.4,43.5,-116.1,43.7" in urls[1] and "Accident_Year IN ('2022', '2023')" in urls[1]
    assert sum("/11/query" in u and "outStatistics" not in u for u in urls) == 3    # 58 rows: 20 + 20 + 18
    assert got["years_missing"] == [2023] and got["cleaning"]["part_year_dropped"] == 3
    assert {c["year"] for c in got["crashes"]} == {2022}
    assert all(packs.check_crash(c, PACK) == [] for c in got["crashes"] if c["lat"] is not None)
    assert any(c["ped"] for c in got["crashes"])                                     # units joined by serial
    again = id_itd.fetch_contract((43.5, -116.4, 43.7, -116.1), ["16001"], [2022, 2023], tmp_path, opener=None)
    assert again == got                                                              # cache, no network


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')   # noqa: E731
    with pytest.raises(RuntimeError):
        id_itd.last_full_year(err)
