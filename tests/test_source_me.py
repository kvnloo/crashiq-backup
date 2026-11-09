"""Maine: MaineDOT crash layer reader (sources/me_mainedot.py), offline on a recorded fixture of 38 live rows
(Portland 2024 by severity, mode, Interstate and light, plus the statewide rows with no point), recorded 2026-11-08."""

import io
import json
import re
import urllib.parse
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import me_mainedot

from conftest import FIXTURES

ROWS = [f["attributes"] for f in json.loads((FIXTURES / "me_mainedot_crashes.json").read_text())["features"]]
PACK = packs.get("ME")


def test_plugin_loads_and_every_row_with_a_point_meets_the_contract():
    assert PACK.status == "active" and "me" not in packs.PLUGIN_ERRORS
    recs = [me_mainedot.contract_record(a) for a in ROWS]
    placed = [c for c in recs if c["lat"] is not None]
    assert len(placed) == len(recs) - 4                    # the 4 statewide rows with no point
    assert all(packs.check_crash(c, PACK) == [] for c in recs if c["county_fips"])
    assert all(c["primary_road"] is None and c["route"] for c in placed)       # route codes, never street names


def test_severity_is_mainedots_kabco_and_matches_the_people_counts():
    recs = [me_mainedot.contract_record(a) for a in ROWS]
    assert {"K", "A", "B", "C", "O"} <= {c["severity"] for c in recs}
    for a, c in zip(ROWS, recs):
        worst = next((k for k in "KABC" if a[f"NO_OF_{k}_INJ"]), "O")
        assert c["severity"] == worst, a["CRASH_ID"]
        assert len(c["person_kabco"]) == c["injured"] + c["killed"]
    assert me_mainedot.contract_record({**ROWS[0], "INJURY_LEVEL": None, "NO_OF_B_INJ": 1})["severity"] in "KAB"


def test_dates_are_local_and_codes_map_only_where_they_mean_the_same():
    a = next(a for a in ROWS if a["ACCIDENT_YEAR"] == 2024)
    # 2024-12-31 local midnight arrives as 05:00 UTC; the date must not slip a day
    c = me_mainedot.contract_record({**a, "ACCIDENT_DATE": 1735621200000, "ACCIDENT_HOUR": 15})
    assert (c["date"], c["hour"], c["day_of_week"]) == ("2024-12-31", 15, "Tuesday")
    assert c["county_fips"] == "23005" and c["city"] == "PORTLAND"
    recs = [me_mainedot.contract_record(a) for a in ROWS]
    types = Counter(c["collision_type"] for c in recs)
    assert "OVERTURNED" in types and "REAR END / SIDESWIPE" in types and "REAR END" not in types
    assert any(c["lighting"] == "DARK - STREET LIGHTS" for c in recs)
    assert any(c["is_freeway"] for c in recs) and any(not c["is_freeway"] for c in recs)
    assert any(c["ped"] for c in recs) and any(c["bike"] for c in recs)


def test_points_outside_maine_are_dropped_and_flagged():
    far = me_mainedot.contract_record({**ROWS[0], "LATITUDE": 34.0, "LONGITUDE": -118.0})
    assert far["lat"] is None and far["bad_coords"]
    zero = me_mainedot.contract_record({**ROWS[0], "LATITUDE": 0.0, "LONGITUDE": 0.0})
    assert zero["lat"] is None and not zero["bad_coords"]


def test_fetch_pages_by_objectid_caches_and_sends_the_box(tmp_path, monkeypatch):
    monkeypatch.setattr(me_mainedot, "PAGE", 10)
    urls = []

    def opener(req, timeout):
        urls.append(urllib.parse.unquote_plus(req.full_url))
        last = int(re.search(r"OBJECTID>(\d+)", urls[-1]).group(1))
        return io.BytesIO(json.dumps({"features": [{"attributes": a} for a in ROWS if a["OBJECTID"] > last][:10]})
                          .encode())

    got = me_mainedot.fetch_contract((43.6, -70.3, 43.7, -70.2), ["23005"], [2023, 2024], tmp_path, opener=opener)
    assert len(urls) == 4                                       # 38 rows: 10 + 10 + 10 + 8
    assert "LATITUDE >= 43.600000 AND LATITUDE <= 43.700000" in urls[0] and "ACCIDENT_YEAR IN (2023, 2024)" in urls[0]
    assert got["cleaning"]["source_rows"] == len(ROWS) and len(got["crashes"]) == len(ROWS)
    assert 2023 in got["years_missing"] and 2024 not in got["years_missing"]
    again = me_mainedot.fetch_contract((43.6, -70.3, 43.7, -70.2), ["23005"], [2023, 2024], tmp_path, opener=None)
    assert again == got                                         # second call reads the cache, no network


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')
    with pytest.raises(RuntimeError):
        me_mainedot.fetch("nope", None, opener=err)


def test_methods_cite_maine_only():
    m = packs.methods(PACK)
    assert packs.value(PACK, "min_years")["value"] == 3 and packs.value(PACK, "crash_costs") is None
    assert {v["jurisdiction"] for v in m["manuals"].values()} <= {"ME", "US"}
