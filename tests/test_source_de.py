"""Delaware: DSHS Public Crash Data reader (sources/de_dshs.py), offline on a recorded fixture: 42 live 2024 rows
(Wilmington by crash class, pedestrian injury crashes, and 4 Sussex rows) from data.delaware.gov 827n-m6xc,
recorded 2026-11-08."""

import io
import json
import urllib.parse
from collections import Counter

from crashiq import packs
from crashiq.sources import de_dshs

from conftest import FIXTURES

ROWS = json.loads((FIXTURES / "de_dshs_public_crash_2024.json").read_text())


def test_every_reportable_row_maps_to_the_contract():
    pack = packs.get("DE")
    got = [de_dshs.crash_record(r) for r in ROWS]
    kept = [c for c in got if c]
    assert len(kept) == len(ROWS) - sum(r["crash_class"] == "01" for r in ROWS) == 37      # non-reportable out
    assert all(packs.check_crash(c, pack) == [] for c in kept)
    assert {c["county_fips"] for c in kept} == {"10003", "10005"}
    assert all(c["lat"] is not None and c["primary_road"] is None for c in kept)


def test_severity_is_k_u_o_from_crash_class():
    sev = Counter(c["severity"] for c in map(de_dshs.crash_record, ROWS) if c)
    assert set(sev) == {"K", "U", "O"} and sev["K"] == 6
    assert de_dshs.crash_record({**ROWS[0], "crash_class": "NA"}) is None


def test_local_time_from_utc():
    c = de_dshs.crash_record({**ROWS[0], "crash_class": "02", "crash_datetime": "2024-02-01T16:55:00.000Z"})
    assert (c["date"], c["hour"], c["year"]) == ("2024-02-01", 11, 2024)      # FirstMap CRASH_TIME 1155
    c = de_dshs.crash_record({**ROWS[0], "crash_class": "02", "crash_datetime": "2025-01-01T03:10:00.000Z"})
    assert (c["date"], c["year"]) == ("2024-12-31", 2024)                    # New Year's Eve, local


def test_codes_and_flags():
    got = [c for c in map(de_dshs.crash_record, ROWS) if c]
    assert any(c["ped"] and c["collision_type"] == "VEHICLE/PEDESTRIAN" for c in got)
    assert {"REAR END", "BROADSIDE", "SIDE SWIPE"} <= {c["collision_type"] for c in got}
    assert all(c["lighting"] in set(de_dshs.LIGHT.values()) | {None} for c in got)
    far = de_dshs.crash_record({**ROWS[0], "crash_class": "02", "latitude": "34.0", "longitude": "-118.0"})
    assert far["lat"] is None and far["bad_coords"]


def test_fetch_contract_pages_queries_the_box_and_caches(tmp_path, monkeypatch):
    seen = []

    def opener(req, timeout):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(req.full_url).query))
        seen.append(q)
        assert req.headers["User-agent"] == "CrashIQ/0.1"
        return io.BytesIO(json.dumps(ROWS[int(q["$offset"]):int(q["$offset"]) + int(q["$limit"])]).encode())

    monkeypatch.setattr(de_dshs, "PAGE", 20)
    box = (39.70, -75.60, 39.78, -75.50)
    got = de_dshs.fetch_contract(box, ["10003"], [2023, 2024], tmp_path, opener=opener)
    assert [q["$offset"] for q in seen] == ["0", "20", "40"]
    assert "latitude >= 39.700000" in seen[0]["$where"] and "year IN ('2023', '2024')" in seen[0]["$where"]
    assert len(got["crashes"]) == 37 and got["cleaning"]["non_reportable_left_out"] == 5
    assert got["years_missing"] == [2023]
    again = de_dshs.fetch_contract(box, ["10003"], [2023, 2024], tmp_path, opener=None)    # cached: no network
    assert len(again["crashes"]) == 37


def test_pack_is_registered_and_its_methods_are_cited():
    pack = packs.get("DE")
    assert pack.status == "active" and pack.severity_note
    assert packs.value(pack, "crash_costs") is None and "FHWA" in packs.why_missing(pack, "crash_costs")
    assert set(json.loads(pack.county_boxes.read_text())["counties"]) == {"10001", "10003", "10005"}
