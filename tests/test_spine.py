import json

from crashiq import spine
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

DIQ = json.loads((FIXTURES / "context_demandiq.json").read_text())
LINE = [[33.8953, -118.32662], [33.9040, -118.32662], [33.9123, -118.32662]]


def setup(client, ctx=None):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "Crenshaw safety", "mode": "tis"}).json()["id"]
    pre = client.put(f"/api/studies/{sid}/context", json=ctx).json() if ctx else None
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    client.post(f"/api/studies/{sid}/crashes/pull")
    return sid, pre


def test_reads_a_demandiq_object_for_prefill(client):
    _, pre = setup(client, DIQ)
    p = pre["prefill"]
    assert p["name"] == "Crenshaw Blvd corridor" and p["termini"] == {"from": "Marine Ave", "to": "132nd St"}
    assert p["line"] == LINE                                   # GeoJSON lon/lat → lat/lon
    assert p["functional_class"] == "principal arterial" and p["setting"] == "urban"


def test_writes_results_with_provenance(client):
    sid, _ = setup(client, DIQ)
    ctx = client.get(f"/api/studies/{sid}/context").json()
    assert "crashiq_profile" in ctx["analysis"]["completed"]
    assert ctx["analysis"]["completed"][:2] == ["corridor_recon", "demandiq_existing"]
    ccrs = [h for h in ctx["data_holdings"] if h["kind"] == "CCRS"]
    assert len(ccrs) == 1 and ccrs[0]["period"] == "2021–2025"
    s = ctx["safety"]
    assert s["window"]["from_year"] == 2021 and s["locate_summary"]["unmatched"] == 3 and s["findings"] == []
    assert sum(loc["crashes"] for loc in s["locations"]) + 0 >= 1
    assert any(f["type"] == "data_gap" for f in ctx["analysis"]["flags"])
    for path in ("safety", "analysis.completed", "data_holdings.CCRS", "corridor.intersections"):
        assert ctx["provenance"][path]["method"] == "auto" and ctx["provenance"][path]["date"]
    assert ctx["project"]["version"] == 4


def test_never_overwrites_another_tiles_values_and_keeps_unknown_fields(client):
    sid, _ = setup(client, DIQ)
    ctx = client.get(f"/api/studies/{sid}/context").json()
    assert ctx["corridor"]["name"] == "Crenshaw Blvd"            # DemandIQ's, not OSM's "Crenshaw Boulevard"
    assert ctx["corridor"]["length_mi"] == 1.17
    assert ctx["provenance"]["corridor.length_mi"]["date"] == "2026-10-01"
    assert ctx["demand"] == DIQ["demand"] and ctx["provenance"]["demand.aadt"] == DIQ["provenance"]["demand.aadt"]
    assert ctx["corridor"]["lane_profile"] == DIQ["corridor"]["lane_profile"]
    assert ctx["context"]["generators"] == DIQ["context"]["generators"]
    assert {"type": "bottleneck", "detail": "SB queue at Rosecrans PM"} in ctx["analysis"]["flags"]
    # intersections were empty, so CrashIQ fills them from OSM (method auto), control never guessed
    ints = ctx["corridor"]["intersections"]
    assert ints[0]["name"] == "Marine Avenue" and ints[0]["method"] == "auto"
    assert {i["control"] for i in ints} <= {"signal", "stop", None}


def test_round_trip_is_stable(client):
    sid, _ = setup(client, DIQ)
    once = client.get(f"/api/studies/{sid}/context").json()
    sid2, _ = setup(client, once)                                  # another study imports CrashIQ's export
    twice = client.get(f"/api/studies/{sid2}/context").json()
    assert twice["analysis"]["completed"].count("crashiq_profile") == 1
    assert len([h for h in twice["data_holdings"] if h["kind"] == "CCRS"]) == 2          # one per study
    assert twice["corridor"]["intersections"] == once["corridor"]["intersections"]
    assert twice["analysis"]["flags"].count(once["analysis"]["flags"][-1]) == 1
    assert twice["safety"]["locate_summary"] == once["safety"]["locate_summary"]


def test_export_without_import_starts_from_blank(client):
    sid, _ = setup(client)
    ctx = client.get(f"/api/studies/{sid}/context").json()
    assert ctx["project"]["name"] == "Crenshaw safety" and ctx["corridor"]["name"] == "Crenshaw Boulevard"
    assert ctx["provenance"]["corridor.name"]["source"] == "OSM"


def test_parse_geometry_forms():
    assert spine.parse_geometry([[1, 2], [3, 4]]) == [[1.0, 2.0], [3.0, 4.0]]
    assert spine.parse_geometry('{"type": "LineString", "coordinates": [[2, 1], [4, 3]]}') == [[1, 2], [3, 4]]
    assert spine.parse_geometry("s3://bucket/corridor.shp") is None
