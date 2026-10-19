import json
import urllib.error

import pytest

from crashiq import crashes
from crashiq.sources import ca_ccrs as cc
from crashiq.sources.ckan import Ckan, CkanError
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

OSM = json.loads((FIXTURES / "overpass_crenshaw.json").read_text())
LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]
STUDY = {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}
NET = {"line": LINE, "corridor_name": "Crenshaw Boulevard"}


@pytest.fixture
def fake():
    return FakeCkan(FIXTURES / "ckan_crenshaw.json")


def test_resource_ids_resolved_at_runtime(fake):
    res = cc.table_resources(fake("package_show", {}))
    assert sorted(res["crashes"]) == [2021, 2022, 2023, 2024, 2025]
    assert res["iwp"][2023] == "iwp-2023-0000-0000"


def test_columns_resolve_across_spellings():
    fields = [{"id": "Collision Id", "type": "int4"}, {"id": "Primary Rd", "type": "text"}, {"id": "Latitude", "type": "text"}]
    got, missing = cc.resolve_columns(fields, {"collision_id": ["CollisionId", "Collision Id"],
                                               "primary_road": ["PrimaryRoad", "Primary Rd"],
                                               "lat": ["Latitude"], "lon": ["Longitude"]})
    assert got["primary_road"]["id"] == "Primary Rd" and missing == ["lon"]
    assert cc.num_expr({"id": "Latitude", "type": "text"}) == "CAST(NULLIF(\"Latitude\", '') AS float)"
    assert cc.num_expr({"id": "Latitude", "type": "numeric"}) == '"Latitude"'


def test_pull_counts_and_cleaning_log(fake):
    out = crashes.pull(STUDY, NET, Ckan(fake))
    log = out["cleaning"]
    # 120 of the 121 real crashes are in the box (one is 0.85 mi north at I-105) + duplicate (2 versions)
    # + deleted report + 3 no-coordinate Crenshaw crashes in Hawthorne
    # + 9200005 (Crenshaw / 135th, no coordinates, in Gardena): found by the county-wide search
    assert log["rows_read"] == 120 + 2 + 1 + 3 + 1
    assert log["deleted_dropped"] == 1
    assert log["duplicate_versions_dropped"] == 1
    assert log["no_coords_read"] == 4            # rows naming the corridor street, anywhere in the county
    assert log["no_coords_not_corridor_street"] == 0
    assert (log["with_coords"], log["without_coords"]) == (121, 4)
    ids = {c["crash_id"] for c in out["crashes"]}
    assert "9000058" not in ids                  # real crash at the I-105 ramps, outside the corridor box
    assert "9300001" not in ids                  # far away
    assert "9200005" in ids                      # same street in the next city (Gardena): corridors cross city lines
    assert "9200004" not in ids                  # MARINE AV / AVIATION BL: not the corridor street
    assert {"9200001", "9200002", "9200003"} <= ids
    assert log["kept"] == len(out["crashes"]) == 125
    assert log["cities"] == ["HAWTHORNE"]
    assert log["preliminary_kept"] == sum(c["preliminary"] for c in out["crashes"]) > 0


def test_duplicate_keeps_highest_report_version(fake):
    out = crashes.pull(STUDY, NET, Ckan(fake))
    d = [c for c in out["crashes"] if c["crash_id"] == "9100002"]
    assert len(d) == 1 and d[0]["report_version"] == 2 and d[0]["severity"] == "B"


def test_severity_counted_once_at_most_severe(fake):
    out = crashes.pull(STUDY, NET, Ckan(fake))
    sev = {c["crash_id"]: c["severity"] for c in out["crashes"]}
    assert sev["9200003"] == "A"
    assert set(sev.values()) <= set("KABCUO")
    assert list(sev.values()).count("U") == 1     # injury crash with no IWP row
    two = [c for c in out["crashes"] if c["injured"] == 2]
    assert two and all(c["severity"] == "C" for c in two)   # two POSSIBLE INJURY victims → one C crash


