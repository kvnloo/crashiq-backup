"""#287: Caltrans Traffic Census AADT, the loader and the segment join (user decision 2026-10-26, docs/03). The fixture
rows are cut from Caltrans' public annual files (2021 and 2024 traffic volumes, 2024 truck AADT; downloaded
2026-10-26): LA-405 around Artesia Blvd and ORA-1 at Dana Point, with its route break. Tests build small .xlsx files
from them (both header styles), so the loader parses real spreadsheets and needs no network."""

import io
import json

import pytest
from openpyxl import Workbook

from crashiq import aadt

from conftest import FIXTURES

ROWS = json.loads((FIXTURES / "aadt_la405_ora1.json").read_text())


def xlsx(name: str, rows: dict | None = None) -> bytes:
    f = (rows or ROWS)[name]
    wb = Workbook()
    wb.active.title = "Preface"
    wb.active.append(["Caltrans Traffic Census Program"])
    ws = wb.create_sheet(f["sheet"])
    ws.append(f["header"])
    for r in f["rows"]:
        ws.append(r)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


FILES = {"v21": xlsx("2021-traffic-volumes-ca-v2-a11y.xlsx"), "v24": xlsx("2024-traffic-volumes-ca-a11y.xlsx"),
         "t24": xlsx("2024-truck-aadt-a11y.xlsx")}
YEARS = {2021: {"volumes": "https://x/v21"}, 2024: {"volumes": "https://x/v24", "trucks": "https://x/t24"}}


class Get:
    def __init__(self, files):
        self.files, self.urls = files, []

    def __call__(self, url):
        self.urls.append(url)
        if self.files is None:
            raise OSError("down")
        return self.files[url.rsplit("/", 1)[1]]


@pytest.fixture
def cache(tmp_path):
    return aadt.AadtCache(tmp_path / "aadt", years=YEARS, get=Get(FILES), background=False, now=lambda: 1_793_000_000)


def test_both_header_styles_load_and_blanks_are_none(cache):
    con = cache.db()
    assert cache.ready().name == "caltrans_aadt_2026-10-26.sqlite"                # the download date is the vintage
    n = dict(con.execute("SELECT year, COUNT(*) FROM point GROUP BY year").fetchall())
    assert n == {2021: 10, 2024: 10}
    r = con.execute("SELECT route, county, prefix, pm, description, back_aadt, ahead_aadt FROM point "
                    "WHERE year = 2024 AND route = '1' ORDER BY pm").fetchall()
    assert r[0] == ("1", "ORA", "R", 0.129, "DANA POINT, JCT. RTE. 5", None, 38250)   # '001' and ' ' read
    assert r[2][4] == "BREAK IN RTE" and r[2][5:] == (None, None)
    assert {u.rsplit("/", 1)[1] for u in cache.get.urls} == {"v21", "v24", "t24"}


def test_a_crash_between_two_count_points_gets_that_segments_aadt(cache):
    s = cache.segment("405", "LA", 13.5, year=2024)
    assert (s["from"]["pm"], s["to"]["pm"]) == (13.28, 13.826)
    assert s["from"]["description"] == "LOS ANGELES, VERMONT AVENUE"
    assert s["aadt"] == 285000 and s["to"]["back_aadt"] == 285000              # AHEAD of the first = BACK of the next
    assert s["length_mi"] == pytest.approx(0.546) and s["year"] == 2024 and not s["latest_used"]


def test_the_nearer_count_point_s_leg_facing_the_crash_gives_its_aadt(cache):
    # ORA-1 between Mountain Rd (8.43, AHEAD 37,900) and Jct Rte 133 (9.418, BACK 38,800): the halves split at 8.924
    first, second = cache.segment("1", "ORA", 8.6, year=2024), cache.segment("1", "ORA", 9.0, year=2024)
    assert first["aadt"] == 37900 and first["piece"] == {"from_pm": 8.43, "to_pm": 8.924, "length_mi": 0.494,
                                                         "leg": "ahead of LAGUNA BEACH, MOUNTAIN ROAD"}
    assert second["aadt"] == 38800 and second["piece"]["from_pm"] == 8.924 and second["piece"]["to_pm"] == 9.418
    assert second["piece"]["leg"] == "back of LAGUNA BEACH, JCT. RTE. 133 NORTH"


def test_a_crash_at_a_count_point_is_on_the_segment_ahead_of_it(cache):
    s = cache.segment("405", "LA", 13.28, year=2024)
    assert s["from"]["pm"] == 13.28 and s["aadt"] == 285000


