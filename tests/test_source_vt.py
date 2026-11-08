"""Vermont: VTrans CrashPQT reader (sources/vt_vtrans.py), offline on a recorded fixture of 40 live rows (Burlington
and South Burlington 2024 by severity, mode, collision and light, I-89, rows with no point, no severity or no town),
recorded 2026-11-08. No live 2024 row has a severity but no town, so the no-town test row is made in the test."""

import io
import json
import re
import urllib.parse
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import vt_vtrans

from conftest import FIXTURES

ROWS = [f["attributes"] for f in json.loads((FIXTURES / "vt_vtrans_crashpqt.json").read_text())["features"]]
GOOD = [a for a in ROWS if a["InjuryType"] in vt_vtrans.SEVERITY]
PACK = packs.get("VT")


def test_plugin_loads_and_rows_meet_the_contract_with_k_u_o_only():
    assert PACK.status == "active" and PACK.severity_note and "vt" not in packs.PLUGIN_ERRORS
    recs = [vt_vtrans.contract_record(a) for a in GOOD]
    assert all(packs.check_crash(c, PACK) == [] for c in recs if c["county_fips"])
    assert {c["severity"] for c in recs} == {"K", "U", "O"}
    assert sum(c["lat"] is None for c in recs) == 4 and all(c["primary_road"] for c in recs)


def test_town_id_gives_the_county_fips():
    assert vt_vtrans.county_fips("0403") == vt_vtrans.county_fips("403") == "50007"     # Burlington, Chittenden
    assert vt_vtrans.county_fips("1128") == "50021" and vt_vtrans.county_fips("1415") == "50027"
    assert vt_vtrans.county_fips(None) is None and vt_vtrans.county_fips("2001") is None
    boxes = json.loads((packs.REF / "county_boxes_vt.json").read_text())["counties"]
    for c in map(vt_vtrans.contract_record, GOOD):          # every placed crash sits in its county's box
        if c["lat"] is not None and c["county_fips"]:
            s, w, n, e = boxes[c["county_fips"]]["box"]
            assert s <= c["lat"] <= n and w <= c["lon"] <= e, c["crash_id"]


def test_wall_clock_time_and_ccrs_words():
    a = GOOD[0]
    c = vt_vtrans.contract_record({**a, "ACCIDENTDATE": 1447241340000})    # "2015-11-11 11:29" as VTrans stores it
    assert (c["date"], c["hour"], c["day_of_week"]) == ("2015-11-11", 11, "Wednesday")
    assert vt_vtrans.collision_type("Left Turn and Thru, Angle Broadside -->v--") == "BROADSIDE"
    assert vt_vtrans.collision_type("Left Turns, Opposite Directions, Head On/Angle Crash --^v--").startswith("LEFT")
    assert vt_vtrans.collision_type("Opp Direction Sideswipe") == "SIDE SWIPE"
    assert vt_vtrans.collision_type("Single Vehicle Crash") == "SINGLE VEHICLE CRASH"
    recs = [vt_vtrans.contract_record(a) for a in GOOD]
    assert any(c["lighting"] == "DARK - UNKNOWN STREET LIGHTS" for c in recs)
    assert any(c["is_freeway"] for c in recs) and any(not c["is_freeway"] for c in recs)
    flags = Counter(k for c in recs for k in ("ped", "bike", "motorcycle", "heavy_truck") if c[k])
    assert set(flags) == {"ped", "bike", "motorcycle", "heavy_truck"}


def test_fetch_contract_reads_box_and_county_no_gps_and_skips_non_reportable(tmp_path, monkeypatch):
    monkeypatch.setattr(vt_vtrans, "PAGE", 10)
    no_town = next(a for a in ROWS if not a["CITYORTOWNid"])
    rows = ROWS + [{**no_town, "OBJECTID": 9_000_000, "InjuryType": "Injury"}]     # severity but no town: not read
    urls = []

    def opener(req, timeout):
        urls.append(urllib.parse.unquote_plus(req.full_url))
        last = int(re.search(r"OBJECTID>(\d+)", urls[-1]).group(1))
        nogps = "LATITUDE IS NULL" in urls[-1]
        page = [a for a in rows if a["OBJECTID"] > last and (nogps == (not a["LATITUDE"]))][:10]
        return io.BytesIO(json.dumps({"features": [{"attributes": a} for a in page]}).encode())

    got = vt_vtrans.fetch_contract((44.4, -73.3, 44.6, -73.1), ["50007"], [2023, 2024], tmp_path, opener=opener)
    assert "LATITUDE >= 44.400000" in urls[0] and "TIMESTAMP '2023-01-01 00:00:00'" in urls[0]
    assert "TIMESTAMP '2025-01-01 00:00:00'" in urls[0]
    log = got["cleaning"]
    assert log["no_severity_not_read"] == 2 and log["no_county_not_read"] == 1
    assert all(packs.check_crash(c, PACK) == [] for c in got["crashes"])
    assert any(c["lat"] is None for c in got["crashes"])                  # a no-GPS Chittenden crash is handed over
    assert got["years_missing"] == [2023]
    again = vt_vtrans.fetch_contract((44.4, -73.3, 44.6, -73.1), ["50007"], [2023, 2024], tmp_path, opener=None)
    assert again == got                                                   # cached, no network


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')
    with pytest.raises(RuntimeError):
        vt_vtrans.fetch_raw("nope", None, opener=err)


def test_methods_cite_vermont_only_and_price_nothing():
    m = packs.methods(PACK)
    assert packs.value(PACK, "crash_costs") is None and packs.value(PACK, "screening")["manual"] == "hsm"
    assert {v["jurisdiction"] for v in m["manuals"].values()} <= {"VT", "US"}
