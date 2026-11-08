"""#19 step 6: a non-California pack's reader runs through pull -> place -> assign -> profile -> export.

The fake pack "ZZ" reuses the recorded Crenshaw corridor (Overpass fixture) with ~12 contract crashes from a fake
reader: GPS on the corridor, GPS beyond the margin, no-GPS street pairs (study cross street, side street), a house
address, a placeholder, an out-of-window year, a duplicate version and a contract break.
"""

import dataclasses
import io

import pytest

from crashiq import packs
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]


def crash(i, **kw):
    c = {"crash_id": f"z{i}", "report_version": 0, "deleted": False, "preliminary": False, "date": "2023-04-0" + str(i % 9 + 1),
         "year": 2023, "hour": 9, "lat": None, "lon": None, "primary_road": "CRENSHAW BLVD", "secondary_road": None,
         "offset_ft": None, "offset_dir": None, "city": "GARDENA", "county_fips": "06037", "county_code": "06037",
         "state": "ZZ", "is_freeway": False, "killed": 0, "injured": 0, "severity": "O", "ped": False, "bike": False,
         "ebike": False, "escooter": False, "motorcycle": False, "heavy_truck": False, "parties": [],
         "collision_type": "REAR END", "lighting": "DAYLIGHT", "weather": None, "surface": None, "day_of_week": None}
    c.update(kw)
    return c


CRASHES = [
    crash(1, lat=33.9016, lon=-118.32662, secondary_road="ROSECRANS AVE", severity="K", killed=1),   # at Rosecrans
    crash(2, lat=33.9050, lon=-118.32665, severity="B", injured=1),                                   # mid-block
    crash(3, lat=33.9050, lon=-118.3100),                                                             # ~1 mi east
    crash(4, secondary_road="W 135TH ST", severity="C", injured=1),                                  # no GPS, corner
    crash(5, secondary_road="MANHATTAN BEACH BLVD"),                                                 # side street
    crash(6, primary_road="14500 CRENSHAW BLVD"),                                                    # house address
    crash(7, secondary_road="NOT STATED"),                                                           # placeholder
    crash(8, lat=33.9093, lon=-118.32662, year=2015, date="2015-01-01"),                             # outside window
    crash(9, lat=33.8999, lon=-118.32662, secondary_road="W 144TH ST", report_version=0),
    crash(9, lat=33.8999, lon=-118.32662, secondary_road="W 144TH ST", report_version=1, severity="A", injured=1),
    crash(10, lat=33.8978, lon=-118.3267, severity="X"),                                             # contract break
    crash(11, lat=33.8978, lon=-118.3267, primary_road="ELM ST", secondary_road="OAK ST"),           # other street, GPS
]


@pytest.fixture
def zz(monkeypatch):
    seen = {}

    def fetch(box, county_fips, years, cache_dir):
        seen.update(box=box, counties=county_fips, years=years)
        return {"crashes": [dict(c) for c in CRASHES], "cleaning": {"fake": True}, "years_missing": []}
    pack = dataclasses.replace(packs.get("CA"), code="ZZ", name="Zedland", status="active", source="Crash data: Zedland test",
                               source_short="ZED", fetch=fetch, caltrans=False, methods=packs.REF / "methods_va.json")
    monkeypatch.setitem(packs.PACKS, "ZZ", pack)
    return seen


def test_a_reader_pack_runs_end_to_end(client, zz):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")      # recorded: no TIGER/NAD download starts
    sid = client.post("/api/studies", json={"name": "Zed corridor", "mode": "profile", "state": "ZZ",
                                            "from_year": 2021, "to_year": 2025}).json()["id"]
    assert client.get(f"/api/studies/{sid}").json()["state"] == "ZZ"
    assert client.put(f"/api/studies/{sid}/corridor", json={"line": LINE}).status_code == 200
    s = client.post(f"/api/studies/{sid}/crashes/pull").json()
    cl = s["cleaning"]
    assert zz["years"] == [2021, 2022, 2023, 2024, 2025] and zz["counties"] == ["037"]
    assert cl["contract_errors"] == 1 and cl["gps_beyond_margin_dropped"] == 1 and cl["outside_window_dropped"] == 1
    assert cl["duplicate_versions_dropped"] == 1 and cl["reader"] == {"fake": True}
    ids = {c["crash_id"]: c for c in client.get(f"/api/studies/{sid}/crashes").json()["crashes"]}
    assert ids["z9"]["severity"] == "A"                                           # the newest version wins
    assert ids["z5"]["exclude_rule"] == "cross_street_not_on_corridor"
    assert ids["z6"]["review_reason"] == "house_address" and ids["z7"]["review_reason"] == "no_cross_street"
    assert s["source"] == "Crash data: Zedland test"
    p = client.get(f"/api/studies/{sid}/profile").json()
    t1 = {r["key"]: r["values"]["value"] for r in p["tables"][0]["rows"]}
    assert t1["fatal_crashes"] == 1 and t1["crashes"] >= 4
    assert client.get(f"/api/studies/{sid}/export.xlsx").status_code == 200
    pdf = client.get(f"/api/studies/{sid}/export.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