def test_parties_and_mode_flags(fake):
    out = crashes.pull(STUDY, NET, Ckan(fake))
    peds = [c for c in out["crashes"] if c["ped"]]
    assert len(peds) == 4 and all(any(p["party_type"] == "PEDESTRIAN" for p in c["parties"]) for c in peds)
    assert any(c["motorcycle"] for c in out["crashes"])
    assert all(c["parties"] for c in out["crashes"])


def test_sql_uses_bbox_and_names(fake):
    crashes.pull(STUDY, NET, Ckan(fake))
    sqls = fake.sql_log
    assert any("BETWEEN 33.89" in s and "CAST(NULLIF(\"Latitude\", '') AS float)" in s for s in sqls)
    assert any("REPLACE(REPLACE(UPPER(\"PrimaryRoad\")" in s and "LIKE '%CRENSHAW%'" in s
               and "\"County Code\" IN ('19')" in s for s in sqls)
    assert any("\"CollisionId\" IN (" in s for s in sqls)


def test_missing_required_column_is_a_clear_error(fake):
    for t in fake.tables.values():
        t["fields"] = [f for f in t["fields"] if f["id"] != "Latitude"]
    with pytest.raises(crashes.PullError, match="lat"):
        crashes.pull(STUDY, NET, Ckan(fake))


def test_missing_year_is_logged_not_fatal(fake):
    fake.package["resources"] = [r for r in fake.package["resources"] if not r["name"].endswith("2025")]
    out = crashes.pull(STUDY, NET, Ckan(fake))
    assert out["cleaning"]["years_missing"] == [2025]
    assert all(c["year"] != 2025 for c in out["crashes"])


def test_ckan_retries_then_raises():
    calls = []

    def down(action, params):
        calls.append(action)
        raise urllib.error.HTTPError("u", 502, "Bad Gateway", {}, None)

    with pytest.raises(CkanError, match="data.ca.gov"):
        Ckan(down, retries=2, sleep=lambda s: None).get("package_show")
    assert len(calls) == 3


# -- API + per-study cache ------------------------------------------------------------------------------
@pytest.fixture
def sid(client, fake):
    client.app.state.overpass = lambda url, data, timeout: json.dumps(OSM).encode()
    client.app.state.ckan = fake
    s = client.post("/api/studies", json={"name": "Crenshaw", "mode": "profile"}).json()["id"]
    client.put(f"/api/studies/{s}/corridor", json={"line": LINE})
    return s


def test_api_pull_then_cache_then_refresh(client, sid, fake):
    r = client.post(f"/api/studies/{sid}/crashes/pull").json()
    assert r["count"] == 125 and r["from_cache"] is False
    n_sql = len(fake.sql_log)
    assert client.post(f"/api/studies/{sid}/crashes/pull").json()["from_cache"] is True
    assert len(fake.sql_log) == n_sql                          # cache hit: no queries
    assert client.post(f"/api/studies/{sid}/crashes/pull?refresh=true").json()["from_cache"] is False
    full = client.get(f"/api/studies/{sid}/crashes").json()
    assert len(full["crashes"]) == 125 and full["crashes"][0]["parties"]


def test_api_window_change_repulls(client, sid):
    client.post(f"/api/studies/{sid}/crashes/pull")
    client.patch(f"/api/studies/{sid}", json={"from_year": 2023, "to_year": 2025})
    r = client.post(f"/api/studies/{sid}/crashes/pull").json()
    assert r["from_cache"] is False and r["years"] == [2023, 2024, 2025]


def test_api_errors(client, sid):
    def down(action, params):
        raise urllib.error.URLError("unreachable")
    client.app.state.ckan = down
    client.app.state.ckan_retries = 0
    r = client.post(f"/api/studies/{sid}/crashes/pull")
    assert r.status_code == 502 and "data.ca.gov" in r.json()["detail"]
    s2 = client.post("/api/studies", json={"name": "x", "mode": "profile"}).json()["id"]
    assert client.post(f"/api/studies/{s2}/crashes/pull").status_code == 409     # no corridor yet
    assert client.get(f"/api/studies/{s2}/crashes").status_code == 404
