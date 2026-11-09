"""MNCrash reader (backend/crashiq/sources/mn_mncrash.py), offline, on real 2024 Lake St rows (fixture)."""
import io
import json
import urllib.parse
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from crashiq import packs
from crashiq.sources import mn_mncrash as mn

FX = (Path(__file__).parent / "fixtures" / "mn_mncrash_lake_st.csv").read_text()
BOX = (44.9465, -93.2890, 44.9505, -93.2675)
PAGE = b'<input type="hidden" name="__VIEWSTATE" value="v"><span id="ContentPlaceHolder_lblErr" class="err">%s</span>'


def _portal(calls, err=b""):
    """A fake MNCrash: every postback returns the form; the Export postback returns the zipped CSV."""
    def opener(req, timeout=None):
        f = dict(urllib.parse.parse_qsl(req.data.decode())) if req.data else {}
        calls.append(f)
        if "ctl00$ContentPlaceHolder$btnExport" in f:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("Collision-Export.CSV", "\ufeff" + FX)
            return io.BytesIO(buf.getvalue())
        return io.BytesIO(PAGE % err)
    return opener


def test_contract_rows_pass_the_pack_checker(tmp_path):
    calls = []
    got = mn.fetch_contract(BOX, ["27053"], [2024], tmp_path, opener=_portal(calls))
    pack = packs.get("MN")
    assert pack.status == "active" and not got["years_missing"]
    assert got["crashes"] and all(packs.check_crash(c, pack) == [] for c in got["crashes"])
    assert Counter(c["county_fips"] for c in got["crashes"])["27053"] >= 249          # Hennepin
    assert got["cleaning"]["severity_blank_from_counts"] == sum(not a["Crash Severity"] for a in mn.rows(FX)) >= 3
    assert list(tmp_path.glob("mn_mncrash_*.csv"))                                    # raw export cached
    again = mn.fetch_contract(BOX, ["27053"], [2024], tmp_path, opener=None)          # cache hit: no portal
    assert len(again["crashes"]) == len(got["crashes"])


def test_postbacks_send_dates_and_utm_rectangle(tmp_path):
    calls = []
    mn.fetch(BOX, [2020, 2024], tmp_path, opener=_portal(calls))
    assert len(calls) == 5                                                            # GET, operator, map, search, export
    assert calls[1]["__EVENTTARGET"] == mn.DATE_OP and calls[1]["__EVENTARGUMENT"] == mn.CUSTOM_PERIOD
    m = calls[2]
    assert (m[mn.DATE_FROM], m[mn.DATE_TO]) == ("01/01/2020", "12/31/2024")
    ext = json.loads(m[mn.MAP_FIELD])
    assert ext["spatialReference"]["wkid"] == 26915
    assert 477000 < ext["xmin"] < ext["xmax"] < 480000 and 4977000 < ext["ymin"] < ext["ymax"] < 4978000
    assert calls[4]["ctl00$ContentPlaceHolder$rdoListExportOptions"] == "CSV"


def test_portal_error_raises_but_the_1000_row_note_does_not(tmp_path):
    with pytest.raises(RuntimeError, match="Bad query"):
        mn.fetch(BOX, [2024], None, opener=_portal([], b"Bad query"))
    assert mn.fetch(BOX, [2024], None, opener=_portal([], b"Please note: only 1,000 rows shown"))


def test_utm15_known_point():
    x, y = mn.utm15(45.0, -93.0)                       # central meridian: GRS80 meridian arc to 45N x 0.9996
    assert abs(x - 500000) < 0.01 and abs(y - 4984944.4 * 0.9996) < 0.5


def test_severity_words_and_blank_falls_back_to_counts():
    sev = Counter(c["severity"] for c in map(mn.crash_record, mn.rows(FX)))
    assert set(sev) <= set("KABCUO") and sev["O"] > sev["C"] > 0
    assert mn.severity("Suspected Serious Injury Crash", 0, 1) == "A"
    assert mn.severity("", 1, 0) == "K" and mn.severity("", 0, 2) == "U" and mn.severity("", 0, 0) == "O"


def test_roadway_split_and_route_names():
    assert mn.split_road("HENNEPIN AVE  at 9TH ST N") == ("HENNEPIN AVE", "9TH ST N")
    assert mn.split_road("SB ISTH 35E @ MARYLAND AVE") == ("I-35E", "MARYLAND AVE")
    assert mn.split_road("MNTH 99  at USTH 169") == ("STATE HWY 99", "US HWY 169")
    assert mn.split_road("CSAH 81  near 85TH AVE N") == ("CO RD 81", "85TH AVE N")
    assert mn.split_road("E LAKE ST") == ("E LAKE ST", None) and mn.split_road("") == (None, None)
    r = mn.crash_record({"Roadway": "SB ISTH 35E @ MARYLAND AVE", "County": "Ramsey", "Crash Date": "06/01/2024 08:15:00 AM"})
    assert r["is_freeway"] and r["county_fips"] == "27123" and (r["date"], r["hour"]) == ("2024-06-01", 8)
    assert r["road_text"] == "SB ISTH 35E @ MARYLAND AVE"                           # the officer's words kept


def test_unquoted_comma_rejoined_and_bad_points_dropped():
    recs = mn.rows(FX)
    assert all(len(a) == mn.COLUMNS for a in recs)
    odd = [mn.crash_record(a) for a in recs if not mn.plausible(mn._num(a["Latitude"]), mn._num(a["Longitude"]))]
    assert odd and all(r["lat"] is None for r in odd)


def test_county_names_match_the_census_boxes():
    boxes = json.loads((packs.REF / "county_boxes_mn.json").read_text())["counties"]
    assert len(mn.COUNTIES) == len(boxes) == 87
    for name in mn.COUNTIES:
        assert boxes[mn.FIPS[name.upper()]]["name"] == f"{name} County"
