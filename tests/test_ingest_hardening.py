"""Fixes from the 2026-10-18 independent review of the step 3 data pipeline (data QA, domain, code, efficiency).
Each test pins one way real CCRS data could have been silently miscounted."""
import copy
import io
import json

import pytest
from pypdf import PdfReader

from crashiq import crashes
from crashiq.sources import ca_ccrs as cc
from crashiq.sources.ckan import Ckan, CkanError
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]
STUDY = {"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}
NET = {"line": LINE, "corridor_name": "Crenshaw Boulevard"}
BASE = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())


def fixture(edit=None):
    d = copy.deepcopy(BASE)
    if edit:
        for rid, t in d["tables"].items():
            if rid.startswith("cra-"):
                for r in t["rows"]:
                    edit(r)
    return d


def pull(d, **kw):
    return crashes.pull(STUDY, NET, Ckan(FakeCkan(d, **kw), retries=0))


def key_numbers(out):
    from collections import Counter
    cs = out["crashes"]
    return (len(cs), Counter(c["severity"] for c in cs), Counter(c["collision_type"] for c in cs),
            sum(c["lighting"] is not None and "DARK" in c["lighting"].upper() for c in cs), sum(c["ped"] for c in cs))


# -- data.ca.gov row cap ----------------------------------------------------------------------------------
def test_row_cap_is_detected_and_paging_adapts():
    full = pull(fixture())
    capped = pull(fixture(), rows_max=7)                     # far below our page size
    assert key_numbers(capped) == key_numbers(full)
    with pytest.raises(CkanError, match="only part of a result"):
        Ckan(FakeCkan(fixture(), rows_max=3), retries=0).sql('SELECT * FROM "cra-2023-0000-0000"')


# -- CHP's coded values and spellings -----------------------------------------------------------------------
def test_code_prefixes_and_chp_spellings_are_normalized():
    letters = {"BROADSIDE": "D", "REAR END": "C", "SIDE SWIPE": "B", "HEAD-ON": "A", "HIT OBJECT": "E",
               "OVERTURNED": "F", "VEHICLE/PEDESTRIAN": "G", "OTHER": "H"}

    def chp_style(r):
        ct = (r.get("Collision Type Description") or "").upper()
        if ct in letters:
            r["Collision Type Description"] = f"{letters[ct]}-{'VEHICLE/PEDESTRAIN' if ct == 'VEHICLE/PEDESTRIAN' else ct}"
        if r.get("LightingDescription"):
            r["LightingDescription"] = "C-" + r["LightingDescription"]
        if r.get("Weather 1"):
            r["Weather 1"] = "A - " + r["Weather 1"]
    assert key_numbers(pull(fixture(chp_style))) == key_numbers(pull(fixture()))
    assert cc.clean_coded("G-VEHICLE/PEDESTRAIN") == "VEHICLE/PEDESTRIAN"
    assert cc.clean_coded("F – Felony") == "Felony"
    assert cc.clean_coded("MAKING U-TURN") == "MAKING U-TURN"            # not a code prefix


# -- dates ------------------------------------------------------------------------------------------------
def test_us_date_format_parses_the_same():
    def us(r):
        d = r["Crash Date Time"]
        y, m, dd, hh, mi = d[0:4], d[5:7], d[8:10], int(d[11:13]), d[14:16]
        r["Crash Date Time"] = f"{int(m)}/{int(dd)}/{y} {hh % 12 or 12}:{mi}:00 {'PM' if hh >= 12 else 'AM'}"
    a, b = pull(fixture(us)), pull(fixture())
    assert key_numbers(a) == key_numbers(b)
    assert [(c["date"], c["hour"]) for c in a["crashes"]] == [(c["date"], c["hour"]) for c in b["crashes"]]
    assert cc.parse_dt("12/31/2024 12:05:00 AM") == ("2024-12-31", 2024, 0)


def test_unrecognized_dates_stop_the_pull_instead_of_dropping_everything():
    def junk(r):
        r["Crash Date Time"] = "Tuesday the fifth"
    with pytest.raises(crashes.PullError, match="Crash Date Time"):
        pull(fixture(junk))


# -- coordinates and the no-coordinates search -------------------------------------------------------------
def test_impossible_coordinates_are_treated_as_missing_not_lost():
    def swap(r):
        if str(r["Collision Id"]) == "9000045":                # a real Crenshaw crash: lat/lon swapped
            r["Latitude"], r["Longitude"] = r["Longitude"], r["Latitude"]
    out = pull(fixture(swap))
    c = next(c for c in out["crashes"] if c["crash_id"] == "9000045")
    assert c["lat"] is None and c["location_source"] == "unmatched"
    assert out["cleaning"]["implausible_coords"] == 1


