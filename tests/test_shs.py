"""#287: exposure for state-highway crash rates from Caltrans AADT (user decision 2026-10-26, docs/03). A study segment
is sampled every 0.05 mi; each sample gets its postmile (#248) and each count year's AADT (aadt.py). A calendar year is
9 months of its own count year (Oct-Sep) and 3 of the next."""

import pytest

from crashiq import aadt, profile, shs

from test_aadt import FILES, YEARS, Get, ROWS

LAT0, MI_LAT = 33.88, 1 / 69.0         # a north-south line; 1 mile = 1/69 degree of latitude
PM0 = 13.0                             # the fake postmile at LAT0, rising 1 per mile north


class FakePM:
    def lookup(self, lat, lon, routes, travel=None):
        if "405" not in routes:
            return None
        return {"route": "405", "route_suffix": "", "county": "LA", "prefix": "", "suffix": "",
                "pm": round(PM0 + (lat - LAT0) / MI_LAT, 3)}


@pytest.fixture
def cache(tmp_path):
    return aadt.AadtCache(tmp_path / "aadt", years=YEARS, get=Get(FILES), background=False, now=lambda: 1_793_000_000)


def net(pm_from, pm_to, names=("San Diego Freeway", "I 405")):
    """A corridor from postmile 13.0 northward, with one study segment between two postmiles."""
    to_ft = lambda pm: (pm - PM0) * 5280                                          # noqa: E731
    return {"line": [(LAT0, -118.3), (LAT0 + 2.0 * MI_LAT, -118.3)], "corridor_names": list(names),
            "segments": [{"id": "s1", "name": "x", "from_station_ft": to_ft(pm_from), "to_station_ft": to_ft(pm_to),
                          "length_mi": pm_to - pm_from}]}


def ahead(year, pm):
    f = ROWS[f"{year}-traffic-volumes-ca{'-v2-a11y' if year == 2021 else '-a11y'}.xlsx"]
    r = next(r for r in f["rows"] if str(r[1]).lstrip("0") == "405" and float(str(r[5]).strip()) == pm)
    return int(r[13])


def test_a_state_highway_segment_gets_each_calendar_year_s_aadt(cache):
    v = shs.segment_volumes(net(13.3, 13.8), FakePM(), cache, [2021, 2024])["s1"]
    a21, a24 = ahead(2021, 13.28), ahead(2024, 13.28)                             # Vermont Ave AHEAD = Normandie BACK
    assert v["by_year"][2024] == a24                                            # 2025's count year is past 2024: latest
    assert v["by_year"][2021] == pytest.approx(0.75 * a21 + 0.25 * cache.segment("405", "LA", 13.5, 2022)["aadt"])
    assert v["coverage"] == 1.0 and v["latest_used"] and v["routes"] == ["405"]
    assert v["source"] == "Caltrans Traffic Census Program" and v["count_years"] == "2021–2024; later count years use 2024"
    assert v["pm_coverage"] == 1.0


def test_a_segment_running_past_the_counted_route_gets_no_exposure_for_it(cache):
    v = shs.segment_volumes(net(14.2, 14.9), FakePM(), cache, [2024])["s1"]     # the fixture's last point is 14.398
    assert v["by_year"][2024] is None and v["coverage"] < 1.0


def test_a_corridor_that_is_not_a_state_highway_gets_none(cache):
    assert shs.segment_volumes(net(13.3, 13.8, names=("Crenshaw Boulevard",)), FakePM(), cache, [2024]) is None
    assert shs.segment_volumes(net(13.3, 13.8), None, cache, [2024]) is None


def test_crash_rates_per_million_vehicle_miles_with_the_corridor_average_and_by_year():
    from test_profile import golden
    study, n, pull, asg = golden()
    n["shs_volumes"] = {"S1": {"by_year": {y: 20000 for y in range(2021, 2026)}, "coverage": 1.0, "latest_used": True,
                               "count_years": "2021–2024 (2025 uses 2024)", "routes": ["1"],
                               "source": "Caltrans Traffic Census Program"}}
    p = profile.build(study, n, pull, asg)
    t = {x["id"]: x for x in p["tables"]}
    r = {x["key"]: x["values"] for x in t["T22"]["rows"]}["S1"]
    mvm = 20000 * 0.6 * 365 * 5 / 1e6                                          # 21.9 million vehicle-miles
    assert r["mvm"] == pytest.approx(round(mvm, 2)) and r["crashes"] == 20
    assert r["rate_all"] == pytest.approx(round(20 / mvm, 2))                  # 0.91 crashes per MVM
    assert r["rate_fi"] == pytest.approx(round(6 / mvm, 2)) and r["rate_fatal"] == 0
    assert r["corridor_rate_all"] == r["rate_all"] and r["ratio_to_corridor"] == 1.0   # the only SHS segment
    assert r["count_years"] == "2021–2024 (2025 uses 2024)" and r["source"].startswith("Caltrans")
    years = {x["key"]: x["values"] for x in t["T23"]["rows"]}
    assert sum(v["crashes"] for v in years.values()) == 20
    assert years["2021"]["rate_all"] == pytest.approx(round(years["2021"]["crashes"] / (20000 * 0.6 * 365 / 1e6), 2))
    assert "T22" not in {x["id"] for x in profile.build(*golden())["tables"]}                 # no Caltrans volumes, no T22


