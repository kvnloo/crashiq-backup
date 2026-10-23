"""#247 GPS repair (an obvious format fix, Tester's run 9A measurement): degrees-minutes-seconds written as decimal is
read per crash for every agency, and a longitude that lost its minus sign is restored. Either repair is used only
when it is the one reading that fits the report's streets; the raw coordinates are kept. No whole-degree shifts."""

import json

from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]
ROSECRANS = (33.9016, -118.32662)        # study intersection osm-1023
DMS = ("33.540576", "-118.1935832")       # Rosecrans written as degrees-minutes-seconds


def _row(template, cid, lat, lon, primary, secondary, agency="1999"):
    return {**template, "Collision Id": cid, "Report Version": 1, "NCIC Code": agency, "Latitude": lat,
            "Longitude": lon, "PrimaryRoad": primary, "SecondaryRoad": secondary, "SecondaryDistance": "0",
            "SecondaryDirection": "", "SecondaryUnitOfMeasure": "F", "IsFreeway": "False",
            "Crash Date Time": f"2023-08-{1 + cid % 28:02d}T{cid // 28 % 24:02d}:{cid % 60:02d}:00"}


def _study(client, rows):
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    t = d["tables"]["cra-2023-0000-0000"]
    live = next(r for r in t["rows"] if str(r.get("IsDeleted")).lower() not in ("true", "1"))
    t["rows"] += [_row(live, *r) for r in rows]
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(d)
    sid = client.post("/api/studies", json={"name": "R", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    log = client.post(f"/api/studies/{sid}/crashes/pull").json()["cleaning"]
    got = {c["crash_id"]: c for c in client.get(f"/api/studies/{sid}/crashes?full=true").json()["crashes"]}
    return log, got


def test_dms_is_read_per_crash_for_any_agency(client):
    # agency 1999 has no DMS habit (too few points to judge): before #247 its DMS point was never read
    log, got = _study(client, [(85000001, *DMS, "CRENSHAW BLVD", "ROSECRANS AV")])
    c = got["85000001"]
    assert c["location_source"] == "gps_dms_corrected" and c["gps_repair"] == "dms"
    assert abs(c["lat"] - ROSECRANS[0]) < 1e-4 and abs(c["lon"] - ROSECRANS[1]) < 1e-4
    assert c["gps_as_written"] == list(DMS)
    assert any("1999" in a and "per crash" in a for a in log["gps_dms_agencies"])


def test_a_dms_reading_that_fits_nothing_leaves_another_agencys_point_alone(client):
    # read as DMS it would be at Rosecrans, but the report names Marine Avenue: not this corridor's crash
    _, got = _study(client, [(85000002, *DMS, "CRENSHAW BLVD", "MARINE AV")])
    assert "85000002" not in got


def test_a_lost_longitude_minus_is_restored_when_it_fits(client):
    log, got = _study(client, [(85000003, "33.901600", "118.326620", "CRENSHAW BLVD", "ROSECRANS AV")])
    c = got["85000003"]
    assert c["location_source"] == "gps_sign_corrected" and c["gps_repair"] == "lon_sign"
    assert (c["lat"], c["lon"]) == (33.9016, -118.32662) and c["gps_as_written"] == ["33.901600", "118.326620"]
    assert log["gps_sign_corrected"] == 1


def test_a_flipped_point_that_doesnt_fit_stays_no_gps(client):
    # flipped, it's at Rosecrans; the report says Marine Avenue: no repair, placed by its names instead
    _, got = _study(client, [(85000004, "33.901600", "118.326620", "CRENSHAW BLVD", "MARINE AV")])
    c = got["85000004"]
    assert "gps_repair" not in c and c["location_source"] in ("exact", "unique_pair", "unmatched")


def test_no_whole_degree_repairs(client):
    # one degree of latitude off (34.9016): a point elsewhere in California, never shifted back
    _, got = _study(client, [(85000005, "34.901600", "-118.326620", "CRENSHAW BLVD", "ROSECRANS AV")])
    assert "85000005" not in got
