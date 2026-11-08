"""New York sources (state/ny): NYC open data, the DMV statewide table with its reference-marker join, and the CLEAR
export reader. Offline: recorded responses and synthetic exports in tests/fixtures/ny."""

import json

import pytest

from crashiq.osm import metres
from crashiq.sources import ny_clear, ny_dmv, ny_nyc

from conftest import FIXTURES

NY = FIXTURES / "ny"


# ---- NYC (h9gi-nx95 + f55k-p6yu) ----------------------------------------------------------------------------------

@pytest.fixture
def nyc(monkeypatch, tmp_path):
    rec = json.loads((NY / "nyc_2025-03-05.json").read_text())
    seen = []

    def fake_get(url, params):
        seen.append(params)
        assert params["$limit"] <= 50000 and params.get("$offset", 0) == 0
        return rec["crashes"] if url == ny_nyc.CRASHES else rec["persons"]

    monkeypatch.setattr(ny_nyc, "_get", fake_get)
    crashes, persons = ny_nyc.fetch("2025-03-05", "2025-03-05", tmp_path)
    return rec, crashes, persons, seen


def test_nyc_shape_and_severity(nyc):
    rec, crashes, persons, _ = nyc
    assert len(crashes) == len(rec["crashes"]) == 40
    for c in crashes:
        assert c["date"] == "2025-03-05" and c["severity"] in "KABCUO"
        assert (c["lat"] is None) == (c["lon"] is None)
        assert c["lat"] is None or ny_nyc.plausible(c["lat"], c["lon"])
        assert c["severity"] == ("K" if c["killed"] else "U" if c["injured"] or any(
            p["kabco"] for p in persons.get(c["collision_id"], [])) else "O")
    # every person row belongs to a crash in the pull (collision_id links the tables)
    assert set(persons) <= {c["collision_id"] for c in crashes}
    assert sum(len(v) for v in persons.values()) == len(rec["persons"])


def test_nyc_house_address_goes_to_secondary_and_is_collapsed():
    c = ny_nyc.crash_record({"collision_id": "x", "crash_date": "2024-03-05T00:00:00.000", "crash_time": "14:00",
                             "borough": "BRONX", "latitude": "0", "longitude": "0",
                             "off_street_name": "1501      WESTCHESTER AVENUE", "number_of_persons_injured": "1"})
    assert c["secondary_road"] == "1501 WESTCHESTER AVENUE" and c["primary_road"] is None
    assert c["lat"] is None and not c["bad_coords"]          # 0/0 is "no GPS", not bad GPS
    assert c["county_code"] == "005" and c["severity"] == "U"


def test_nyc_person_kabco():
    assert [ny_nyc.person_kabco(v) for v in ("Killed", "Injured", "Unspecified", None)] == ["K", "U", None, None]


def test_nyc_cache_means_one_pull(nyc, monkeypatch, tmp_path):
    _, crashes, _, seen = nyc
    monkeypatch.setattr(ny_nyc, "_get", lambda *a: pytest.fail("cached pull went to the network"))
    again, _ = ny_nyc.fetch("2025-03-05", "2025-03-05", tmp_path)
    assert again == crashes and len(seen) == 2


# ---- NYS DMV statewide (e8ky-4vqe) + NYSDOT reference markers -------------------------------------------------------

@pytest.mark.parametrize("raw,panel", [("9 84041008", "  9 84041008"), ("9N12031058", "  9N12031058"),
                                       ("278IX6M13057", "278IX6M13057"), ("87IX1M11003", " 87IX1M11003"),
                                       ("", None), (None, None), ("12345", None)])
def test_panel_padding(raw, panel):
    assert ny_dmv.panel(raw) == panel


def test_dmv_marker_join(monkeypatch):
    rec = json.loads((NY / "nys_dmv_2024_sample.json").read_text())
    calls = []

    def fake_get(url, params):
        calls.append(params["where"])
        assert url == ny_dmv.MARKERS
        return rec["markers"]

    monkeypatch.setattr(ny_dmv, "_get", fake_get)
    panels = [ny_dmv.panel(r.get("dot_reference_marker_location")) for r in rec["cases"]]
    marks = ny_dmv.marker_points(panels)
    assert calls == [rec["markers_query"]["where"]]          # 30 panels, one request
    crashes = [ny_dmv.crash_record(r, marks) for r in rec["cases"]]
    with_rm = [c for c in crashes if c["reference_marker"]]
    assert len(with_rm) == 30 and all(c["lat"] is None for c in crashes if not c["reference_marker"])
    placed = [c for c in with_rm if c["lat"] is not None]
    assert len(placed) >= 28                                  # 98% measured on 500 (tests/statewide/ny_refmarker_sample.py)
    for c in placed:
        assert 40.4 < c["lat"] < 45.1 and -79.8 < c["lon"] < -71.8 and c["location_method"] == "reference_marker"
        assert c["route"] and c["reference_marker"].startswith(c["reference_marker"][:4])
    assert {c["severity"] for c in crashes} <= set("KUO")
    assert all(c["collision_id"].startswith("nydmv-row-") for c in crashes)


