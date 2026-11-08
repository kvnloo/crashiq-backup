"""Illinois: IDOT crash-layer reader (sources/il_idot.py) and its plug-in pack, offline on a recorded fixture of live
rows (Chicago, the 2025 layer by severity, first-crash type, ped/bike, freeway, offset and street pair, plus 2019 and
2014 rows from the older layer schema; the last row has no point), recorded 2026-11-08."""

import json

from crashiq import packs
from crashiq.sources import il_idot

from conftest import FIXTURES

FX = json.loads((FIXTURES / "il_idot.json").read_text())
ROWS = FX["rows"]
PACK = packs.get("IL")


def recs():
    return [il_idot.contract_record(r["attributes"], r["geometry"], r["year"]) for r in ROWS]


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "il" not in packs.PLUGIN_ERRORS and PACK.name == "Illinois" and PACK.status == "active"
    assert PACK.severity_note is None and packs.value(PACK, "crash_costs") is None
    assert packs.check_methods(packs.methods(PACK), "IL") == []
    assert packs.value(PACK, "min_years")["value"] == 5


def test_rows_with_a_point_pass_the_contract_and_severity_is_idots_kabco():
    cs = recs()
    gps = [c for c in cs if c["lat"] is not None]
    assert len(gps) == len(ROWS) - 1 and all(packs.check_crash(c, PACK) == [] for c in gps)
    assert set("KABCO") >= {c["severity"] for c in cs} >= set("ABCO")
    code = {"4": "K", "3": "A", "2": "B", "1": "C", "0": "O"}           # IDOT's own crash KABCO, where not shifted
    for r, c in zip(ROWS, cs):
        assert c["severity"] == code.get(r["attributes"]["CrashSeverityCd"], c["severity"])
    assert il_idot.severity({"TotalFatals": 0, "AInjuries": 0, "BInjuries": 1}) == "B"
    assert il_idot.severity({"TotalInjured": 1}) == "U" and il_idot.severity({"CrashSeverity": "Injury"}) == "U"
    shifted = {"TotalFatals": 0, "AInjuries": 1, "CrashSeverityCd": "C", "RoadwayFunctionalClass": " No Median Barrier",
               "ClassOfTrafficway": "Urban InterState (PAS)", "CrashID": "1", "CountyCode": 16, "CrashMonth": 1,
               "CrashDay": 2}                                            # a 2019 row after the column shift
    c = il_idot.contract_record(shifted, {"x": -87.64, "y": 41.9}, 2019)
    assert c["severity"] == "A" and c["is_freeway"]


def test_point_comes_from_the_geometry_and_counties_from_idots_numbers():
    old = next(r for r in ROWS if r["year"] == 2014 and r["geometry"])
    c = il_idot.contract_record(old["attributes"], old["geometry"], 2014)
    assert c["lon"] < 0 and c["date"].startswith("2014-")                # 2014's own longitude column is unsigned
    assert il_idot.contract_record(old["attributes"], {"x": -118.0, "y": 34.0}, 2014)["bad_coords"]
    assert il_idot.county_fips(16) == "17031" and il_idot.county_fips(1) == "17001"
    assert il_idot.county_fips(102) == "17203" and il_idot.county_fips(0) is None
    assert all(c["county_fips"] == "17031" for c in recs())


def test_streets_pairs_offsets_and_flags():
    cs = recs()
    new, old = [c for c in cs if c["year"] == 2025], [c for c in cs if c["year"] < 2025]
    assert all(c["primary_road"] for c in new) and not any(c["primary_road"] for c in old)
    assert any(c["secondary_road"] for c in new) and any(c["offset_ft"] for c in new)
    assert any(c["ped"] for c in cs) and any(c["bike"] for c in cs) and any(c["is_freeway"] for c in cs)
    assert "BROADSIDE" in {c["collision_type"] for c in cs} and "ANGLE" not in {c["collision_type"] for c in cs}
    assert il_idot.cross_street("Front Rd/Mannheim", "Front Rd") == "Mannheim"
    assert il_idot.cross_street("Moss/Western", "Western") == "Moss"
    assert il_idot.cross_street("(UNK)/W Wabansia Ave", "W Wabansia Ave") is None
    assert il_idot.cross_street("Dundee Road/S/B Kennicott Drive", "S/B Kennicott Drive") == "Dundee Road"
    assert il_idot.cross_street("(N/A)", "Main St") is None


class FakeLayer:
    """The layer's two calls answered from the fixture: ids in the envelope, then rows by id."""
    def __init__(self):
        self.calls = []

    def __call__(self, url, params):
        year = next(y for y, name in il_idot.LAYERS.items() if f"/{name}/" in url)
        rows = [r for r in ROWS if r["year"] == year]
        self.calls.append((year, "ids" if params.get("returnIdsOnly") else "rows"))
        if params.get("returnIdsOnly"):
            assert params["geometryType"] == "esriGeometryEnvelope" and params["inSR"] == "4326"
            return {"objectIds": [r["attributes"]["OBJECTID"] for r in rows]}
        want = set(map(int, params["objectIds"].split(",")))
        return {"features": [r for r in rows if r["attributes"]["OBJECTID"] in want]}


def test_fetch_contract_reads_each_years_layer_and_caches(tmp_path):
    layer = FakeLayer()
    box = (41.85, -87.75, 41.95, -87.62)
    got = il_idot.fetch_contract(box, ["17031"], [2013, 2014, 2019, 2025], tmp_path, get=layer)
    assert {y for y, _ in layer.calls} == {2014, 2019, 2025}             # 2013 has no layer, never asked
    assert got["years_missing"] == [2013] and got["cleaning"]["source_rows"] == len(ROWS)
    assert len(got["crashes"]) == len(ROWS)
    again = il_idot.fetch_contract(box, ["17031"], [2013, 2014, 2019, 2025], tmp_path, get=None)
    assert again == got                                                  # second call reads the cache, no network
