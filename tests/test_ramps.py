"""#287 ramps: crashes per million vehicles from Caltrans' district ramp ADT (user decision 2026-10-30, docs/03, #300).
The fixture rows are cut from Caltrans' public District 7 ramp files (2021 and 2024 editions, downloaded 2026-10-30):
LA-405 at Vermont and Normandie, the two Rosecrans southbound off-ramps, a ramp with the 2021 placeholder 999 and a
closed ramp coded 1001 / 999. A ramp is identified only when exactly one Caltrans ramp within 0.3 mi fits the report's
direction, on/off and cross street; 2 or more fits wait for the engineer's pick."""

import json

import pytest

from crashiq import aadt, ramps

from conftest import FIXTURES
from test_aadt import FILES, Get, xlsx

RAMP_ROWS = json.loads((FIXTURES / "ramps_la405.json").read_text())
RAMP_FILES = {**FILES, "r21": xlsx("d07-ramp-adt-2021-v2-a11y.xlsx", RAMP_ROWS),
              "r24": xlsx("2024-d7-ramp-adt-a11y.xlsx", RAMP_ROWS)}
RAMP_YEARS = {2021: {"volumes": "https://x/v21", "ramps": ["https://x/r21"]},
              2024: {"volumes": "https://x/v24", "trucks": "https://x/t24", "ramps": ["https://x/r24"]}}


@pytest.fixture
def cache(tmp_path):
    return aadt.AadtCache(tmp_path / "aadt", years=RAMP_YEARS, get=Get(RAMP_FILES), background=False,
                          now=lambda: 1_793_000_000)


def crash(primary, secondary, pm, when="2024-03-02T08:00:00", cid="x1"):
    return {"crash_id": cid, "primary_road": primary, "secondary_road": secondary, "reported_at": when,
            "postmile": {"route": "405", "route_suffix": "", "county": "LA", "prefix": "", "pm": pm, "suffix": ""}}


# -- the counts --------------------------------------------------------------------------------------------------
def test_ramp_adt_is_the_latest_count_at_or_before_the_year_never_a_later_one(cache):
    r = next(x for x in cache.ramps_near("405", "LA", 13.49, 0.01) if x["description"] == "SB OFF TO VERMONT AVE")
    assert cache.ramp_adt(r, 2024) == {"adt": 5062, "count_year": 2023}        # no 2024 count: 2023's, labelled
    assert cache.ramp_adt(r, 2019) == {"adt": 8700, "count_year": 2018}        # 2019 not counted; never 2020's
    assert cache.ramp_adt(r, 2014) == {"adt": 4358, "count_year": 2014}        # from the 2021 edition
    assert cache.ramp_adt(r, 2011) is None                                     # nothing at or before 2011


def test_a_ramp_count_more_than_5_years_before_the_year_is_too_old(cache):
    r = next(x for x in cache.ramps_near("405", "LA", 12.166, 0.01) if "TRUCK SCALES" in x["description"])
    assert cache.ramp_adt(r, 2019) == {"adt": 144, "count_year": 2014}         # 5 years old: used
    assert cache.ramp_adt(r, 2020) == {"adt": None, "count_year": 2014, "too_old": True}


def test_the_newest_edition_wins_where_editions_overlap(cache):
    r = next(x for x in cache.ramps_near("405", "LA", 13.47, 0.01) if x["description"] == "NB ON FROM VERMONT AVE")
    assert r["by_year"][2012] == 5600                                          # only in the 2021 edition
    assert r["by_year"][2023] == 7646 and r["by_year"][2024] == 7724          # only in the 2024 edition


def test_placeholder_values_1001_and_999_count_as_missing(cache):
    r = next(x for x in cache.ramps_near("405", "LA", 21.7, 0.01) if x["description"] == "NB ON FROM WB RTE 105")
    assert 2021 not in r["by_year"]                                            # 999 in 2021, between real counts
    assert cache.ramp_adt(r, 2021) == {"adt": 9793, "count_year": 2020}
    closed = [x for x in cache.ramps_near("405", "LA", 12.166, 0.01) if "TRUCK SCALES" in x["description"]]
    assert closed and closed[0]["by_year"] == {2014: 144}                      # then 1001 (2015), 999 (2016): missing
    assert cache.ramp_adt(closed[0], 2019) == {"adt": 144, "count_year": 2014}
    assert json.loads(dict(cache.db().execute("SELECT key, value FROM meta").fetchall())["ramp_placeholders"]) > 0


