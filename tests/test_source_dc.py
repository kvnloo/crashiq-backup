"""DC 'Crashes in DC' reader (backend/crashiq/sources/dc_crashes.py), offline, on real 2025 rows (fixture)."""
import io
import json
import urllib.parse
from collections import Counter
from pathlib import Path

import pytest

from crashiq.sources import dc_crashes as dc

FX = json.loads((Path(__file__).parent / "fixtures" / "dc_crashes_2025.json").read_text())
SHARED_KEYS = {"collision_id", "datetime", "lat", "lon", "primary_road", "secondary_road", "sec_distance",
               "sec_direction", "city_name", "county_code", "killed", "injured", "collision_type", "lighting",
               "weather", "surface", "is_freeway", "severity", "persons"}


@pytest.fixture(scope="module")
def recs():
    return dc.records(FX["crashes"], FX["persons"])


def test_shape_and_link(recs):
    assert len(recs) == len(FX["crashes"])
    assert all(SHARED_KEYS <= set(r) for r in recs)
    assert sum(len(r["persons"]) for r in recs) == len(FX["persons"])   # every person row joins on CRIMEID
    assert all(dc.plausible(r["lat"], r["lon"]) and r["location_source"] == "police_gps" for r in recs)
    assert all(r["severity"] in dc.SEVERITY_ORDER for r in recs)
    assert all(p["kabco"] in (None, "K", "A", "B") for r in recs for p in r["persons"])


def test_severity_from_flags(recs):
    sev = Counter(r["severity"] for r in recs)
    assert sev["K"] >= 1 and sev["A"] >= 1 and sev["B"] >= 1 and sev["C"] == 0
    for r in recs:
        if r["killed"]:
            assert r["severity"] == "K"
        elif r["injured"] == 0:
            assert r["severity"] == "O"
    assert dc.kabco({"FATAL": "N", "MAJORINJURY": "Y", "MINORINJURY": "Y"}) == "A"
    assert dc.kabco({"FATAL": "N", "MAJORINJURY": "N", "MINORINJURY": "N"}) is None
    # a crash count with no matching person row still sets the level; unknown-level injuries are U
    assert dc.severity({"MAJORINJURIESPASSENGER": 1}, []) == "A"
    assert dc.severity({"UNKNOWNINJURIES_DRIVER": 1}, []) == "U"
    assert dc.severity({}, []) == "O"


def test_address_forms():
    assert dc.split_address("FLORIDA AVENUE NE & NEW YORK AVENUE NE\nWASHINGTON,") == {
        "form": "intersection", "primary": "FLORIDA AVENUE NE", "secondary": "NEW YORK AVENUE NE", "house_number": None}
    assert dc.split_address("16461/2 NEW JERSEY AVENUE NW")["house_number"] == 1646
    assert dc.split_address("38.9, -77.0")["form"] == "coords"
    assert dc.split_address("INTERSTATE 695 INTERSTATE BN\nWASHINGTON,")["form"] == "street"


def test_house_address_gets_ddot_cross_street_in_feet(recs):
    r = next(r for r in recs if r["collision_id"] == "64836886772")   # 2300 NEW YORK AVENUE NE
    assert (r["primary_road"], r["house_number"], r["secondary_road"]) == ("NEW YORK AVENUE NE", 2300, "BLADENSBURG RD NE")
    assert r["secondary_from_ddot"] and r["sec_direction"] == "E"
    raw = next(c for c in FX["crashes"] if c["CRIMEID"] == "64836886772")
    assert r["sec_distance"] == pytest.approx(raw["OFFINTERSECTION"] * 3.28084, abs=0.1)
    ix = next(r for r in recs if r["address_form"] == "intersection")
    assert not ix["secondary_from_ddot"] and ix["sec_distance"] is None


def test_time_and_location_fallback():
    base = dict(FX["crashes"][0])
    t = dc.crash_record({**base, "REPORTDATE": 1748764800000})        # 2025-06-01 08:00 UTC
    assert (t["date"], t["hour"]) == ("2025-06-01", 4)                 # EDT
    t = dc.crash_record({**base, "REPORTDATE": 1748750400000})        # 04:00 UTC = local midnight: time unknown
    assert t["hour"] is None and t["date"] == "2025-06-01"
    assert dc.crash_record({**base, "REPORTDATE": -4573000000000})["year"] is None   # the layer's 1825 dates
    g = dc.crash_record({**base, "MPDLATITUDE": 0.0, "MPDLONGITUDE": 0.0})
    assert g["location_source"] == "ddot_geocode" and (g["lat"], g["lon"]) == (base["LATITUDE"], base["LONGITUDE"])
    assert not g["bad_coords"]                                          # 0/0 is missing, not wrong
    assert dc.crash_record({**base, "MPDLATITUDE": 40.7, "MPDLONGITUDE": -74.0})["bad_coords"]


def test_fetch_pages_and_links_offline():
    """fetch() pages crashes by OBJECTID and asks for persons by CRIMEID, against a fake server."""
    crashes = sorted(FX["crashes"], key=lambda c: c["OBJECTID"])
    calls = []

    def opener(req, timeout=None):
        q = dict(urllib.parse.parse_qsl(req.data.decode()))
        calls.append((req.full_url, q["where"]))
        last = int(q["where"].rsplit("OBJECTID >", 1)[1])
        if req.full_url == dc.CRASH_URL:
            rows = [c for c in crashes if c["OBJECTID"] > last][:40]
        else:
            ids = set(q["where"].split("IN (")[1].split(")")[0].replace("'", "").split(","))
            rows = sorted((p for p in FX["persons"] if p["CRIMEID"] in ids and p["OBJECTID"] > last),
                          key=lambda p: p["OBJECTID"])[:dc.PAGE]
        return io.BytesIO(json.dumps({"features": [{"attributes": r} for r in rows]}).encode())

    recs = dc.fetch(2025, opener=opener)
    assert len(recs) == len(crashes) and sum(len(r["persons"]) for r in recs) == len(FX["persons"])
    assert sum(u == dc.CRASH_URL for u, _ in calls) == -(-len(crashes) // 40) + 1   # pages + the empty one
    assert "date '2025-01-01'" in calls[0][1]


def test_server_error_raises():
    opener = lambda req, timeout=None: io.BytesIO(b'{"error": {"code": 400}}')
    with pytest.raises(RuntimeError):
        dc.fetch(2025, opener=opener)
