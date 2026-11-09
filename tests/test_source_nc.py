"""North Carolina readers (Raleigh, NCDOT statewide KA + non-motorist, Durham), offline on recorded ArcGIS pages."""

import json

import pytest

from crashiq.sources import nc_arcgis, nc_durham, nc_ncdot, nc_raleigh

from conftest import FIXTURES

PAGES = json.loads((FIXTURES / "nc_sources.json").read_text())


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Replay: the first page of each layer is the recording, the next page is empty (end of paging)."""
    calls = []

    def fake(url, params):
        calls.append((url, params))
        return PAGES[url.removesuffix("/query")] if "> -1" in params["where"] else {"features": []}

    monkeypatch.setattr(nc_arcgis, "_get", fake)
    return calls


def test_paging_by_object_id(offline):
    rows = list(nc_arcgis.query(nc_ncdot.KA, "1=1", oid="FID"))
    assert len(rows) == len(PAGES[nc_ncdot.KA]["features"])
    assert [c[1]["where"] for c in offline] == ["(1=1) AND FID > -1", f"(1=1) AND FID > {rows[-1]['FID']}"]
    assert offline[0][1]["outSR"] == 4326


def test_helpers():
    assert [nc_arcgis.kabco_letter(v) for v in ("K", "A: Suspected Serious Injury", "C Type Injury (Possible)",
            "O No Injury", "Unknown", "N Unknown", "Killed", None)] == ["K", "A", "C", "O", None, None, None, None]
    assert nc_arcgis.day_time("08/20/2016.", "1:29") == "2016-08-20T01:29:00"
    assert nc_arcgis.day_time(1767139200000, 9) == "2025-12-31T09:00:00"
    assert nc_arcgis.day_time(1767139200000, None) == "2025-12-31"
    assert nc_arcgis.coord(0, 0) == (None, None) and nc_arcgis.coord(35.8, -78.6) == (35.8, -78.6)
    assert nc_arcgis.coord(40.7, -74.0) == (None, None)            # outside North Carolina


def test_raleigh_crashes_and_offsets():
    cs = nc_raleigh.fetch_crashes("Crash_Date_Year=2025")
    assert len(cs) == 35 and all(c["lat"] and c["lon"] for c in cs)
    c = next(c for c in cs if c["collision_id"] == "356547")
    assert (c["primary_road"], c["secondary_road"], c["offset_ft"], c["offset_dir"]) == ("OAKWOOD AVE", "TARBORO ST",
                                                                                      220.0, "E")
    at = next(c for c in cs if c["collision_id"] == "356623")       # "At" the cross street: no offset
    assert at["offset_ft"] is None and at["offset_dir"] is None
    assert any(c["primary_road"].startswith("3000 ") for c in cs)  # house addresses in the on-road field


def test_raleigh_time_zone_switch():
    """True UTC until Oct 2024, local wall time labelled UTC since: both read as the report's local time."""
    old = {"DateOfCrash": 1719811740000, "Crash_Date_Hour": 1}      # 2024-07-01T05:29Z = 01:29 EDT
    new = {"DateOfCrash": 1735743660000, "Crash_Date_Hour": 15}     # 2025-01-01T15:01 written as UTC
    assert nc_raleigh.when(old) == "2024-07-01T01:29:00"
    assert nc_raleigh.when(new) == "2025-01-01T15:01:00"
    assert all(len(c["datetime"]) == 19 for c in nc_raleigh.fetch_crashes("x"))   # date and time


def test_raleigh_severity_from_counts_and_persons():
    cs = nc_raleigh.fetch_crashes("x")
    sev = {c["severity"] for c in cs}
    assert {"K", "A", "O"} <= sev and sev <= set(nc_raleigh.SEVERITY_ORDER)
    k = next(c for c in cs if c["severity"] == "K")
    assert k["killed"] > 0
    ps = nc_raleigh.fetch_persons([c["collision_id"] for c in cs])
    assert ps and all(p["collision_id"] in {c["collision_id"] for c in cs} for p in ps)
    c = dict(cs[0], severity="O")
    assert nc_raleigh.crash_severity(c, [{"kabco": "B"}, {"kabco": "O"}, {"kabco": None}]) == "B"
    assert nc_raleigh.crash_severity(dict(c, severity="A"), [{"kabco": "C"}]) == "A"
    assert nc_raleigh.person({"key_crash": 1, "Injury": "A type injury (disabling)"})["kabco"] == "A"
    assert nc_raleigh.person({"key_crash": 1, "Injury": "Unknown"})["kabco"] == "U"


def test_raleigh_person_ids_are_integers_in_sql(offline):
    with pytest.raises(ValueError):
        nc_raleigh.fetch_persons(["1) OR (1=1"])


def test_ncdot_ka():
    cs = nc_ncdot.fetch_ka()
    assert len(cs) == 25 and {c["severity"] for c in cs} <= {"K", "A"}
    c = next(c for c in cs if c["collision_id"] == "104824194")
    assert c["datetime"] == "2016-08-20T11:43:00" and c["primary_road"] == "NC 58" and c["secondary_road"] == "SR 1607"
    assert c["offset_ft"] == pytest.approx(528.0) and c["offset_dir"] == "N" and c["city_name"] is None
    assert c["gis_route"] == "30000058016" and c["flags"]["motorcycle"]


def test_ncdot_non_motorist():
    cs = nc_ncdot.fetch_non_motorist("CrashYear=2025")
    assert len(cs) == 25 and all(c["datetime"].startswith("2025") for c in cs)
    assert all(c["severity"] in "KABCOU" and len(c["persons"]) == 2 for c in cs)
    assert all(p["kabco"] in "KABCOU" for c in cs for p in c["persons"])
    assert all(c["primary_road"] is None for c in cs)               # no street names in this layer


def test_durham_groups_people_into_crashes():
    rows = PAGES[nc_durham.LAYER]["features"]
    cs = nc_durham.fetch()
    assert len(cs) == len({f["attributes"]["Crash_ID"] for f in rows})
    c = next(c for c in cs if c["collision_id"] == "108357041")
    assert c["primary_road"] == "I 885" and c["is_freeway"] and c["county_code"] == "37063"
    assert len(c["persons"]) == 14 and {p["kabco"] for p in c["persons"]} == {"O"}
    assert all(c["severity"] in "KABCOU" for c in cs)
    assert all(c["offset_dir"] in (None, *nc_durham.COMPASS) for c in cs)
