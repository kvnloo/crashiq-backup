"""#229: the TIGER/Line county cache, and a pull on the OSM + TIGER network: a report naming the cross street by a
name only TIGER has is kept, placed and tagged; the network is logged; a county still downloading leaves OSM alone."""

import io
import json
import zipfile

import pytest

from crashiq.sources import tiger_files
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]


@pytest.fixture
def union_on(monkeypatch):
    """The union is switched off since run 9 (#243); these tests exercise it switched on."""
    from crashiq import union
    monkeypatch.setitem(union.CONFIG, "union", True)


def _zip(name: str, writer_fn) -> bytes:
    """A TIGER-shaped zip (shapefile parts) written with pyshp."""
    shapefile = pytest.importorskip("shapefile")
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf)
    writer_fn(w)
    w.close()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for ext, buf in ((".shp", shp), (".shx", shx), (".dbf", dbf)):
            z.writestr(name + ext, buf.getvalue())
    return out.getvalue()


def _edges(segments):
    def fn(w):
        w.shapeType = 3                                          # polyline
        for f, t, size in (("TLID", "N", 10), ("TNIDF", "N", 10), ("TNIDT", "N", 10), ("MTFCC", "C", 5),
                           ("FULLNAME", "C", 100)):
            w.field(f, t, size)
        for tlid, f, t, mtfcc, name, pts in segments:
            w.line([[(lon, lat) for lat, lon in pts]])
            w.record(tlid, f, t, mtfcc, name)
    return _zip("tl_2026_06037_edges", fn)


def _featnames(rows):
    def fn(w):
        w.shapeType = 0
        w.field("TLID", "N", 10)
        w.field("FULLNAME", "C", 100)
        for tlid, name in rows:
            w.null()
            w.record(tlid, name)
    return _zip("tl_2026_06037_featnames", fn)


# TIGER's West 135th Street, along OSM's, also called Hawthorne Plaza Drive; a stream (H-class) that's left out
SEGMENTS = [(7001, 1, 2, "S1400", "W 135th St", [(33.90931, -118.3290), (33.90931, -118.3240)]),
            (7002, 3, 4, "H3010", "Dominguez Channel", [(33.905, -118.33), (33.906, -118.32)])]
FEAT = [(7001, "Hawthorne Plaza Dr"), (7001, "W 135th St")]


class Opener:
    def __init__(self, files):
        self.files, self.urls = files, []

    def __call__(self, url):
        self.urls.append(url)
        for k, v in self.files.items():
            if url.endswith(k):
                return io.BytesIO(v)
        raise OSError("404 " + url)


def _cache(tmp_path, ok=True):
    files = {"_edges.zip": _edges(SEGMENTS), "_featnames.zip": _featnames(FEAT)} if ok else {}
    return tiger_files.TigerCache(tmp_path / "tiger", vintage=2026, opener=Opener(files), background=False)


def test_a_county_downloads_once_into_a_trimmed_copy(tmp_path):
    tc = _cache(tmp_path)
    assert tiger_files.counties_for([(33.9, -118.33)]) == ["037"]                   # Hawthorne: Los Angeles County
    assert tc.ready("037") and tc.path("037") == tmp_path / "tiger" / "2026" / "037.sqlite"
    assert tc.opener.urls == ["https://www2.census.gov/geo/tiger/TIGER2026/EDGES/tl_2026_06037_edges.zip",
                              "https://www2.census.gov/geo/tiger/TIGER2026/FEATNAMES/tl_2026_06037_featnames.zip"]
    edges = tc.edges_in("037", (33.90, -118.34, 33.92, -118.31))
    assert [e["tlid"] for e in edges] == [7001]                                     # roads only
    assert edges[0]["names"] == ["W 135th St", "Hawthorne Plaza Dr"]
    tc.ready("037")
    assert len(tc.opener.urls) == 2                                                 # not again


def test_a_failed_download_leaves_no_copy_and_waits_an_hour(tmp_path):
    tc = _cache(tmp_path, ok=False)
    assert not tc.ready("037") and "404" in tc.error("037")
    assert not list((tmp_path / "tiger" / "2026").glob("*"))
    tc.ready("037")
    assert len(tc.opener.urls) == 1                                                 # no retry within the hour


