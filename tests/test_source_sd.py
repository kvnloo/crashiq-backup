"""South Dakota: DPS SDARS reader (sources/sd_dps.py), offline on a recorded fixture: 40 live 2025 Accident rows
(Minnehaha by severity, pedestrian, wild-animal and one-field-intersection rows, 4 Pennington rows and the one slipped
row) with their Person/Vehicle/Weather rows, cut to the columns the reader reads (no names or other personal data),
from safesd.gov SDARSFiles2025.zip, recorded 2026-11-08."""

import io
import json
import zipfile
from collections import Counter

from crashiq import packs
from crashiq.sources import sd_dps

from conftest import FIXTURES

ZIP = (FIXTURES / "sd_sdars_2025_sample.zip").read_bytes()


def _read():
    return sd_dps.read_zip(zipfile.ZipFile(io.BytesIO(ZIP)))


def test_every_row_maps_to_the_contract_and_the_slipped_row_is_dropped():
    crashes, slipped = _read()
    pack = packs.get("SD")
    assert (len(crashes), slipped) == (39, 1)
    assert all(packs.check_crash(c, pack) == [] for c in crashes)
    assert Counter(c["county_fips"] for c in crashes) == {"46099": 35, "46103": 4}
    assert all(c["lat"] is not None and c["primary_road"] for c in crashes)


def test_kabco_from_persons_never_below_the_crash_severity():
    crashes, _ = _read()
    assert Counter(c["severity"] for c in crashes) == {"O": 20, "C": 8, "B": 6, "K": 3, "A": 2}
    assert all(c["severity"] == "K" for c in crashes if c["severity_reported"] == "Fatal")
    assert all(c["severity"] in "ABCU" for c in crashes if c["severity_reported"] == "Injury")
    one = {"Severity": "Injury", "AccidentNbr": "1", "AccidentDateTime": "05/11/2025 12:00:00 AM"}
    assert sd_dps.contract_record(one, [], set(), None)["severity"] == "U"      # injury crash, no person level


def test_street_pair_repairs():
    assert sd_dps.street_pair("W 41ST ST / S LARCH AVE", None, None) == ("W 41ST ST", "S LARCH AVE")
    assert sd_dps.street_pair("W 41ST ST / S LARCH AVE", "W 41ST ST", None) == ("W 41ST ST", "S LARCH AVE")
    assert sd_dps.street_pair("W 37TH ST", "W 37TH ST", "S CENTER AVE") == ("W 37TH ST", "S CENTER AVE")
    assert sd_dps.street_pair("W 12TH ST", "W 12TH ST", None) == ("W 12TH ST", None)
    assert sd_dps.street_pair("E 10TH ST", "S WAYLAND AVE", "S VAN EPS AVE") == ("E 10TH ST", "S WAYLAND AVE")


def test_codes_flags_and_offsets():
    crashes, _ = _read()
    assert sum(c["ped"] for c in crashes) == 3 and sum(c["wild_animal"] for c in crashes) == 4
    assert {"REAR END", "BROADSIDE", "VEHICLE/PEDESTRIAN"} <= {c["collision_type"] for c in crashes}
    k = next(c for c in crashes if c["crash_id"] == "2505744")
    assert (k["primary_road"], k["secondary_road"], k["offset_ft"], k["offset_dir"]) == ("I 29 N2", "W 12TH ST", 456.0, "NW")
    assert k["is_freeway"] and k["route"] is None and k["milepost"] is None and (k["date"], k["hour"]) == ("2025-05-11", 18)


def test_fetch_contract_downloads_once_drops_the_zip_and_keeps_the_box(tmp_path):
    calls = []

    def opener(req, timeout):
        calls.append(req.full_url)
        assert req.headers["User-agent"] == "CrashIQ/0.1"
        return io.BytesIO(ZIP)

    box = (43.4, -96.9, 43.7, -96.6)                       # Sioux Falls
    got = sd_dps.fetch_contract(box, ["46099"], [2025, 2026], tmp_path, opener=opener)
    assert calls == ["https://www.safesd.gov/downloads/raw-data/SDARSFiles2025.zip"]
    assert got["years_missing"] == [2026] and got["cleaning"]["slipped_rows_dropped"] == 1
    assert {c["county_fips"] for c in got["crashes"]} == {"46099"} and len(got["crashes"]) == 32      # 3 rural Minnehaha crashes lie outside the box
    assert [p.name for p in tmp_path.iterdir()] == ["sd_dps_2025.json"]          # no zip (personal data) kept
    again = sd_dps.fetch_contract(box, ["46099"], [2025], tmp_path, opener=None)  # cached: no network
    assert len(again["crashes"]) == 32


def test_pack_is_registered_and_its_methods_are_cited():
    pack = packs.get("SD")
    assert pack.status == "active"
    assert packs.value(pack, "crash_costs") is None and "SD2019-02" in packs.why_missing(pack, "crash_costs")
    assert len(json.loads(pack.county_boxes.read_text())["counties"]) == 66
