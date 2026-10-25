"""#248: the derived Caltrans postmile of a placed state-highway crash, from the public SHN Postmiles Tenth layer
(the Tester's source and vintage, 2026-10-24). The fixture is LA-405 and LA-107 near Artesia Blvd, as the layer's query
API returns it."""

import json

import pytest

from crashiq import postmile

from conftest import FIXTURES

PAGE = json.loads((FIXTURES / "postmiles_la405_artesia.json").read_text())


class Get:
    def __init__(self, pages):
        self.pages, self.urls = pages, []

    def __call__(self, url):
        self.urls.append(url)
        if not self.pages:
            raise OSError("down")
        return self.pages.pop(0)


@pytest.fixture
def cache(tmp_path):
    half = len(PAGE["features"]) // 2               # two pages, as the service pages its answers
    pages = [{"features": PAGE["features"][:half], "exceededTransferLimit": True}, {"features": PAGE["features"][half:]}]
    return postmile.PostmileCache(tmp_path / "pm", get=Get(pages), background=False)


def points(route, direction):
    return sorted(((f["attributes"]["PM"], f["geometry"]["y"], f["geometry"]["x"]) for f in PAGE["features"]
                   if f["attributes"]["Route"] == route and f["attributes"]["Direction"] == direction))


def test_a_published_point_returns_its_postmile(cache):
    pm, lat, lon = points("405", "NB")[10]
    got = cache.lookup(lat, lon, {"405"}, "N")
    assert abs(got["pm"] - pm) < 0.01 and got["county"] == "LA" and got["direction"] == "NB"
    assert len(cache.get.urls) == 2 and "outSR=4326" in cache.get.urls[0]          # paged, WGS84


def test_between_two_points_the_postmile_is_interpolated(cache):
    (pm1, la1, lo1), (pm2, la2, lo2) = points("405", "NB")[10:12]
    got = cache.lookup((la1 + la2) / 2, (lo1 + lo2) / 2, {"405"}, "N")
    assert abs(got["pm"] - (pm1 + pm2) / 2) < 0.01


def test_the_stated_travel_direction_picks_that_sides_points(cache):
    _, lat, lon = points("405", "SB")[10]
    assert cache.lookup(lat, lon, {"405"}, "S")["direction"] == "SB"


def test_off_the_route_or_another_route_is_no_postmile(cache):
    _, lat, lon = points("405", "NB")[10]
    assert cache.lookup(lat + 0.01, lon, {"405"}) is None                      # ~1 km away
    assert cache.lookup(lat, lon, {"91"}) is None                              # not route 91


def test_a_crash_gets_a_labelled_derived_postmile(cache):
    pm, lat, lon = points("405", "NB")[12]
    c = {"lat": lat, "lon": lon, "primary_road": "I-405 N/B (SAN DIEGO FREEWAY)", "secondary_road": "ARTESIA BLVD."}
    p = cache.for_crash(c)
    assert p["derived"] and p["label"].startswith("LA-405 PM ") and abs(float(p["label"].split()[-1]) - pm) < 0.01
    assert cache.for_crash({**c, "primary_road": "HAWTHORNE BLVD", "secondary_road": "ARTESIA BLVD"}) is None
    assert cache.for_crash({**c, "lat": None}) is None


def test_the_download_is_kept_by_date_and_a_failure_waits(tmp_path):
    c = postmile.PostmileCache(tmp_path / "pm", get=Get([]), background=False, now=lambda: 1_792_800_000)
    assert c.ready() is None and "down" in c.error()
    c.ready()
    assert len(c.get.urls) == 1                                                 # no retry within the hour
    ok = postmile.PostmileCache(tmp_path / "pm", get=Get([{"features": PAGE["features"]}]), background=False,
                                now=lambda: 1_792_800_000)
    assert ok.ready().name == "shn_postmiles_tenth_2026-10-24.sqlite"         # the download date is the vintage


class FakePM:
    """Any crash naming a state route gets a postmile (the wiring, not the lookup)."""
    def for_crash(self, c):
        from crashiq.names import route_numbers
        roads = f"{c.get('primary_road') or ''} {c.get('secondary_road') or ''}"
        if c.get("lat") is None or not route_numbers(roads):
            return None
        return {"label": "LA-405 PM 13.100", "pm": 13.1, "county": "LA", "route": "405", "route_suffix": "",
                "prefix": "", "suffix": "", "align": "Right", "direction": "NB", "distance_m": 4.0, "derived": True}


def test_the_crash_list_and_the_export_carry_the_derived_postmile(client):
    import io
    from openpyxl import load_workbook
    from crashiq.sources.fake_ckan import FakeCkan
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    t = d["tables"]["cra-2023-0000-0000"]
    live = next(r for r in t["rows"] if str(r.get("IsDeleted")).lower() not in ("true", "1"))
    t["rows"].append({**live, "Collision Id": 84000001, "Report Version": 1, "Latitude": "33.901600",
                      "Longitude": "-118.326620", "PrimaryRoad": "CRENSHAW BLVD", "SecondaryRoad": "ROSECRANS AV (SR 1)",
                      "Crash Date Time": "2023-09-01T10:00:00"})
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(d)
    client.app.state.postmiles = FakePM()
    sid = client.post("/api/studies", json={"name": "P", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9123, -118.32662]]})
    client.post(f"/api/studies/{sid}/crashes/pull")
    got = {c["crash_id"]: c for c in client.get(f"/api/studies/{sid}/crashes").json()["crashes"]}
    assert got["84000001"]["postmile"]["label"] == "LA-405 PM 13.100" and got["84000001"]["postmile"]["derived"]
    assert "postmile" not in got[next(k for k in got if k != "84000001")]           # city streets: none
    wb = load_workbook(io.BytesIO(client.get(f"/api/studies/{sid}/export.xlsx").content))
    sh = wb["State-highway postmiles"]
    assert [c.value for c in sh[3]][:4] == ["84000001", "CRENSHAW BLVD / ROSECRANS AV (SR 1)", "2023-09-01", "LA-405 PM 13.100"]


def test_fake_ckan_never_downloads_the_postmile_layer(client):
    from crashiq import crashes
    from crashiq.sources.fake_ckan import FakeCkan
    client.app.state.ckan, client.app.state.postmiles = FakeCkan(FIXTURES / "ckan_crenshaw.json"), None
    assert crashes.postmile_for(client.app.state) is None