def _pull(client, tiger, extra_rows=()):
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    t = d["tables"]["cra-2023-0000-0000"]
    live = next(r for r in t["rows"] if str(r.get("IsDeleted")).lower() not in ("true", "1"))
    for i, (pr, sr) in enumerate(extra_rows):
        t["rows"].append({**live, "Collision Id": 87000001 + i, "Report Version": 1, "Latitude": "", "Longitude": "",
                          "PrimaryRoad": pr, "SecondaryRoad": sr, "SecondaryDistance": "0",
                          "Crash Date Time": f"2023-07-0{1 + i}T10:00:00"})
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(d)
    client.app.state.tiger = tiger
    sid = client.post("/api/studies", json={"name": "T", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    log = client.post(f"/api/studies/{sid}/crashes/pull").json()["cleaning"]
    got = {c["crash_id"]: c for c in client.get(f"/api/studies/{sid}/crashes?full=true").json()["crashes"]}
    asg = {a["crash_id"]: a for a in client.get(f"/api/studies/{sid}/assignment").json()["assignments"]}
    return log, got, asg


def test_a_cross_street_named_as_only_tiger_names_it_is_kept_and_placed(client, tmp_path, union_on):
    rows = [("CRENSHAW BLVD", "HAWTHORNE PLAZA DR")]
    log, got, asg = _pull(client, None, rows)                                       # OSM only: off the stretch
    assert got["87000001"].get("exclude_rule") == "cross_street_not_on_corridor"
    log, got, asg = _pull(client, _cache(tmp_path), rows)
    c = got["87000001"]
    assert not c.get("exclude_rule") and c["location_source"] in ("exact", "unique_pair")
    assert c["placed_on"] == "tiger"                                                # the visible tag
    assert asg["87000001"]["kind"] == "intersection" and asg["87000001"]["location_id"] == "osm-1029"
    assert log["network"]["sources"] == ["osm", "tiger"] and log["network"]["tiger_counties"] == ["037"]
    assert log["network"]["coincide_with_osm"] == 1 and log["network"].get("added_from_tiger", 0) == 0


def test_a_county_still_downloading_leaves_the_network_osm_only(client, tmp_path, union_on):
    tc = tiger_files.TigerCache(tmp_path / "tiger", vintage=2026, opener=Opener({}), background=True)
    tc._start = lambda fips: None                                                   # "downloading"
    log, got, _ = _pull(client, tc, [("CRENSHAW BLVD", "HAWTHORNE PLAZA DR")])
    assert log["network"]["sources"] == ["osm"]
    assert log["network"]["tiger_pending"] == {"tiger_2026_037": str(tc.path("037"))}
    assert log["files_pending"]["tiger_2026_037"]                                  # the next view pulls again
    assert got["87000001"].get("exclude_rule") == "cross_street_not_on_corridor"


def test_fake_ckan_never_downloads_tiger(client):
    from crashiq import crashes
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    client.app.state.tiger = None
    assert crashes.tiger_for(client.app.state) is None


def test_switched_off_the_network_is_osm_only_and_nothing_downloads(client, tmp_path, monkeypatch):
    # #243 switched it off; the user turned it on statewide 2026-10-24 (#255). The switch still works
    from crashiq import crashes, union
    assert union.enabled() is True
    monkeypatch.setitem(union.CONFIG, "union", False)
    tc = _cache(tmp_path)
    log, got, _ = _pull(client, tc, [("CRENSHAW BLVD", "HAWTHORNE PLAZA DR")])
    assert "network" not in log or log["network"]["sources"] == ["osm"]
    assert got["87000001"].get("exclude_rule") == "cross_street_not_on_corridor"      # TIGER's name not used
    assert tc.opener.urls == []                                                       # nothing downloaded
    client.app.state.ckan, client.app.state.tiger = None, None
    assert crashes.tiger_for(client.app.state) is None
