"""Tester: failing tests for CCRS recording habits found in the statewide agency profile (2026-10-19).

Each test reproduces, on the offline Crenshaw fixture, a pattern measured in real 2023-24 CCRS data
(#73 workbook, reports/testing/). Open bugs are strict xfails (XPASS fails the suite, so the
marker comes off when the fix lands); fixed ones stay as plain regression tests.
"""

from __future__ import annotations

import copy
import json

import pytest

from crashiq import crashes, network
from crashiq.sources.ckan import Ckan
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]
STUDY = {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}
CROSS = ("Marine Avenue", "West 144th Street", "Rosecrans Avenue")
NET_X = {"line": LINE, "corridor_name": "Crenshaw Boulevard",
         "intersections": [{"name": n, "is_study": True} for n in CROSS]}


def _fixture(no_gps: bool = False) -> dict:
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    if no_gps:
        for rid, t in d["tables"].items():
            if rid.startswith("cra-"):
                for r in t["rows"]:
                    r["Latitude"], r["Longitude"] = "", ""
    return d


def _row(d: dict, cid: int) -> tuple[list, dict]:
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                if r["Collision Id"] == cid:
                    return t["rows"], r
    raise KeyError(cid)


# Regression test for #81 (fixed on main).
def test_same_crash_filed_under_two_collision_ids_counts_once():
    # Real CCRS 2023: CHP 9630-2023-00084 is in the table twice, Collision Ids 1975974 and 1975975, same minute,
    # I-10 E/B & BOB HOPE DR, same GPS. Statewide 2023-24: 445 report numbers with 2+ Collision Ids and the same two
    # roads (LAPD 77, LASD 49, Hesperia 27). The pull de-duplicates on Collision Id only.
    # The pull doesn't read Report Number today, so the fixture has no such column: the twin is the same row
    # (same agency, time, roads, offset) under a new Collision Id, as in the CHP example.
    d = _fixture()
    rows, r = _row(d, 9200001)
    twin = copy.deepcopy(r)
    twin["Collision Id"], twin["Report Version"] = 9299999, 2      # the re-filed copy, a new id
    rows.append(twin)
    for rid, t in d["tables"].items():          # a re-filed report carries its own party and victim rows
        if rid.startswith(("par-", "iwp-")):
            col = next(f["id"] for f in t["fields"] if f["id"].replace(" ", "").lower() == "collisionid")
            t["rows"] += [{**r, col: 9299999} for r in t["rows"] if str(r.get(col)) == "9200001"]
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    ids = {c["crash_id"] for c in out["crashes"]}
    assert len(ids & {"9200001", "9299999"}) == 1


# Regression test for #82 (fixed on main).
def test_cross_street_not_stated_is_not_called_a_side_street():
    # Real CCRS 2024: SecondaryRoad is 'NOT STATED' on 4,649 rows and 'PRIVATE PROPERTY' on 644. Santa Monica PD
    # (8% GPS) has no usable cross street on 16% of its street crashes, Signal Hill (1% GPS) 15%. The no-GPS
    # filter reads 'NOT STATED' as a street name, finds it isn't a study cross street, and lists the crash under
    # `cross_street_not_on_corridor` (a side street, #39). The report says nothing about a side street: where on
    # the corridor it happened is unknown, which is a different reason with a different count.
    d = _fixture(no_gps=True)
    _, r = _row(d, 9200001)                     # CRENSHAW BL & W 144TH ST, no GPS
    r["SecondaryRoad"] = "NOT STATED"
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    c = next(c for c in out["crashes"] if c["crash_id"] == "9200001")
    assert c.get("exclude_rule") != "cross_street_not_on_corridor"


def _state_route_osm() -> dict:
    """A corridor that is a state highway in OSM: name 'Pacific Coast Highway', ref 'CA 1', three cross streets."""
    lats = [LINE[0][0] + i * (LINE[-1][0] - LINE[0][0]) / 20 for i in range(21)]
    lon = LINE[0][1]
    nodes = [{"type": "node", "id": i + 1, "lat": la, "lon": lon} for i, la in enumerate(lats)]
    ways = [{"type": "way", "id": 100, "nodes": [n["id"] for n in nodes],
             "tags": {"highway": "primary", "name": "Pacific Coast Highway", "ref": "CA 1"}}]
    for k, (name, i) in enumerate(zip(CROSS, (3, 10, 17))):
        a, b = 1000 + 2 * k, 1001 + 2 * k
        nodes += [{"type": "node", "id": a, "lat": lats[i], "lon": lon - 0.003},
                  {"type": "node", "id": b, "lat": lats[i], "lon": lon + 0.003}]
        ways.append({"type": "way", "id": 200 + k, "nodes": [a, i + 1, b],
                     "tags": {"highway": "secondary", "name": name}})
    return {"elements": nodes + ways}


