"""FARS as a location source for fatal crashes (#174): store, link rule, usable point, placement."""

import csv
import json

from crashiq import crashes, fars, placement
from crashiq.db import Database
from crashiq.sources.ckan import Ckan
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES
from test_crashes import NET_X, STUDY

HEAD = ["STATE", "ST_CASE", "COUNTY", "CITY", "MONTH", "DAY", "YEAR", "HOUR", "MINUTE", "FATALS", "LATITUDE", "LONGITUD",
        "TWAY_ID", "TWAY_ID2"]


def _db(tmp_path, rows, bom=False):
    p = tmp_path / "accident.csv"
    with open(p, "w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEAD)
        w.writeheader()
        for r in rows:
            w.writerow({"STATE": 6, "CITY": 0, "TWAY_ID": "", "TWAY_ID2": "", "HOUR": 99, "MINUTE": 99, **r})
    db = Database(tmp_path / "t.sqlite")
    fars.load_csv(db, p)
    return db


CRASH = {"reported_at": "2024-01-08T08:50:00", "county_code": "19", "killed": 1, "primary_road": "CRENSHAW BL",
         "secondary_road": "W 144TH ST"}


def test_county_code_maps_to_fips():
    assert (fars.fips("19"), fars.fips(1), fars.fips("58")) == (37, 1, 115)


def test_load_skips_other_states_and_the_byte_order_mark(tmp_path):
    db = _db(tmp_path, [{"ST_CASE": 60001, "COUNTY": 37, "YEAR": 2024, "MONTH": 1, "DAY": 8, "FATALS": 1},
                        {"ST_CASE": 50001, "STATE": 5, "COUNTY": 37, "YEAR": 2024, "MONTH": 1, "DAY": 8, "FATALS": 1}],
             bom=True)
    assert fars.years_loaded(db) == [2024]
    assert db.one("SELECT COUNT(*) AS n FROM fars_accident")["n"] == 1


def test_link_same_day_time_and_deaths(tmp_path):
    db = _db(tmp_path, [{"ST_CASE": 60001, "COUNTY": 37, "YEAR": 2024, "MONTH": 1, "DAY": 8, "HOUR": 9, "MINUTE": 30,
                         "FATALS": 1, "LATITUDE": 33.9, "LONGITUD": -118.33},
                        {"ST_CASE": 60002, "COUNTY": 37, "YEAR": 2024, "MONTH": 1, "DAY": 8, "HOUR": 14, "MINUTE": 0,
                         "FATALS": 1},                                      # 5 hours later: not this crash
                        {"ST_CASE": 60003, "COUNTY": 37, "YEAR": 2024, "MONTH": 1, "DAY": 8, "HOUR": 8, "MINUTE": 45,
                         "FATALS": 2}])                                     # two killed: not this crash
    status, row = fars.link(db, CRASH)
    assert status == "linked" and fars.case_key(row["year"], row["st_case"]) == "2024-60001"


def test_unknown_time_matches_and_roads_break_a_tie(tmp_path):
    day = {"COUNTY": 37, "YEAR": 2024, "MONTH": 1, "DAY": 8, "FATALS": 1}
    db = _db(tmp_path, [{**day, "ST_CASE": 60001, "TWAY_ID": "CRENSHAW BLVD"}, {**day, "ST_CASE": 60002, "TWAY_ID": "SR-1"}])
    status, row = fars.link(db, CRASH)
    assert status == "linked" and row["st_case"] == 60001
    db = _db(tmp_path, [{**day, "ST_CASE": 60001}, {**day, "ST_CASE": 60002}])
    assert fars.link(db, CRASH) == ("ambiguous", None)                     # never used


def test_cases_are_keyed_by_year_because_st_case_restarts(tmp_path):
    db = _db(tmp_path, [{"ST_CASE": 60011, "COUNTY": 37, "YEAR": 2021, "MONTH": 1, "DAY": 8, "FATALS": 1},
                        {"ST_CASE": 60011, "COUNTY": 37, "YEAR": 2024, "MONTH": 1, "DAY": 8, "FATALS": 1}])
    assert db.one("SELECT COUNT(*) AS n FROM fars_accident")["n"] == 2
    status, row = fars.link(db, CRASH)
    assert status == "linked" and fars.case_key(row["year"], row["st_case"]) == "2024-60011"
    assert fars.link(db, {**CRASH, "reported_at": "2025-01-08T08:50:00"}) == ("no_fars_year", None)


def test_unknown_and_shared_points_are_not_used(tmp_path):
    day = {"COUNTY": 37, "YEAR": 2024, "MONTH": 1, "FATALS": 1}
    db = _db(tmp_path, [{**day, "DAY": 1, "ST_CASE": 1, "LATITUDE": 77.7777, "LONGITUD": 777.7777},
                        *[{**day, "DAY": d, "ST_CASE": 10 + d, "LATITUDE": 34.0, "LONGITUD": -118.0} for d in (2, 3, 4)],
                        {**day, "DAY": 5, "ST_CASE": 20, "LATITUDE": 33.9, "LONGITUD": -118.33}])
    r = lambda case: db.one("SELECT * FROM fars_accident WHERE st_case = ?", (case,))
    assert fars.point(db, r(1)) is None                                     # FARS unknown code
    assert fars.point(db, r(12)) is None                                    # shared by 3 crashes
    assert fars.point(db, r(20)) == (33.9, -118.33)


# -- placement -----------------------------------------------------------------------------------------
def _fatal_no_gps_pull():
    """Crash 9200001 (CRENSHAW BL & W 144TH ST, no GPS in the fixture) made fatal. The test network names its study
    intersections without coordinates, so the street check is "within 400 ft of the corridor it names"."""
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                if r["Collision Id"] == 9200001:
                    r.update(Latitude="", Longitude="", NumberKilled=1)
    return crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d))), NET_X["line"][1]      # a point on the corridor line


