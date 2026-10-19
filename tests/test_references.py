import io

from pypdf import PdfReader

from crashiq import references

from test_ingest_hardening import _study


def test_every_method_cites_a_listed_source_and_every_source_is_https():
    data = references.load()
    assert data["methods"] and {m["status"] for m in data["methods"]} <= {"follows", "decision", "planned"}
    for m in data["methods"]:
        assert m["cite"], m["topic"]
        assert all(k in data["sources"] for k, _ in m["cite"])
    assert all(s["url"].startswith("https://") for s in data["sources"].values())


def test_the_screen_method_cites_hsm_and_fhwa():
    m = next(m for m in references.load()["methods"] if m["topic"].startswith("Over-represented"))
    assert {"hsm", "fhwa_rsf4"} <= {k for k, _ in m["cite"]}


def test_api_and_pdf_carry_the_references(client):
    assert client.get("/api/references").json()["sources"]["fhwa_ihsdm"]["publisher"] == "FHWA"
    sid = _study(client)
    text = " ".join(" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content)).pages)
    assert "References" in text and "IHSDM Crash Prediction Module" in text and "Local Roadway Safety Manual" in text
