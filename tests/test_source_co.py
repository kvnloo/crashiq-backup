"""Colorado: CDOT crash-listing reader (sources/co_cdot.py) and its plug-in pack, offline on a recorded fixture: 57 live
rows of the 2024 Statewide Crash Data Listing (Denver by severity, statewide by road user, system, Link form, no GPS
and mile-marker locations), saved as a small Excel file in the listing's own column names, 2026-11-08."""

import io
from pathlib import Path

import pytest

from crashiq import packs
from crashiq.sources import co_cdot

from conftest import FIXTURES

XLSX = FIXTURES / "co_cdot_2024.xlsx"
ROWS = co_cdot.read_xlsx(XLSX)
RECS = [co_cdot.contract_record(a) for a in ROWS]
PACK = packs.get("CO")


def test_plugin_is_registered_and_costs_wait_for_a_checked_copy():
    assert "co" not in packs.PLUGIN_ERRORS and PACK.name == "Colorado" and PACK.status == "active"
    assert packs.value(PACK, "crash_costs") is None                     # cited, not yet checked against a saved copy
    assert "not yet checked" in packs.why_missing(PACK, "crash_costs")
    assert packs.value(PACK, "screening")["engine"] == "critical_rate_own_sites"
    from datetime import date

    from crashiq import study
    assert study.default_window(date(2026, 11, 8), PACK) == (2021, 2025)   # inside first_year: a default study saves


def test_rows_pass_the_contract_and_severity_is_the_worst_persons_level():
    assert len(ROWS) >= 50 and all(packs.check_crash(c, PACK) == [] for c in RECS)
    assert {c["severity"] for c in RECS} == set("KABCO")
    a = {**ROWS[0], "Injury 00": 2, "Injury 01": 1, "Injury 02": 1, "Injury 03": 0, "Injury 04": 0,
         "Number Killed": 0, "Number Injured": 2}
    assert co_cdot.severity(a) == "B" and co_cdot.contract_record(a)["injured"] == 2
    assert co_cdot.severity({**a, "Injury 04": 1}) == "K"
    assert co_cdot.severity({"Injury 00": 0, "Number Injured": 1}) == "U"
    assert co_cdot.severity({}) is None


def test_link_offsets_mile_markers_and_counties():
    assert co_cdot.offset("00201FN") == (201.0, "N") and co_cdot.offset("0.25MW") == (1320, "W")
    assert co_cdot.offset("AT") == (None, None) and co_cdot.offset("S/O") == (None, "S")
    assert co_cdot.offset("00150FNE") == (None, None)                    # diagonal: not a N/S/E/W offset
    mm = [c for a, c in zip(ROWS, RECS) if str(a.get("Location 2") or "").startswith("MM ")]
    assert mm and all(c["secondary_road"] is None and c["offset_ft"] is None for c in mm)
    assert any(c["offset_ft"] for c in RECS)
    assert len(co_cdot.FIPS) == 64 and co_cdot.FIPS["DENVER"] == "08031" and co_cdot.FIPS["EL PASO"] == "08041"
    assert co_cdot.contract_record({**ROWS[0], "City": ""})["city"] == "UNINCORPORATED"


def test_road_users_freeway_types_and_no_gps():
    for flag in ("ped", "bike", "motorcycle", "heavy_truck", "is_freeway"):
        assert any(c[flag] for c in RECS) and not all(c[flag] for c in RECS), flag
    assert {"REAR END", "BROADSIDE", "HIT OBJECT"} <= {c["collision_type"] for c in RECS}
    nogps = [c for c in RECS if c["lat"] is None]
    assert nogps and all(c["county_fips"] for c in nogps)
    far = co_cdot.contract_record({**ROWS[0], "Latitude": 34.0, "Longitude": -118.0})
    assert far["lat"] is None and far["bad_coords"]


def test_docids_read_the_crash_data_page_links():
    page = ('<a data-val="x?docid=35111742" href="https://oitco.hylandcloud.com/CDOTRMPop/docpop/docpop.aspx?'
            'clienttype=html&amp;docid=35111742" text="\u00a02024" title="\u00a02024 Link">'
            '<a href="https://x/docpop.aspx?clienttype=html&amp;docid=8077599" rel="noopener" text=" 2018">'
            '<a href="https://x/docpop.aspx?docid=17470635" text="Data Dictionary (2021-2024)">')
    assert co_cdot.docids(lambda req, timeout: io.BytesIO(page.encode())) == {2024: "35111742", 2018: "8077599"}


def test_fetch_contract_filters_by_box_keeps_no_gps_in_county_and_caches(tmp_path, monkeypatch):
    calls = []

    def fake_download(docid, out: Path):
        calls.append(docid)
        out.write_bytes(XLSX.read_bytes())

    monkeypatch.setattr(co_cdot, "download", fake_download)
    ids = {2024: "35111742", 2025: "54973381", 2020: "9760262"}
    box = (39.61, -105.11, 39.92, -104.60)                              # Denver
    got = co_cdot.fetch_contract(box, ["08031"], [2020, 2024], tmp_path, ids=ids)
    assert got["years_missing"] == [2020] and calls == ["35111742"]     # 2020's layout isn't read
    assert not list(tmp_path.glob("*.xlsx")) and list(tmp_path.glob("co_cdot_2024_35111742.json.gz"))
    inbox = [c for c in got["crashes"] if c["lat"] is not None]
    assert inbox and all(box[0] <= c["lat"] <= box[2] and box[1] <= c["lon"] <= box[3] for c in inbox)
    assert all(c["county_fips"] == "08031" for c in got["crashes"] if c["lat"] is None)
    assert len(got["crashes"]) < len(RECS) and not any(c["preliminary"] for c in got["crashes"])
    again = co_cdot.fetch_contract(box, ["08031"], [2020, 2024], tmp_path, ids=ids)
    assert again == got and calls == ["35111742"]                       # cache, no second download

    def refused(docid, out):
        raise RuntimeError("OnBase asked for a sign-in instead of serving the file")

    monkeypatch.setattr(co_cdot, "download", refused)
    part = co_cdot.fetch_contract(box, ["08031"], [2024, 2025], tmp_path, ids=ids)
    assert part["years_missing"] == [2025] and 2025 in part["cleaning"]["download_failed"]
    assert len(part["crashes"]) == len(got["crashes"])                  # 2024 still read from cache


def test_a_file_in_the_old_layout_is_refused(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active.append(["SYSTEM", "RTE", "SEC", "MP", "DATE"])
    wb.save(tmp_path / "old.xlsx")
    with pytest.raises(ValueError):
        co_cdot.read_xlsx(tmp_path / "old.xlsx")
