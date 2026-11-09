"""Iowa DOT crash reader (backend/crashiq/sources/ia_dot.py), offline, on real Merle Hay Rd rows (fixture)."""
import io
import json
import urllib.parse
from collections import Counter
from pathlib import Path

import pytest

from crashiq import packs
from crashiq.sources import ia_dot as ia

FX = json.loads((Path(__file__).parent / "fixtures" / "ia_dot_merle_hay.json").read_text())


def _server(calls=None, page=None):
    """A fake ArcGIS: answers each layer from the fixture, paged by OBJECTID."""
    def opener(req, timeout=None):
        q = dict(urllib.parse.parse_qsl(req.data.decode()))
        if calls is not None:
            calls.append((req.full_url, q))
        last = int(q["where"].rsplit("OBJECTID >", 1)[1].strip(" )"))
        layer = {ia.CRASH_URL: "crashes", ia.PERSON_URL: "persons", ia.VEHICLE_URL: "vehicles"}[req.full_url]
        rows = sorted((f for f in FX[layer] if f["attributes"]["OBJECTID"] > last), key=lambda f: f["attributes"]["OBJECTID"])
        return io.BytesIO(json.dumps({"features": rows[:page or ia.PAGE]}).encode())
    return opener


def test_contract_rows_pass_the_pack_checker(tmp_path):
    got = ia.fetch_contract(tuple(FX["box"]), ["19153"], [2020, 2021, 2022, 2023, 2024], tmp_path, opener=_server())
    pack = packs.get("IA")
    assert len(got["crashes"]) == len(FX["crashes"]) and not got["years_missing"]
    assert all(packs.check_crash(c, pack) == [] for c in got["crashes"])
    assert {c["county_fips"] for c in got["crashes"]} == {"19153"}            # Polk, from Iowa DOT county 77
    assert got["cleaning"]["severity_differs_from_iowa_dot"] == 0
    assert list(tmp_path.glob("ia_dot_*.json"))                                # raw pull cached


def test_severity_from_iowa_counts_and_unknown_is_u():
    recs = ia.records(FX)
    sev = Counter(r["severity"] for r in recs)
    assert sev["K"] == 1 and sev["A"] == 4 and sev["U"] > 0 and sev["C"] > 0
    for f, r in zip(FX["crashes"], recs):
        a = f["attributes"]
        assert r["severity"] in ia.CSEV[a["CSEV"]]                             # agrees with Iowa DOT's own CSEV
        if r["severity"] == "U":
            assert a["CSEV"] == 4 and a["UNKINJURY"] and not a["POSSINJURY"]
    assert ia.severity({"MAJINJURY": 1, "POSSINJURY": 2}) == "A"
    assert ia.severity({"UNKINJURY": 1}) == "U" and ia.severity({}) == "O"


def test_modes_join_persons_and_vehicles_by_crash_key():
    recs = {r["crash_id"]: r for r in ia.records(FX)}
    assert recs["20231342063"]["ped"] and recs["20231342063"]["collision_type"] == "VEHICLE/PEDESTRIAN"
    assert recs["20231373973"]["bike"] and not recs["20231373973"]["ped"]
    assert recs["20231373973"]["collision_type"] != "VEHICLE/PEDESTRIAN"     # a cyclist keeps the manner of collision
    assert sum(r["motorcycle"] for r in recs.values()) and sum(r["heavy_truck"] for r in recs.values())


def test_literal_forms():
    assert ia.split_literal("US 69 S MEASURING 45 FEET NORTH FROM MAURY ST") == {
        "form": "offset", "primary": "US 69 S", "secondary": "MAURY ST", "offset_ft": 45.0, "offset_dir": "N",
        "house_number": None, "milepost": None}
    x = ia.split_literal("US 6/MERLE HAY RD AND US 6/DOUGLAS AVE")
    assert (x["form"], x["primary"], x["secondary"]) == ("intersection", "MERLE HAY RD", "DOUGLAS AVE")
    assert ia.split_literal("JOHNSTON DR & NW BEAVER DR")["secondary"] == "NW BEAVER DR"
    assert ia.split_literal("SE DELAWARE/SE 16TH")["form"] == "intersection"
    b = ia.split_literal("1100-BLK E 1ST ST")
    assert (b["form"], b["house_number"], b["primary"]) == ("block", 1100, "E 1ST ST")
    assert ia.split_literal("5000-2200 BLOCK OF I-235 EB")["primary"] == "I-235 EB"
    m = ia.split_literal("I 80 W - 132.00MM")
    assert (m["form"], m["primary"], m["milepost"]) == ("milepost", "I 80 W", 132.0)
    assert ia.split_literal("700 9TH ST")["house_number"] == 700
    assert ia.split_literal("94MM I 35 S")["form"] == "street"
    assert ia.split_literal(None)["form"] == "none"


def test_dates_counties_and_house_numbers():
    f = next(f for f in FX["crashes"] if f["attributes"]["TIMESTR"])
    r = ia.crash_record({**f, "attributes": {**f["attributes"], "CRASH_DATE": 1717200000000, "TIMESTR": "08:18",
                                             "LITERAL": "11400 BLOCK FOREST AVE"}})
    assert (r["date"], r["hour"], r["day_of_week"]) == ("2024-06-01", 8, "Saturday")   # UTC midnight = local date
    assert r["primary_road"] == "11400 FOREST AVE" and r["secondary_road"] is None
    assert ia.county_fips(1) == "19001" and ia.county_fips(77) == "19153" and ia.county_fips(99) == "19197"
    assert ia.county_fips(0) is None and ia.county_fips(None) is None
    far = ia.crash_record({**f, "geometry": {"x": -118.2, "y": 34.0}})
    assert far["lat"] is None and far["bad_coords"]


def test_pages_by_objectid_and_box_query(tmp_path):
    calls = []
    got = ia.fetch_contract(tuple(FX["box"]), ["19153"], [2020, 2024], tmp_path, opener=_server(calls, page=40))
    crash_calls = [q for u, q in calls if u == ia.CRASH_URL]
    assert len(crash_calls) == -(-len(FX["crashes"]) // 40) + 1                  # pages + the empty one
    q = crash_calls[0]
    assert q["geometry"] == "-93.701,41.612,-93.694,41.632" and q["inSR"] == "4326" and q["outSR"] == "4326"
    assert "CRASH_DATE >= DATE '2020-01-01' AND CRASH_DATE < DATE '2025-01-01'" in q["where"]
    assert {c["year"] for c in got["crashes"]} <= {2020, 2024}               # the years between are dropped


def test_server_error_raises(tmp_path):
    with pytest.raises(RuntimeError):
        ia.fetch_contract(tuple(FX["box"]), ["19153"], [2024], tmp_path,
                          opener=lambda req, timeout=None: io.BytesIO(b'{"error": {"code": 400}}'))
