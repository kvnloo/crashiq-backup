"""Utah: UDOT Utah Crash Locations reader (sources/ut_udot.py) and its plug-in pack, offline on a recorded fixture of
49 live Salt Lake County 2024 crashes (by severity, road user, freeway, cross street and house address), 2026-11-08."""

import io
import json
import re
import urllib.parse

import pytest

from crashiq import packs
from crashiq.sources import ut_udot

from conftest import FIXTURES

FIX = json.loads((FIXTURES / "ut_udot_crashes.json").read_text())
FEATS = FIX["features"]
PACK = packs.get("UT")
RECS = [ut_udot.contract_record(f) for f in FEATS]


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "ut" not in packs.PLUGIN_ERRORS and PACK.name == "Utah" and PACK.status == "active"
    costs = packs.value(PACK, "crash_costs")
    assert costs["K"] == costs["A"] == 3904059 and costs["O"] == 17100       # UDOT's weighted KA for observed crashes
    assert packs.value(PACK, "statewide_rates") is None


def test_every_row_passes_the_contract_and_severity_words_map():
    assert len(RECS) == 49 and all(packs.check_crash(c, PACK) == [] for c in RECS)
    for f, c in zip(FEATS, RECS):
        assert c["severity"] == ut_udot.SEVERITY[f["attributes"]["crash_severity_desc"]]
        assert c["killed"] >= (c["severity"] == "K") and c["injured"] >= (c["severity"] in "ABC")
    assert {c["severity"] for c in RECS} == set("KABCO")
    assert ut_udot.contract_record({**FEATS[0], "attributes": {**FEATS[0]["attributes"],
                                    "crash_severity_desc": "Unknown"}})["severity"] is None


def test_utc_times_become_utah_dates_and_counties_map():
    assert len(ut_udot.FIPS) == 29 and ut_udot.FIPS["SALT LAKE"] == "49035"
    f = {**FEATS[0], "attributes": {**FEATS[0]["attributes"], "crash_datetime": "2025-01-01T06:30:00+00:00"}}
    c = ut_udot.contract_record(f)
    assert c["date"] == "2024-12-31" and c["hour"] == 23 and c["year"] == 2024     # 23:30 MST on New Year's Eve


def test_cross_street_offset_house_address_and_flags():
    c = ut_udot.contract_record({"attributes": {**FEATS[0]["attributes"], "main_road_name": "I-15",
                                 "location_desc": "I-15, at 249 Feet S of 700 South, at 3 tenths of a mile N of MP 307"},
                                 "geometry": FEATS[0]["geometry"]})
    assert (c["primary_road"], c["secondary_road"], c["offset_ft"], c["offset_dir"]) == ("I-15", "700 South", 249, "S")
    at = ut_udot.contract_record({"attributes": {**FEATS[0]["attributes"],
                                  "location_desc": "Bangerter Highway, at 0 Feet S of 4100 South, at 1 tenths"},
                                  "geometry": FEATS[0]["geometry"]})
    assert at["secondary_road"] == "4100 South" and at["offset_ft"] is None and at["offset_dir"] is None
    assert any(re.match(r"^\d+ ", c["primary_road"] or "") and c["secondary_road"] is None for c in RECS)
    for flag in ("ped", "bike", "motorcycle", "heavy_truck", "is_freeway"):
        assert any(c[flag] for c in RECS) and not all(c[flag] for c in RECS), flag
    assert {"REAR END", "BROADSIDE", "VEHICLE/PEDESTRIAN", "HIT OBJECT"} <= {c["collision_type"] for c in RECS}
    far = ut_udot.contract_record({**FEATS[0], "geometry": {"x": -118.0, "y": 34.0}})
    assert far["lat"] is None and far["bad_coords"]


def _opener(urls):
    def opener(req, timeout):
        q = urllib.parse.unquote_plus(req.full_url)
        urls.append(q)
        if "/query" not in q:
            return io.BytesIO(json.dumps({"layers": [{"id": i, "name": f"{y} Crash Locations"}
                                                     for y, i in FIX["layers"]]}).encode())
        last = int(re.search(r"OBJECTID>(\d+)", q).group(1))
        out = sorted((f for f in FEATS if f["attributes"]["OBJECTID"] > last), key=lambda f: f["attributes"]["OBJECTID"])
        return io.BytesIO(json.dumps({"features": out[:ut_udot.PAGE]}).encode())
    return opener


def test_fetch_contract_sends_the_box_pages_marks_preliminary_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(ut_udot, "PAGE", 20)
    urls = []
    got = ut_udot.fetch_contract((40.5, -112.1, 40.8, -111.7), ["49035"], [2018, 2024, 2025], tmp_path,
                                 opener=_opener(urls))
    q = [u for u in urls if "/query" in u]
    assert "geometry=-112.1,40.5,-111.7,40.8" in q[0] and "outSR=4326" in q[0]
    assert len(q) == 6                                     # 49 rows twice (2024 and 2025 layers), 20 + 20 + 9 each
    assert got["years_missing"] == [2018] and got["cleaning"]["source_rows"] == 98
    assert {c["preliminary"] for c in got["crashes"]} == {False, True}   # the fixture's rows read as 2024 and 2025
    again = ut_udot.fetch_contract((40.5, -112.1, 40.8, -111.7), ["49035"], [2018, 2024, 2025], tmp_path, opener=None)
    assert again == got                                    # cache, no network


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')   # noqa: E731
    with pytest.raises(RuntimeError):
        ut_udot.layers(err)
