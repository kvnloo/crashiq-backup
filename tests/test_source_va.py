"""Virginia: VDOT Full Crash reader (sources/va_vdot.py), offline on a recorded fixture of 36 live rows
(Richmond City 2024 by severity and type, plus the first statewide rows with no GPS), recorded 2026-11-07."""

import io
import json
import re
from collections import Counter

from crashiq.sources import va_vdot

from conftest import FIXTURES

ROWS = [f["attributes"] for f in json.loads((FIXTURES / "va_vdot_full_crash.json").read_text())["features"]]


def test_every_row_maps_to_the_shared_shape():
    for a in ROWS:
        c = va_vdot.crash_record(a)
        assert c["collision_id"] == str(a["DOCUMENT_NBR"])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?", c["datetime"])
        assert c["severity"] in va_vdot.SEVERITY_ORDER
        assert c["secondary_road"] is None
        assert len(c["person_kabco"]) == sum(a[f"{k}_PEOPLE"] for k in "KABC")


def test_severity_matches_vdot_and_counts():
    recs = [va_vdot.crash_record(a) for a in ROWS]
    assert not [c for c in recs if c["severity_mismatch"]]
    assert {"K", "A", "B", "C", "O"} <= {c["severity"] for c in recs}
    k = next(c for c in recs if c["severity"] == "K")
    assert k["killed"] >= 1 and "K" in k["person_kabco"]
    assert va_vdot.severity({"PERSONS_INJURED": 1}) == "U"      # injured, no KABC level
    assert va_vdot.severity({"A_PEOPLE": 1, "C_PEOPLE": 2}) == "A"


def test_gps_kept_when_in_virginia_else_none():
    recs = {c["collision_id"]: c for c in map(va_vdot.crash_record, ROWS)}
    rich = [c for c in recs.values() if c["county_code"] == "127"]
    assert rich and all(c["lat"] and va_vdot.plausible(c["lat"], c["lon"]) for c in rich)
    nogps = [c for c in recs.values() if c["county_code"] != "127"]
    assert len(nogps) == 3 and all(c["lat"] is None and not c["bad_coords"] for c in nogps)
    out = va_vdot.crash_record({**ROWS[0], "LAT": 0.0, "LON": 0.0})
    assert out["lat"] is None and not out["bad_coords"]
    far = va_vdot.crash_record({**ROWS[0], "LAT": 34.0, "LON": -118.0})
    assert far["lat"] is None and far["bad_coords"]


def test_codes_jurisdiction_and_local_date():
    rich = next(a for a in ROWS if a["PHYSICAL_JURIS"] == "127")
    c = va_vdot.crash_record(rich)
    assert c["city_name"] == "Richmond City" and c["county_fips"] == "51760"
    assert va_vdot.JURIS["29"] == ("Fairfax County", "51059")
    types = Counter(va_vdot.crash_record(a)["collision_type"] for a in ROWS)
    assert not [t for t in types if t and t.startswith("code ")]
    assert va_vdot._decode(va_vdot.WEATHER, "2") == "code 2"          # unmapped code stays visible
    # 2025-03-01 local midnight arrives as 05:00 UTC; the date must not slip a day
    d = va_vdot.crash_record({**rich, "CRASH_DT": 1740805200000, "CRASH_MILITARY_TM": 245})
    assert d["datetime"] == "2025-03-01T02:45" and d["hour"] == 2 and d["year"] == 2025


def test_freeway_and_mode_flags():
    recs = [va_vdot.crash_record(a) for a in ROWS]
    assert any(c["is_freeway"] for c in recs) and any(not c["is_freeway"] for c in recs)
    ped = [c for c in recs if c["ped"]]
    assert ped and any(c["collision_type"] == "Pedestrian" for c in ped)


def test_fetch_pages_by_objectid_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(va_vdot, "PAGE", 10)
    seen = []

    def opener(req, timeout):
        last = int(re.search(r"OBJECTID%3E(\d+)", req.full_url).group(1))
        seen.append(last)
        page = [{"attributes": a} for a in ROWS if a["OBJECTID"] > last][:10]
        return io.BytesIO(json.dumps({"features": page}).encode())

    got = va_vdot.fetch("1=1", tmp_path, opener=opener)
    assert len(got) == len(ROWS) and len({c["collision_id"] for c in got}) == len(ROWS)
    assert seen[0] == 0 and len(seen) == 4                       # 36 rows: 10 + 10 + 10 + 6
    assert va_vdot.fetch("1=1", tmp_path, opener=None) == got    # second call reads the cache, no network


def test_query_error_is_raised():
    import pytest
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')
    with pytest.raises(RuntimeError):
        va_vdot.fetch("nope", None, opener=err)
