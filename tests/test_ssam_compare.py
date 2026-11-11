"""#484: `python -m crashiq.ssam.compare`, run offline on a saved conflict CSV instead of FHWA's exe.

tests/fixtures/ssam/handmade_fhwa_format.csv is HAND-MADE in SSAM's conflict-table column names (FHWA's SSAM_MT.exe
could not run on this PC yet), with known differences planted against our results:
- rear_end: same pair and type, TTC 1.1 vs our 1.0, PET 0.6 vs 0.5;
- crossing: same pair (listed in the other order), typed "rear end" (ours: crossing), TTC 0.8 vs 0.9;
- near_pass: a 1-3 conflict only FHWA has; cut_in: our conflict, absent from FHWA.
"""

from __future__ import annotations

import shutil

import pytest

from conftest import FIXTURES
from crashiq.ssam.compare import compare, main, read_fhwa_csv

CSV = FIXTURES / "ssam" / "handmade_fhwa_format.csv"


def test_compare_command(tmp_path, capsys):
    for p in (FIXTURES / "ssam").glob("*.trj"):
        shutil.copy(p, tmp_path)
    assert main([str(tmp_path), "--fhwa-csv", str(CSV)]) == 0
    report = (tmp_path / "ssam_compare.txt").read_text()
    assert report == capsys.readouterr().out
    assert "Found by both: 2" in report and "Only FHWA: 1" in report and "Only CrashIQ: 1" in report
    assert "Same type: 1 of 2" in report
    assert "near_pass: vehicles 1-3" in report and "cut_in: vehicles 2-1" in report
    assert "crossing: vehicles 1-2 at t=3.1: ours crossing, FHWA rear-end" in report
    assert "TTC difference (s): median 0.100, worst 0.100" in report
    assert "PET difference (s): median 0.050, worst 0.100 (rear_end" in report


def test_compare_counts():
    fhwa = read_fhwa_csv(CSV)
    assert sorted(fhwa) == ["crossing", "near_pass", "rear_end"]
    ours = {"rear_end": [dict(fhwa["rear_end"][0], ConflictType="rear-end")]}
    summary, _ = compare(ours, {"rear_end": fhwa["rear_end"]})
    assert summary == {"both": 1, "only_fhwa": 0, "only_ours": 0, "type_agree": 1, "type_differ": 0,
                       "ttc_worst": 0.0, "pet_worst": 0.0}


def test_bad_csv(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="header"):
        read_fhwa_csv(p)
