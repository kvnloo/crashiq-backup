"""MassDOT IMPACT importer (crashiq.sources.ma_impact), offline against a recorded 2025 Middlesex fixture."""
import json
from pathlib import Path

import pytest

from crashiq.sources import ma_impact as m

FIX = json.loads((Path(__file__).parent / "fixtures" / "ma_impact_2025.json").read_text())


@pytest.fixture
def fake_impact(monkeypatch):
    """Answers the importer's ArcGIS calls from the fixture; a row's object id is its index in the fixture list."""
    calls = []

    def fake_get(url, **p):
        calls.append((url, p))
        if url.endswith("FeatureServer"):
            return FIX["service"]
        rows = FIX["crashes"] if url.endswith("/0/query") else FIX["persons"]
        if p.get("returnIdsOnly"):
            w = p["where"]
            want = {int(x) for x in w[w.index("(") + 1:-1].split(",")} if w.startswith("CRASH_NUMB IN") else None
            return {"objectIds": [i for i, r in enumerate(rows) if want is None or r["CRASH_NUMB"] in want]}
        return {"features": [{"attributes": rows[int(i)]} for i in p["objectIds"].split(",")]}

    monkeypatch.setattr(m, "_get", fake_get)
    return calls


def test_fetch_links_persons_and_severity(fake_impact, tmp_path):
    crashes = m.fetch(2025, "CNTY_NAME='MIDDLESEX'", tmp_path)
    assert len(crashes) == 60
    assert sum(len(c["persons"]) for c in crashes) == len(FIX["persons"]) == 149
    assert all(c["severity"] in m.SEVERITY_ORDER for c in crashes)
    by_max = {m.kabco(r["MAX_INJR_SVRTY_CL"]) for r in FIX["crashes"]}
    assert by_max == {"O", "B", "C"}
    # crash-level severity never falls below the crash's own max-injury class
    for c in crashes:
        k = m.kabco(c["max_injury"])
        assert k is None or m.SEVERITY_ORDER.index(c["severity"]) <= m.SEVERITY_ORDER.index(k)
    assert (tmp_path / next(p.name for p in tmp_path.iterdir())).exists()   # cached
    n = len(fake_impact)
    assert m.fetch(2025, "CNTY_NAME='MIDDLESEX'", tmp_path) == crashes and len(fake_impact) == n


def test_record_shape_and_gps(fake_impact, tmp_path):
    crashes = {c["collision_id"]: c for c in m.fetch(2025, "1=1", tmp_path)}
    c = crashes["5582854"]                       # ' FARWELL ST Rte N  / CALVARY ST Rte E', At Intersection
    assert (c["primary_road"], c["secondary_road"]) == ("FARWELL ST", "CALVARY ST")
    assert c["date"] == "2025-10-08" and c["hour"] == 15 and c["year"] == 2025
    assert c["lat"] and 41.2 < c["lat"] < 42.9 and c["city_name"]
    for key in ("collision_id", "datetime", "lat", "lon", "primary_road", "secondary_road", "sec_distance",
                "sec_direction", "city_name", "county_code", "killed", "injured", "collision_type", "lighting",
                "weather", "surface", "is_freeway"):
        assert key in c
    gps = sum(c["lat"] is not None for c in crashes.values())
    assert gps == 58                              # 2 of the 60 recorded crashes have no coordinates


def test_split_rdwy_and_offset():
    assert m.split_rdwy(" Washington St Rte W  / Lesher St Rte S", None) == ("Washington St", "Lesher St")
    assert m.split_rdwy(" Chelsea St Rte 1 E", None) == ("Chelsea St", None)
    assert m.split_rdwy(" GARDEN STREET", " APPIAN WAY") == ("GARDEN STREET", "APPIAN WAY")
    assert m.split_rdwy(" Belgrade Ave", " Rexhame St Rte") == ("Belgrade Ave", "Rexhame St")
    assert m.split_rdwy(None, None) == (None, None)
    assert m.offset("15 feet N  of") == (15.0, "N")
    assert m.offset("0 feet    of") == (0.0, None)
    assert m.offset(None) == (None, None)
    assert m.house_number("548", " Columbus Ave Rte W") == 548
    assert m.house_number("495", " 495 SB Rte") is None and m.house_number("US1", " US1 N Rte") is None


