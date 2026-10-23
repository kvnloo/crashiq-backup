import json
import random

import pytest

from crashiq import assign, network
from crashiq.geo import LocalProjection

from conftest import FIXTURES

PROJ = LocalProjection(34.0, -118.0)


def ll(x, y):
    return PROJ.to_ll(x, y)


# Straight line A (0,0) → B (0,3000) ft. Study intersections at 0 (A), 1500 and 1900 (400 ft apart: radii overlap).
A, B = ll(0, 0), ll(0, 3000)
INTS = [
    {"id": "i1", "name": "First St", "station_ft": 0.0, "lat": A[0], "lon": A[1], "is_study": True},
    {"id": "i2", "name": "Second St", "station_ft": 1500.0, **dict(zip(("lat", "lon"), ll(0, 1500))), "is_study": True},
    {"id": "i3", "name": "Third St", "station_ft": 1900.0, **dict(zip(("lat", "lon"), ll(0, 1900))), "is_study": True},
]


def net(ints=INTS):
    from crashiq.geo import Polyline
    L = Polyline([A, B]).length_ft
    return {"line": [A, B], "intersections": ints, "segments": network.segments(ints, L)}


def crash(cid, x, y):
    lat, lon = ll(x, y)
    return {"crash_id": cid, "lat": lat, "lon": lon, "location_source": "gps"}


def one(c, radius=250.0, buffer=100.0, n=None):
    return assign.assign([c], n or net(), radius, buffer)["assignments"][0]


def test_exactly_250_ft_is_an_intersection_crash():
    a = one(crash("c", 250, 1500))
    assert (a["kind"], a["location_id"], a["rule"]) == ("intersection", "i2", "influence_radius")
    assert a["distance_ft"] == pytest.approx(250, abs=0.2)


def test_just_past_250_ft_is_not():
    a = one(crash("c", 251, 1500))
    assert a["kind"] == "excluded" and a["rule"] == "outside_buffer"   # 251 ft off the line, buffer 100


def test_overlapping_radii_go_to_the_nearest():
    assert one(crash("c", 0, 1690))["location_id"] == "i2"
    assert one(crash("c", 0, 1710))["location_id"] == "i3"
    assert one(crash("c", 0, 1690))["rule"] == "nearest_of_overlapping_radii"


def test_segment_crash_by_projection_and_ordering():
    a = one(crash("c", 50, 800))
    assert (a["kind"], a["location_id"]) == ("segment", "seg:i1:i2")
    assert a["distance_ft"] == pytest.approx(50, abs=0.2) and a["station_ft"] == pytest.approx(800, abs=0.5)
    assert one(crash("c", -40, 2500))["location_id"] == "seg:i3:B"


def test_outside_buffer_and_outside_limits_are_excluded():
    assert one(crash("c", 150, 800))["rule"] == "outside_buffer"
    beyond = one(crash("c", 0, 3200))
    assert beyond["kind"] == "excluded" and beyond["rule"] == "outside_study_limits"


def test_no_coordinates_is_unmatched_not_dropped():
    a = one({"crash_id": "c", "lat": None, "lon": None, "location_source": "unmatched"})
    assert a["kind"] == "unmatched" and a["location_provenance"] == "unmatched"


def test_pull_time_exclusion_is_listed_under_its_rule():
    c = {**crash("c", 0, 1500), "exclude_rule": "cross_street_not_on_corridor"}    # even with a point on the line
    a = one(c)
    assert (a["kind"], a["rule"], a["location_id"]) == ("excluded", "cross_street_not_on_corridor", None)


def test_radius_change_reassigns():
    c = crash("c", 280, 1500)
    assert one(c)["kind"] == "excluded"
    assert one(c, radius=300)["kind"] == "intersection"


def test_unflagged_intersection_does_not_attract_crashes():
    ints = [dict(i) for i in INTS]
    ints[1]["is_study"] = False
    a = one(crash("c", 20, 1500), n=net(ints))
    assert (a["kind"], a["location_id"]) == ("segment", "seg:i1:i3")


def test_provenance_carried_through():
    c = crash("c", 10, 10)
    c["location_source"] = "jev(0.97)"
    assert one(c)["location_provenance"] == "jev(0.97)"


