"""WisDOT DT4000 reader (backend/crashiq/sources/wi_dt4000.py), offline, on real 2022 W Capitol Dr rows (fixture)."""
import gzip
import io
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from crashiq import packs
from crashiq.sources import wi_dt4000 as wi

FX = (Path(__file__).parent / "fixtures" / "wi_dt4000_capitol_dr.csv").read_text()
BOX = (43.0885, -87.9675, 43.0910, -87.9465)


def _box(calls, body=None):
    """A fake Box.com: the year's zip holds the crash CSV (latin-1, CRLF, as WisDOT ships it) plus a person file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("dt4000/WI_annual_dt4000_2022_crash.csv", FX.replace("\n", "\r\n").encode("latin-1"))
        z.writestr("dt4000/WI_annual_dt4000_2022_person.csv", "CRSHNMBR\r\n")
        z.writestr("legacy/WI_annual_legacy_2022_crash.csv", "nope\r\n")

    def opener(req, timeout=None):
        calls.append(req.full_url)
        return io.BytesIO(body if body is not None else buf.getvalue())
    return opener


def test_contract_rows_pass_the_pack_checker(tmp_path):
    calls = []
    got = wi.fetch_contract(BOX, ["55079"], [2018, 2022, 2023], tmp_path, opener=_box(calls))
    pack = packs.get("WI")
    assert pack.status == "active" and got["years_missing"] == [2023]           # not posted by WisDOT
    assert all(packs.check_crash(c, pack) == [] for c in got["crashes"])
    assert len(got["crashes"]) == 2 * (215 + 3)          # the box + Milwaukee's no-GPS rows, once per year file
    assert got["cleaning"]["no_gps_in_counties"] == 2 * 3
    assert calls == [wi.BOX.format(wi.YEARS[2018]), wi.BOX.format(wi.YEARS[2022])]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["wi_dt4000_2018.csv.gz", "wi_dt4000_2022.csv.gz"]   # zips deleted
    calls.clear()
    wi.fetch_contract(BOX, ["55079"], [2022], tmp_path, opener=_box(calls))
    assert calls == []                                                           # cached


def test_2017_2019_layout_at_the_zip_root(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("WIN_annual_dt4000_2018_crash.csv", FX.replace("\n", "\r\n"))
        z.writestr("WIN_annual_legacy_2018_crash.csv", "nope\r\n")
    got = wi.fetch_contract(BOX, ["55079"], [2018], tmp_path, opener=lambda req, timeout=None: io.BytesIO(buf.getvalue()))
    assert len(got["crashes"]) == 215 + 3


def test_compact_keeps_only_the_contract_columns(tmp_path):
    wi.fetch_contract(BOX, [], [2022], tmp_path, opener=_box([]))
    with gzip.open(tmp_path / "wi_dt4000_2022.csv.gz", "rt") as f:
        assert f.readline().strip().split(",") == list(wi.KEEP)


def test_not_a_zip_raises_and_leaves_no_file(tmp_path):
    with pytest.raises(RuntimeError, match="did not return a zip"):
        wi.fetch_contract(BOX, [], [2022], tmp_path, opener=_box([], body=b"<html>login</html>"))
    assert not list(tmp_path.iterdir())


def test_severity_modes_and_collision_types():
    recs = [wi.contract_record(a) for a in __import__("csv").DictReader(io.StringIO(FX))]
    sev = Counter(r["severity"] for r in recs[:215])                           # the corridor rows
    assert sev["K"] == 1 and sev["A"] == 6 and sev["B"] == 17 and sev["C"] == 42 and not sev["U"]
    assert sum(r["ped"] for r in recs) == 8
    assert all(r["collision_type"] == "VEHICLE/PEDESTRIAN" for r in recs if r["ped"] and not r["bike"])
    assert wi.severity({"INJSVR": "", "TOTINJ": "2"}) == "U" and wi.severity({"INJSVR": " "}) == "O"
    assert wi.collision_type({"CRSHTYPE": "113", "MNRCOLL": "101"}) == "HIT OBJECT"


def test_roads_offsets_dates_and_points():
    assert wi.road("", "032", "STH") == "STATE HWY 32" and wi.road("", "PP", "CTH") == "CO RD PP"
    assert wi.road("", "094", "IH") == "I-94" and wi.road("W CAPITOL DR", "190", "STH") == "W CAPITOL DR"
    assert wi.road("", "", "") is None
    r = wi.contract_record({"CRSHNMBR": "1", "CRSHDATE": "06/01/2022", "CRSHTIME": "0815", "CNTYFIPS": "55079",
                            "LATDECDG": "34.0", "LONDECDG": "-118.2", "ONSTR": "", "ONHWY": "190", "ONHWYSYS": "STH",
                            "ATSTR": "N 35TH ST", "INTDIS": "0.05", "INTDIR": "E", "ACSCNTL": "103", "INJSVR": "O"})
    assert (r["date"], r["hour"], r["day_of_week"]) == ("2022-06-01", 8, "Wednesday")
    assert (r["primary_road"], r["secondary_road"], r["offset_ft"], r["offset_dir"]) == ("STATE HWY 190", "N 35TH ST", 264, "E")
    assert r["lat"] is None and r["bad_coords"] and not r["is_freeway"]
