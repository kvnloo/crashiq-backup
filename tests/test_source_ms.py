"""Mississippi: DPS eCrash reader (sources/ms_dps.py), offline on a recorded fixture: 55 live 2024 crashes (Hinds
County: 40 random, fatal, pedestrian, motorcycle and interstate crashes; 4 Harrison) with their drivers, passengers,
non-motorists and vehicles, cut from DPS's 2024 workbook (posted 2026-02-05) on 2026-11-08."""

import gzip
import io
import json
from collections import Counter

from crashiq import packs
from crashiq.sources import ms_dps

from conftest import FIXTURES

BOOK = FIXTURES / "ms_dps_ecrash_2024.xlsx"
INDEX = ('<a href="https://publicdata.dps.ms.gov/Public-CrashData/eCrash/Public Data Request 26-02-05 0946 '
         '(24-01-01 to 24-12-31).xlsx">eCrash-2024</a> <a href="https://publicdata.dps.ms.gov/Public-CrashData/eCrash/'
         'Public Data Request 26-02-05 1002 (25-01-01 to 25-12-31) DRAFT.xlsx">eCrash-2025</a>')


def test_every_crash_maps_to_the_contract():
    pack = packs.get("MS")
    got = ms_dps.read_workbook(BOOK)
    assert len(got) == 55 and all(packs.check_crash(c, pack) == [] for c in got)
    assert {c["county_fips"] for c in got} == {"28049", "28047"}                  # Hinds, Harrison
    boxes = json.loads(pack.county_boxes.read_text())["counties"]
    assert {boxes[c["county_fips"]]["name"] for c in got} == {"Hinds County", "Harrison County"}
    assert all(c["lat"] is not None and c["primary_road"] for c in got)


def test_severity_is_the_worst_person_and_flags_join():
    got = ms_dps.read_workbook(BOOK)
    sev = Counter(c["severity"] for c in got)
    assert sev["K"] >= 4 and set(sev) <= set("KABCUO")
    assert all(c["severity"] == "K" for c in got if c["killed"])
    assert sum(c["ped"] for c in got) >= 4 and all(c["collision_type"] == "VEHICLE/PEDESTRIAN" for c in got if c["ped"])
    assert sum(c["motorcycle"] for c in got) >= 3 and sum(c["is_freeway"] for c in got) >= 3


def test_severity_and_road_rules():
    assert ms_dps.severity(["O", "B", "C"], 0, 2) == "B"
    assert ms_dps.severity([], 0, 1) == "U"           # an injury on the report that no person row carries
    assert ms_dps.severity(["A"], 1, 0) == "K"        # the report's death count wins
    assert ms_dps.severity([], 0, 0) == "O"
    assert ms_dps.road("", "55", "Interstate") == "I-55"
    assert ms_dps.road("", "49", "US highway") == "US 49" and ms_dps.road("", "25", "State highway") == "MS 25"
    assert ms_dps.road("LAKELAND DRIVE", "25", "State highway") == "LAKELAND DRIVE"
    assert ms_dps.road("", "I-20 WEST", "Interstate") == "I-20 WEST" and ms_dps.road("", "", "City street") is None


def test_year_files_reads_the_index_and_marks_drafts():
    files = ms_dps.year_files(lambda req, timeout: io.BytesIO(INDEX.encode()))
    assert set(files) == {2024, 2025} and files[2025][1] and not files[2024][1]
    assert files[2024][0].endswith("Public%20Data%20Request%2026-02-05%200946%20(24-01-01%20to%2024-12-31).xlsx")


def test_fetch_contract_downloads_once_filters_the_box_and_caches(tmp_path):
    seen = []

    def opener(req, timeout):
        seen.append(req.full_url)
        assert req.headers["User-agent"] == "CrashIQ/0.1"
        return io.BytesIO(INDEX.encode() if req.full_url == ms_dps.INDEX else BOOK.read_bytes())

    box = (32.25, -90.25, 32.40, -90.10)                                         # Jackson
    got = ms_dps.fetch_contract(box, ["28049"], [2023, 2024], tmp_path, opener=opener)
    assert len(seen) == 2 and got["years_missing"] == [2023]
    assert got["crashes"] and all(32.25 <= c["lat"] <= 32.40 for c in got["crashes"])
    assert got["cleaning"]["statewide_rows_read"] == 55 and not list(tmp_path.glob("*.xlsx"))   # workbook deleted
    cached = next(tmp_path.glob("ms_dps_2024_*.json.gz"))
    assert len(json.loads(gzip.decompress(cached.read_bytes()))) == 55
    again = ms_dps.fetch_contract(box, ["28049"], [2024], tmp_path, opener=opener)
    assert len(seen) == 3 and len(again["crashes"]) == len(got["crashes"])     # index only, no second download


def test_pack_is_registered_and_its_methods_are_cited():
    pack = packs.get("MS")
    assert pack.status == "active" and pack.severity_note is None and pack.first_year == 2020
    assert packs.check_methods(packs.methods(pack), "MS") == []
    assert packs.value(pack, "crash_costs") is None and "MDOT" in packs.why_missing(pack, "crash_costs")
    assert len(json.loads(pack.county_boxes.read_text())["counties"]) == 82