# -- reading the report ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("primary, secondary, want", [
    ("NORMANDIE AV", "I-405 NB OFF RAMP", ("N", "OFF", ["NORMANDIE"])),
    ("I-405 S/B TO VERMONT AVE OFF-RAMP", "Vermont Ave", ("S", "OFF", ["VERMONT"])),
    ("SR-51 N/B ON RAMP FROM EL CAMINO AVE W/B", "EL CAMINO AVE", ("N", "ON", ["EL", "CAMINO"])),
    ("RALSTON AVENUE NORTHBOUND", "SR-92 WB ON-RAMP", ("W", "ON", ["RALSTON"])),     # the ramp road's direction
    ("MONUMENT BLVD ONRAMP TO I-680S", "MONUMENT BOULEVARD", ("S", "ON", ["MONUMENT"])),
    ("SR 99 NB TO AVE 200 (OFF-RAMP) ", "AVENUE 200 O/C", ("N", "OFF", ["200"])),
    ("EUCALYPTUS AVE", "I-215 N/B ON/OFF RAMP", ("N", None, ["EUCALYPTUS"])),         # on or off: not said
    ("RT 101", "RT 101 NB OFFRAMP (4)", ("N", "OFF", [])),                           # no cross street
])
def test_the_report_gives_direction_on_off_and_cross_street(primary, secondary, want):
    r = ramps.report({"primary_road": primary, "secondary_road": secondary})
    assert (r["dir"], r["on_off"], r["cross"]) == want


def test_a_report_without_a_ramp_word_is_not_a_ramp_crash():
    assert ramps.report({"primary_road": "I-405", "secondary_road": "VERMONT AVE"}) is None


# "<route> <dir> TO <local street>" = the <dir> off-ramp to that street (user 1a, 2026-11-01, docs/03 #297)
@pytest.mark.parametrize("primary, secondary, want", [
    ("I-405 S/B TO VERMONT AVE", "VERMONT AVE", ("S", "OFF", ["VERMONT"])),
    ("RT 99 NB TO AVENUE 200", "AVENUE 200", ("N", "OFF", ["200"])),
    ("VERMONT AVE", "I-405 SB TO VERMONT AVE", ("S", "OFF", ["VERMONT"])),
])
def test_route_dir_to_a_local_street_names_the_off_ramp(primary, secondary, want):
    r = ramps.report({"primary_road": primary, "secondary_road": secondary})
    assert (r["dir"], r["on_off"], r["cross"]) == want and not r.get("connector")


# "<local street> TO <route> <dir>" = the <dir> on-ramp from that street (user 1a, 2026-11-01, #331)
@pytest.mark.parametrize("primary, secondary, want", [
    ("REDONDO BEACH BLVD. TO I-405 NB", "REDONDO BEACH BLVD.", ("N", "ON", ["REDONDO", "BEACH"])),
    ("VERMONT AVE TO SB I-405", "VERMONT AVE", ("S", "ON", ["VERMONT"])),
])
def test_street_to_route_dir_names_the_on_ramp(primary, secondary, want):
    r = ramps.report({"primary_road": primary, "secondary_road": secondary})
    assert (r["dir"], r["on_off"], r["cross"]) == want and r["from_street"]


# "<route> <dir> FROM <street>" = the <dir> on-ramp from that street (user 2026-11-01, #341)
@pytest.mark.parametrize("primary, secondary, want", [
    ("I-405 S/B FROM ARTESIA", "ARTESIA BLVD", ("S", "ON", ["ARTESIA"])),
    ("N/B FROM HAWTHORNE BLVD", "HAWTHORNE BLVD", ("N", "ON", ["HAWTHORNE"])),
])
def test_route_dir_from_a_street_names_the_on_ramp(primary, secondary, want):
    r = ramps.report({"primary_road": primary, "secondary_road": secondary})
    assert (r["dir"], r["on_off"], r["cross"]) == want and r["from_street"]