def test_conservation_on_random_crashes():
    rnd = random.Random(7)
    cs = [crash(f"c{k}", rnd.uniform(-600, 600), rnd.uniform(-500, 3500)) for k in range(500)]
    cs += [{"crash_id": f"u{k}", "lat": None, "lon": None} for k in range(17)]
    out = assign.assign(cs, net(), 250, 100)
    c = out["counts"]
    assert c["intersection"] + c["segment"] + c["excluded"] + c["unmatched"] == c["total"] == 517
    assert sum(out["by_location"].values()) == c["intersection"] + c["segment"]
    assert c["unmatched"] == 17


# -- API on the Crenshaw fixtures ---------------------------------------------------------------------
def test_api_assignment_follows_radius(client):
    from crashiq.sources.fake_ckan import FakeCkan
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "Crenshaw", "mode": "profile"}).json()["id"]
    assert client.get(f"/api/studies/{sid}/assignment").status_code == 409
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9123, -118.32662]]})
    assert client.get(f"/api/studies/{sid}/assignment").status_code == 409          # not pulled yet
    client.post(f"/api/studies/{sid}/crashes/pull")
    a250 = client.get(f"/api/studies/{sid}/assignment").json()
    client.patch(f"/api/studies/{sid}", json={"radius_ft": 150})
    a150 = client.get(f"/api/studies/{sid}/assignment").json()
    assert a250["counts"]["total"] == a150["counts"]["total"] == 126    # + 1 coarse-GPS report found by name (#218)
    assert a250["counts"]["unmatched"] == 0  # the 4 no-GPS Crenshaw reports are now placed by the locator (#35, PR #36)
    assert a150["counts"]["intersection"] < a250["counts"]["intersection"]
    json.dumps(a150)


# -- #53 road-name check and GPS-vs-report flag --------------------------------------------------------------
def named(cid, x, y, pr, sr, **kw):
    return {**crash(cid, x, y), "primary_road": pr, "secondary_road": sr, **kw}


def n_main():
    return {**net(), "corridor_name": "Main Street"}


def test_gps_crash_on_another_street_in_the_buffer_is_excluded():
    a = one(named("c", 60, 800, "ALLEY", "PARKING LOT"), n=n_main())
    assert (a["kind"], a["rule"]) == ("excluded", "not_on_corridor_street")
    assert one(named("c", 60, 800, "MAIN ST", "SECOND ST"), n=n_main())["kind"] == "segment"


def test_blank_road_fields_are_kept():
    assert one(named("c", 60, 800, "", None), n=n_main())["kind"] == "segment"


def test_intersection_crash_on_the_cross_street_is_kept_but_not_on_an_unrelated_street():
    assert one(named("c", 150, 1500, "SECOND ST", "ELM ST"), n=n_main())["location_id"] == "i2"   # cross-street approach
    a = one(named("c", 150, 1500, "ELM ST", "OAK ST"), n=n_main())
    assert (a["kind"], a["rule"]) == ("excluded", "not_on_corridor_street")


def test_placed_crashes_are_not_road_checked():
    c = {**named("c", 60, 800, "ELM ST", "OAK ST"), "location_source": "exact"}   # placed from its own names
    assert one(c, n=n_main())["kind"] == "segment"


def test_gps_far_from_the_intersection_the_report_names_is_flagged_not_moved():
    # Report says Main & Third (station 1900), GPS 390 ft away near Second: within 400 ft, not flagged
    a = one(named("c", 0, 1510, "MAIN ST", "THIRD ST"), n=n_main())
    assert a["location_id"] == "i2" and "gps_check" not in a
    b = one(named("c", 0, 1200, "MAIN ST", "THIRD ST"), n=n_main())                # 700 ft from Third
    assert b["gps_check"] == "far_from_stated_intersection" and b["stated_location_id"] == "i3"
    assert b["kind"] == "segment"                                                    # counted where the GPS is
    c = one(named("c", 0, 1200, "MAIN ST", "THIRD ST", offset_ft=700.0), n=n_main())  # the offset explains it
    assert "gps_check" not in c
    r = assign.assign([named("c", 0, 1200, "MAIN ST", "THIRD ST")], n_main(), 250.0, 100.0)
    assert r["gps_far_from_stated"] == 1



def test_every_placed_crash_has_a_station_along_the_corridor():
    # #102 strip diagram: intersection crashes sit at the intersection's station, segment crashes at their own
    a = one(crash("c", 30, 1510))
    assert a["kind"] == "intersection" and a["station_ft"] == 1500.0
    b = one(crash("c", 40, 800))
    assert b["kind"] == "segment" and b["station_ft"] == pytest.approx(800, abs=1)
