"""#484: `python -m crashiq.ssam.compare` against REAL output of FHWA's SSAM_MT.exe (SSAM 3.0), run offline.

tests/fixtures/ssam/fhwa/<stem>.csv are SSAM_MT's own CSVs for the fixture .trj files (TTC 1.5, PET 5.0), saved
unchanged: `SSAM_MT.exe trjfiles=<fixture>.trj csvfile=<stem>.csv`. SSAM_MT wrote no CSV for crossing and near_pass
(no conflicts). FHWA and we agree on every conflict FHWA lists. The one difference is crossing: we list a TTC 0.9
event with no PET observed, SSAM_MT lists none (it drops events with no PET; an OPEN rule choice on PR #487).
"""

from __future__ import annotations

import shutil

import pytest

from conftest import FIXTURES
from crashiq.ssam import find_conflicts, read_trj
from crashiq.ssam.compare import compare, main, read_fhwa_csv

SSAM = FIXTURES / "ssam"
FHWA = SSAM / "fhwa"


def test_read_real_fhwa_csv():
    # Summary block first, then 'Conflict Listing,1', then FHWA's header (with its 'FristVID' spelling).
    assert read_fhwa_csv(FHWA / "cut_in.csv") == [
        {"FirstVID": 2, "SecondVID": 1, "tMinTTC": 3.0, "TTC": 1.2, "PET": 0.1, "ConflictType": "lane-change"}]
    assert read_fhwa_csv(FHWA / "rear_end.csv")[0]["ConflictType"] == "rear-end"


@pytest.mark.parametrize("stem", ["rear_end", "follow_brake", "cut_in"])
def test_ours_matches_fhwa(stem):
    (f,) = read_fhwa_csv(FHWA / f"{stem}.csv")
    (o,) = find_conflicts(read_trj(SSAM / f"{stem}.trj"))
    assert (o["FirstVID"], o["SecondVID"], o["ConflictType"]) == (f["FirstVID"], f["SecondVID"], f["ConflictType"])
    assert (o["tMinTTC"], o["TTC"], o["PET"]) == pytest.approx((f["tMinTTC"], f["TTC"], f["PET"]))


def test_compare_command(tmp_path, capsys):
    for p in SSAM.glob("*.trj"):
        shutil.copy(p, tmp_path)
    assert main([str(tmp_path), "--fhwa-dir", str(FHWA)]) == 0
    report = (tmp_path / "ssam_compare.txt").read_text()
    assert report == capsys.readouterr().out
    assert "Found by both: 3" in report and "Only FHWA: 0" in report and "Only CrashIQ: 1 (1 with no PET)" in report
    assert "Same type: 3 of 3" in report and "crossing: vehicles 1-2 at t=3.1 (no PET)" in report
    assert "TTC difference (s): median 0.000, worst 0.000" in report
    assert "PET difference (s): median 0.000, worst 0.000" in report
    assert "Wall-clock: FHWA SSAM_MT not run (saved CSVs), CrashIQ " in report


def test_compare_counts():
    # Within a pair, conflicts are aligned in time: b's two FHWA events 10 s apart match ours at 0.5 s and 10.4 s.
    e = lambda t: {"FirstVID": 3, "SecondVID": 4, "tMinTTC": t, "TTC": 1.0, "PET": 1.0, "ConflictType": "crossing"}
    s2, _ = compare({"x": [e(0.5), e(5.0), e(10.4)]}, {"x": [e(0.0), e(10.0)]})
    assert (s2["both"], s2["only_ours"], s2["only_fhwa"]) == (2, 1, 0)
    o = {"FirstVID": 1, "SecondVID": 2, "tMinTTC": 3.0, "TTC": 1.0, "PET": 0.5, "ConflictType": "rear-end"}
    f = dict(o, FirstVID=2, SecondVID=1, TTC=1.1, ConflictType="lane-change")  # same pair, other order
    summary, report = compare({"a": [o], "b": [o]}, {"a": [f], "c": [o]})
    assert summary == {"both": 1, "only_fhwa": 1, "only_ours": 1, "only_ours_no_pet": 0, "type_agree": 0, "type_differ": 1,
                       "ttc_worst": 0.1, "pet_worst": 0.0}
    assert "a: vehicles 1-2 at t=3.0: ours rear-end, FHWA lane-change" in report


def test_bad_csv(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="Conflict Listing"):
        read_fhwa_csv(p)
    p.write_text((FHWA / "cut_in.csv").read_text().replace("Conflict Listing,1", "Conflict Listing,2"))
    with pytest.raises(ValueError, match="says 2"):
        read_fhwa_csv(p)
