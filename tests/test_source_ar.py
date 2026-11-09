"""Arkansas: ARDOT ACAT reader (sources/ar_ardot.py) and its plug-in pack, offline on a recorded fixture of 51 live rows
(Pulaski County 2025 by severity, crash manner and non-motorist type, plus statewide rows with no GPS and rows ARDOT
files under Texas's Bowie County), recorded 2026-11-08."""

import io
import json
import re
import urllib.parse
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import ar_ardot

from conftest import FIXTURES

ROWS = [f["attributes"] for f in json.loads((FIXTURES / "ar_ardot_acat.json").read_text())["features"]]
PACK = packs.get("AR")


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "ar" not in packs.PLUGIN_ERRORS and PACK.name == "Arkansas" and PACK.status == "active"
    assert packs.value(PACK, "crash_costs")["K"] == 6343000
    assert packs.value(PACK, "statewide_rates") is None


def test_rows_with_gps_pass_the_contract():
    recs = [ar_ardot.contract_record(a) for a in ROWS]
    gps = [c for c in recs if c["lat"] is not None]
    assert len(gps) >= 45 and all(packs.check_crash(c, PACK) == [] for c in gps)
    assert {"K", "A", "B", "C", "O"} <= {c["severity"] for c in recs}


def test_severity_letter_and_people_floors():
    assert ar_ardot.severity({"CrashSeverity": "Suspected Serious Injury (A)"}) == "A"
    assert ar_ardot.severity({"CrashSeverity": "Unknown"}) is None
    for a in ROWS:
        c = ar_ardot.contract_record(a)
        assert c["severity"] == a["CrashSeverity"][-2]
        assert c["killed"] >= (c["severity"] == "K") and c["injured"] >= (c["severity"] in "ABC")
        assert c["killed"] >= a["NumFatalities"] and c["injured"] >= a["NumSerInj"]


def test_county_from_road_id_including_st_francis_and_border_rows():
    assert ar_ardot.ARDOT_NO[60] == "Pulaski" and ar_ardot.ARDOT_NO[68] == "St. Francis"
    assert ar_ardot.county_fips({"AH_RoadID": "68x306x3xA"}) == "05123"      # St. Francis, FIPS order differs
    assert ar_ardot.county_fips({"AH_RoadID": "62x30x399xA"}) == "05125"     # Saline
    assert ar_ardot.county_fips({"AH_RoadID": None, "County": "Yell"}) == "05149"
    assert ar_ardot.county_fips({"AH_RoadID": None, "County": "Bowie County"}) is None
    bowie = [ar_ardot.contract_record(a) for a in ROWS if a["County"] == "Bowie County"]
    assert bowie and all(c["county_fips"] == "05091" for c in bowie)            # road id 46 = Miller County, AR
    pul = [ar_ardot.contract_record(a) for a in ROWS if a["County"] == "Pulaski"]
    assert pul and Counter(c["county_fips"] for c in pul).most_common(1)[0][0] == "05119"


def test_local_date_and_both_time_formats():
    for a in ROWS:
        c = ar_ardot.contract_record(a)
        m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?(?: ([AP]M))?", a["CrashTime"])
        h = int(m.group(1)) % 12 + (12 if m.group(3) == "PM" else 0) if m.group(3) else int(m.group(1))
        assert c["hour"] == h and c["year"] == int(a["Year"]) and c["day_of_week"] == a["DayOfWeek"]
    # 2025-01-01 00:30 Central arrives as 06:30 UTC; the date must not slip a day
    c = ar_ardot.contract_record({**ROWS[0], "CrashDate": 1735713000000})
    assert c["date"] == "2025-01-01" and c["hour"] == 0


def test_words_flags_and_no_street_names():
    recs = [ar_ardot.contract_record(a) for a in ROWS]
    types = Counter(c["collision_type"] for c in recs)
    assert "REAR END" in types and "BROADSIDE" in types and "Angle" not in types
    assert any((c["lighting"] or "") == "DARK - STREET LIGHTS" for c in recs)
    assert any(c["ped"] for c in recs) and any(c["bike"] for c in recs)
    assert any(c["is_freeway"] for c in recs) and any(not c["is_freeway"] for c in recs)
    assert all(c["primary_road"] is None and c["secondary_road"] is None for c in recs)
    nogps = [c for c in recs if c["lat"] is None]
    assert len(nogps) == 3 and not any(c["bad_coords"] for c in nogps)
    far = ar_ardot.contract_record({**ROWS[0], "Latitude": 34.0, "Longitude": -118.0})
    assert far["lat"] is None and far["bad_coords"]


def test_fetch_contract_sends_the_box_query_pages_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(ar_ardot, "PAGE", 20)
    urls = []

    def opener(req, timeout):
        q = urllib.parse.unquote_plus(req.full_url)
        urls.append(q)
        last = int(re.search(r"OBJECTID>(\d+)", q).group(1))
        page = sorted((a for a in ROWS if a["OBJECTID"] > last), key=lambda a: a["OBJECTID"])[:20]
        return io.BytesIO(json.dumps({"features": [{"attributes": a} for a in page]}).encode())

    got = ar_ardot.fetch_contract((34.6, -92.5, 34.9, -92.2), ["05119"], [2024, 2025], tmp_path, opener=opener)
    assert "Latitude >= 34.600000 AND Latitude <= 34.900000" in urls[0] and "Year IN ('2024', '2025')" in urls[0]
    assert len(urls) == 3                                         # 51 rows: 20 + 20 + 11
    assert got["cleaning"]["source_rows"] == len(ROWS)
    assert got["years_missing"] == [y for y in (2024, 2025) if str(y) not in {a["Year"] for a in ROWS}]
    assert all(packs.check_crash(c, PACK) == [] for c in got["crashes"] if c["lat"] is not None)
    again = ar_ardot.fetch_contract((34.6, -92.5, 34.9, -92.2), ["05119"], [2024, 2025], tmp_path, opener=None)
    assert again == got                                           # second call reads the cache, no network


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')   # noqa: E731
    with pytest.raises(RuntimeError):
        ar_ardot.fetch_raw("nope", None, opener=err)