# Regression test for #83 (fixed on main).
def test_no_gps_crash_written_by_route_number_is_found():
    # Real CCRS 2023-24: Laguna Beach PD (0% GPS) writes 26% of its road fields as route numbers ('SR-1',
    # 'PCH - SR1', 'SR-133'); Yuba City (1% GPS) 14%, San Carlos/SMCSO (0.4% GPS) 9%. OSM tags the road with
    # name + ref ('Pacific Coast Highway', 'CA 1'). The net keeps one corridor_name and the no-GPS search is a
    # LIKE on that name only, so 'SR-1 & W 144TH ST' is never read.
    net = network.detect(_state_route_osm(), LINE)
    for i in net["intersections"]:
        i["is_study"] = True
    d = _fixture(no_gps=True)
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                for col in ("PrimaryRoad", "SecondaryRoad"):
                    if str(r.get(col) or "").upper().startswith("CRENSHAW"):
                        r[col] = "PACIFIC COAST HWY"
    _, r = _row(d, 9200001)
    r["PrimaryRoad"] = "SR-1"                   # same corner, written the Laguna Beach way
    out = crashes.pull(STUDY, {**net, "line": LINE}, Ckan(FakeCkan(d)))
    ids = {c["crash_id"] for c in out["crashes"]}
    assert {"9200002", "9200003"} <= ids        # control: the name-written crashes are found
    assert "9200001" in ids


# Regression test for #80 (fixed on main).
def test_hyphenated_corridor_name_finds_no_gps_reports():
    # Union City, statewide run 2026-10-19 (#73): OSM names the road 'Alvarado-Niles Road'; Union City PD (0% GPS)
    # writes 'ALVARADO NILES RD'. street_key keeps the hyphen in the core, the no-GPS search becomes
    # LIKE '%ALVARADO-NILES%' against the squeezed column 'ALVARADONILESRD', and matches nothing: the app pulled
    # 8 crashes where 58 no-GPS reports name the corridor and one of its study cross streets.
    d = _fixture(no_gps=True)
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                for col in ("PrimaryRoad", "SecondaryRoad"):
                    if str(r.get(col) or "").upper().startswith("CRENSHAW"):
                        r[col] = "ALVARADO NILES RD"
    net = {**NET_X, "corridor_name": "Alvarado-Niles Road"}
    out = crashes.pull(STUDY, net, Ckan(FakeCkan(d)))
    ids = {c["crash_id"] for c in out["crashes"]}
    assert {"9200001", "9200002", "9200003"} <= ids


# Regression test for #84 (fixed on main).
def test_empty_overpass_answer_is_not_cached(db):
    # Statewide run 2026-10-19 (#73): overpass-api.de answered valid corridor queries with 0 elements and no remark
    # 7 times in 14 calls (the same query live a minute later: 312 elements). fetch_overpass accepts the empty list,
    # caches it under the query key, and every later visit reuses it: the study shows no corridor street, no
    # intersections, and only the GPS crashes in the box, with no error.
    from crashiq import network
    empty = b'{"version": 0.6, "osm3s": {}, "elements": []}'
    q = network.overpass_query([(37.5976, -122.0583), (37.5926, -122.0410)])
    try:
        network.fetch_overpass(db, q, transport=lambda url, data, timeout: empty, retries=0, sleep=lambda s: None)
    except network.NetworkError:
        pass
    assert db.one("SELECT 1 FROM http_cache WHERE source = 'overpass'") is None