def test_dmv_prefers_current_marker(monkeypatch):
    feats = {"features": [{"attributes": {"Panel": "  9 84041008", "TO_DATE": 1}, "geometry": {"x": -74.0, "y": 42.0}},
                          {"attributes": {"Panel": "  9 84041008", "TO_DATE": None}, "geometry": {"x": -74.1, "y": 42.1}},
                          {"attributes": {"Panel": "  9 84041009", "TO_DATE": 1}, "geometry": {"x": -74.2, "y": 42.2}}]}
    monkeypatch.setattr(ny_dmv, "_get", lambda url, p: feats)
    assert ny_dmv.marker_points(["  9 84041008", "  9 84041009"]) == {"  9 84041008": (42.1, -74.1),
                                                                         "  9 84041009": (42.2, -74.2)}


def test_dmv_severity_and_person_kabco():
    sev = lambda d: ny_dmv.crash_record({"accident_descriptor": d, ":id": "row-1"}, {})["severity"]
    assert [sev(d) for d in ("Fatal Accident", "Injury Accident", "Property Damage & Injury Accident",
                             "Property Damage Accident")] == ["K", "U", "U", "O"]
    assert [ny_dmv.person_kabco(v) for v in ("Killed", "Severe", "Moderate", "Minor", "Injured with Unkn Severity",
                                             "Uninjured")] == ["K", "A", "B", "C", "U", None]


# ---- CLEAR / ALIS export (synthetic, from the published layouts) ----------------------------------------------------

def test_utm18_known_point():
    # Gardiner export: COMPX/COMPY of a crash ~35 m from the intersection the analyst joined (X, Y in degrees)
    lat, lon = ny_clear.utm18_to_latlon(567257.6517, 4616580.899)
    assert metres((lat, lon), (41.6983986, -74.1920013)) < 60
    # the zone's central meridian maps exactly
    assert abs(ny_clear.utm18_to_latlon(500000.0, 4650000.0)[1] + 75.0) < 1e-9


def test_clear_spreadsheet_layout():
    crashes, missing = ny_clear.read(NY / "clear_export_spreadsheet_synthetic.csv")
    assert set(missing) == {"lat", "lon", "kabco"}
    by = {c["collision_id"]: c for c in crashes}
    assert len(by) == 5
    assert [by[f"9000000{i}"]["severity"] for i in range(1, 6)] == ["U", "O", "K", "A", "O"]
    assert by["90000005"]["non_reportable"] and by["90000005"]["lat"] is None and by["90000005"]["parking_lot"]
    a = by["90000001"]
    assert a["datetime"] == "2022-06-29 16:00" and a["reference_marker"] == " 44 86011126"
    assert a["primary_road"] == "ROUTE 44 55" and a["secondary_road"] == "Bruynswick Rd"
    assert a["city_name"] == "Gardiner" and a["county_code"] == "ULSTER" and a["location_method"] == "export_utm18"
    west = by["90000002"]                                     # Chautauqua: zone 18 coordinates far west of the zone
    assert 42.0 < west["lat"] < 42.5 and -79.8 < west["lon"] < -79.2 and west["at_intersection"]


def test_clear_dbf_layout_and_name_collisions():
    crashes, missing = ny_clear.read(NY / "clear_export_dbf_synthetic.csv")
    assert set(missing) == {"lat", "lon"}
    c = crashes[0]
    # COMP_MUNI (town) vs COMP_MUNI_ (type code) squeeze to the same name; COMP_COUNT beats the joined County = ULS
    assert c["city_name"] == "Gardiner" and c["county_code"] == "ULSTER"
    assert c["severity"] == "B" and crashes[1]["severity"] == "O"   # analyst KABCO column wins when present
    assert metres((c["lat"], c["lon"]), (41.6983986, -74.1920013)) < 60


def test_clear_rejects_a_file_without_case_numbers(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="case number"):
        ny_clear.read(p)