def test_crashes_without_coordinates_are_limited_to_the_study_stretch(client):
    d = fixture()
    rid = "cra-2024-0000-0000"
    row = dict(next(r for r in d["tables"][rid]["rows"] if str(r["Collision Id"]) == "9200003"))
    row.update({"Collision Id": 9200099, "PrimaryRoad": "CRENSHAW BL", "SecondaryRoad": "W 190TH ST"})
    d["tables"][rid]["rows"].append(row)                       # same street, miles south of the study
    client.app.state.ckan = FakeCkan(d)
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    sid = client.post("/api/studies", json={"name": "S", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    r = client.post(f"/api/studies/{sid}/crashes/pull").json()
    assert r["cleaning"]["no_coords_off_study_stretch"] == 1
    ids = {c["crash_id"] for c in client.get(f"/api/studies/{sid}/crashes").json()["crashes"]}
    assert "9200099" not in ids and "9200005" in ids           # 135th (Gardena) is a study intersection


# -- parties, freeway, missing years ------------------------------------------------------------------------
def test_parties_are_one_row_per_party():
    out = pull(fixture())
    c = next(c for c in out["crashes"] if c["crash_id"] == "9100002")
    nums = [p["party_number"] for p in c["parties"]]
    assert len(nums) == len(set(nums)) and out["cleaning"]["duplicate_parties_dropped"] >= 1


def test_freeway_crashes_are_excluded_with_their_own_rule(client):
    def fwy(r):
        if str(r["Collision Id"]) == "9000045":
            r["IsFreeway"] = "True"
    client.app.state.ckan = FakeCkan(fixture(fwy))
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    sid = client.post("/api/studies", json={"name": "F", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    client.post(f"/api/studies/{sid}/crashes/pull")
    a = client.get(f"/api/studies/{sid}/assignment").json()
    assert a["excluded_by_rule"]["freeway"] == 1
    assert next(x for x in a["assignments"] if x["crash_id"] == "9000045")["rule"] == "freeway"


def test_no_crash_table_for_any_year_is_an_error_not_zero_crashes():
    d = fixture()
    d["package"]["resources"] = [r for r in d["package"]["resources"] if not r["name"].startswith("Crashes")]
    with pytest.raises(crashes.PullError, match="any year"):
        pull(d)


# -- stale pulls and stale findings -------------------------------------------------------------------------
def _study(client):
    client.app.state.ckan = FakeCkan(fixture())
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    sid = client.post("/api/studies", json={"name": "Crenshaw Blvd safety", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    client.post(f"/api/studies/{sid}/crashes/pull")
    return sid


def test_a_pull_from_an_old_window_is_never_used(client):
    sid = _study(client)
    assert client.get(f"/api/studies/{sid}").json()["progress"]["crashes"] is True
    client.patch(f"/api/studies/{sid}", json={"from_year": 2024, "to_year": 2025})
    for path in ("profile", "assignment", "export.pdf"):
        r = client.get(f"/api/studies/{sid}/{path}")
        assert r.status_code == 409 and "pull them again" in r.json()["detail"]
    assert client.get(f"/api/studies/{sid}").json()["progress"]["crashes"] is False
    client.post(f"/api/studies/{sid}/crashes/pull")
    assert client.get(f"/api/studies/{sid}/profile").status_code == 200


def test_submitted_findings_cannot_approve_themselves(client):
    sid = _study(client)
    shown = client.post(f"/api/studies/{sid}/findings/screen").json()["shown"]
    forged = {**shown[0], "id": shown[1]["id"], "status": "accepted", "source": "screen"}
    r = client.post(f"/api/studies/{sid}/findings", json=[forged]).json()
    f = r["shown"][0]
    assert f["status"] == "proposed" and f["source"] == "analyst" and f["id"] not in {x["id"] for x in shown}
    stored = {x["id"]: x for x in client.get(f"/api/studies/{sid}/findings").json()["findings"]}
    assert stored[shown[1]["id"]]["text"] == shown[1]["text"]          # nothing was overwritten


def test_accepted_findings_that_no_longer_match_are_flagged_and_left_out_of_the_pdf(client):
    sid = _study(client)
    top = client.post(f"/api/studies/{sid}/findings/screen").json()["shown"][0]
    ok = client.patch(f"/api/studies/{sid}/findings/{top['id']}?status=accepted").json()
    assert ok["meta"]["decided_at"] and ok["stale"] is False
    client.patch(f"/api/studies/{sid}", json={"radius_ft": 120})
    client.post(f"/api/studies/{sid}/crashes/pull")                    # radius changes the bbox margin → re-pull
    f = next(x for x in client.get(f"/api/studies/{sid}/findings").json()["findings"] if x["id"] == top["id"])
    assert f["stale"] is True and f["stale_reasons"]
    assert client.patch(f"/api/studies/{sid}/findings/{top['id']}?status=accepted").status_code == 409
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content)).pages)
    assert top["title"] not in text and "no longer match the data" in text


def test_pdf_states_the_method_and_what_it_does_not_do(client):
    sid = _study(client)
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content)).pages)
    flat = " ".join(text.split())
    assert "nearest study intersection within 250 ft" in flat
    assert "does not compare the corridor's crash rates with statewide" in flat
    assert "including 1 fatal or serious-injury crash(es) not in the KSI count" in flat   # 9200003 (A), unplaced
