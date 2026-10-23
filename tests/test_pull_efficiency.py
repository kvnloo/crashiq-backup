"""#54 part 1: fewer calls per pull, cache expiry, Overpass back-off."""

from __future__ import annotations

import json
import urllib.error
from collections import Counter
from datetime import datetime, timezone

from crashiq import crashes, network
from crashiq.sources import ckan as ckan_mod
from crashiq.sources.ckan import Ckan
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LIVE = FIXTURES / "live"
STUDY = {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}


def crenshaw_net():
    line = [tuple(p) for p in json.loads((LIVE / "line_crenshaw.json").read_text())]
    found = network.detect(json.loads((LIVE / "overpass_crenshaw.json").read_text()), line)
    return {"line": line, **found, "intersections": [{**i, "is_study": True} for i in found["intersections"]]}


def counted_pull():
    fake, calls = FakeCkan(LIVE / "ckan_crenshaw.json"), Counter()

    def t(action, params):
        calls[action] += 1
        if action == "datastore_search_sql" and "\"CollisionId\" IN (" in params["sql"]:
            calls["id_lookups"] += 1
        return fake(action, params)
    return crashes.pull(STUDY, crenshaw_net(), Ckan(t, retries=0)), calls


def test_excluded_reports_get_no_party_or_injury_lookups():
    out, calls = counted_pull()
    excluded = [c for c in out["crashes"] if c.get("exclude_rule")]
    assert excluded and all(c["severity"] is None and c["details"] == "not_looked_up" for c in excluded)
    # 5 years x (Parties + IWP), at most one 500-id batch each for ~320 counted crashes; was 24 lookups of 150
    assert calls["id_lookups"] <= 10
    assert calls["datastore_search_sql"] <= 30        # + the street-name area query, up to one per year (#111)
    # + the name query for reports whose GPS is a default point or coarse, one per year (#218)


def test_gps_rows_far_from_a_diagonal_line_stop_before_the_lookups():
    out, _ = counted_pull()
    assert out["cleaning"]["gps_beyond_margin_dropped"] == 4
    margin = crashes.margin_ft(STUDY)
    from crashiq.geo import Polyline
    line = Polyline(crenshaw_net()["line"])
    assert all(line.project(c["lat"], c["lon"]).offset_ft <= margin
               for c in out["crashes"] if c["location_source"] == "gps")


def test_live_metadata_is_cached_per_process(monkeypatch):
    seen = Counter()

    def fake_http(action, params, timeout=120):
        seen[action] += 1
        return {"resources": []} if action == "package_show" else {"fields": [], "records": []}
    monkeypatch.setattr(ckan_mod, "http_transport", fake_http)
    monkeypatch.setattr(ckan_mod, "_META_CACHE", {})
    for _ in range(3):
        k = Ckan()
        k.get("package_show", id="x")
        k.fields("r1")
        k.get("datastore_search_sql", sql="SELECT 1")
    assert seen == {"package_show": 1, "datastore_search": 1, "datastore_search_sql": 3}   # SQL never cached


def test_recent_windows_expire_old_ones_do_not():
    now = datetime(2026, 10, 19, tzinfo=timezone.utc)
    old = {"pulled_at": "2026-09-01T00:00:00+00:00"}
    fresh = {"pulled_at": "2026-10-10T00:00:00+00:00"}
    assert crashes.stale(old, {"to_year": 2025}, now) and not crashes.stale(fresh, {"to_year": 2025}, now)
    assert not crashes.stale(old, {"to_year": 2020}, now)                     # final years never change


def test_overpass_honours_retry_after_and_falls_back_to_an_old_map(db):
    q = "q"
    db.execute("INSERT INTO http_cache (key, source, body, created_at) VALUES (?, 'overpass', ?, '2020-01-01 00:00:00')",
               ("overpass:" + __import__("hashlib").sha1(q.encode()).hexdigest(), json.dumps({"elements": [1]})))
    waits = []

    def busy(url, data, timeout):
        raise urllib.error.HTTPError(url, 429, "Too Many Requests", {"Retry-After": "7"}, None)
    got = network.fetch_overpass(db, q, transport=busy, retries=1, sleep=waits.append)
    assert waits == [7.0] and got == {"elements": [1]}                         # stale map, after waiting as told


def test_id_lookups_stay_under_the_url_limit():
    # #113: 500 ids with the full column list made a URL too long for data.ca.gov (HTTP 414, Pasadena)
    import urllib.parse
    seen = []

    class Rec:
        def sql_page(self, sql):
            seen.append(len(urllib.parse.quote(sql)))
            return [], False
    cols = {"collision_id": {"id": "CollisionId", "type": "numeric"},
            **{f"c{i}": {"id": f"SomeLongColumnName{i}", "type": "text"} for i in range(25)}}
    crashes._by_ids(Rec(), "rid-0000", cols, [str(4000000 + i) for i in range(1200)])
    assert seen and max(seen) <= crashes.MAX_URL_SQL and len(seen) > 3
