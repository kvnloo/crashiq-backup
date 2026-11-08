"""Kentucky: KSP Location Search reader (sources/ky_ksp.py) and its plug-in pack, offline on a recorded fixture of 29
live rows (central Louisville, Jan-Feb 2025, by severity, manner, ped/bike, freeway and parkway, light; the last row has
no mapping point) with their GPS points, recorded 2026-11-08."""

import json
from datetime import date

import pytest

from crashiq import packs
from crashiq.sources import ky_ksp

from conftest import FIXTURES

FX = json.loads((FIXTURES / "ky_ksp.json").read_text())
ROWS, PTS = FX["rows"], FX["points"]
PACK = packs.get("KY")


def recs():
    return [ky_ksp.contract_record(r, PTS.get(r["xIncidentGUID"])) for r in ROWS]


def test_plugin_is_registered_and_its_methods_are_cited():
    assert "ky" not in packs.PLUGIN_ERRORS and PACK.name == "Kentucky" and PACK.status == "active"
    assert PACK.severity_note and packs.value(PACK, "crash_costs") is None
    assert packs.check_methods(packs.methods(PACK), "KY") == []


def test_rows_with_a_point_pass_the_contract_and_severity_is_k_u_o():
    cs = recs()
    gps = [c for c in cs if c["lat"] is not None]
    assert len(gps) == len(ROWS) - 1 and all(packs.check_crash(c, PACK) == [] for c in gps)
    assert {c["severity"] for c in cs} == {"K", "U", "O"}
    for r, c in zip(ROWS, cs):
        assert c["severity"] == ("K" if r["Number Killed"] else "U" if r["Number Injured"] else "O")
    assert ky_ksp.severity({"Number Killed": 0, "Number Injured": 2}) == "U"


def test_point_comes_from_the_mapping_call_not_the_rounded_grid():
    r = ROWS[0]
    assert r["Latitude"] == round(r["Latitude"])                       # the grid rounds to whole degrees
    c = ky_ksp.contract_record(r, PTS[r["xIncidentGUID"]])
    assert c["lat"] == PTS[r["xIncidentGUID"]]["xLatitude"] and c["lat"] != round(c["lat"])
    assert ky_ksp.contract_record(r, {**PTS[r["xIncidentGUID"]], "xLongitude": 85.7})["lon"] == -85.7
    none = ky_ksp.contract_record(ROWS[-1], None)
    assert none["lat"] is None and not none["bad_coords"]
    far = ky_ksp.contract_record(r, {"xLatitude": 34.0, "xLongitude": -118.0})
    assert far["lat"] is None and far["bad_coords"]


def test_dates_streets_flags_and_county():
    cs = recs()
    assert all(c["date"].startswith("2025-0") and c["county_fips"] == "21111" for c in cs)
    assert all(c["hour"] == int(r["Time"][:2]) for r, c in zip(ROWS, cs) if r["Time"])
    assert any(c["secondary_road"] for c in cs) and all(c["primary_road"] or c["road_number"] for c in cs)
    assert any(c["ped"] for c in cs) and any(c["is_freeway"] for c in cs) and any(not c["is_freeway"] for c in cs)
    assert ky_ksp.FREEWAY.match("I 0065") and ky_ksp.FREEWAY.match("WK9001") and not ky_ksp.FREEWAY.match("KY0022")
    types = {c["collision_type"] for c in cs}
    assert "BROADSIDE" in types and "ANGLE" not in types
    assert ky_ksp.FIPS["JEFFERSON"] == "21111" and ky_ksp.FIPS["ADAIR"] == "21001" and len(ky_ksp.FIPS) == 120


class FakeSite:
    """The two site calls, answered from the fixture; a range longer than 31 days is 'too large'."""
    def __init__(self):
        self.calls = []

    def __call__(self, path, fields):
        f = dict(fields)
        self.calls.append((path, f.get("DateRangeStart"), f.get("DateRangeEnd")))
        if path.endswith("ExecuteQuery"):
            a, b = (date(int(x[6:]), int(x[:2]), int(x[3:5])) for x in (f["DateRangeStart"], f["DateRangeEnd"]))
            if (b - a).days > 31:
                return {"errorMessage": "Sorry, Result set is too large. Please limit your Search further.",
                        "result": {}}
            return {"errorMessage": None, "result": {"results": [r for r in ROWS if a.isoformat() <= r["Date"][:10]
                                                                 <= b.isoformat()]}}
        guids = [v for k, v in fields if k == "aIncidentGUID[]"]
        return {"results": [PTS[g] for g in guids if g in PTS]}


def test_fetch_contract_splits_large_ranges_reads_points_and_caches(tmp_path):
    site = FakeSite()
    got = ky_ksp.fetch_contract((38.15, -85.80, 38.30, -85.60), ["21111"], [2025], tmp_path, post=site)
    q = [c for c in site.calls if c[0].endswith("ExecuteQuery")]
    assert q[0][1:] == ("01/01/2025", "12/31/2025") and len(q) > 8        # halved until each range answers
    assert got["cleaning"]["source_rows"] == len(ROWS) and got["cleaning"]["no_mapping_point"] == 1
    assert got["years_missing"] == [] and len(got["crashes"]) == len(ROWS)
    again = ky_ksp.fetch_contract((38.15, -85.80, 38.30, -85.60), ["21111"], [2025], tmp_path, post=None)
    assert again == got                                                  # second call reads the cache, no network


def test_other_site_errors_are_raised():
    with pytest.raises(RuntimeError):
        ky_ksp.search(lambda p, f: {"errorMessage": "Sorry, an unexpected error occurred"}, (38, -86, 38.1, -85.9),
                      date(2025, 1, 1), date(2025, 1, 2))