def test_from_without_a_direction_or_from_a_route_is_not_a_ramp():
    assert ramps.report({"primary_road": "I-405 FROM ARTESIA", "secondary_road": "ARTESIA BLVD"}) is None
    assert ramps.report({"primary_road": "I-405 S/B FROM I-110", "secondary_road": "I-110"}) is None
    assert ramps.report({"primary_road": "MAIN ST FROM OAK AVE", "secondary_road": "OAK AVE"}) is None
    # a ramp word still reads as before; Caltrans descriptions with "ON FR" are unaffected
    assert ramps.report({"primary_road": "SR-51 N/B ON RAMP FROM EL CAMINO AVE", "secondary_road": "EL CAMINO AVE"})["on_off"] == "ON"
    assert ramps.describe("099/NB ON FR BELLEVUE RD")["on_off"] == "ON"


def test_the_on_ramp_reading_leaves_the_other_to_forms_alone():
    off = ramps.report({"primary_road": "I-405 S/B TO VERMONT AVE", "secondary_road": "VERMONT AVE"})
    assert off["on_off"] == "OFF" and not off.get("from_street")
    assert ramps.report({"primary_road": "I-405 NB TO I-110", "secondary_road": "VERMONT AVE"}) is None
    assert ramps.report({"primary_road": "VERMONT AVE TO I-405", "secondary_road": "VERMONT AVE"}) is None    # no dir
    assert ramps.report({"primary_road": "MAIN ST TO OAK AVE", "secondary_road": "OAK AVE"}) is None          # no route


def test_route_to_route_is_a_connector_only_when_the_cross_street_is_one_of_the_routes():
    r = ramps.report({"primary_road": "I-405 NB TO I-110", "secondary_road": "I-110"})
    assert r["connector"] is True
    # a local cross street: the local street passes under or over the freeway; stays mainline (2026-10-25)
    assert ramps.report({"primary_road": "I-405 NB TO I-110", "secondary_road": "VERMONT AVE"}) is None
    assert ramps.report({"primary_road": "I-405 TO VERMONT AVE", "secondary_road": "VERMONT AVE"}) is None   # no dir


def test_a_connector_crash_gets_no_ramp_rate_with_the_reason(cache):
    c = crash("I-405 NB TO I-110", "I-110", 13.49)
    r = ramps.identify(c, cache)
    assert r["status"] == "none" and r["why"] == "freeway connector"


@pytest.mark.parametrize("desc, want", [
    ("SB OFF TO VERMONT AVE", ("S", "OFF")), ("NB ON FROM NB RTE 110", ("N", "ON")),
    ("099/NB ON FR BELLEVUE RD", ("N", "ON")), ("NBOFF TRAVER/MERRITT DR", ("N", "OFF")),
    ("N/B OFF TO CROWS LANDING RD", ("N", "OFF")), ("NB OFFTO AIRPORT DR&204", ("N", "OFF")),
    ("RIVER RD OC SB ON RAMP", ("S", "ON")), ("NORWOOD TO WB-80", ("W", "ON")), ("WB-80 TO NORWOOD", ("W", "OFF")),
])
def test_caltrans_descriptions_give_direction_and_on_off(desc, want):
    d = ramps.describe(desc)
    assert (d["dir"], d["on_off"]) == want


# -- identifying the ramp ----------------------------------------------------------------------------------------
def test_exactly_one_fitting_ramp_within_0_3_mi_identifies_it(cache):
    r = ramps.identify(crash("NORMANDIE AV", "I-405 NB OFF RAMP", 13.80), cache)
    assert r["status"] == "identified" and r["ramp"]["description"] == "NB OFF TO NORMANDIE AVE"
    assert r["ramp"]["pm"] == 13.707


