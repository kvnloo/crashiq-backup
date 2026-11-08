"""Alaska: DOT&PF Public Crash Portal reader (sources/ak_dotpf.py), offline on a recorded fixture: 37 live 2024 rows of
the portal's CSV feed (Anchorage by KABCO level, pedestrian and Interstate rows, three crashes with no point, rows
from the portal's 'Unorganized Borough', moose hits), recorded 2026-11-08."""

import csv
import io
import json
from collections import Counter
from datetime import date

from crashiq import packs, study
from crashiq.sources import ak_dotpf

from conftest import FIXTURES

CSV = (FIXTURES / "ak_dotpf_2024_sample.csv").read_bytes()


def _rows():
    return list(csv.DictReader(io.StringIO(CSV.decode("utf-8-sig"))))


def test_every_row_maps_to_the_contract():
    pack = packs.get("AK")
    crashes = [ak_dotpf.contract_record(r) for r in _rows()]
    assert len(crashes) == 37
    assert all(packs.check_crash(c, pack) == [] for c in crashes if c["county_fips"])
    assert Counter(c["severity"] for c in crashes) == {"O": 21, "C": 6, "B": 5, "A": 3, "K": 2}
    assert sum(c["lat"] is None for c in crashes) == 3                      # the portal's 0/0
    assert all(c["primary_road"] is None and c["killed"] == 0 for c in crashes)


def test_borough_fips_and_codes():
    crashes = {c["crash_id"]: c for c in map(ak_dotpf.contract_record, _rows())}
    assert Counter(c["county_fips"] for c in crashes.values()) == {"02020": 29, "02170": 3, "02063": 2, "02180": 1,
                                                                   None: 2}
    assert crashes["202400002"]["county_fips"] == "02063"       # 'Unorganized Borough' near Valdez -> Chugach
    assert crashes["202400223"]["county_fips"] is None          # unorganized, no point: no county
    k = crashes["202402940"]
    assert (k["severity"], k["ped"], k["collision_type"], k["city"], k["date"], k["hour"]) == \
        ("K", True, "VEHICLE/PEDESTRIAN", "ANCHORAGE", "2024-01-30", 9)
    assert sum(c["is_freeway"] for c in crashes.values()) >= 2
    died = dict(_rows()[0], **{"Crash Severity": "Died Prior to Crash"})
    assert ak_dotpf.contract_record(died)["severity"] == "O"    # not a crash injury


def test_fetch_contract_reads_each_year_once_and_keeps_the_box(tmp_path):
    calls = []

    def opener(req, timeout):
        calls.append(req.full_url)
        assert req.headers["User-agent"] == "CrashIQ/0.1"
        if "FilterCache" in req.full_url:
            opener.year = json.loads(req.data)["DateRanges"][0]["StartDate"][:4]
            return io.BytesIO(json.dumps({"Id": "f-" + opener.year, "SelectedCount": 1}).encode())
        assert f"filterid=f-{opener.year}" in req.full_url and "NonCategoricalVariableName=Latitude" in req.full_url
        return io.BytesIO(CSV if opener.year == "2024" else CSV.split(b"\r\n", 1)[0] + b"\r\n")

    box = (61.08, -150.0, 61.25, -149.7)                                        # Anchorage bowl
    got = ak_dotpf.fetch_contract(box, ["02020"], [2024, 2026], tmp_path, opener=opener)
    assert got["years_missing"] == [2026] and len(calls) == 4
    assert {c["county_fips"] for c in got["crashes"]} == {"02020"}
    assert got["cleaning"]["no_point_in_boroughs"] == 0 and len(got["crashes"]) == 26   # 3 lie outside the bowl
    assert [p.name for p in tmp_path.iterdir()] == ["ak_dotpf_2024.json"]      # the empty year isn't cached
    again = ak_dotpf.fetch_contract(box, ["02020", "02170"], [2024], tmp_path, opener=None)   # cached: no network
    assert again["cleaning"]["no_point_in_boroughs"] == 1                       # Mat-Su's crash with no point


def test_pack_is_registered_and_its_methods_are_cited():
    pack = packs.get("AK")
    assert pack.status == "active"
    assert study.default_window(date(2026, 11, 8), pack) == (2021, 2025)
    assert packs.check_methods(packs.methods(pack), "AK") == []
    assert packs.value(pack, "crash_costs")["K"] == 2986000 and packs.value(pack, "min_years") is None
    boxes = json.loads(pack.county_boxes.read_text())["counties"]
    assert len(boxes) == 30 and all(-180 <= b["box"][1] < b["box"][3] < -129 for b in boxes.values())
