"""New Mexico: Albuquerque/UNM crash layer reader (sources/nm_cabq.py), offline on a recorded fixture of 36 live 2024
rows (Bernalillo by severity, pedestrian, bicycle, interstate, landmark offsets, no GPS, one Sandoval row) plus one copy
with a repeated report number, recorded 2026-11-08."""

import io
import json
import re
import urllib.parse
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import nm_cabq

from conftest import FIXTURES

ROWS = [f["attributes"] for f in json.loads((FIXTURES / "nm_cabq_bernalillo_2024.json").read_text())["features"]]
PACK = packs.get("NM")


def _opener(page, urls=None):
    def opener(req, timeout):
        q = urllib.parse.unquote_plus(req.full_url)
        if urls is not None:
            urls.append(q)
        last = int(re.search(r"OBJECTID>(\d+)", q).group(1))
        out = [a for a in sorted(ROWS, key=lambda a: a["OBJECTID"]) if a["OBJECTID"] > last][:page]
        return io.BytesIO(json.dumps({"features": [{"attributes": a} for a in out]}).encode())
    return opener


def test_plugin_registers_a_reader_only_new_mexico_pack():
    assert "nm" not in packs.PLUGIN_ERRORS and PACK.name == "New Mexico" and PACK.status == "reader_only"
    assert packs.check_methods(packs.methods(PACK), "NM") == []
    assert packs.value(PACK, "crash_costs") is None               # vendor-page figure, verified: false: never printed


def test_every_row_passes_the_contract():
    recs = [nm_cabq.contract_record(a) for a in ROWS]
    assert all(packs.check_crash(c, PACK) == [] for c in recs)
    assert Counter(c["county_fips"] for c in recs) == {"35001": len(ROWS) - 1, "35043": 1}
    assert any(c["lat"] is None for c in recs) and not any(c["bad_coords"] for c in recs if c["lat"] is not None)


def test_severity_is_kabco_from_the_people_counts_and_agrees_with_unm():
    recs = [nm_cabq.contract_record(a) for a in ROWS]
    assert set(c["severity"] for c in recs) == set("KABCO")
    assert all((c["severity"] == "K") == (c["severity_reported"] == "Fatal Crash") for c in recs)
    assert all((c["severity"] == "O") == (c["severity_reported"] == "Property Damage Only Crash") for c in recs)
    assert nm_cabq.severity({"SEVERITY": "Injury Crash"}) == "U"            # injury crash with no class: U, never C


def test_time_is_local_and_landmark_offsets_become_the_cross_street():
    r = nm_cabq.contract_record({**ROWS[0], "DATETIME": 1705531380000})      # 22:43 UTC = 3:43 PM MST
    assert (r["date"], r["hour"]) == ("2024-01-17", 15)
    r = nm_cabq.contract_record({**ROWS[0], "DATETIME": None, "DATE": 1641020400000})   # no time: date only
    assert (r["date"], r["year"], r["hour"]) == ("2022-01-01", 2022, None)
    a = {"PRIMARY_ST": "GIBSON BLVD SE", "SECONDARY_ST": None, "LANDMARK": "CARLISLE BLVD SE", "DIR_LANDMARK": "E",
         "DISTANCE_FROM_LANDMARK": 100, "DISTANCE_UNIT": "FT", "REPORT_NUMBER": 1, "COUNTY": "Bernalillo"}
    r = nm_cabq.contract_record(a)
    assert (r["secondary_road"], r["offset_ft"], r["offset_dir"]) == ("CARLISLE BLVD SE", 100, "E")
    mm = nm_cabq.contract_record({**a, "PRIMARY_ST": "INTERSTATE 40", "LANDMARK": "MM 179"})
    assert (mm["secondary_road"], mm["offset_ft"]) == (None, None)          # a milepost is not a street
    both = nm_cabq.contract_record({**a, "SECONDARY_ST": "YALE BLVD SE", "LANDMARK": "JUAN TABO/CONSTITUTION"})
    assert (both["secondary_road"], both["offset_ft"]) == ("YALE BLVD SE", None)   # offset is from another place
    mi = nm_cabq.contract_record({**a, "DISTANCE_FROM_LANDMARK": 0.5, "DISTANCE_UNIT": "MI"})
    assert mi["offset_ft"] == 2640


def test_ccrs_words_and_flags():
    recs = [nm_cabq.contract_record(a) for a in ROWS]
    types = {c["collision_type"] for c in recs}
    assert {"REAR END", "BROADSIDE", "HIT OBJECT"} <= types and "Front-to-Rear" not in types
    assert any(c["ped"] and c["collision_type"] == "VEHICLE/PEDESTRIAN" for c in recs)
    assert any(c["bike"] for c in recs) and any(c["is_freeway"] for c in recs) and any(not c["is_freeway"] for c in recs)
    assert "Dark-Lighted" not in {c["lighting"] for c in recs} and "CLEAR" in {c["weather"] for c in recs}
    assert "LEFT BLANK" not in {c["weather"] for c in recs} | {c["lighting"] for c in recs}


def test_fetch_pages_by_objectid_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(nm_cabq, "PAGE", 15)
    urls = []
    got = nm_cabq.fetch("1=1", tmp_path, opener=_opener(15, urls))
    assert len(got) == len(ROWS) and len(urls) == 3                         # 37 rows: 15 + 15 + 7
    assert "(1=1) AND OBJECTID>0" in urls[0]
    assert nm_cabq.fetch("1=1", tmp_path, opener=None) == got               # second call reads the cache


def test_query_error_is_raised():
    err = lambda req, timeout: io.BytesIO(b'{"error": {"code": 400, "message": "bad where"}}')
    with pytest.raises(RuntimeError):
        nm_cabq.fetch("nope", None, opener=err)


def test_fetch_contract_box_years_duplicates_and_coverage(tmp_path):
    urls = []
    got = nm_cabq.fetch_contract((35.0, -106.7, 35.2, -106.5), ["35001"], [2024, 2025], tmp_path,
                                 opener=_opener(2000, urls))
    assert "LAT >= 35.000000 AND LAT <= 35.200000 AND LON >= -106.700000 AND LON <= -106.500000" in urls[0]
    assert "YEAR IN (2024)" in urls[0] and got["years_missing"] == [2025]
    assert len(got["crashes"]) == len(ROWS) - 1 and got["cleaning"]["dropped_duplicate_or_undated"] == 1
    assert len({c["crash_id"] for c in got["crashes"]}) == len(got["crashes"])
    away = nm_cabq.fetch_contract((32.2, -106.9, 32.4, -106.7), ["35013"], [2023, 2024], tmp_path, opener=None)
    assert away["crashes"] == [] and away["years_missing"] == [2023, 2024]    # Las Cruces: missing, never zero
    assert nm_cabq.fetch_contract((0, 0, 1, 1), ["35001"], [2019], tmp_path, opener=None)["years_missing"] == [2019]