# Regression test for #111 (fixed on main by #115).
def test_wrong_county_gps_crash_does_not_redirect_the_no_gps_search():
    # Statewide run 2026-10-20 (#73), Marina (Monterey, county 27), Reservation Rd: in 2021 the only GPS crashes in
    # the corridor box are two Woodland PD reports (Yolo, county 57; ids 2796970, 2829517, ELM ST & COURT ST, a
    # Woodland corner) with GPS in Marina. The pull takes the no-GPS search area from the GPS crashes in the box,
    # searches county 57 for 2021, and misses every Marina no-GPS report that year (10 of 11 silent drops).
    d = _fixture()
    for rid, t in d["tables"].items():
        if rid == "cra-2023-0000-0000":
            for r in t["rows"]:
                if r.get("Latitude"):
                    r["County Code"] = "57"            # every GPS crash in the box that year is from another county
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    ids = {c["crash_id"] for c in out["crashes"]}
    assert "9200001" in ids                    # Crenshaw & W 144th St, 2023, no GPS, county 19


# Regression test for #113 (fixed on main by #114).
@pytest.mark.parametrize("osm_name, written", [
    ("East Colorado Boulevard", "COLORADO BL"), ("East Colorado Boulevard", "E COLORADO BL"),
    ("West Manning Avenue", "MANNING AV"), ("North Center Street", "CENTER ST"), ("South Main Street", "S MAIN ST"),
])
def test_corridor_name_with_leading_direction_finds_no_gps_reports(osm_name, written):
    # Statewide run 1 (#73/#112), Pasadena: test road 'East Colorado Boulevard' pulled 0 crashes; CCRS 2021 alone has
    # 48 Pasadena no-GPS reports on 'COLORADO BL'. Blythe ('East Hobsonway') the same. The no-GPS SQL prefilter
    # squeezes the core with its directional ('ECOLORADO'), so LIKE '%ECOLORADO%' never matches 'COLORADOBL'.
    d = _fixture(no_gps=True)
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                for col in ("PrimaryRoad", "SecondaryRoad"):
                    if str(r.get(col) or "").upper().startswith("CRENSHAW"):
                        r[col] = written
    net = {**NET_X, "corridor_name": osm_name}
    out = crashes.pull(STUDY, net, Ckan(FakeCkan(d)))
    ids = {c["crash_id"] for c in out["crashes"]}
    assert {"9200001", "9200002", "9200003"} <= ids


# Regression test for #121 (fixed on main).
def test_not_stated_does_not_name_a_state_street_corridor():
    # Statewide run 2 (#73), Santa Barbara, 'State Street': 6,136 no-GPS reports with SecondaryRoad 'NOT STATED' were
    # pulled from four counties (Riverside, San Diego, Santa Clara, Santa Barbara), e.g. '32456 HAUN ROAD | NOT STATED'
    # in Menifee, and listed as side-street exclusions. The squeezed placeholder 'NOTSTATED' contains the corridor
    # core 'STATE', so the SQL prefilter and _names_street both read it as the corridor, and the street-name search
    # area spreads to every county with such a report.
    d = _fixture(no_gps=True)
    rows, r = _row(d, 9200001)
    junk = copy.deepcopy(r)
    junk.update({"Collision Id": 9288888, "PrimaryRoad": "32456 HAUN ROAD", "SecondaryRoad": "NOT STATED"})
    real = copy.deepcopy(r)                    # a genuine State St report, so the street-name search area exists
    real.update({"Collision Id": 9288887, "PrimaryRoad": "STATE ST", "SecondaryRoad": "W 144TH ST"})
    rows += [junk, real]
    net = {**NET_X, "corridor_name": "State Street"}
    out = crashes.pull(STUDY, net, Ckan(FakeCkan(d)))
    ids = {c["crash_id"] for c in out["crashes"]}
    assert "9288887" in ids                    # control: the real State St report is found
    assert "9288888" not in ids


def _to_dms(v: float) -> float:
    """Decimal degrees written the way San Jose PD writes them in CCRS: DD.MMSSss (37.24077 -> 37.142677)."""
    s, v = (-1 if v < 0 else 1), abs(v)
    d = int(v)
    m = (v - d) * 60
    sec = (m - int(m)) * 60
    return s * round(d + int(m) / 100 + sec / 10000, 6)