def _crash(out):
    return next(c for c in out["crashes"] if c["crash_id"] == "9200001")


def test_fatal_crash_without_gps_takes_its_fars_point_when_it_fits(tmp_path):
    out, (la, lo) = _fatal_no_gps_pull()
    c = _crash(out)
    t = c["reported_at"]
    db = _db(tmp_path, [{"ST_CASE": 60077, "COUNTY": 37, "YEAR": int(t[:4]), "MONTH": int(t[5:7]), "DAY": int(t[8:10]),
                         "FATALS": 1, "LATITUDE": la + 0.0002, "LONGITUD": lo}])     # ~70 ft from its corner
    counts = placement.place_fatal_from_fars(db, NET_X, out)
    assert counts["placed"] == 1
    assert c["location_source"] == "fars" and c["fars_case"] == f"{t[:4]}-60077"


def test_fars_point_off_the_reports_streets_is_not_used(tmp_path):
    out, (la, lo) = _fatal_no_gps_pull()
    c = _crash(out)
    t = c["reported_at"]
    db = _db(tmp_path, [{"ST_CASE": 60077, "COUNTY": 37, "YEAR": int(t[:4]), "MONTH": int(t[5:7]), "DAY": int(t[8:10]),
                         "FATALS": 1, "LATITUDE": la + 0.02, "LONGITUD": lo + 0.02}])  # ~2 km away
    counts = placement.place_fatal_from_fars(db, NET_X, out)
    assert counts["linked_point_off_streets"] == 1 and c["location_source"] == "unmatched"


def test_fars_never_places_a_crash_nobody_died_in(tmp_path):
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                r["Latitude"], r["Longitude"] = "", ""
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    db = _db(tmp_path, [{"ST_CASE": 1, "COUNTY": 37, "YEAR": 2021, "MONTH": 6, "DAY": 15, "FATALS": 0,
                         "LATITUDE": 33.9, "LONGITUD": -118.33}])
    counts = placement.place_fatal_from_fars(db, NET_X, out)
    assert counts["tried"] == sum((c.get("killed") or 0) > 0 and not c.get("exclude_rule") for c in out["crashes"])
    assert not any(c["location_source"] == "fars" and not c.get("killed") for c in out["crashes"])
