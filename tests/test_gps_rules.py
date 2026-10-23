"""#218 (user decision 2026-10-22, docs/03): police GPS vs the report's own description.
1. GPS snapped to the intersection the report names, while the report states an offset (> 50 ft and a direction):
   the crash goes to that intersection plus the offset, along the named road (`gps_offset_applied`).
2. A default / dispatch point (a pile: one exact point shared by many crashes and street pairs, most of which don't
   fit it), and coarse coordinates (2 decimals or fewer, ~1 km): not a location. The crash is placed by its street
   names, and the ignored point is kept on the crash (`gps_ignored`)."""

import json

from crashiq import crashes, gps_rules
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]
ROSECRANS = (33.9016, -118.32662)          # study intersection osm-1023, station 2292.7 ft
FT_PER_DEG_LAT = 364_000


def _row(template, cid, lat, lon, primary, secondary, dist="0", direction="", agency="1904"):
    return {**template, "Collision Id": cid, "Report Version": 1, "NCIC Code": agency, "Latitude": lat,
            "Longitude": lon, "PrimaryRoad": primary, "SecondaryRoad": secondary, "SecondaryDistance": dist,
            "SecondaryDirection": direction, "SecondaryUnitOfMeasure": "F", "IsFreeway": "False",
            # each its own time: the same agency, time and roads twice is one crash filed twice (#81)
            "Crash Date Time": f"2023-06-{1 + cid % 28:02d}T{cid // 28 % 24:02d}:{cid % 60:02d}:00"}