def test_with_shs_adds_exposure_on_a_state_highway_and_nothing_elsewhere(cache):
    pull = {"years": [2024], "cleaning": {"years_missing": []}}
    on = profile.with_shs(net(13.3, 13.8), pull, FakePM(), cache)
    assert on["shs_volumes"]["s1"]["by_year"][2024] == ahead(2024, 13.28)
    off = net(13.3, 13.8, names=("Crenshaw Boulevard",))
    assert "shs_volumes" not in profile.with_shs(off, pull, FakePM(), cache)
    assert "shs_volumes" not in profile.with_shs(net(13.3, 13.8), pull, None, cache)        # no postmile layer yet


def test_off_the_state_highway_system_no_rates_says_local_counts_are_needed():
    from test_profile import golden
    study, n, pull, asg = golden()
    n["segments"] = [{**s, "aadt": None} for s in n["segments"]]
    n["intersections"] = [{**i, "major_aadt": None, "minor_aadt": None} for i in n["intersections"]]
    cav = {c["key"]: c["text"] for c in profile.build(study, n, pull, asg)["caveats"]}
    assert "local traffic counts are needed" in cav["rates_not_computed"]
    n["corridor_names"] = ["I 405"]                                                          # a state route, no AADT yet
    cav = {c["key"]: c["text"] for c in profile.build(study, n, pull, asg)["caveats"]}
    assert "local traffic counts" not in cav["rates_not_computed"]


def rated(crashes_on_s1, years=range(2021, 2026)):
    """The golden profile with Caltrans volumes on S1 and that segment's crashes cut to the first N."""
    from test_profile import golden
    study, n, pull, asg = golden()
    n["shs_volumes"] = {"S1": {"by_year": {y: 20000 for y in years}, "coverage": 1.0, "latest_used": False,
                               "count_years": "2021–2024", "routes": ["1"], "source": "Caltrans Traffic Census Program"}}
    on_s1 = [a["crash_id"] for a in asg["assignments"] if a["location_id"] == "S1"]
    drop = set(on_s1[crashes_on_s1:])
    asg = {**asg, "assignments": [a for a in asg["assignments"] if a["crash_id"] not in drop]}
    pull = {**pull, "crashes": [c for c in pull["crashes"] if c["crash_id"] not in drop]}
    return {x["id"]: x for x in profile.build(study, n, pull, asg)["tables"]}


def test_a_rate_on_fewer_than_10_crashes_is_kept_and_marked_too_few():
    t = rated(4)
    r = t["T22"]["rows"][0]["values"]
    assert r["crashes"] == 4 and r["rate_all"] is not None                 # kept for the export, marked
    assert r["small_base"] == "n < 10: segment, corridor average"
    assert t["T22"]["scope"]["small"] is True
    assert all(y["values"].get("small_base") == "n < 10" for y in t["T23"]["rows"])   # 4 crashes over 5 years
    full = rated(20)
    assert "small_base" not in full["T22"]["rows"][0]["values"] and full["T22"]["scope"]["small"] is False


def test_the_rates_say_how_many_corridor_crashes_are_at_intersections_and_left_out():
    sc = rated(20)["T22"]["scope"]
    assert sc["rated_crashes"] == 20 and sc["intersection_crashes"] == sc["corridor_crashes"] - 20
    assert sc["text"] == (f"Segment crashes only: {sc['intersection_crashes']} of {sc['corridor_crashes']} crashes on "
                          "this corridor are at intersections and aren't in these rates.")


