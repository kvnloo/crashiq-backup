"""Corridor detection as a background job: behind the Cloudflare Tunnel a request is cut at 100 s, and a slow Overpass
day (4 attempts x 120 s) went past it. PUT ?background=true answers at once; the screen polls .../corridor/status."""

from __future__ import annotations

import threading
import time
import urllib.error

import pytest

from crashiq import network

from conftest import FIXTURES

OSM = (FIXTURES / "overpass_crenshaw.json").read_bytes()
LINE = [[33.8953, -118.32662], [33.9040, -118.32662], [33.9123, -118.32662]]


class FlakyOverpass:
    """Blocks the first call until released, fails the first `fails` street calls, then answers. Driveways: empty."""

    def __init__(self, fails=2):
        self.fails, self.calls, self.release = fails, 0, threading.Event()

    def __call__(self, url, data, timeout):
        if b"service" in data:                       # the driveway query (#413)
            return b'{"elements": []}'
        self.calls += 1
        if self.calls == 1:
            assert self.release.wait(10)
        if self.calls <= self.fails:
            raise urllib.error.URLError("timed out")
        return OSM


@pytest.fixture
def sid(client):
    client.app.state.overpass_backoff = 0.0
    network._JOBS.clear()
    return client.post("/api/studies", json={"name": "Job", "mode": "profile"}).json()["id"]


def status(client, sid):
    return client.get(f"/api/studies/{sid}/corridor/status").json()


def wait(client, sid, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = status(client, sid)
        if st["state"] != "running":
            return st
        time.sleep(0.05)
    raise AssertionError("corridor job never finished")


def test_slow_overpass_never_holds_the_request_and_the_status_counts_attempts(client, sid):
    fake = client.app.state.overpass = FlakyOverpass(fails=2)
    assert status(client, sid) == {"state": "idle"}
    t0 = time.time()
    r = client.put(f"/api/studies/{sid}/corridor?background=true", json={"line": LINE})
    assert time.time() - t0 < 5                       # the network is still blocked: the handler didn't wait on it
    assert r.status_code == 202 and r.json()["job"]["state"] == "running"
    st = status(client, sid)
    assert st["state"] == "running" and st["attempt"] == 1 and st["attempts"] == 4 and st["line"] == LINE
    joined = client.put(f"/api/studies/{sid}/corridor?background=true", json={"line": LINE}).json()["job"]
    assert joined["started_at"] == st["started_at"]   # the same line joins the running job
    fake.release.set()
    st = wait(client, sid)
    assert st["state"] == "done" and st["attempt"] == 3 and fake.calls == 3
    assert st["network"]["intersections"] and st["network"]["line"] == LINE
    assert client.get(f"/api/studies/{sid}/network").json()["line"] == LINE
    # seen before: the cache answers in the request, no job
    again = client.put(f"/api/studies/{sid}/corridor?background=true", json={"line": LINE})
    assert again.status_code == 200 and again.json()["line"] == LINE and fake.calls == 3


def test_an_error_names_the_last_failure_and_try_again_starts_a_new_job(client, sid):
    fake = client.app.state.overpass = FlakyOverpass(fails=2)
    client.app.state.overpass_retries = 1            # 2 attempts, both fail
    fake.release.set()
    assert client.put(f"/api/studies/{sid}/corridor?background=true", json={"line": LINE}).status_code == 202
    st = wait(client, sid)
    assert st["state"] == "error" and st["status"] == 502 and "OpenStreetMap" in st["error"]
    assert st["attempt"] == 2 and st["attempts"] == 2
    assert client.get(f"/api/studies/{sid}/network").json().get("line") is None
    client.app.state.overpass_retries = 3             # Try again: a new job, which now gets an answer
    r = client.put(f"/api/studies/{sid}/corridor?background=true", json={"line": LINE})
    assert r.status_code in (200, 202)               # an answer within the first second comes back in the request
    assert wait(client, sid)["state"] == "done" and fake.calls == 3


def test_bad_lines_are_still_refused_in_the_request(client, sid):
    r = client.put(f"/api/studies/{sid}/corridor?background=true", json={"line": [[33.45, -112.07], [33.46, -112.07]]})
    assert r.status_code == 400 and status(client, sid) == {"state": "idle"}


def test_clearing_the_line_mid_detection_cancels_it(client, sid):
    """Review on #489: Clear line while a detection ran brought the cleared corridor back when the job finished."""
    fake = client.app.state.overpass = FlakyOverpass(fails=0)
    assert client.put(f"/api/studies/{sid}/corridor?background=true", json={"line": LINE}).status_code == 202
    assert client.delete(f"/api/studies/{sid}/corridor").status_code == 200
    fake.release.set()
    time.sleep(0.5)
    assert status(client, sid) == {"state": "idle"}
    assert not client.get(f"/api/studies/{sid}/network").json().get("line")
