"""C7/C8 (#45): HSM threshold-proportion test, screening rules, templated findings through the C10 validator."""
import json

import pytest

from crashiq import patterns as P

from conftest import FIXTURES


def test_betainc_matches_closed_forms():
    assert P.betainc(2, 3, 0.3) == pytest.approx(0.3483, abs=1e-4)      # binomial-sum identity
    assert 1 - P.betainc(4, 2, 0.5) == pytest.approx(0.8125, abs=1e-6)   # 3 of 4 under a uniform prior
    assert P.betainc(1, 1, 0.37) == pytest.approx(0.37)
    assert P.betainc(5, 5, 0.5) == pytest.approx(0.5)


def test_reference_threshold_and_hsm_variance():
    sites = [(2, 10), (1, 10), (6, 10), (1, 10)]
    ref = P.reference(sites)
    assert ref["p_star"] == pytest.approx(10 / 40)
    # HSM: s2 = [Σ (t²-t)/(n²-n) - (Σ t/n)² / k] / (k-1)
    expect = ((2 / 90 + 0 + 30 / 90 + 0) - (0.2 + 0.1 + 0.6 + 0.1) ** 2 / 4) / 3
    assert ref["variance"] == pytest.approx(expect)
    a = (0.25 ** 2 - 0.25 ** 3 - expect * 0.25) / expect
    assert ref["alpha"] == pytest.approx(a) and ref["beta"] == pytest.approx(a / 0.25 - a)


def test_variance_not_estimable_uses_conservative_pooled_prior():
    ref = P.reference([(3, 5), (1, 5)])      # p* = 0.4, sites agree too well for an HSM variance
    assert ref["alpha"] is None and ref["pooled_n"] == 10
    prob, method = P.probability_exceeds(3, 5, ref)
    assert method.startswith("pooled reference prior")
    assert prob == pytest.approx(1 - P.betainc(0.4 * 10 + 3, 0.6 * 10 + 2, 0.4))
    assert prob < 1 - P.betainc(4, 3, 0.4)    # stricter than a uniform prior


def _crash(lid, ctype, sev="O"):
    return {"location_id": lid, "collision_type": ctype, "severity": sev, "lighting": "DAYLIGHT"}


LOCS = [{"key": k, "label": f"Street {k}", "values": {"kind": "intersection"}} for k in "ABCD"]


def test_screen_flags_the_outlier_only_with_two_or_more_targets():
    placed = ([_crash("A", "BROADSIDE")] * 7 + [_crash("A", "REAR END")] * 2
              + [_crash("B", "REAR END")] * 8 + [_crash("B", "BROADSIDE")]
              + [_crash("C", "REAR END")] * 8 + [_crash("C", "BROADSIDE")]
              + [_crash("D", "REAR END")] * 9 + [_crash("D", "HEAD-ON")])
    flags = P.screen(placed, LOCS)
    hits = {(f["location_id"], f["pattern"]) for f in flags}
    assert ("A", "broadside") in hits
    assert ("D", "head_on") not in hits                        # one head-on: below the 2-crash minimum
    a = next(f for f in flags if (f["location_id"], f["pattern"]) == ("A", "broadside"))
    assert (a["target"], a["total"]) == (7, 9) and a["probability_pct"] >= 90 and a["reference_pct"] == round(100 * 9 / 37, 1)


def test_findings_text_cites_every_number_and_hedges():
    placed = [_crash("A", "BROADSIDE")] * 7 + [_crash("A", "REAR END")] * 2 + \
             [_crash(x, "REAR END") for x in "BCD" for _ in range(8)] + [_crash(x, "BROADSIDE") for x in "BC"]
    t12 = P.table_t12(P.screen(placed, LOCS))
    f = next(x for x in P.findings_from(t12) if x["id"] == "auto-A-broadside")
    assert "7 of 9 crashes" in f["text"] and "to verify in the field" in f["text"]
    assert {n["cell"].split("/")[-1] for n in f["numbers"]} == {"target", "total", "share_pct", "reference_pct",
                                                                "probability_pct"}
    assert f["evidence_refs"]["records"] == {"location_id": "A", "collision_type": ["BROADSIDE"]}


def test_library_seed_has_every_pattern_and_no_digits_in_prose():
    lib = P.library()["patterns"]
    assert set(lib) == set(P.PATTERNS) and all(e["phrase"] for e in lib.values())
    for e in lib.values():
        prose = " ".join(e["factors_intersection"] + e["factors_segment"] + e["field_checks"])
        assert not any(ch.isdigit() for ch in prose)          # the validator would read digits as claims


def test_api_generate_passes_validator_and_keeps_user_decisions(client):
    from crashiq.sources.fake_ckan import FakeCkan
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "Crenshaw", "mode": "profile"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9123, -118.32662]]})
    client.post(f"/api/studies/{sid}/crashes/pull")
    prof = client.get(f"/api/studies/{sid}/profile").json()
    t12 = next(t for t in prof["tables"] if t["id"] == "T12")
    g = client.post(f"/api/studies/{sid}/findings/generate").json()
    assert g["rejected"] == [] and len(g["shown"]) == g["flagged"] == len(t12["rows"])
    if g["shown"]:
        fid = g["shown"][0]["id"]
        client.patch(f"/api/studies/{sid}/findings/{fid}?status=accepted")
        again = client.post(f"/api/studies/{sid}/findings/generate").json()
        assert next(x for x in again["shown"] if x["id"] == fid)["status"] == "accepted"
    json.dumps(g)
