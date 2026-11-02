"""#54 part 2: the pull runs in the background with progress; one pull per study; memoized assignment."""

from __future__ import annotations

import json
import threading
import time

import pytest

from crashiq import assign, crashes
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

OSM = (FIXTURES / "overpass_crenshaw.json").read_bytes()
LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]


@pytest.fixture
def sid(client):
    client.app.state.overpass = lambda url, data, timeout: OSM
    client.app.state.ckan = FakeCkan(json.loads((FIXTURES / "ckan_crenshaw.json").read_text()))
    s = client.post("/api/studies", json={"name": "BG", "mode": "profile"}).json()["id"]
    client.put(f"/api/studies/{s}/corridor", json={"line": LINE})
    crashes._JOBS.clear()
    return s


def wait(client, sid, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = client.get(f"/api/studies/{sid}/crashes/pull/status").json()
        if st["state"] != "running":
            return st
        time.sleep(0.05)
    raise AssertionError("background pull never finished")


def test_background_pull_reports_progress_then_the_summary(client, sid):
    assert client.get(f"/api/studies/{sid}/crashes/pull/status").json() == {"state": "idle"}
    r = client.post(f"/api/studies/{sid}/crashes/pull?background=true")
    assert r.status_code == 202 and r.json()["job"]["state"] == "running"
    st = wait(client, sid)
    assert st["state"] == "done" and st["summary"]["count"] == 126 and st["summary"]["from_cache"] is False
    again = client.post(f"/api/studies/{sid}/crashes/pull?background=true")      # cached now: answered at once
    assert again.status_code == 200 and again.json()["from_cache"] is True


def test_progress_names_each_step(client, sid):
    steps = []
    gate = threading.Event()
    real = crashes.pull

    def slow_pull(study, net, ckan, progress=None, raw=None):
        def tell(step, done, total):
            steps.append(step)
            progress(step, done, total)
        out = real(study, net, ckan, tell, raw)
        gate.set()
        return out
    crashes_pull = crashes.pull
    crashes.pull = slow_pull
    try:
        client.post(f"/api/studies/{sid}/crashes/pull?background=true")
        assert gate.wait(20)
        wait(client, sid)
    finally:
        crashes.pull = crashes_pull
    assert "Crash reports 2021" in steps and any(s.startswith("Parties and injuries") for s in steps)


def test_two_requests_share_one_pull(client, sid):
    calls = []
    real = crashes.pull
    started = threading.Event()
    release = threading.Event()

    def held(study, net, ckan, progress=None, raw=None):
        calls.append(1)
        started.set()
        release.wait(10)
        return real(study, net, ckan, progress, raw)
    crashes.pull = held
    try:
        a = client.post(f"/api/studies/{sid}/crashes/pull?background=true").json()["job"]
        assert started.wait(10)
        b = client.post(f"/api/studies/{sid}/crashes/pull?background=true").json()["job"]
        assert a["started_at"] == b["started_at"]
        release.set()
        wait(client, sid)
    finally:
        crashes.pull = real
    assert calls == [1]


def test_a_failed_background_pull_says_why(client, sid):
    def down(action, params):
        raise crashes.CkanError("data.ca.gov is down")
    client.app.state.ckan = down
    client.post(f"/api/studies/{sid}/crashes/pull?background=true")
    st = wait(client, sid)
    assert st["state"] == "error" and st["status"] == 502 and "data.ca.gov" in st["error"]


def test_a_study_edited_mid_pull_is_pulled_again_not_stored_stale(client, sid):
    real = crashes.pull
    n = []

    def edit_during_first(study, net, ckan, progress=None, raw=None):
        n.append(study["from_year"])
        if len(n) == 1:      # the user changes the window while the first pull runs
            client.patch(f"/api/studies/{sid}", json={"from_year": 2023, "to_year": 2025})
        return real(study, net, ckan, progress, raw)
    crashes.pull = edit_during_first
    try:
        r = client.post(f"/api/studies/{sid}/crashes/pull").json()
    finally:
        crashes.pull = real
    assert n == [2021, 2023] and r["years"] == [2023, 2024, 2025]


def test_assignment_is_memoized_until_an_input_changes(client, sid, monkeypatch):
    client.post(f"/api/studies/{sid}/crashes/pull")
    runs = []
    real = assign.assign
    monkeypatch.setattr(assign, "assign", lambda *a, **k: runs.append(1) or real(*a, **k))
    for _ in range(3):
        assert client.get(f"/api/studies/{sid}/profile").status_code == 200
    assert len(runs) == 1
    client.patch(f"/api/studies/{sid}", json={"radius_ft": 300})
    client.get(f"/api/studies/{sid}/assignment")
    assert len(runs) == 2
