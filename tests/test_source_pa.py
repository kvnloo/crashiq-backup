"""Pennsylvania: PennDOT public crash data reader (sources/pa_penndot.py), offline on a recorded fixture: 46 live
Philadelphia 2024 crashes (CRASH, ROADWAY and FLAGS rows as PennDOT ships them; 5 per severity code, 3 with no GPS,
pedestrian, freeway and '... PK' street rows), cut from Philadelphia_2024.zip on 2026-11-08."""

import io
import json
import urllib.error
import zipfile
from collections import Counter

import pytest

from crashiq import packs
from crashiq.sources import pa_penndot

from conftest import FIXTURES

ZIP = FIXTURES / "pa_penndot_philadelphia_2024.zip"
MUNIS = pa_penndot.municipalities()


def rows():
    with zipfile.ZipFile(ZIP) as z:
        return list(pa_penndot._table(z, "CRASH"))


def recs():
    return pa_penndot.read_zip(ZIP, lambda r: True, MUNIS)


def test_every_crash_maps_to_the_contract():
    pack = packs.get("PA")
    got = recs()
    assert len(got) == len(rows()) == 46
    assert all(packs.check_crash(c, pack) == [] for c in got)
    assert all(c["date"] == "" and 1 <= c["month"] <= 12 and c["year"] == 2024 for c in got)
    assert all(c["county_fips"] == "42101" and c["city"] == "PHILADELPHIA" for c in got)
    assert all(c["day_of_week"] in pa_penndot.DOW.values() for c in got)


def test_severity_follows_max_severity_level():
    by = {c["crash_id"]: c for c in recs()}
    for r in rows():
        assert by[r["CRN"]]["severity"] == pa_penndot.SEVERITY[r["MAX_SEVERITY_LEVEL"]]
    sev = Counter(c["severity"] for c in by.values())
    assert sev["K"] >= 5 and sev["A"] >= 5 and sev["B"] >= 5 and sev["C"] >= 5
    assert sev["U"] >= 10                        # 8 (injury, unknown severity) and 9 (unknown if injured)
    k = next(c for c in by.values() if c["severity"] == "K")
    assert k["killed"] >= 1


def test_streets_from_roadway_rows():
    got = recs()
    assert all(c["primary_road"] for c in got)
    pair = [c for c in got if c["secondary_road"]]
    assert pair and all(c["secondary_road"] != c["primary_road"] for c in pair)
    assert not [c for c in got if (c["primary_road"] or "").endswith(" PK")]      # PK -> PIKE for street_key
    assert pa_penndot.street("limekiln  pk") == "LIMEKILN PIKE" and pa_penndot.street("BROAD ST") == "BROAD ST"
    assert [pa_penndot.street(n) for n in ("SIXTYTHIRD ST", "FIFTY-FIFTH ST", "TWENTIETH ST", "N SECOND ST",
                                           "THIRTEENTH ST", "FIRSTSIDE AV")] == \
        ["63RD ST", "55TH ST", "20TH ST", "N 2ND ST", "13TH ST", "FIRSTSIDE AV"]
    first, second, _ = pa_penndot.roads([{"RDWY_SEQ_NUM": "4", "STREET_NAME": "FOX ST"},
                                        {"RDWY_SEQ_NUM": "3", "STREET_NAME": "HUNTING PARK AV"},
                                        {"RDWY_SEQ_NUM": "5", "STREET_NAME": "HUNTING PARK AV"}])
    assert (first, second) == ("HUNTING PARK AV", "FOX ST")


def test_gps_flags_and_codes():
    got = recs()
    nogps = [c for c in got if c["lat"] is None]
    assert len(nogps) == 3 and not any(c["bad_coords"] for c in nogps)
    assert any(c["is_freeway"] for c in got) and any(not c["is_freeway"] for c in got)
    assert any(c["ped"] and c["collision_type"] == "VEHICLE/PEDESTRIAN" for c in got)
    assert not [c for c in got if (c["collision_type"] or "").startswith("code ")]
    far = pa_penndot.crash_record({**rows()[0], "DEC_LATITUDE": "34.0", "DEC_LONGITUDE": "-118.0"}, [], None, MUNIS)
    assert far["lat"] is None and far["bad_coords"]
    assert pa_penndot.code("4.0") == "4" and pa_penndot.code(" 09") == "9" and pa_penndot.code("") is None


def _opener(seen):
    body = ZIP.read_bytes()

    def opener(req, timeout):
        seen.append(req.full_url)
        if "_2024.zip" not in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        return io.BytesIO(body)
    return opener


def test_fetch_contract_downloads_filters_by_box_and_caches(tmp_path):
    seen = []
    box = (39.90, -75.30, 40.14, -74.95)
    got = pa_penndot.fetch_contract(box, ["42101", "34007"], [2023, 2024], tmp_path, opener=_opener(seen))
    assert seen == ["https://gis.penndot.pa.gov/gishub/crashZip/County/PHILADELPHIA/PHILADELPHIA_2023.zip",
                    "https://gis.penndot.pa.gov/gishub/crashZip/County/PHILADELPHIA/PHILADELPHIA_2024.zip"]
    assert got["years_missing"] == [2023]       # 404: not posted; the NJ county (34007) is skipped
    s, w, n, e = box
    inside = [c for c in got["crashes"] if c["lat"] is not None]
    assert inside and all(s <= c["lat"] <= n and w <= c["lon"] <= e for c in inside)
    assert got["cleaning"]["no_gps"] == 3       # the county's no-GPS crashes come along for the street sort
    again = pa_penndot.fetch_contract(box, ["42101"], [2024], tmp_path, opener=None)    # cached: no network
    assert len(again["crashes"]) == len(got["crashes"])
    tiny = pa_penndot.fetch_contract((39.95, -75.17, 39.96, -75.16), ["42101"], [2024], tmp_path, opener=None)
    assert len(tiny["crashes"]) < len(got["crashes"])


def test_a_cut_off_download_never_lands_in_the_cache(tmp_path):
    with pytest.raises(zipfile.BadZipFile):
        pa_penndot.download("PHILADELPHIA", 2024, tmp_path, opener=lambda req, timeout: io.BytesIO(b"PK\x03\x04junk"))
    assert not list(tmp_path.glob("*.zip"))


def test_pack_is_registered_and_its_methods_are_cited():
    pack = packs.get("PA")
    assert pack.status == "active" and pack.county_boxes.exists()
    assert packs.value(pack, "crash_costs")["K"] == 15327533
    assert packs.value(pack, "min_years") is None                    # research value, not verified
    assert "42101" in json.loads(pack.county_boxes.read_text())["counties"]
    assert len(pa_penndot.COUNTY) == 67 and len({f for _, f in pa_penndot.COUNTY.values()}) == 67
    assert len(MUNIS) == 2567 and MUNIS["67301"] == "PHILADELPHIA"
