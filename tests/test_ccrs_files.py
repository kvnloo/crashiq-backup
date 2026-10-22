"""#196: a CCRS Parties / IWP year that data.ca.gov publishes as a file but not in its datastore (Parties_2025) is
downloaded once, kept column-trimmed, and read from that copy; the #189 caveat clears. Refresh at most weekly;
a failed download keeps the caveat and never fails the pull."""

import csv
import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from crashiq import crashes
from crashiq.sources import ccrs_files
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]
RID = "par-2025-0000-0000"


def _fixture(inactive=True, last_modified="2026-10-22T02:08:49"):
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    res = next(r for r in d["package"]["resources"] if r["id"] == RID)
    if inactive:
        res.update(datastore_active=False, format="CSV", last_modified=last_modified,
                   url="https://publish.data.ca.gov/x/parties_2025.csv")
        d["package"]["resources"].append({"id": "docx", "name": "Raw Data Template", "format": "DOCX",
                                          "datastore_active": False, "url": "https://x/t.docx"})
    return d


def _csv(d) -> bytes:
    """The datastore table written the way CHP's file is: every column, text, header with stray spaces."""
    t = d["tables"][RID]
    names = [f["id"] for f in t["fields"]]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["PartyId"] + [f" {n}" if n.startswith("Vehicle") else n for n in names] + ["Lane"])
    for i, r in enumerate(t["rows"]):
        w.writerow([i] + ["" if r.get(n) is None else r[n] for n in names] + ["1"])
    return ("﻿" + out.getvalue()).encode()


class Opener:
    def __init__(self, body: bytes | None):
        self.body, self.calls = body, 0

    def __call__(self, url):
        self.calls += 1
        if self.body is None:
            raise OSError("network down")
        return io.BytesIO(self.body)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 22, 12, tzinfo=timezone.utc).timestamp()

    def __call__(self):
        return self.t


def _study(client, d, files=None):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(d)
    client.app.state.ccrs_files = files
    sid = client.post("/api/studies", json={"name": "M", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    pull = client.post(f"/api/studies/{sid}/crashes/pull").json()
    return sid, pull


def _cache(tmp_path, body, clock=None):
    return ccrs_files.FileCache(tmp_path / "files", opener=Opener(body), now=clock or Clock(), background=False)


def test_a_year_only_in_a_file_is_read_from_the_copy_and_the_caveat_clears(client, tmp_path):
    live = _fixture(inactive=False)
    sid0, _ = _study(client, live)
    want = client.get(f"/api/studies/{sid0}/profile").json()

    fc = _cache(tmp_path, _csv(live))
    sid, pull = _study(client, _fixture(), fc)
    assert pull["cleaning"]["parties_source"]["2025"] == "file_cache (2026-10-22)"
    assert pull["cleaning"]["parties_source"]["2024"] == "datastore"
    assert pull["cleaning"]["parties_missing_years"] == [] and not pull["cleaning"]["files_pending"]
    got = client.get(f"/api/studies/{sid}/profile").json()
    assert not {c["key"] for c in got["caveats"]} & {"parties_missing", "iwp_missing"}
    assert [t["rows"] for t in got["tables"]] == [t["rows"] for t in want["tables"]]     # same tables as the datastore
    assert fc.opener.calls == 1

    # only the columns CrashIQ reads are kept, indexed by Collision Id
    con = sqlite3.connect(fc.path(RID))
    cols = [r[1] for r in con.execute("PRAGMA table_info(rows)")]
    assert "collision_id" in cols and "party_type" in cols and "Lane" not in cols and "PartyId" not in cols
    assert con.execute("SELECT COUNT(*) FROM rows").fetchone()[0] == len(live["tables"][RID]["rows"])


def test_failed_download_keeps_the_caveat_and_the_pull_completes(client, tmp_path):
    clock = Clock()
    fc = _cache(tmp_path, None, clock)
    sid, pull = _study(client, _fixture(), fc)
    cl = pull["cleaning"]
    assert cl["parties_missing_years"] == [2025] and "parties_2025" in cl["files_pending"]
    assert "network down" in cl["file_errors"]["parties_2025"]
    cav = next(c for c in client.get(f"/api/studies/{sid}/profile").json()["caveats"] if c["key"] == "parties_missing")
    assert "2025" in cav["text"] and "downloading" in cav["text"]
    assert not list((tmp_path / "files").glob("*"))                   # no half-written copy left behind

    # not retried within the hour; retried after it, and the next pull reads the copy
    res = ccrs_files.inactive_resources(_fixture()["package"])["parties"][2025]
    fc.opener.body = _csv(_fixture(inactive=False))
    clock.t += 30 * 60
    assert fc.ready(res, crashes.cc.PARTY_COLS) is None and fc.opener.calls == 1
    clock.t += 31 * 60
    assert fc.ready(res, crashes.cc.PARTY_COLS) and fc.opener.calls == 2


def test_a_pull_waiting_for_a_file_goes_stale_when_the_file_arrives(tmp_path):
    study = {"to_year": datetime.now(timezone.utc).year - 1}
    now = datetime.now(timezone.utc).isoformat()
    p = tmp_path / "x.sqlite"
    cached = {"pulled_at": now, "cleaning": {"parties_missing_years": [2025], "files_pending": {"parties_2025": str(p)}}}
    assert not crashes.stale(cached, study)
    p.write_bytes(b"")
    assert crashes.stale(cached, study)


def test_refresh_at_most_weekly_and_only_for_a_newer_file(tmp_path):
    clock = Clock()
    body = _csv(_fixture(inactive=False))
    fc = _cache(tmp_path, body, clock)
    pkg = _fixture()["package"]
    res = ccrs_files.inactive_resources(pkg)["parties"][2025]
    assert fc.ready(res, crashes.cc.PARTY_COLS)["last_modified"] == res["last_modified"]
    newer = {**res, "last_modified": "2026-10-23T02:00:00"}
    clock.t += 6 * 86400
    fc.ready(newer, crashes.cc.PARTY_COLS)
    assert fc.opener.calls == 1                                      # CHP re-dates the file daily: not yet
    clock.t += 1 * 86400
    fc.ready(res, crashes.cc.PARTY_COLS)
    assert fc.opener.calls == 1                                      # a week old but the same file: kept
    m = fc.ready(newer, crashes.cc.PARTY_COLS)
    assert fc.opener.calls == 2 and m["last_modified"] == "2026-10-22T02:08:49"   # old copy answered this call
    assert fc.meta(RID)["last_modified"] == "2026-10-23T02:00:00"


def test_only_csv_tables_count_and_fake_ckan_never_downloads(client):
    inact = ccrs_files.inactive_resources(_fixture()["package"])
    assert list(inact["parties"]) == [2025] and not inact["iwp"]
    client.app.state.ckan = FakeCkan(_fixture())
    assert crashes.files_for(client.app.state) is None             # no app.state.ccrs_files: nothing is fetched


def test_live_ckan_gets_one_file_cache_in_the_settings_folder(client, tmp_path):
    st = client.app.state
    st.ckan, st.ccrs_files = None, None
    a, b = crashes.files_for(st), crashes.files_for(st)
    assert a is b and a.folder == st.settings.ccrs_files_dir
    assert (timedelta(days=ccrs_files.REFRESH_DAYS), ccrs_files.RETRY_MINUTES) == (timedelta(days=7), 60)
