"""C7 over-representation screen (T12) and the code-written findings built on it."""
import io
import math

import pytest
from pypdf import PdfReader

from crashiq import findings, profile, signals
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES
from test_profile import golden

LINE = [[33.8953, -118.32662], [33.9123, -118.32662]]


def test_incomplete_beta_matches_closed_forms():
    assert signals.betainc(1, 1, 0.3) == pytest.approx(0.3)                       # uniform
    x = 0.4
    assert signals.betainc(2, 3, x) == pytest.approx(6 * x**2 - 8 * x**3 + 3 * x**4)  # Beta(2,3) CDF
    assert signals.betainc(5, 2, 0.7) + signals.betainc(2, 5, 0.3) == pytest.approx(1.0)  # symmetry
    assert signals.betainc(40.5, 60.2, 0.42) == pytest.approx(1 - signals.betainc(60.2, 40.5, 0.58))


def test_binomial_tail():
    assert signals.binom_sf(3, 10, 0.2) == pytest.approx(1 - sum(math.comb(10, k) * .2**k * .8**(10 - k) for k in range(3)))
    assert signals.binom_sf(0, 7, 0.4) == pytest.approx(1.0)


def test_beta_prior_method_of_moments_and_invalid_cases():
    a, b = signals.beta_prior([0.2, 0.4, 0.3, 0.5, 0.1], 0.3)
    s2 = sum((p - 0.3) ** 2 for p in [0.2, 0.4, 0.3, 0.5, 0.1]) / 4
    assert a / (a + b) == pytest.approx(0.3)                                       # prior mean = p*
    assert a * b / ((a + b) ** 2 * (a + b + 1)) == pytest.approx(s2)               # prior variance = s^2
    assert signals.beta_prior([0.3, 0.3, 0.3], 0.3) is None                        # no spread
    assert signals.beta_prior([0.1, 0.9], 0.5) is None                             # too few locations
    assert signals.beta_prior([0.0, 1.0, 0.0, 1.0], 0.5) is None                   # alpha/beta <= 0


def test_golden_screen_rows_are_consistent():
    study, net, pull, a = golden()
    p = profile.build(study, net, pull, a)
    t12 = p["tables"][-1]
    assert t12["id"] == "T12" and t12["rows"]
    for r in t12["rows"]:
        v = r["values"]
        assert v["target_crashes"] >= signals.MIN_TARGET_CRASHES and v["location_crashes"] >= signals.MIN_LOCATION_CRASHES
        assert v["share_pct"] == profile.pct(v["target_crashes"], v["location_crashes"])
        assert v["corridor_share_pct"] == profile.pct(v["corridor_target"], v["corridor_crashes"])
        assert v["share_pct"] > v["corridor_share_pct"]
        assert signals.PROB_MODERATE <= v["probability"] <= 0.99
        assert "/" not in r["key"]                                                 # cell addresses split on "/"
    assert [s["row"] for s in p["signals"]] == [r["key"] for r in t12["rows"]][:len(p["signals"])]


def _study(client):
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "Crenshaw Blvd safety", "mode": "tis"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": LINE})
    client.post(f"/api/studies/{sid}/crashes/pull")
    return sid


def test_crenshaw_screen_findings_pass_the_validator(client):
    sid = _study(client)
    r = client.post(f"/api/studies/{sid}/findings/screen").json()
    assert r["rejected"] == [] and len(r["shown"]) >= 2
    top = r["shown"][0]
    assert top["text"] == ("Crashes after dark are over-represented at West 135th Street: "
                           "12 of 20 crashes here (60%) vs 36.2% corridor-wide.")
    assert top["source"] == "screen" and top["meta"]["strength"] == "Strong" and top["evidence_refs"]["tables"] == ["T12"]
    assert top["pattern_ref"] and top["meta"]["library_status"] == "draft"
    for f in r["shown"]:                                                           # evidence = exactly the counted crashes
        recs = client.get(f"/api/studies/{sid}/findings/{f['id']}/records").json()["records"]
        assert len(recs) == f["numbers"][0]["value"]
    per_loc = {}
    for f in r["shown"]:
        per_loc[f["location_id"]] = per_loc.get(f["location_id"], 0) + 1
    assert max(per_loc.values()) <= signals.MAX_PER_LOCATION


def test_rerun_keeps_decisions_and_drops_unsupported_findings(client):
    sid = _study(client)
    shown = client.post(f"/api/studies/{sid}/findings/screen").json()["shown"]
    client.patch(f"/api/studies/{sid}/findings/{shown[0]['id']}?status=accepted")
    client.app.state.db.execute(
        "INSERT INTO finding (study_id, id, body, status) VALUES (?, 'c7-stale', ?, 'proposed')",
        (sid, findings.Finding(id="c7-stale", text="x").model_dump_json()))
    again = client.post(f"/api/studies/{sid}/findings/screen").json()["shown"]
    assert again[0]["status"] == "accepted"
    ids = [f["id"] for f in client.get(f"/api/studies/{sid}/findings").json()["findings"]]
    assert "c7-stale" not in ids and len(ids) == len(again)


def test_tampered_screen_numbers_are_rejected(client):
    sid = _study(client)
    prof, tables, _ = findings.context(client.app.state.db, sid)
    f = findings.screen_findings(prof, tables)[0]
    f.text = f.text.replace("12 of 20", "14 of 20")
    assert any("14" in r for r in findings.validate(f, tables, findings.context(client.app.state.db, sid)[2], (2021, 2025)))


def test_accepted_findings_print_in_the_pdf(client):
    sid = _study(client)
    shown = client.post(f"/api/studies/{sid}/findings/screen").json()["shown"]
    client.patch(f"/api/studies/{sid}/findings/{shown[0]['id']}?status=accepted")
    pdf = PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content))
    text = " ".join(pg.extract_text() for pg in pdf.pages)
    assert "F1. Crashes after dark over-represented at West 135th Street" in text
    assert shown[1]["title"] not in text                                           # not accepted → not printed
    assert "no AI narrative" in text and "(draft)" in text


def test_patterns_library_is_marked_draft(client):
    lib = client.get("/api/patterns").json()
    assert lib["status"] == "draft" and "type_broadside" in lib["entries"]