def test_a_state_route_with_no_caltrans_postmiles_says_local_counts_are_needed():
    from test_profile import golden
    study, n, pull, asg = golden()
    n["segments"] = [{**s, "aadt": None} for s in n["segments"]]
    n["intersections"] = [{**i, "major_aadt": None, "minor_aadt": None} for i in n["intersections"]]
    n["corridor_names"] = ["Lakewood Boulevard", "CA 19"]                    # relinquished: no route 19 postmiles here
    n["shs_volumes"] = {s["id"]: {"by_year": {2024: None}, "coverage": 0.0, "pm_coverage": 0.0} for s in n["segments"]}
    cav = {c["key"]: c["text"] for c in profile.build(study, n, pull, asg)["caveats"]}
    assert "Route 19 isn't in Caltrans' state-highway postmiles here" in cav["rates_not_computed"]
    assert "local traffic counts are needed" in cav["rates_not_computed"]


# Trucks (docs/03 #287: truck-involved crash rates using 3+ axle truck AADT; heavy truck as docs/03 defines it)
def test_a_segment_gets_its_3_plus_axle_truck_aadt_from_the_truck_point_behind(cache):
    v = shs.segment_volumes(net(13.3, 13.8), FakePM(), cache, [2021, 2024])["s1"]
    assert v["trucks_by_year"][2024] == 917 + 560 + 3708          # CARSON, JCT. RTE. 110 ahead leg: 3, 4, 5+ axles
    assert v["trucks_by_year"][2021] is None                       # the fixture has no 2021 truck file
    assert v["truck_count_years"] == "2024; later count years use 2024"   # 2024 blends in count year 2025 (#299 r1)


def trucked(n_truck, aadt3=1000, years=range(2021, 2026), whole=False):
    from test_profile import golden
    study, n, pull, asg = golden()
    on_s1 = {a["crash_id"] for a in asg["assignments"] if a["location_id"] == "S1"}
    hit = sorted(on_s1)[:n_truck]
    pull = {**pull, "crashes": [{**c, "heavy_truck": c["crash_id"] in hit} for c in pull["crashes"]]}
    n["shs_volumes"] = {"S1": {"by_year": {y: 20000 for y in years}, "coverage": 1.0, "latest_used": False,
                               "count_years": "2021–2024", "routes": ["1"], "source": "Caltrans Traffic Census Program",
                               "trucks_by_year": {y: aadt3 for y in years}, "truck_count_years": "2021–2024"}}
    p = profile.build(study, n, pull, asg)
    return p if whole else {x["id"]: x for x in p["tables"]}


def test_the_rates_caveat_names_the_truck_table():
    cav = {c["key"]: c["text"] for c in trucked(12, whole=True)["caveats"]}
    assert cav["shs_rates"].startswith("State-highway crash rates (T22, T23, T24) use Caltrans Traffic Census AADT "
                                       "(T24: heavy-truck-involved crashes over 3+ axle truck AADT);")


def test_truck_involved_crash_rate_per_million_3_plus_axle_truck_miles():
    t = trucked(12)
    r = t["T24"]["rows"][0]["values"]
    tmvm = 1000 * 0.6 * 365 * 5 / 1e6                              # 1.095 million truck-miles
    assert r["truck_crashes"] == 12 and r["trucks_3plus"] == 1000 and r["truck_mvm"] == pytest.approx(round(tmvm, 2))
    assert r["rate_truck"] == pytest.approx(round(12 / tmvm, 2)) and "small_base" not in r
    assert r["count_years"] == "2021–2024" and r["source"] == "Caltrans Traffic Census Program"
    assert trucked(3)["T24"]["rows"][0]["values"]["small_base"] == "n < 10: segment, corridor average"


def test_the_truck_table_says_what_it_counts_over_what():
    assert trucked(12)["T24"]["scope"]["text"] == ("Crashes involving a heavy truck (which can include trucks under 3 "
                                                   "axles) per million miles driven by trucks with 3 or more axles.")


def test_zero_truck_aadt_gives_no_rate_and_no_ratio():
    r = trucked(12, aadt3=0)["T24"]["rows"][0]["values"]
    assert r["truck_mvm"] == 0 and r["rate_truck"] is None and r["ratio_to_corridor"] is None


def test_no_truck_counts_for_a_window_year_means_no_truck_rate():
    assert "T24" in trucked(12)
    from test_profile import golden
    study, n, pull, asg = golden()
    n["shs_volumes"] = {"S1": {"by_year": {y: 20000 for y in range(2021, 2026)}, "coverage": 1.0, "latest_used": False,
                               "count_years": "2021–2024", "routes": ["1"], "source": "Caltrans Traffic Census Program",
                               "trucks_by_year": {**{y: 1000 for y in range(2021, 2025)}, 2025: None}}}
    ids = {x["id"] for x in profile.build(study, n, pull, asg)["tables"]}
    assert "T22" in ids and "T24" not in ids
