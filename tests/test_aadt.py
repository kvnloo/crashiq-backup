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


def xlsx(name: str) -> bytes:
    f = ROWS[name]
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