def test_each_count_year_has_its_own_aadt(cache):
    a21, a24 = cache.segment("405", "LA", 13.5, year=2021), cache.segment("405", "LA", 13.5, year=2024)
    assert a21["year"] == 2021 and a24["year"] == 2024
    row21 = next(r for r in ROWS["2021-traffic-volumes-ca-v2-a11y.xlsx"]["rows"] if str(r[5]).strip() in ("13.28", ".13.28"))
    assert a21["aadt"] == int(row21[13])


def test_no_segment_across_a_route_break_or_past_the_ends(cache):
    assert cache.segment("1", "ORA", 0.9, year=2024)["aadt"] == 38900           # before the break
    for pm in (5.0, 0.05, 20.0):                                                  # in the break, before, after
        assert cache.segment("1", "ORA", pm, year=2024) is None
    assert cache.segment("5", "ORA", 1.0, year=2024) is None                      # no count points on that route


def test_the_count_year_runs_october_to_september_and_later_years_use_the_latest_labelled(cache):
    assert aadt.count_year("2023-09-30T10:00:00") == 2023
    assert aadt.count_year("2023-10-01T00:05:00") == 2024
    s = cache.segment("405", "LA", 13.5, year=2025)
    assert s["year"] == 2024 and s["latest_used"] and s["wanted_year"] == 2025
    assert cache.segment("405", "LA", 13.5, year=2019) is None                   # before the first loaded year: none


def test_truck_aadt_three_axles_and_up_on_the_truck_segment(cache):
    s = cache.truck_segment("1", "ORA", 0.5, year=2024)
    row = next(r for r in ROWS["2024-truck-aadt-a11y.xlsx"]["rows"] if r[5] == 0.129 and r[7] == "A")
    assert (s["from"]["pm"], s["to"]["pm"]) == (0.129, 0.78)
    assert s["truck_aadt"] == row[10] and s["trucks_3plus"] == row[14] + row[16] + row[18]


def test_a_crash_gets_its_segment_through_its_derived_postmile(cache):
    c = {"reported_at": "2024-03-02T08:00:00",
         "postmile": {"route": "405", "route_suffix": "", "county": "LA", "prefix": "", "pm": 13.5, "suffix": "",
                      "label": "LA-405 PM 13.500", "derived": True}}
    s = cache.for_crash(c)
    assert s["aadt"] == 285000 and s["year"] == 2024
    assert s["source"].startswith("Caltrans Traffic Census") and "2024" in s["source"]
    assert cache.for_crash({**c, "postmile": None}) is None


def test_the_download_waits_after_a_failure(tmp_path):
    c = aadt.AadtCache(tmp_path / "aadt", years=YEARS, get=Get(None), background=False, now=lambda: 1_793_000_000)
    assert c.ready() is None and "down" in c.error()
    c.ready()
    assert len(c.get.urls) == 1                                                   # no retry within the hour


def test_up_to_0_05_mi_past_a_line_s_last_or_first_count_point_uses_that_point_labelled(cache):
    # PM decision on #289 (a): a 0.05 mi end tolerance at a line's first and last count points only, labelled
    last = cache.segment("405", "LA", 14.398 + 0.04, year=2024)          # Western Ave is the fixture's last LA-405 point
    assert last["aadt"] == 241000 and last["aadt_end_tolerance"] and last["from"]["pm"] == 14.398
    first = cache.segment("405", "LA", 11.224 - 0.05, year=2024)          # Avalon Blvd, the first: its BACK leg
    assert first["aadt"] == 232000 and first["aadt_end_tolerance"]
    assert cache.segment("405", "LA", 14.398 + 0.06, year=2024) is None
    assert not cache.segment("405", "LA", 13.5, year=2024)["aadt_end_tolerance"]
    assert cache.segment("1", "ORA", 1.077 + 0.01, year=2024) is None      # a route break is not a line end (b: no bridging)


def test_a_segment_whose_ends_have_different_prefixes_takes_the_leg_of_the_crash_s_prefix(cache):
    # #287 point 1: never measure across a prefix change; ORA-1 R1.077 (break) .. 8.43 is a break anyway, so this
    # builds one: R0.78 (AHEAD 38,900) then 8.43 (no prefix, BACK 37,900)
    con = cache.db()
    s = cache._pick(aadt._around([(0.78, "R", "a", 38900, 38900), (8.43, "", "b", 37900, 37900)], 5.0), 5.0, "")
    assert s["aadt"] == 37900 and s["prefix_change"] and s["piece"]["length_mi"] is None
    s = cache._pick(aadt._around([(0.78, "R", "a", 38900, 38900), (8.43, "", "b", 37900, 37900)], 5.0), 5.0, "R")
    assert s["aadt"] == 38900
    assert con is not None