def _study(client, rows):
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    t = d["tables"]["cra-2023-0000-0000"]
    live = next(r for r in t["rows"] if str(r.get("IsDeleted")).lower() not in ("true", "1"))
    t["rows"] += [_row(live, *r) for r in rows]
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(d)
    sid = client.post("/api/studies", json={"name": "G", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    pull = client.post(f"/api/studies/{sid}/crashes/pull").json()
    got = {c["crash_id"]: c for c in client.get(f"/api/studies/{sid}/crashes?full=true").json()["crashes"]}
    asg = {a["crash_id"]: a for a in client.get(f"/api/studies/{sid}/assignment").json()["assignments"]}
    return pull["cleaning"], got, asg


# -- 1. snapped GPS + stated offset ------------------------------------------------------------------------
def test_snapped_gps_moves_by_the_reported_offset_along_the_named_road(client):
    log, got, asg = _study(client, [(88100001, "33.901600", "-118.326620", "CRENSHAW BLVD", "ROSECRANS AV", "300", "N")])
    c = got["88100001"]
    assert c["location_source"] == "gps_offset_applied"
    assert c["gps_as_reported"] == [33.9016, -118.32662]
    assert abs((c["lat"] - ROSECRANS[0]) * FT_PER_DEG_LAT - 300) < 15 and abs(c["lon"] - ROSECRANS[1]) < 1e-4
    assert asg["88100001"]["kind"] == "segment"          # 300 ft: out of the 250 ft influence area
    assert log["gps_offset_applied"] >= 1


def test_gps_already_at_the_offset_point_or_small_or_no_offset_is_left_alone(client):
    north = f"{ROSECRANS[0] + 300 / FT_PER_DEG_LAT:.6f}"
    log, got, _ = _study(client, [
        (88100002, north, "-118.326620", "CRENSHAW BLVD", "ROSECRANS AV", "300", "N"),     # GPS already moved
        (88100003, "33.901600", "-118.326620", "CRENSHAW BLVD", "ROSECRANS AV", "40", "N"),  # <= 50 ft
        (88100004, "33.901600", "-118.326620", "CRENSHAW BLVD", "ROSECRANS AV", "0", ""),    # no offset
    ])
    assert {got[k]["location_source"] for k in ("88100002", "88100003", "88100004")} == {"gps"}


# -- 2. default / dispatch points ----------------------------------------------------------------------------
PILE = ("33.905470", "-118.326620")        # mid-block, ~1,400 ft from both Rosecrans and 135th
CROSS = ["ROSECRANS AV", "147TH ST", "144TH ST", "MARINE AV", "132ND ST", "135TH ST"]


def test_a_pile_point_that_fits_few_of_its_crashes_is_ignored_and_names_place_them(client):
    rows = [(88200000 + i, *PILE, "CRENSHAW BLVD", CROSS[i % 6]) for i in range(12)]
    log, got, asg = _study(client, rows)
    for i in range(12):
        c = got[str(88200000 + i)]
        assert c["location_source"] in ("exact", "unique_pair"), c       # placed at its own named corner
        assert c["gps_ignored"] == {"lat": 33.90547, "lon": -118.32662, "reason": "default_point", "shared_by": 12}
        assert asg[str(88200000 + i)]["kind"] == "intersection"
    assert log["gps_default_ignored"] == 12 and log["gps_default_ignored_by_agency"] == {"1904": 12}


def test_a_shared_point_with_few_street_pairs_is_not_a_pile(client):
    rows = [(88300000 + i, *PILE, "CRENSHAW BLVD", CROSS[i % 4]) for i in range(12)]       # 4 street pairs
    log, got, _ = _study(client, rows)
    assert all(got[str(88300000 + i)]["location_source"] == "gps" for i in range(12))
    assert log["gps_default_ignored"] == 0


def test_a_busy_snapped_intersection_is_not_a_pile(client):
    rows = [(88400000 + i, "33.901600", "-118.326620", "CRENSHAW BLVD", "ROSECRANS AV") for i in range(8)]
    rows += [(88400100 + i, "33.901600", "-118.326620", "CRENSHAW BLVD", CROSS[1 + i]) for i in range(5)]
    log, got, _ = _study(client, rows)                                 # 13 crashes, 6 pairs, 8 of 13 fit
    assert got["88400000"]["location_source"] == "gps" and got["88400100"]["location_source"] == "gps"
    assert log["gps_default_ignored"] == 0


def test_coarse_coordinates_are_no_gps(client, monkeypatch):
    # the fixture's corridor has no 2-decimal point near it; the rule is the same at any precision setting
    monkeypatch.setitem(gps_rules.CONFIG, "coarse_max_decimals", 4)
    log, got, _ = _study(client, [(88500001, "33.9016", "-118.3266", "CRENSHAW BLVD", "ROSECRANS AV")])
    c = got["88500001"]
    assert c["location_source"] in ("exact", "unique_pair") and c["gps_ignored"]["reason"] == "coarse"
    assert log["gps_coarse_ignored"] >= 1


def test_default_thresholds_are_the_testers():
    assert gps_rules.CONFIG["pile"] == {"decimals": 5, "min_crashes": 10, "min_street_pairs": 5, "max_fit_share": 0.5}
    assert gps_rules.CONFIG["coarse_max_decimals"] == 2
    assert gps_rules.coarse("34.1", "-118.334") and gps_rules.coarse("34.123", "-118.33")
    assert not gps_rules.coarse("34.123", "-118.334")
    assert gps_rules.decimals("34.120000") == 2          # trailing zeros don't count (the Tester's #219 definition)
    assert crashes.GPS_SOURCES == ("gps", "gps_dms_corrected", "gps_offset_applied")


def test_offset_across_the_primary_road_goes_along_the_cross_street(client):
    # "CRENSHAW BLVD | ROSECRANS AV, 200 ft E": Crenshaw runs north-south, so the crash is on Rosecrans, east of it
    log, got, _ = _study(client, [(88600001, "33.901600", "-118.326620", "CRENSHAW BLVD", "ROSECRANS AV", "200", "E")])
    c = got["88600001"]
    assert c["location_source"] == "gps_offset_applied"
    assert abs(c["lat"] - ROSECRANS[0]) < 1e-4 and c["lon"] > ROSECRANS[1]


def test_the_default_point_query_stays_well_inside_the_url_limit():
    import urllib.parse
    cond = gps_rules.sql_condition('CAST(NULLIF("Latitude", \'\') AS float)', 'CAST(NULLIF("Longitude", \'\') AS float)')
    assert len(urllib.parse.quote(cond)) < crashes.MAX_URL_SQL / 2
    assert len(gps_rules.listed_piles()) == 50
