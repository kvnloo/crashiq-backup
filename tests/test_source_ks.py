"""Kansas: KDOT Crashes in Kansas reader (sources/ks_kdot.py), offline on a recorded fixture of 35 live rows
(Wichita 2024 by severity, mode and road type, two Turnpike crashes and two rows with no date), recorded 2026-11-08."""

import io
import json
import re
import urllib.parse
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import ks_kdot

from conftest import FIXTURES

ROWS = [f["attributes"] for f in json.loads((FIXTURES / "ks_kdot_crashes.json").read_text())["features"]]
FIPS = ks_kdot._county_fips()


def _opener(rows, urls=None):
    def opener(req, timeout):
        if urls is not None:
            urls.append(urllib.parse.unquote_plus(req.full_url))
        last = int(re.search(r"OBJECTID>(\d+)", urllib.parse.unquote_plus(req.full_url)).group(1))
        page = [{"attributes": a} for a in rows if a["OBJECTID"] > last][:ks_kdot.PAGE]
        return io.BytesIO(json.dumps({"features": page}).encode())
    return opener


def test_every_county_name_maps_and_rows_pass_the_contract():
    assert len(FIPS) == 105 and FIPS["SEDGWICK"] == "20173" and FIPS["MCPHERSON"] == "20113"
    pack = packs.get("KS")
    recs = [ks_kdot.contract_record(a, FIPS) for a in ROWS]
    dated = [c for c in recs if c["year"]]
    assert len(dated) == len(recs) - 2 and all(packs.check_crash(c, pack) == [] for c in dated)
    assert all(c["primary_road"] is None and c["secondary_road"] is None for c in recs)


def test_severity_is_the_worst_person_and_matches_kdot():
    recs = [ks_kdot.contract_record(a, FIPS) for a in ROWS]
    assert {"K", "A", "B", "C", "O"} <= {c["severity"] for c in recs}
    assert not [c for c in recs if c["severity_mismatch"]]
    k = next(c for c in recs if c["severity"] == "K")
    assert k["killed"] >= 1 and k["severity_reported"] == "FATAL"
    assert ks_kdot.severity({"DISABLING_INJURIES": 1, "POSSIBLE_INJURIES": 3}) == "A"
    assert ks_kdot.severity({"ACC_SEVERITY": "INJURY"}) == "U"        # injured, no level counted
    assert ks_kdot.severity({"ACC_SEVERITY": "PROPERTY DAMAGE ONLY"}) == "O"


def test_words_flags_and_dates():
    recs = [ks_kdot.contract_record(a, FIPS) for a in ROWS]
    types = Counter(c["collision_type"] for c in recs)
    assert types["BROADSIDE"] and types["VEHICLE/PEDESTRIAN"] and "ANGLE - SIDE IMPACT" not in types
    assert any(c["lighting"] == "DARK - STREET LIGHTS" for c in recs)
    assert any(c["ped"] for c in recs) and any(c["bike"] for c in recs)
    assert any(c["is_freeway"] for c in recs if c["city"] == "WICHITA")              # Interstate
    assert all(c["is_freeway"] for c in recs if c["crash_id"] in
               {a["ACCIDENT_KEY"] for a in ROWS if a["TURNPIKE_INVOLVED"] == "Y"})
    one = ks_kdot.contract_record({**ROWS[0], "ACC_YEAR": "2024", "ACC_MONTH_NUMBER": 3, "ACC_DAY_OF_MONTH": 1,
                                   "ACC_HOUR": "07"}, FIPS)
    assert one["date"] == "2024-03-01" and one["hour"] == 7 and one["day_of_week"] == "Friday"
    far = ks_kdot.contract_record({**ROWS[0], "LATITUDE": 34.0, "LONGITUDE": -118.0}, FIPS)
    assert far["lat"] is None and far["bad_coords"]


def test_fetch_contract_sends_the_box_pages_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(ks_kdot, "PAGE", 10)
    urls = []
    got = ks_kdot.fetch_contract((37.6, -97.5, 37.8, -97.2), ["20173"], [2023, 2024], tmp_path, _opener(ROWS, urls))
    assert "LATITUDE >= 37.600000 AND LATITUDE <= 37.800000" in urls[0] and "ACC_YEAR IN ('2023', '2024')" in urls[0]
    assert len(urls) == 4                                          # 35 rows: 10 + 10 + 10 + 5
    assert len(got["crashes"]) == len(ROWS) and got["years_missing"] == [2023]
    again = ks_kdot.fetch_contract((37.6, -97.5, 37.8, -97.2), ["20173"], [2023, 2024], tmp_path, opener=None)
    assert again["crashes"] == got["crashes"]                      # second call reads the cache, no network


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')
    with pytest.raises(RuntimeError):
        ks_kdot.fetch_raw("nope", None, opener=err)