# -- older editions (#345, user OK 2026-11-01): synthetic sheets in each year's layout ---------------------------
def book(sheets: list[tuple[str, list[list]]]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for title, rows in sheets:
        ws = wb.create_sheet(title)
        for r in rows:
            ws.append(r)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def test_2016_volumes_have_no_header_row_and_read_in_2017s_columns():
    data = book([("2016AADT", [["12", "001", None, "ORA", "R", ".129", None, "DANA POINT, JCT. RTE. 5", None, None, None,
                                3800, 41000, 37750],
                               ["12", "001", None, "ORA", "R", ".78", None, "DANA POINT, DOHENY PARK ROAD", 3800, 41000,
                                37750, 3900, 42000, 38800]]), ("2016a", [[None] * 14])])
    rows = list(aadt._rows(data))
    assert len(rows) == 2 and aadt._key(rows[1]) == ("1", "", "ORA", "R", 0.78, "")
    assert rows[1]["BACK_AADT"] == 37750 and rows[1]["AHEAD_AADT"] == 38800


def test_2016_to_2018_trucks_read_the_three_row_header_and_the_combined_postmile():
    head = [[None, None, None, None, "L", None, "VEHICLE", "TRUCK", "TRUCK", None, "TRUCK", "AADT"],
            [None, None, None, "POST", "E", None, "AADT", "AADT", "% TOT"],
            ["RTE", "DIST", "CNTY", "MILE", "G", "DESCRIPTION", "TOTAL", "TOTAL", "VEH", 2, 3, 4, "5+", 2, 3, 4, "5+",
             "(1000)", "EST"], [None] * 19]
    data = book([("PREFACE", [["x"]]), ("2018 AADTT", head + [
        ["001", "12", "ORA", "R.129", "A", "DANA POINT, JCT. RTE. 5", "38250", "2379", 6.22, 807, 1126, 319, 128, 33.93,
         47.32, 13.39, 5.36, 220, "18E"],
        ["005", "07", "LA", "12.3R", "B", "SOMEWHERE", "50000", "900", 1.8, 400, 200, 100, 200, 44.4, 22.2, 11.1, 22.2,
         90, "18E"]])])
    rows = list(aadt._rows(data))
    assert [aadt._key(r) for r in rows] == [("1", "", "ORA", "R", 0.129, ""), ("5", "", "LA", "", 12.3, "R")]
    assert rows[0]["TOT_TRK_AADT"] == "2379" and (rows[0]["TRK_3_AXLE"], rows[0]["TRK_4_AXLE"], rows[0]["TRK_5_AXLE"]) == \
        (1126, 319, 128) and rows[0]["LEG"] == "A"


def test_2019_and_2020_trucks_spell_the_postmile_and_total_columns_differently():
    data = book([("Preface", [["x"]]), ("2019 Truck AADT", [
        ["RTE", "RTE_SFX", "DIST", "CNTY", "POSTMILE_PFX", "POSTMILE", "POSTMILE_SFX", "LEG", "DESCRIPTION",
         "VEHICLE_AADT_TOTAL", "TRUCK_AADT_TOTAL", "TRK_PERCENT_TOT", "TRK_2_AXLE", "TRK_3_AXLE", "TRK_4_AXLE", "TRK_5_AXLE"],
        ["001", None, "12", "ORA", "R", 0.129, None, "A", "DANA POINT, JCT. RTE. 5", 38250, 2379, 6.22, 807, 1126, 319, 128]])])
    r = next(aadt._rows(data))
    assert aadt._key(r) == ("1", "", "ORA", "R", 0.129, "") and r["TOT_TRK_AADT"] == 2379


def test_a_zero_count_is_no_count_as_2018_writes_blanks():
    assert aadt._count(0) is None and aadt._count("0") is None and aadt._count("38900") == 38900 and aadt._count(None) is None


def test_a_workbook_already_downloaded_with_its_checksum_is_read_locally(tmp_path):
    import hashlib
    d = tmp_path / "caltrans_downloads_2026-11-01"
    d.mkdir()
    (d / "2019-traffic-volumes.xlsx").write_bytes(b"workbook")
    (d / "SHA256SUMS").write_text(f"{hashlib.sha256(b'workbook').hexdigest()}  2019-traffic-volumes.xlsx\n")
    url = "https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/census/aadt/2019-traffic-volumes.xlsx"
    assert aadt.local_copy(url, [d]) == b"workbook"
    (d / "2019-traffic-volumes.xlsx").write_bytes(b"changed")                    # a checksum mismatch: never used
    assert aadt.local_copy(url, [d]) is None
    assert aadt.local_copy(url.replace("2019", "2015"), [d]) is None


def test_the_config_lists_2016_to_2024():
    assert sorted(aadt.YEARS) == list(range(2016, 2025))
    assert all({"volumes", "trucks"} <= set(aadt.YEARS[y]) for y in range(2016, 2021))
