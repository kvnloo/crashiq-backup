"""#235: the user-approved street alias table (data/reference/street_aliases.csv) is used in its own city only,
draft rows are ignored, and a new entry needs no code change."""

import json

import pytest

from crashiq import aliases, crashes
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

HEAD = "scope_type,scope,county_code,raw,replacement,status\n"


@pytest.fixture
def table(tmp_path, monkeypatch):
    def use(text):
        f = tmp_path / "street_aliases.csv"
        f.write_text(HEAD + text)
        monkeypatch.setattr(aliases, "FILE", f)
        aliases.table.cache_clear()
    yield use
    aliases.table.cache_clear()


def crash(city, county, sec, prim="BROADWAY"):
    return {"city": city, "county_code": county, "primary_road": prim, "secondary_road": sec}


def test_the_live_table_has_the_40_approved_entries():
    aliases.table.cache_clear()
    assert sum(len(v) for v in aliases.table().values()) == 40
    c = aliases.apply(crash("OAKLAND", "1", "MARTIN LUTHER KING JR WY"))
    assert c["secondary_road"] == "MARTIN LUTHER KING JUNIOR WAY"
    assert c["roads_as_reported"] == {"secondary_road": "MARTIN LUTHER KING JR WY"}
    assert c["aliases_used"] == ["Oakland|MARTIN LUTHER KING JR WY"]


def test_an_alias_applies_in_its_own_city_only(table):
    table("city,Torrance,19,HAWTHORN BL,HAWTHORNE BOULEVARD,approved\n")
    assert aliases.apply(crash("TORRANCE", "19", "HAWTHORN BL."))["secondary_road"] == "HAWTHORNE BOULEVARD"
    assert aliases.apply(crash("LAWNDALE", "19", "HAWTHORN BL"))["secondary_road"] == "HAWTHORN BL"
    assert aliases.apply(crash("TORRANCE", "30", "HAWTHORN BL"))["secondary_road"] == "HAWTHORN BL"   # county too


def test_a_draft_row_is_ignored_and_a_new_approved_row_needs_no_code(table):
    table("city,Torrance,19,HAWTHORN BL,HAWTHORNE BOULEVARD,draft\n")
    assert "aliases_used" not in aliases.apply(crash("TORRANCE", "19", "HAWTHORN BL"))
    table("city,Torrance,19,HAWTHORN BL,HAWTHORNE BOULEVARD,draft\ncity,Torrance,19,ARLINGTN AV,ARLINGTON AVENUE,approved\n")
    assert aliases.apply(crash("TORRANCE", "19", "ARLINGTN AV"))["secondary_road"] == "ARLINGTON AVENUE"


def test_the_pull_searches_the_approved_spellings_of_the_corridor(table):
    table("city,Oakland,1,MARTIN LUTHER KING JR WY,MARTIN LUTHER KING JUNIOR WAY,approved\n")
    assert "MARTIN LUTHER KING JR WY" in crashes._like_words("MARTIN LUTHER KING JUNIOR")


def test_a_report_using_its_citys_approved_spelling_is_kept_and_placed(client, table):
    # Hawthorne writes "HAWTHORNE PLAZA DR" for West 135th Street (a test entry): the no-GPS report is on the stretch
    table("city,Hawthorne,19,HAWTHORNE PLAZA DR,WEST 135TH STREET,approved\n")
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    t = d["tables"]["cra-2023-0000-0000"]
    live = next(r for r in t["rows"] if str(r.get("IsDeleted")).lower() not in ("true", "1"))
    t["rows"].append({**live, "Collision Id": 86000001, "Report Version": 1, "Latitude": "", "Longitude": "",
                      "PrimaryRoad": "CRENSHAW BLVD", "SecondaryRoad": "HAWTHORNE PLAZA DR", "SecondaryDistance": "0",
                      "City Name": "HAWTHORNE", "County Code": "19", "Crash Date Time": "2023-07-09T10:00:00"})
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(d)
    sid = client.post("/api/studies", json={"name": "A", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9123, -118.32662]]})
    client.post(f"/api/studies/{sid}/crashes/pull")
    c = next(x for x in client.get(f"/api/studies/{sid}/crashes?full=true").json()["crashes"] if x["crash_id"] == "86000001")
    assert not c.get("exclude_rule") and c["location_source"] in ("exact", "unique_pair")
    assert c["aliases_used"] == ["Hawthorne|HAWTHORNE PLAZA DR"]
    assert c["roads_as_reported"]["secondary_road"] == "HAWTHORNE PLAZA DR"
    a = next(x for x in client.get(f"/api/studies/{sid}/assignment").json()["assignments"] if x["crash_id"] == "86000001")
    assert a["location_id"] == "osm-1029"
    t1 = next(t for t in client.get(f"/api/studies/{sid}/profile").json()["tables"] if t["id"] == "T1")
    assert next(r for r in t1["rows"] if r["key"] == "located_alias")["values"]["value"] == 1
