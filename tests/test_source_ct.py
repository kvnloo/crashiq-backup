"""Connecticut: CTCDR public MapServer reader (sources/ct_uconn.py), offline on a recorded fixture of 44 live Hartford
2024 crashes with their 107 person and 86 vehicle rows (by severity, mode, route class, intersecting road, dark,
one with no MostSevereInjury), recorded 2026-11-08 with outSR=4326."""

import io
import json
import re
import urllib.parse
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import ct_uconn

from conftest import FIXTURES

RAW = json.loads((FIXTURES / "ct_uconn_hartford_2024.json").read_text())
PACK = packs.get("CT")


def _opener(urls=None, page=None):
    """Serves the fixture by layer number and OBJECTID paging, like the MapServer."""
    by_layer = {0: RAW["crash"], 1: RAW["person"], 2: RAW["vehicle"]}

    def opener(req, timeout):
        q = urllib.parse.unquote_plus(req.full_url)
        if urls is not None:
            urls.append(q)
        layer = int(re.search(r"/MapServer/(\d)/query", q).group(1))
        last = int(re.search(r"OBJECTID>(\d+)", q).group(1))
        rows = sorted(by_layer[layer], key=lambda f: f["attributes"]["OBJECTID"])
        out = [f for f in rows if f["attributes"]["OBJECTID"] > last][:page or ct_uconn.PAGE]
        return io.BytesIO(json.dumps({"features": out}).encode())
    return opener


def test_plugin_registers_an_active_connecticut_pack():
    assert "ct" not in packs.PLUGIN_ERRORS and PACK.name == "Connecticut" and PACK.status == "active"
    assert packs.methods(PACK)["state"] == "CT" and packs.check_methods(packs.methods(PACK), "CT") == []
    assert packs.value(PACK, "crash_costs")["K"] == 6415389 and packs.value(PACK, "statewide_rates") is None


def test_every_crash_passes_the_contract_with_its_people():
    recs = ct_uconn.records(RAW)
    assert len(recs) == len(RAW["crash"]) == 44
    assert all(packs.check_crash(c, PACK) == [] for c in recs)
    assert all(c["county_fips"] == "09110" and c["city"] == "HARTFORD" and c["year"] == 2024 for c in recs)
    assert all(c["lat"] is not None for c in recs)                       # every CTCDR crash has its point


def test_severity_is_kabco_from_most_severe_injury_else_people_else_crash_severity():
    recs = {c["crash_id"]: c for c in ct_uconn.records(RAW)}
    assert set(Counter(c["severity"] for c in recs.values())) == set("KABCO")
    k = next(c for c in recs.values() if c["severity"] == "K")
    assert k["killed"] >= 1
    nomsi = next(f["attributes"] for f in RAW["crash"] if f["attributes"]["MostSevereInjury"] is None)
    assert recs[str(nomsi["CrashID"])]["severity"] == "O"                # PDO, its people say O
    assert ct_uconn.severity({"CrashSeverity": "Injury of any type (Serious, Minor, Possible)"}, []) == "U"
    assert ct_uconn.severity({"CrashSeverity": "Fatal (Kill)"}, []) == "K"
    assert ct_uconn.severity({}, [{"InjuryStatus": "Possible Injury (C)"}, {"InjuryStatus": "Suspected Serious Injury (A)"}]) == "A"


def test_route_names_read_as_osm_refs_and_town_suffix_drops():
    assert ct_uconn.road("84-W", "Interstate") == "I 84"
    assert ct_uconn.road("44-E", "USRoute") == "US 44"
    assert ct_uconn.road("187-N", "State") == "CT 187"
    assert ct_uconn.road("MAIN ST NO 1", "Local") == "MAIN ST"
    assert ct_uconn.road("44-E", None) == "US 44" and ct_uconn.road("91-N", None) == "I 91"
    assert ct_uconn.road("530-E", None) == "CT 530" and ct_uconn.road("  ", "State") is None
    assert ct_uconn.road("91-S-165A (EXIT 33)", "Interstate") == "91-S-165A (EXIT 33)"     # a ramp: kept
    recs = ct_uconn.records(RAW)
    assert any(c["is_freeway"] and c["primary_road"].startswith("I ") for c in recs)
    assert any(c["secondary_road"] for c in recs) and any(not c["is_freeway"] for c in recs)


def test_ccrs_words_modes_and_local_time():
    recs = ct_uconn.records(RAW)
    types = {c["collision_type"] for c in recs}
    assert {"REAR END", "BROADSIDE", "SIDE SWIPE"} <= types and "Front to rear" not in types
    assert any((c["lighting"] or "").startswith("DARK - ") for c in recs)
    assert any(c["ped"] for c in recs) and any(c["bike"] for c in recs)
    assert any(c["motorcycle"] for c in recs) and any(c["heavy_truck"] for c in recs)
    # 2024-03-01 00:30 EST arrives as 05:30 UTC: the local date must not slip
    a = {**RAW["crash"][0]["attributes"], "CrashDate": 1709271000000}
    c = ct_uconn.contract_record(a, RAW["crash"][0]["geometry"], [], [])
    assert c["date"] == "2024-03-01" and c["hour"] == 0 and c["day_of_week"] == "Friday"


def test_point_outside_connecticut_is_refused_and_flagged():
    a = RAW["crash"][0]["attributes"]
    c = ct_uconn.contract_record(a, {"x": -118.2, "y": 34.0}, [], [])
    assert c["lat"] is None and c["bad_coords"]
    c = ct_uconn.contract_record(a, None, [], [])
    assert c["lat"] is None and not c["bad_coords"]


def test_fetch_pages_all_three_layers_by_objectid_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(ct_uconn, "PAGE", 20)
    urls = []
    raw = ct_uconn.fetch("CrashDateYear IN (2024)", None, tmp_path, opener=_opener(urls, 20))
    assert [len(raw[k]) for k in ("crash", "person", "vehicle")] == [44, 107, 86]
    assert len(urls) == 3 + 6 + 5                                        # 44 / 107 / 86 rows in pages of 20
    assert "outSR=4326" in urls[0] and ") AND OBJECTID>0&" in urls[0]
    assert ct_uconn.fetch("CrashDateYear IN (2024)", None, tmp_path, opener=None) == raw   # cache, no network


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')   # noqa: E731
    with pytest.raises(RuntimeError):
        ct_uconn.fetch("nope", None, None, opener=err)


def test_fetch_contract_sends_the_box_and_years_and_reports_missing_years(tmp_path):
    urls = []
    got = ct_uconn.fetch_contract((41.7, -72.75, 41.8, -72.6), ["09110"], [2023, 2024], tmp_path, opener=_opener(urls))
    assert "CrashDateYear IN (2023, 2024)" in urls[0] and "geometry=-72.750000,41.700000,-72.600000,41.800000" in urls[0]
    assert all("esriGeometryEnvelope" in u for u in urls)                # people and vehicles asked by the same box
    assert len(got["crashes"]) == 44 and got["years_missing"] == [2023]
    assert got["cleaning"]["persons_read"] == 107 and got["cleaning"]["no_person_rows"] == 1   # one live crash has none
