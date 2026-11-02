"""Bad input to every input-taking route gets a 4xx, never a 5xx or a silent 200 (#361, from #357 condition 3)."""

import json

import pytest

from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES
from test_spine import DIQ, LINE

NO_STUDY = "no-such-study"


@pytest.fixture
def sid(client):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    return client.post("/api/studies", json={"name": "Bad input", "mode": "profile"}).json()["id"]


@pytest.mark.parametrize("method, path, body", [
    ("DELETE", "/corridor", None),
    ("DELETE", "/intersections/I1", None),
    ("GET", "/context", None),
    ("GET", "/context/prefill", None),
    ("GET", "/crashes/pull/status", None),
    ("GET", "/export.xlsx", None),
    ("GET", "/findings", None),
    ("GET", "/findings/f-0000/diagram", None),
    ("GET", "/findings/f-0000/records", None),
    ("GET", "/network", None),
    ("GET", "/profile/locations/I1", None),
    ("GET", "/review", None),
    ("GET", "/spend", None),
    ("PATCH", "/segments/S1", {"aadt": 1000}),
    ("POST", "/findings", []),
    ("POST", "/findings/screen", None),
    ("PUT", "/context", {"project": {"name": "x"}}),
    ("PUT", "/corridor", {"line": LINE}),
])
def test_an_unknown_study_is_404(client, method, path, body):
    r = client.request(method, f"/api/studies/{NO_STUDY}{path}", json=body)
    assert r.status_code == 404, (method, path, r.status_code, r.text[:200])


@pytest.mark.parametrize("method, path, body", [
    ("PUT", "/corridor", {"line": [[33.9, -118.3]]}),                   # one point
    ("PUT", "/corridor", {"line": [[95, -118.3], [33.9, -118.3]]}),     # latitude out of range
    ("PUT", "/corridor", {"line": "not a line"}),
    ("POST", "/findings", {"text": "not a list"}),
    ("POST", "/findings", [{"text": ""}]),
    ("PUT", "/context", "not an object"),
])
def test_a_bad_body_is_422(client, sid, method, path, body):
    r = client.request(method, f"/api/studies/{sid}{path}", json=body)
    assert r.status_code == 422, (method, path, r.status_code, r.text[:200])


def test_malformed_json_is_422(client, sid):
    r = client.put(f"/api/studies/{sid}/context", content=b"{not json", headers={"content-type": "application/json"})
    assert r.status_code == 422


@pytest.fixture
def pulled(client, sid):
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    client.post(f"/api/studies/{sid}/crashes/pull")
    return sid


@pytest.mark.parametrize("method, path", [
    ("DELETE", "/intersections/no-such-intersection"),
    ("GET", "/findings/no-such-finding/diagram"),
    ("GET", "/findings/no-such-finding/records"),
    ("GET", "/profile/locations/no-such-location"),
])
def test_an_unknown_id_in_a_real_study_is_404(client, pulled, method, path):
    r = client.request(method, f"/api/studies/{pulled}{path}")
    assert r.status_code == 404, (method, path, r.status_code, r.text[:200])


def test_aadt_or_a_rate_group_for_a_segment_that_doesnt_exist_is_404_and_stores_nothing(client, pulled):
    # #361: these used to return 200 and store a row for the made-up id
    assert client.patch(f"/api/studies/{pulled}/segments/no-such-segment", json={"aadt": 1000}).status_code == 404
    r = client.put(f"/api/studies/{pulled}/rate-groups/segment/no-such-segment", json={"rate_group": "H07"})
    assert r.status_code == 404
    r = client.put(f"/api/studies/{pulled}/rate-groups/intersection/no-such-intersection", json={"rate_group": "I14"})
    assert r.status_code == 404
    net = client.get(f"/api/studies/{pulled}/network").json()
    assert all(s.get("aadt") is None and s.get("rate_group") is None for s in net["segments"])
    seg = net["segments"][0]["id"]                                       # a real segment still takes both
    assert client.patch(f"/api/studies/{pulled}/segments/{seg}", json={"aadt": -5}).status_code == 422
    assert client.patch(f"/api/studies/{pulled}/segments/{seg}", json={"aadt": "lots"}).status_code == 422
    assert client.patch(f"/api/studies/{pulled}/segments/{seg}", json={"aadt": 1000}).status_code == 200
    assert client.put(f"/api/studies/{pulled}/rate-groups/segment/{seg}", json={"rate_group": "H07"}).status_code == 200


def test_context_prefill_before_and_after_an_import(client, sid):
    assert client.get(f"/api/studies/{sid}/context/prefill").json() == {"prefill": None}
    client.put(f"/api/studies/{sid}/context", json=DIQ)
    p = client.get(f"/api/studies/{sid}/context/prefill").json()["prefill"]
    assert p["name"] == "Crenshaw Blvd corridor" and p["line"] == LINE
    assert json.loads(json.dumps(p)) == p
