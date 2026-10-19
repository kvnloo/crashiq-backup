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


def test_hsm_variance_removes_sampling_noise():
    """Sites drawn from a known Beta(6, 14) (true between-site variance 0.01): the HSM variance recovers it,
    while the raw spread of observed shares also carries each site's binomial noise and overstates it."""
    import random
    rng = random.Random(7)
    a, b, n = 6, 14, 20
    true_var = a * b / ((a + b) ** 2 * (a + b + 1))
    sites = []
    for _ in range(3000):
        p = rng.betavariate(a, b)
        sites.append((sum(rng.random() < p for _ in range(n)), n))
    shares = [x / n for x, _ in sites]
    mean = sum(shares) / len(shares)
    raw = sum((q - mean) ** 2 for q in shares) / (len(shares) - 1)
    assert signals.hsm_variance(sites) == pytest.approx(true_var, rel=0.15)
    assert raw > 1.5 * true_var


def test_beta_prior_and_invalid_cases():
    sites = [(2, 10), (4, 10), (3, 10), (6, 10), (0, 10), (5, 10)]
    p_star = sum(x for x, _ in sites) / sum(n for _, n in sites)
    a, b = signals.beta_prior(sites, p_star)
    s2 = signals.hsm_variance(sites)
    assert a / (a + b) == pytest.approx(p_star)                                    # prior mean = p*
    assert a * b / ((a + b) ** 2 * (a + b + 1)) == pytest.approx(s2)               # prior variance = s^2
    assert signals.beta_prior([(3, 10), (3, 10), (3, 10)], 0.3) is None            # no spread beyond noise
    assert signals.beta_prior([(1, 10), (9, 10)], 0.5) is None                     # fewer than 3 sites
    assert signals.hsm_variance([(1, 1), (0, 1), (1, 1)]) is None                  # sites with n < 2 don't count


def test_intersections_and_segments_are_screened_against_their_own_kind():
    study, net, pull, a = golden()
    t12 = profile.build(study, net, pull, a)["tables"][-1]
    for r in t12["rows"]:
        lid = r["key"].split("~")[0]
        assert r["values"]["reference"] == ("corridor segments" if lid.startswith("seg") else "corridor intersections")


def test_golden_screen_rows_are_consistent():
    study, net, pull, a = golden()
    p = profile.build(study, net, pull, a)
    t12 = p["tables"][-1]
    assert t12["id"] == "T12" and t12["rows"]
    for r in t12["rows"]:
        v = r["values"]
        assert v["target_crashes"] >= signals.MIN_TARGET_CRASHES and v["location_crashes"] >= signals.MIN_LOCATION_CRASHES
        assert v["share_pct"] == profile.pct(v["target_crashes"], v["location_crashes"])
        assert v["reference_share_pct"] == profile.pct(v["reference_target"], v["reference_crashes"])
        assert v["share_pct"] > v["reference_share_pct"]
        assert signals.PROB_MODERATE <= v["probability"] <= 0.99
        assert "/" not in r["key"]                                                 # cell addresses split on "/"
    assert [s["row"] for s in p["signals"]] == [r["key"] for r in t12["rows"]][:len(p["signals"])]
    ex = [r["values"]["excess_pct"] for r in t12["rows"]]
    assert ex == sorted(ex, reverse=True)                                          # HSM: ranked by excess


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
    assert top["text"] == ("Crashes after dark under street lights are over-represented at West 135th Street: "
                           "12 of 20 crashes here (60%) vs 40% across the corridor intersections.")
    assert top["source"] == "screen" and top["meta"]["strength"] == "Moderate" and top["evidence_refs"]["tables"] == ["T12"]
    assert top["meta"]["method"].startswith("Binomial") and "not a probability" in top["meta"]["method"]
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
    assert "F1. Crashes after dark under street lights over-represented at West 135th Street" in text
    assert shown[1]["title"] not in text                                           # not accepted → not printed
    assert "no AI narrative" in text and "(draft)" in text


def test_patterns_library_is_marked_draft(client):
    lib = client.get("/api/patterns").json()
    assert lib["status"] == "draft" and "type_broadside" in lib["entries"]
