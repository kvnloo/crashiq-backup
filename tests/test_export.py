import io

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader

from crashiq import export, profile
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES
from test_profile import golden


@pytest.fixture
def data():
    study, net, pull, a = golden()
    study.update(name="Main St safety", mode_label="Traffic-study safety section", radius_ft=250, buffer_ft=100)
    net["corridor_name"] = "Main St"
    return {"study": study, "network": net, "profile": profile.build(study, net, pull, a), "generated": "2026-10-18 20:00 UTC"}


def test_xlsx_has_a_sheet_per_table_and_every_number_matches(data):
    wb = load_workbook(io.BytesIO(export.to_xlsx(data)))
    p = data["profile"]
    assert wb.sheetnames[0] == "Study" and len(wb.sheetnames) == 1 + len(p["tables"])
    for t, name in zip(p["tables"], wb.sheetnames[1:]):
        ws = wb[name]
        assert ws["A1"].value.startswith(t["id"] + " ·")
        header = [c.value for c in ws[2]]
        for i, r in enumerate(t["rows"], start=3):
            row = [c.value for c in ws[i]]
            assert row[0] == r["key"] and row[1] == r["label"]
            for c in t["columns"]:
                assert row[header.index(c["label"])] == r["values"].get(c["key"]), (t["id"], r["key"], c["key"])


def test_xlsx_text_that_looks_like_a_formula_stays_text(data):
    """A project name or police text starting with '=' was written as a live formula (found 2026-11-11)."""
    data["study"]["name"] = '=HYPERLINK("http://evil.example","x")'
    data["profile"]["tables"][0]["rows"][0]["label"] = "=1+1"
    wb = load_workbook(io.BytesIO(export.to_xlsx(data)))
    cells = [c for ws in wb for row in ws.iter_rows() for c in row]
    assert not [c.coordinate for c in cells if c.data_type == "f"]
    assert wb["Study"]["B2"].value == data["study"]["name"]                # kept exactly, as text


def test_xlsx_study_sheet_has_caveats_and_credits(data):
    ws = load_workbook(io.BytesIO(export.to_xlsx(data)))["Study"]
    text = " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)
    for c in data["profile"]["caveats"]:
        assert c["text"] in text
    assert "public domain" in text and "OpenStreetMap" in text and "no AI narrative" in text


def test_pdf_opens_and_shows_the_profile_numbers(data):
    pdf = PdfReader(io.BytesIO(export.to_pdf(data)))
    assert len(pdf.pages) >= 2
    text = " ".join(pg.extract_text() for pg in pdf.pages)
    p = data["profile"]
    v = lambda a: profile.cell(p["tables"], a)
    assert "Main St safety: crash profile" in text
    for a in p["kpis"].values():
        assert f"{v(a):,}" in text
    assert "Broadside" in text and "91.32" in text           # T4 label and the S1 segment rate from T2
    assert "no AI narrative" in text and "OpenStreetMap" in text
    assert "Source: table T2" in text


def test_api_downloads(client):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "Crenshaw Blvd safety", "mode": "tis"}).json()["id"]
    assert client.get(f"/api/studies/{sid}/export.pdf").status_code == 409            # nothing to export yet
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9123, -118.32662]]})
    client.post(f"/api/studies/{sid}/crashes/pull")
    x = client.get(f"/api/studies/{sid}/export.xlsx")
    assert x.status_code == 200 and "CrashIQ_Crenshaw_Blvd_safety_2021-2025.xlsx" in x.headers["content-disposition"]
    load_workbook(io.BytesIO(x.content))
    f = client.get(f"/api/studies/{sid}/export.pdf")
    assert f.status_code == 200 and f.content[:4] == b"%PDF"


def test_study_reports_progress_for_the_rail(client):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "P", "mode": "tis"}).json()["id"]
    assert client.get(f"/api/studies/{sid}").json()["progress"] == {"corridor": False, "crashes": False}
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9123, -118.32662]]})
    assert client.get(f"/api/studies/{sid}").json()["progress"] == {"corridor": True, "crashes": False}
    client.post(f"/api/studies/{sid}/crashes/pull")
    assert client.get(f"/api/studies/{sid}").json()["progress"] == {"corridor": True, "crashes": True}


def test_pdf_and_drill_down_carry_one_collision_diagram_per_study_intersection(client):
    # #106 (N10): the location drill-down returns the diagram and T21; the PDF draws the same steps
    from pypdf import PdfReader
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "D", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9123, -118.32662]]})
    client.post(f"/api/studies/{sid}/crashes/pull")
    a = client.get(f"/api/studies/{sid}/assignment").json()
    lid = next(x["location_id"] for x in a["assignments"] if x["kind"] == "intersection")
    loc = client.get(f"/api/studies/{sid}/profile/locations/{lid}").json()
    d = loc["diagram"]
    t21 = next(t for t in loc["tables"] if t["id"] == f"T21@{lid}")
    assert len(t21["rows"]) == len(d["crashes"]) == sum(x["location_id"] == lid for x in a["assignments"])
    assert d["steps"] and d["legend"]["marks"]
    seg = next((x["location_id"] for x in a["assignments"] if x["kind"] == "segment"), None)
    if seg:
        assert client.get(f"/api/studies/{sid}/profile/locations/{seg}").json()["diagram"] is None
    text = "".join(pg.extract_text() for pg in PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content)).pages)
    assert "Collision diagrams" in text