def test_two_fitting_ramps_wait_for_the_engineer_s_pick(cache):
    r = ramps.identify(crash("ROSECRANS AV", "I-405 S/B OFF RAMP", 19.25), cache)
    assert r["status"] == "pick"
    assert sorted(c["description"] for c in r["candidates"]) == ["SB OFF TO EB ROSECRANS AVE", "SB OFF TO WB ROSECRANS AVE"]
    pick = next(c for c in r["candidates"] if c["description"] == "SB OFF TO WB ROSECRANS AVE")
    done = ramps.identify(crash("ROSECRANS AV", "I-405 S/B OFF RAMP", 19.25), cache, picks={"x1": pick["id"]})
    assert done["status"] == "identified" and done["ramp"]["pm"] == 19.364 and done["picked"] is True


@pytest.mark.parametrize("primary, secondary, pm, why", [
    ("RT 405", "RT 405 NB OFFRAMP", 13.8, "no cross street"),
    ("EUCALYPTUS AVE", "I-405 N/B ON/OFF RAMP", 13.8, "on or off not stated"),
    ("WESTERN AVE", "I-405 S/B OFF RAMP", 13.8, "no Caltrans ramp fits"),                 # Normandie and Vermont only
    ("NORMANDIE AV", "I-405 NB OFF RAMP", 30.0, "no Caltrans ramp within 0.3 mi"),
])
def test_otherwise_no_ramp_and_the_reason(cache, primary, secondary, pm, why):
    r = ramps.identify(crash(primary, secondary, pm), cache)
    assert r["status"] == "none" and r["why"] == why


def test_a_crash_with_no_postmile_or_no_ramp_word_is_not_looked_up(cache):
    assert ramps.identify({**crash("NORMANDIE AV", "I-405 NB OFF RAMP", 13.8), "postmile": None}, cache) is None
    assert ramps.identify(crash("I-405", "VERMONT AVE", 13.8), cache) is None


# -- the ramp table (T25) ----------------------------------------------------------------------------------------
VERMONT = {"id": "405||LA||13.492||SB OFF TO VERMONT AVE", "route": "405", "route_suffix": "", "county": "LA",
           "prefix": "", "pm": 13.492, "suffix": "", "description": "SB OFF TO VERMONT AVE", "district": "07",
           "by_year": {2018: 8700, 2020: 6261, 2021: 4152, 2022: 4579, 2023: 5062}}


def ramp_profile(n_on_ramp, statuses=None):
    """The golden profile with its first N S1 crashes on the Vermont off-ramp, plus other ramp outcomes."""
    from crashiq import profile
    from test_profile import golden
    study, n, pull, asg = golden()
    s1 = sorted(a["crash_id"] for a in asg["assignments"] if a["location_id"] == "S1")
    n["shs_ramps"] = {cid: {"crash_id": cid, "status": "identified", "ramp": VERMONT, "picked": False}
                      for cid in s1[:n_on_ramp]}
    for cid, st in zip(s1[n_on_ramp:], statuses or []):
        n["shs_ramps"][cid] = {"crash_id": cid, "status": st, "why": "no cross street" if st == "none" else None,
                               "candidates": [VERMONT, VERMONT] if st == "pick" else None}
    return profile.build(study, n, pull, asg)


def test_ramp_rate_is_crashes_per_million_vehicles_with_the_latest_count_at_or_before_each_year():
    p = ramp_profile(12)
    t = {x["id"]: x for x in p["tables"]}["T25"]
    r = t["rows"][0]
    assert r["label"] == "SB OFF TO VERMONT AVE" and r["key"] == VERMONT["id"]
    v = r["values"]
    adt = {2021: 4152, 2022: 4579, 2023: 5062, 2024: 5062, 2025: 5062}            # 2024 and 2025: 2023's count
    mv = sum(a * 365 for a in adt.values()) / 1e6
    assert v["crashes"] == 12 and v["mv"] == pytest.approx(round(mv, 2))
    assert v["rate_all"] == pytest.approx(round(12 / mv, 2))
    assert v["count_years"] == "2021–2023 (2024, 2025 use 2023)" and v["postmile"] == "LA-405 PM 13.492"
    assert v["source"] == "Caltrans Traffic Census Program, District 7 ramp ADT" and "small_base" not in v


