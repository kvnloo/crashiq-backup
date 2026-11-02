"""#344 (P0): a live crash pull started from the screen deadlocked. post_pull held _LOCKS_GUARD while building
ckan_for(request), and on the live path (no app.state.ckan) files_for / tiger_for / postmile_for take the same
non-reentrant lock again. Fixtures and the Tester's harness set app.state.ckan, which skips those locks, so nothing
caught it. A live-style app must answer the background pull at once and the job must start."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from crashiq import crashes
from crashiq.db import Database
from crashiq.server import create_app

from conftest import make_settings


@pytest.fixture
def live_client(tmp_path, monkeypatch):
    s = make_settings(tmp_path, ccrs_files_dir=tmp_path / "files", tiger_dir=tmp_path / "tiger",
                      postmile_dir=tmp_path / "pm", aadt_dir=tmp_path / "aadt")
    db = Database(s.db_path)

    def fake_ensure(db_, sid, ckan, refresh=False, progress=None, overpass=None):   # no network: the pull itself
        progress("Crash reports 2021", 0, 5)
        time.sleep(0.2)
        raise crashes.PullError("stub pull")
    monkeypatch.setattr(crashes, "ensure", fake_ensure)
    app = create_app(s, db)
    assert getattr(app.state, "ckan", None) is None                       # the live path: every cache lock is taken
    with TestClient(app) as c:
        yield c
    db.close()


def test_a_background_pull_on_the_live_path_answers_202_at_once_and_starts(live_client):
    sid = live_client.post("/api/studies", json={"name": "Live", "mode": "tis"}).json()["id"]
    got = {}
    t = threading.Thread(target=lambda: got.update(r=live_client.post(f"/api/studies/{sid}/crashes/pull?background=true")),
                         daemon=True)
    t0 = time.monotonic()
    t.start()
    t.join(2.0)
    assert not t.is_alive(), "POST /crashes/pull?background=true hung (deadlock on _LOCKS_GUARD)"
    assert got["r"].status_code == 202 and time.monotonic() - t0 < 2.0
    for _ in range(40):                                                   # the job leaves "Starting"
        st = live_client.get(f"/api/studies/{sid}/crashes/pull/status").json()
        if st.get("step") != "Starting":
            break
        time.sleep(0.05)
    assert st.get("step") != "Starting" and st["state"] in ("running", "error")
