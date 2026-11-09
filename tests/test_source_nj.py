"""New Jersey: NJDOT crash-records reader (sources/nj_njdot.py), offline on a recorded fixture: 33 live 2023 Crash
rows (Essex by severity, crashes with no point, pedestrian, cyclist, motorcycle and truck crashes, a crash entered
twice, a line broken by the free-text field) with their Occupant, Pedestrian and Vehicle rows, from NJDOT's
NewJersey2023*.zip, recorded 2026-11-08. Every column the reader doesn't read is blanked (no towns, birth dates,
badge numbers or vehicle details)."""

import io
import json
import zipfile
from collections import Counter

from crashiq import packs
from crashiq.sources import nj_njdot

from conftest import FIXTURES

DIR = FIXTURES / "nj_njdot_2023"
TABLES = ("Accidents", "Occupants", "Pedestrians", "Vehicles")


def _read():
    return nj_njdot.read_tables(*[zipfile.ZipFile(DIR / f"Essex2023{t}.zip") for t in TABLES])


def test_every_row_maps_to_the_contract_and_bad_rows_are_counted():
    crashes, dropped = _read()
    pack = packs.get("NJ")
    assert len(crashes) == 31 and dropped == {"duplicate_keys": 1, "broken_lines": 1}
    assert all(packs.check_crash(c, pack) == [] for c in crashes)
    assert Counter(c["county_fips"] for c in crashes) == {"34013": 30, "34001": 1}
    assert sum(c["lat"] is None for c in crashes) == 12 and all(c["primary_road"] for c in crashes)


def test_kabco_from_people_never_below_the_crash_severity():
    crashes, _ = _read()
    assert Counter(c["severity"] for c in crashes) == {"O": 16, "C": 10, "K": 3, "B": 1, "A": 1}
    assert all(c["severity"] == "K" for c in crashes if c["severity_reported"] == "F")
    assert all(c["severity"] in "ABCU" for c in crashes if c["severity_reported"] == "I")
    k = next(c for c in crashes if c["crash_id"] == "20230721I-2023-000406")
    assert (k["killed"], k["ped"], k["collision_type"]) == (1, True, "VEHICLE/PEDESTRIAN")


def test_road_names_in_tiger_form():
    r = nj_njdot.road
    assert r("Fries Mill Road (GLOUCESTER COUNTY 655)") == "Fries Mill Road"
    assert r("CR 681 / PATERSON PLANK RD") == "PATERSON PLANK RD"
    assert r("I- 80 / E RIDGEWOOD AVE / W RIDGEWO") == "E RIDGEWOOD AVE"
    assert (r("MERCER COUNTY 622"), r("ROUTE 535"), r("NJ 17")) == ("CO RD 622", "CO RD 535", "STATE RTE 17")
    assert (r("I-78 Secondary"), r("JACKSON RD **"), r("US 1 (Herbert Highway)")) == ("I-78", "JACKSON RD", "US 1")
    assert r("ESSEX COUNTY 669 (Granada Ave)") == "Granada Ave"      # 600+ county routes: the name, not the number
    assert r("   ") is None


def test_codes_flags_and_offsets():
    crashes, _ = _read()
    assert (sum(c["ped"] for c in crashes), sum(c["bike"] for c in crashes)) == (4, 1)
    assert (sum(c["motorcycle"] for c in crashes), sum(c["heavy_truck"] for c in crashes)) == (3, 6)
    c = next(c for c in crashes if c["crash_id"] == "2023071323-046237")
    assert (c["primary_road"], c["secondary_road"], c["offset_ft"], c["offset_dir"]) == ("CO RD 506", "GATES AVE", 160.0, "W")
    assert (c["date"], c["hour"], c["route"], c["milepost"]) == ("2023-05-22", 13, "00000506__", 6.56)
    with_point = next(c for c in crashes if c["lat"] is not None)
    r = {k: "" for k in nj_njdot.CRASH} | {"severity": "P", "date": "03/04/2021", "lat": "40.708", "lon": "74.1568"}
    old = nj_njdot.contract_record("k", r, [], [], set())
    assert (old["lat"], old["lon"], old["bad_coords"]) == (40.708, -74.1568, False) and with_point["lon"] < 0


def test_fetch_contract_reads_county_files_tries_both_hosts_and_caches(tmp_path):
    calls = []

    def opener(req, timeout):
        calls.append(req.full_url)
        assert req.headers["User-agent"] == nj_njdot.UA
        if req.full_url.startswith("https://dot.nj.gov"):
            return io.BytesIO(b"<html>not found</html>")       # dot.nj.gov answers a miss with a page
        return io.BytesIO((DIR / req.full_url.rsplit("/", 1)[1]).read_bytes())

    box = (40.70, -74.25, 40.80, -74.15)                       # Newark
    got = nj_njdot.fetch_contract(box, ["34013"], [2023, 2024], tmp_path, opener=opener)
    assert len(calls) == 8 and calls[1] == "https://www.nj.gov/transportation/refdata/accident/2023/Essex2023Accidents.zip"
    assert got["years_missing"] == [2024] and got["cleaning"]["duplicate_keys"] == 1
    assert got["cleaning"]["no_point_in_counties"] == 12           # no point: kept for the street-name sort
    assert all(c["lat"] is None or 40.70 <= c["lat"] <= 40.80 for c in got["crashes"])
    assert [p.name for p in tmp_path.iterdir()] == ["nj_njdot_34013_2023.json"]
    again = nj_njdot.fetch_contract(box, ["34013"], [2023], tmp_path, opener=None)    # cached: no network
    assert len(again["crashes"]) == len(got["crashes"])


def test_pack_is_registered_and_its_methods_are_cited():
    pack = packs.get("NJ")
    assert pack.status == "active" and pack.severity_note is None
    assert packs.value(pack, "crash_costs") is None                # 2001 dollars: not printed until indexed
    assert packs.value(pack, "min_years")["years"] == 3
    assert len(json.loads(pack.county_boxes.read_text())["counties"]) == 21
    assert nj_njdot.COUNTY_FILES["34009"] == "CapeMay"