@pytest.mark.xfail(strict=True, reason="#143: an agency's GPS written as degrees-minutes-seconds lands ~30 km away and the crash is lost")
def test_gps_written_as_degrees_minutes_seconds_is_not_lost():
    # Portal survey (#88), 2026-10-20: 85-88% of San Jose PD's CCRS GPS points 2021-24 carry the DMS digit signature
    # (13% by chance); 2025: 56%. 491 SJPD 2024 crashes link by report number to San Jose's own open data (TCR
    # 24-011-0126 = CCRS 2024-240110126): as written, CCRS GPS sits a median 34 km from the city's point; read as
    # DMS, 80 m. The pull takes the point as real GPS: it falls outside the corridor box, and the no-GPS name search
    # skips it because it has coordinates, so the crash disappears without a count.
    d = _fixture()
    gps_ids = set()
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                if r.get("Latitude") and r.get("Longitude"):
                    gps_ids.add(str(r["Collision Id"]))
                    r["Latitude"] = str(_to_dms(float(r["Latitude"])))
                    r["Longitude"] = str(_to_dms(float(r["Longitude"])))
    base = {c["crash_id"] for c in crashes.pull(STUDY, NET_X, Ckan(FakeCkan(_fixture())))["crashes"]} & gps_ids
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)))
    found = {c["crash_id"] for c in out["crashes"]} & base
    assert len(found) >= 0.9 * len(base)        # the corridor's GPS crashes are still found (converted or by name)


# Regression test for #147 (fixed on main).
def test_unincorporated_place_name_is_not_another_city():
    # Statewide run 3 (#73), Kensington, Arlington Avenue: CCRS files Kensington's crashes under City Name 'Kensington'
    # (an unincorporated place; CCRS even marks it incorporated). The corridor enters Berkeley + unincorporated Contra
    # Costa County, so the #142 filter allows BERKELEY / UNINCORPORATED / CONTRA COSTA COUNTY and drops 11 genuine
    # 'Kensington' reports on Arlington Av as filed in another city (e.g. 2677748 ARLINGTON AV & WESTMINSTER).
    # A place with no OSM city boundary (admin level 8) can't be "another city" when the corridor runs through
    # unincorporated land.
    d = _fixture(no_gps=True)
    _, r = _row(d, 9200001)                     # CRENSHAW BL & W 144TH ST, no GPS
    r["City Name"] = "KENSINGTON"
    net = {**NET_X, "cities": {"cities": ["Hawthorne"], "outside": True, "counties": ["Los Angeles County"]}}
    out = crashes.pull(STUDY, net, Ckan(FakeCkan(d)))
    assert "9200001" in {c["crash_id"] for c in out["crashes"]}


@pytest.mark.xfail(strict=True, reason="#154: a corridor name with 'of' (Avenue of Flags) never matches CHP's spelling")
def test_corridor_name_with_of_matches_chp_spelling():
    # Statewide run 4, corridor list v2 (#73), Buellton, Avenue of Flags: 2752702 'AVENUE OF FLAGS' & '1ST ST' (no GPS)
    # was never read. street_key drops OF from the core ('AVENUE FLAGS'), so the prefilter looks for AVENUEFLAGS in
    # CHP's AVENUEOFFLAGS.
    d = _fixture(no_gps=True)
    _, r = _row(d, 9200001)                     # no GPS, cross street W 144TH ST (a study cross street)
    r["PrimaryRoad"] = "AVENUE OF FLAGS"
    out = crashes.pull(STUDY, {**NET_X, "corridor_name": "Avenue of Flags"}, Ckan(FakeCkan(d)))
    assert "9200001" in {c["crash_id"] for c in out["crashes"]}


@pytest.mark.xfail(strict=True, reason="#155: a numbered corridor with a direction (East 4th Street) misses 'E 4TH ST'")
def test_numbered_corridor_with_direction_matches_abbreviated_direction():
    # Statewide run 4, corridor list v2 (#73), Dorris, East 4th Street: 2508053 'MAIN ST' & '4TH ST' (no GPS) was never
    # read. A core too short without its direction keeps it (_search_core: 'EAST 4TH'), so the prefilter looks for
    # EAST4TH, and CHP writes E 4TH ST (E4TH) or 4TH ST. The abbreviated form is plainly the same street.
    d = _fixture(no_gps=True)
    _, r = _row(d, 9200001)
    r["PrimaryRoad"] = "E 4TH ST"
    out = crashes.pull(STUDY, {**NET_X, "corridor_name": "East 4th Street"}, Ckan(FakeCkan(d)))
    assert "9200001" in {c["crash_id"] for c in out["crashes"]}
