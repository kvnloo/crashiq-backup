"""Montana: MDT Public Crash Information reader (sources/mt_mdt.py), offline on a recorded fixture of 46 live rows
(Yellowstone County 2025 by severity, collision type, light, interstate, ramp and rural, plus the 2 statewide rows
with no date), recorded 2026-11-08 with outSR=4326."""

import io
import json
import re
import urllib.parse
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import mt_mdt

from conftest import FIXTURES

FEATS = json.loads((FIXTURES / "mt_mdt_public_crash.json").read_text())["features"]
PACK = packs.get("MT")


def _opener(pages, urls=None):
    def opener(req, timeout):
        q = urllib.parse.unquote_plus(req.full_url)
        if urls is not None:
            urls.append(q)
        last = int(re.search(r"OBJECTID>(\d+)", q).group(1))
        page = [f for f in sorted(FEATS, key=lambda f: f["attributes"]["OBJECTID"]) if f["attributes"]["OBJECTID"] > last][:pages]
        return io.BytesIO(json.dumps({"features": page}).encode())
    return opener


def test_plugin_registers_an_active_montana_pack():
    assert "mt" not in packs.PLUGIN_ERRORS and PACK.name == "Montana" and PACK.status == "active"
    assert packs.methods(PACK)["state"] == "MT"
    assert packs.value(PACK, "crash_costs") is None               # research figure, verified: false: never printed


def test_dated_rows_pass_the_contract_and_junk_rows_are_dropped():
    recs = [mt_mdt.contract_record(f) for f in FEATS]
    dated = [c for c in recs if c["year"]]
    assert len(dated) == len(FEATS) - 2
    assert all(packs.check_crash(c, PACK) == [] for c in dated)
    junk = [c for c in recs if not c["year"]]
    assert all(c["lat"] is None and c["county_fips"] is None for c in junk)   # its point is in the Arctic: refused
    assert any(c["bad_coords"] for c in junk)


def test_severity_is_mdt_kabco_and_unknown_is_u():
    sev = Counter(mt_mdt.contract_record(f)["severity"] for f in FEATS if f["attributes"]["CRASH_DATE"])
    assert set(sev) == set("KABCOU")
    unk = next(f for f in FEATS if f["attributes"]["CRASH_SEVERITY"] == "Unknown")
    assert mt_mdt.contract_record(unk)["severity"] == "U"


def test_freeway_from_interstate_mainline_and_ramps_and_ccrs_words():
    recs = [mt_mdt.contract_record(f) for f in FEATS if f["attributes"]["CRASH_DATE"]]
    fwy = [c for c in recs if c["is_freeway"]]
    assert {c["route"][:7] for c in fwy} & {"C000090", "C000094"}             # I-90 / I-94 mainline in Billings
    assert any(c["route"] in mt_mdt.FREEWAY_ROUTES and not c["route"].startswith("C0000") for c in fwy)  # a ramp
    assert any(not c["is_freeway"] for c in recs)
    types = {c["collision_type"] for c in recs}
    assert {"REAR END", "BROADSIDE", "HIT OBJECT"} <= types and "Rear-End" not in types
    assert any(c["ped"] and c["collision_type"] == "VEHICLE/PEDESTRIAN" for c in recs)
    assert any(c["lighting"] == "DARK - NO STREET LIGHTS" for c in recs)
    assert all(c["county_fips"] == "30111" for c in recs)                     # Yellowstone County


def test_fetch_pages_by_objectid_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(mt_mdt, "PAGE", 20)
    urls = []
    got = mt_mdt.fetch({"where": "1=1"}, tmp_path, opener=_opener(20, urls))
    assert len(got) == len(FEATS) and len(urls) == 3                          # 46 rows: 20 + 20 + 6
    assert "outSR=4326" in urls[0] and ") AND OBJECTID>0&" in urls[0]
    assert mt_mdt.fetch({"where": "1=1"}, tmp_path, opener=None) == got       # second call reads the cache


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')
    with pytest.raises(RuntimeError):
        mt_mdt.fetch({"where": "nope"}, None, opener=err)


def test_fetch_contract_sends_the_box_and_years_and_says_which_years_the_layer_lacks(tmp_path, monkeypatch):
    monkeypatch.setattr(mt_mdt, "PAGE", 2000)
    urls = []
    got = mt_mdt.fetch_contract((45.77, -108.61, 45.79, -108.58), ["30111"], [2024, 2025, 2026], tmp_path,
                                opener=_opener(2000, urls))
    assert "geometry=-108.610000,45.770000,-108.580000,45.790000" in urls[0] and "inSR=4326" in urls[0]
    assert "CRASH_DATE >= DATE '2024-01-01' AND CRASH_DATE < DATE '2026-01-01'" in urls[0]
    assert got["years_missing"] == [2026]
    assert len(got["crashes"]) == len(FEATS) - 2 and got["cleaning"]["no_county_or_date"] == 2
    assert mt_mdt.fetch_contract((0, 0, 1, 1), [], [2030], tmp_path)["years_missing"] == [2030]