def test_a_ramp_under_10_crashes_is_marked_and_the_scope_counts_every_outcome():
    p = ramp_profile(3, ["pick", "pick", "none"])
    t = {x["id"]: x for x in p["tables"]}["T25"]
    assert t["rows"][0]["values"]["small_base"] == "n < 10"
    assert t["scope"] == {"ramp_crashes": 6, "identified": 3, "pick": 2, "none": 1,
                          "none_why": {"no cross street": 1},
                          "text": "6 ramp crashes: 3 on an identified Caltrans ramp; 2 with 2 or more possible "
                                  "ramps (the engineer picks); 1 with no ramp rate (no cross street: 1)."}


def test_a_year_with_no_ramp_count_at_or_before_it_means_no_rate():
    from crashiq import profile
    from test_profile import golden
    study, n, pull, asg = golden()
    old = {**VERMONT, "by_year": {2023: 5062}}                                   # nothing at or before 2021, 2022
    s1 = sorted(a["crash_id"] for a in asg["assignments"] if a["location_id"] == "S1")
    n["shs_ramps"] = {cid: {"crash_id": cid, "status": "identified", "ramp": old, "picked": False} for cid in s1}
    v = {x["id"]: x for x in profile.build(study, n, pull, asg)["tables"]}["T25"]["rows"][0]["values"]
    assert v["crashes"] == 20 and v["rate_all"] is None and v["mv"] is None
    assert v["count_years"] == "2023 (2024, 2025 use 2023); no count at or before 2021, 2022"


def test_a_too_old_ramp_count_means_no_rate_and_says_so():
    from crashiq import profile
    from test_profile import golden
    study, n, pull, asg = golden()
    old = {**VERMONT, "by_year": {2015: 4000, 2023: 5062}}                       # 2021, 2022 would use 2015
    s1 = sorted(a["crash_id"] for a in asg["assignments"] if a["location_id"] == "S1")
    n["shs_ramps"] = {cid: {"crash_id": cid, "status": "identified", "ramp": old, "picked": False} for cid in s1}
    v = {x["id"]: x for x in profile.build(study, n, pull, asg)["tables"]}["T25"]["rows"][0]["values"]
    assert v["rate_all"] is None and v["mv"] is None and v["adt"] is None
    assert v["count_years"] == "2023 (2024, 2025 use 2023); count too old for 2021, 2022 (newest 2015)"


def test_no_ramp_crashes_no_ramp_table():
    from crashiq import profile
    from test_profile import golden
    assert "T25" not in {x["id"] for x in profile.build(*golden())["tables"]}


def test_named_ramp_crashes_the_freeway_rules_exclude_still_count_in_t25():
    # #314 review (Tester): "I-405 N/B ARTESIA BLVD OFR" is excluded at assignment (rule ramp) on a freeway study, but
    # it is a ramp crash: it counts on its identified ramp in T25 and in T22's "not in this rate" ramp count
    from crashiq import profile
    from test_shs import shs_golden
    study, n, pull, asg = shs_golden()
    s1 = sorted(a["crash_id"] for a in asg["assignments"] if a["location_id"] == "S1")
    out = s1[:3]
    asg = {**asg, "assignments": [{**a, "kind": "excluded", "location_id": None, "rule": "ramp"} if a["crash_id"] in out
                                  else a for a in asg["assignments"]]}
    n["shs_ramps"] = {cid: {"crash_id": cid, "status": "identified", "ramp": VERMONT, "picked": False} for cid in out}
    n["shs_volumes"] = {"S1": {"by_year": {y: 20000 for y in range(2021, 2026)}, "coverage": 1.0, "latest_used": False,
                               "count_years": "2021–2024", "routes": ["1"], "source": "Caltrans Traffic Census Program"}}
    t = {x["id"]: x for x in profile.build(study, n, pull, asg)["tables"]}
    assert t["T25"]["rows"][0]["values"]["crashes"] == 3 and t["T25"]["scope"]["ramp_crashes"] == 3
    assert t["T22"]["scope"]["ramp_crashes"] == 3 and t["T22"]["rows"][0]["values"]["crashes"] == 17
