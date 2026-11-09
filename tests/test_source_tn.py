"""Tennessee: TDOT (2021-2024) and TDOSHS (2025 on) crash layer readers, the Metro Nashville no-injury fill
(sources/tn_tdot.py) and the plug-in pack, offline on a recorded fixture (Davidson County: TDOT 2024 rows per severity
x light, manner and route kind; TDOSHS 2025 rows per severity x light and per flag; 7 Metro rows), recorded 2026-11-08
by research_notes/tn-2026-11-08/tn_pull.py."""

import json

from crashiq import packs
from crashiq.sources import tn_tdot as tn

from conftest import FIXTURES

FX = json.loads((FIXTURES / "tn_crashes.json").read_text())
PACK = packs.get("TN")


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "tn" not in packs.PLUGIN_ERRORS and PACK.name == "Tennessee" and PACK.status == "active"
    assert PACK.severity_note is None and packs.value(PACK, "crash_costs") is None
    assert packs.check_methods(packs.methods(PACK), "TN") == []
    assert len(tn.FIPS) == 95 and tn.FIPS["DAVIDSON"] == "47037" and tn.FIPS["SHELBY"] == "47157"


def test_tdot_rows_pass_the_contract_with_kabco_routes_and_manner():
    cs = [tn.tdot_record(a) for a in FX["tdot"]]
    assert all(packs.check_crash(c, PACK) == [] for c in cs)
    assert {c["severity"] for c in cs} == set("KABCO") and all(c["year"] == 2024 for c in cs)
    assert all(c["lat"] is not None for c in cs)
    assert {"I 24", "SR 11"} & {c["primary_road"] for c in cs} and any(c["primary_road"] is None for c in cs)
    assert all(c["is_freeway"] == (c["primary_road"] or "").startswith("I ") for c in cs)
    assert {"REAR END", "BROADSIDE", "SIDE SWIPE"} <= {c["collision_type"] for c in cs}
    assert any(c["ped"] for c in cs) and any(c["bike"] for c in cs)
    one = tn.tdot_record({**FX["tdot"][0], "TIMEOFCRAS": 1451, "DATEOFCRAS": 1661472000000})
    assert (one["date"], one["hour"]) == ("2022-08-26", 14)
    assert tn._s("--") is None


def test_state_rows_pass_the_contract_with_kabc_from_crash_type():
    cs = [tn.contract_record(a) for a in FX["state"]]
    assert all(packs.check_crash(c, PACK) == [] for c in cs)
    assert {c["severity"] for c in cs} == set("KABC")
    for a, c in zip(FX["state"], cs):
        assert c["severity"] == tn.SEVERITY[a["Crash_Type"]] and c["killed"] == a["Fatality"]
        assert c["date"] == f"{a['Collision_Year']}-{a['Collision_Month']:02d}-{a['Collision_Day']:02d}"
        assert c["lat"] == a["Latitude"] and c["primary_road"] is None and not c["is_freeway"]
    assert all(any(c[k] for c in cs) for k in ("ped", "bike", "motorcycle", "heavy_truck"))
    assert {"DAYLIGHT", "DARK - STREET LIGHTS", "DARK - NO STREET LIGHTS"} <= {c["lighting"] for c in cs}


def test_nashville_rows_are_property_damage_with_a_street_and_central_time():
    cs = [tn.nashville_record(a) for a in FX["nashville"]]
    assert all(packs.check_crash(c, PACK) == [] for c in cs)
    assert {c["severity"] for c in cs} == {"O"} and all(c["county_fips"] == "47037" for c in cs)
    assert all(c["primary_road"] for c in cs[:-1]) and cs[-1]["primary_road"] is None
    assert tn._HOUSE.sub("", "1200 WEST END AVE") == "WEST END AVE"
    two = tn.nashville_record({**FX["nashville"][0], "Street_Address": "NOLENSVILLE PKE & THOMPSON LN"})
    assert (two["primary_road"], two["secondary_road"]) == ("NOLENSVILLE PIKE", "THOMPSON LN")
    one = tn.nashville_record({**FX["nashville"][0], "Date_and_Time": 1751371200000})   # 2025-07-01 12:00 UTC
    assert (one["date"], one["hour"]) == ("2025-07-01", 7)                             # 07:00 CDT
    far = tn.nashville_record({**FX["nashville"][0], "Lat": 34.0, "Long": -118.0})
    assert far["lat"] is None and far["bad_coords"]


class FakeLayers:
    """The three ArcGIS layers' id and row calls, answered from the fixture."""
    LAYERS = {tn.LAYER_TDOT: ("tdot", "OBJECTID"), tn.LAYER: ("state", "OBJECTID"), tn.NASHVILLE: ("nashville", "ObjectId")}

    def __init__(self):
        self.calls = []

    def __call__(self, url, params):
        self.calls.append((url, params))
        name, key = self.LAYERS[url.removesuffix("/query")]
        rows = FX[name]
        if params.get("returnIdsOnly"):
            return {"objectIds": [r[key] for r in rows]}
        want = set(map(int, params["objectIds"].split(",")))
        if name == "tdot":
            return {"features": [{"attributes": {k: v for k, v in r.items() if k[0] != "_"},
                                  "geometry": {"x": r["_lon"], "y": r["_lat"]}} for r in rows if r[key] in want]}
        return {"features": [{"attributes": r} for r in rows if r[key] in want]}


def test_fetch_contract_reads_tdot_to_2024_then_tdoshs_and_metro_and_caches(tmp_path):
    fake = FakeLayers()
    got = tn.fetch_contract(FX["box"], ["47037"], [2020, 2024, 2025], tmp_path, get=fake)
    assert got["years_missing"] == [2020] and got["cleaning"]["nashville_no_injury_rows"] == len(FX["nashville"])
    assert len(got["crashes"]) == len(FX["tdot"]) + len(FX["state"]) + len(FX["nashville"])
    assert {c["source"] for c in got["crashes"] if c["year"] == 2024} == {"TDOT"}
    assert {c["source"] for c in got["crashes"] if c["year"] == 2025} == {"TDOSHS", "Metro Nashville"}
    tdot_q = next(p for u, p in fake.calls if u.startswith(tn.LAYER_TDOT) and "where" in p)
    assert tdot_q["where"] == "YEAROFCRAS IN ('2024')" and tdot_q["inSR"] == "4326"
    assert any(p.get("returnGeometry") == "true" for u, p in fake.calls if u.startswith(tn.LAYER_TDOT))
    nash = [p["where"] for u, p in fake.calls if u.startswith(tn.NASHVILLE) and "where" in p]
    assert "Date_and_Time >= TIMESTAMP '2025-01-01 06:00:00'" in nash[0]                 # midnight CST in UTC
    again = tn.fetch_contract(FX["box"], ["47037"], [2020, 2024, 2025], tmp_path, get=None)  # cached: no network
    assert again == got


def test_outside_davidson_reads_no_metro_rows_and_old_years_are_missing(tmp_path):
    fake = FakeLayers()
    got = tn.fetch_contract(FX["box"], ["47157"], [2025], tmp_path, get=fake)
    assert all(u.startswith(tn.LAYER) for u, _ in fake.calls) and got["cleaning"]["nashville_no_injury_rows"] == 0
    assert tn.fetch_contract(FX["box"], ["47157"], [2019, 2020], tmp_path, get=fake)["years_missing"] == [2019, 2020]