def test_kabco_both_wordings():
    assert [m.kabco(v) for v in ("Fatal injury (K)", "Suspected Serious Injury (A)", "Suspected Minor Injury (B)",
                                 "Possible Injury (C)", "No Apparent Injury (O)")] == list("KABCO")
    assert [m.kabco(v) for v in ("Non-fatal injury - Incapacitating", "Non-fatal injury - Non-incapacitating",
                                 "Non-fatal injury - Possible", "No injury")] == list("ABCO")
    for v in ("Deceased not caused by crash", "Not reported", "Unknown", "Not Applicable", "Reported but invalid", None):
        assert m.kabco(v) is None


def test_severity_rules():
    base = {"killed": 0, "injured": 0, "max_injury": None}
    assert m.severity(base, []) == "O"
    assert m.severity({**base, "injured": 1}, [{"kabco": None}]) == "U"
    assert m.severity({**base, "injured": 1}, [{"kabco": "C"}, {"kabco": "A"}]) == "A"
    assert m.severity({**base, "killed": 1}, [{"kabco": "B"}]) == "K"
    assert m.severity({**base, "max_injury": "Suspected Minor Injury (B)"}, []) == "B"


def test_layers_resolved_by_name(monkeypatch):
    monkeypatch.setattr(m, "_get", lambda url, **p: {"layers": [
        {"id": 0, "name": "2019 Crashes"}, {"id": 1, "name": "2019 Person Level Crash Details"},
        {"id": 2, "name": "2019 Vehicle Level Crash Details"}]})
    assert m.layers(2019) == {"crash": 0, "person": 1, "vehicle": 2}
    assert m.service(2019).endswith("CrashClosedYear2019/FeatureServer")
    assert m.service(2023).endswith("MASSDOT_ODP_OPEN_2023v/FeatureServer")
    assert m.service(2020).endswith("Roads/CrashClosedYears/FeatureServer")


def test_contract_rows_pass_the_pack_checker(fake_impact, tmp_path):
    # #19: what the MA pack hands the core: box OR (no GPS in the corridor's counties), CCRS words, county FIPS
    from crashiq import packs
    pack = packs.get("MA")
    boxes = json.loads((packs.REF / "county_boxes_ma.json").read_text())["counties"]
    got = m.fetch_contract((42.3, -71.4, 42.5, -71.0), ["25017"], [2025], tmp_path, boxes)
    where = next(p["where"] for u, p in fake_impact if p.get("returnIdsOnly") and "LAT" in p.get("where", ""))
    assert "LAT >= 42.300000" in where and "CNTY_NAME IN ('MIDDLESEX')" in where
    assert len(got["crashes"]) == 60 and got["years_missing"] == []
    assert all(packs.check_crash(c, pack) == [] for c in got["crashes"])
    assert {c["county_fips"] for c in got["crashes"]} == {"25017"}
    assert "REAR END" in {c["collision_type"] for c in got["crashes"]}
    assert "DARK - NO STREET LIGHTS" in {c["lighting"] for c in got["crashes"]}
    assert got["cleaning"]["notes"] == []                      # no Boston crash in the fixture


def test_a_boston_crash_brings_the_under_count_note():
    c = m.crash_record({**FIX["crashes"][0], "CITY_TOWN_NAME": "BOSTON", "CNTY_NAME": "SUFFOLK"})
    c["severity"] = "O"
    r = m.contract_record(c, {"SUFFOLK": "25025"})
    assert r["city"] == "BOSTON" and r["county_fips"] == "25025"
    assert "under-counted" in m.BOSTON_NOTE
