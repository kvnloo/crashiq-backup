"""The user's #34 decisions (2026-10-18), each pinned by a test."""
import io
import json
from datetime import date

import pytest
from pypdf import PdfReader

from crashiq import findings, network, profile, signals, study
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]
OSM = json.loads((FIXTURES / "overpass_crenshaw.json").read_text())


def _study(client, ckan=None):
    client.app.state.ckan = ckan or FakeCkan(FIXTURES / "ckan_crenshaw.json")
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    sid = client.post("/api/studies", json={"name": "Crenshaw Blvd safety", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    client.post(f"/api/studies/{sid}/crashes/pull")
    return sid


# item 8 — default window ends on the last finalized year ------------------------------------------------
@pytest.mark.parametrize("on,final", [(date(2026, 10, 18), 2024), (date(2027, 7, 1), 2025), (date(2027, 6, 30), 2024)])
def test_last_final_year_waits_18_months(on, final):
    assert study.last_final_year(on) == final


# items 3/11 — two-way AADT; a T counts half the minor road ----------------------------------------------
def test_legs_are_detected_from_osm():
    legs = {i["name"]: i["legs"] for i in network.detect(OSM, [tuple(p) for p in LINE])["intersections"]}
    assert legs["West 147th Street"] == 3                          # fixture: west side only
    assert legs["Marine Avenue"] == legs["Rosecrans Avenue"] == 4


def test_entering_volume_rule():
    assert profile.entering_volume(30000, 10000, 4) == 40000
    assert profile.entering_volume(30000, 10000, 3) == 35000       # T: minor/2
    assert profile.entering_volume(30000, 10000, None) == 40000    # legs unknown: assume a through cross street
    assert profile.entering_volume(None, 10000, 4) is None
    assert profile.intersection_rate(10, 5, 30000, 10000, 3) == pytest.approx(10 * 1e6 / (365 * 5 * 35000))


def test_t_intersection_rate_and_legs_override(client):
    sid = _study(client)
    net = client.get(f"/api/studies/{sid}/network").json()
    t = next(i for i in net["intersections"] if i["legs"] == 3)
    client.patch(f"/api/studies/{sid}/intersections/{t['id']}", json={"major_aadt": 30000, "minor_aadt": 10000})
    rows = {r["key"]: r for r in next(x for x in client.get(f"/api/studies/{sid}/profile").json()["tables"] if x["id"] == "T2")["rows"]}
    n = rows[t["id"]]["values"]["crashes"]
    assert rows[t["id"]]["values"]["rate"] == pytest.approx(round(n * 1e6 / (365 * 5 * 35000), 2))
    client.patch(f"/api/studies/{sid}/intersections/{t['id']}", json={"legs": 4})      # engineer overrides
    rows = {r["key"]: r for r in next(x for x in client.get(f"/api/studies/{sid}/profile").json()["tables"] if x["id"] == "T2")["rows"]}
    assert rows[t["id"]]["values"]["rate"] == pytest.approx(round(n * 1e6 / (365 * 5 * 40000), 2))
    assert client.patch(f"/api/studies/{sid}/intersections/{t['id']}", json={"legs": 2}).status_code == 422


# item 9 — freeway excluded by default, with an include switch --------------------------------------------
def test_freeway_include_switch(client):
    d = json.loads((FIXTURES / "ckan_crenshaw.json").read_text())
    for rid, t in d["tables"].items():
        for r in t["rows"]:
            if str(r.get("Collision Id")) == "9000045":
                r["IsFreeway"] = "True"
    sid = _study(client, FakeCkan(d))
    a = client.get(f"/api/studies/{sid}/assignment").json()
    assert a["excluded_by_rule"].get("freeway") == 1
    assert client.patch(f"/api/studies/{sid}", json={"include_freeway": True}).json()["include_freeway"] is True
    a = client.get(f"/api/studies/{sid}/assignment").json()
    assert "freeway" not in a["excluded_by_rule"]


# item 13 — COVID note covers 2020 and 2021 ---------------------------------------------------------------
def test_covid_note_covers_2021(client):
    sid = _study(client)                                          # 2021–2025
    caveats = client.get(f"/api/studies/{sid}/profile").json()["caveats"]
    assert any(c["key"] == "covid" and "2021" in c["text"] for c in caveats)


# item 14 — dark split into lit and unlit -----------------------------------------------------------------
def test_dark_is_split_into_lit_and_unlit():
    lit, unlit = {"lighting": "DARK-STREET LIGHTS"}, {"lighting": "DARK-NO STREET LIGHTS"}
    off = {"lighting": "Dark - Street Lights Not Functioning*"}
    assert profile.is_dark(lit) and not profile.is_unlit(lit)
    assert profile.is_unlit(unlit) and profile.is_unlit(off)
    keys = {t["key"] for t in signals.targets([lit, unlit])}
    assert {"dark_lit", "dark_unlit"} <= keys and "dark" not in keys
    f = findings.RecordFilter(lighting_dark=True, lighting_unlit=True)
    assert findings.select_records([lit, unlit, off], f) == [unlit, off]


# item 16 — multiple-comparisons disclosure ---------------------------------------------------------------
def test_pdf_discloses_how_many_tests_ran(client):
    sid = _study(client)
    p = client.get(f"/api/studies/{sid}/profile").json()
    assert p["screen_tests"] > 0
    text = " ".join(" ".join(pg.extract_text().split())
                    for pg in PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content)).pages)
    assert f"The screen ran {p['screen_tests']} location × crash-type tests" in text


def test_short_windows_are_flagged_for_a_warning(client):
    opts = client.get("/api/studies/meta").json()["window_options"]
    assert [o["short"] for o in opts[:3]] == [True, True, False]


