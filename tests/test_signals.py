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


def _mk(lid, n, wet):
    return [dict(location_id=lid, collision_type="REAR END", surface="WET" if i < wet else "DRY", severity="O")
            for i in range(n)]


def test_t12_binomial_handles_a_location_with_more_than_1030_crashes():
    # #358: two segments, no beta prior, so the binomial test runs; math.comb(1200, k) overflowed a float
    placed = _mk("seg-1", 1200, 300) + _mk("seg-2", 400, 20)
    out = signals.screen(placed, [("seg-1", "Mainline A"), ("seg-2", "Mainline B")])
    assert any(s["location_id"] == "seg-1" and s["target"] == "wet" for s in out["signals"])


def test_binom_sf_stays_a_probability_for_large_n():
    p = signals.binom_sf(300, 1200, 0.1)
    assert 0.0 <= p <= 1.0
    assert signals.binom_sf(0, 5000, 0.3) == pytest.approx(1.0)
    assert signals.binom_sf(5001, 5000, 0.3) == 0.0
    assert signals.binom_sf(1500, 5000, 0.3) == pytest.approx(0.5, abs=0.02)     # the mean: about half


def _exact_sf(x, n, p):
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(x, n + 1))


@pytest.mark.parametrize("x, n, p", [(0, 0, 0.5), (3, 10, 0.2), (0, 7, 0.0), (2, 7, 1.0), (40, 100, 0.33),
                                     (300, 1029, 0.25), (600, 1029, 0.5), (11, 10, 0.4)])
def test_binom_sf_is_unchanged_below_1030(x, n, p):
    assert signals.binom_sf(x, n, p) == pytest.approx(_exact_sf(x, n, p), abs=1e-12)


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
    t12 = next(t for t in profile.build(study, net, pull, a)["tables"] if t["id"] == "T12")
    for r in t12["rows"]:
        lid = r["key"].split("~")[0]
        assert r["values"]["reference"] == ("corridor segments" if lid.startswith("seg") else "corridor intersections")


def test_golden_screen_rows_are_consistent():
    study, net, pull, a = golden()
    p = profile.build(study, net, pull, a)
    t12 = next(t for t in p["tables"] if t["id"] == "T12")
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
    # #218: GPS snapped to an intersection while the report states a distance is moved by it; several West 135th
    # Street crashes are on the segments now, so West 147th Street leads (was 12 of 21 at West 135th)
    assert top["text"] == ("Crashes after dark under street lights are over-represented at West 147th Street: "
                           "5 of 8 crashes here (62.5%) vs 35.5% across the corridor intersections.")
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
    f.text = f.text.replace("5 of 8", "7 of 8")
    assert any("7" in r for r in findings.validate(f, tables, findings.context(client.app.state.db, sid)[2], (2021, 2025)))


def test_accepted_findings_print_in_the_pdf(client):
    sid = _study(client)
    shown = client.post(f"/api/studies/{sid}/findings/screen").json()["shown"]
    client.patch(f"/api/studies/{sid}/findings/{shown[0]['id']}?status=accepted")
    pdf = PdfReader(io.BytesIO(client.get(f"/api/studies/{sid}/export.pdf").content))
    text = " ".join(pg.extract_text() for pg in pdf.pages)
    assert "F1. Crashes after dark under street lights over-represented at West 147th Street" in text
    assert shown[1]["title"] not in text                                           # not accepted → not printed
    assert "no AI narrative" in text and "(draft)" in text


def test_patterns_library_is_marked_draft(client):
    lib = client.get("/api/patterns").json()
    assert lib["status"] == "draft" and "type_broadside" in lib["entries"]


def test_findings_are_ordered_fatal_ksi_strength_crashes_with_stale_last_and_named_by_location(client):
    # #267: the most important finding first; a stale one under "Out of date"; a name, never an id
    sid = _study(client)
    client.post(f"/api/studies/{sid}/findings/screen")
    client.app.state.db.execute(
        "INSERT INTO finding (study_id, id, body, status) VALUES (?, 'c7-old', ?, 'proposed')",
        (sid, findings.Finding(id="c7-old", location_id="osm-1035", text="Old claim 99 of 7.",
                               meta={"location": "SEG:OSM-1029:OSM-1035"}).model_dump_json()))
    fs = client.get(f"/api/studies/{sid}/findings").json()["findings"]
    for f in fs:                                       # the rank counts are the finding's own records
        recs = client.get(f"/api/studies/{sid}/findings/{f['id']}/records").json()["records"]
        assert {k: v for k, v in f["rank"].items() if k != "location_fatal_crashes"} == {
            "fatal_crashes": sum(r["severity"] == "K" for r in recs),
            "ksi_crashes": sum(r["severity"] in "KA" for r in recs), "crashes": len(recs)}
    key = [(f["stale"], -(f["rank"]["location_fatal_crashes"] > 0), -f["rank"]["ksi_crashes"],
            -float(f["meta"].get("probability") or 0), -f["rank"]["crashes"]) for f in fs]
    assert key == sorted(key) and fs[-1]["id"] == "c7-old" and fs[-1]["stale"]
    assert sum(f["rank"]["ksi_crashes"] > 0 for f in fs) >= 1 and fs[0]["rank"]["ksi_crashes"] > 0
    assert fs[-1]["location_name"] == "West 132nd Street"                              # T2's label, not the old id
    assert all(f["location_name"] and not f["location_name"].upper().startswith(("SEG:", "INT:", "OSM-")) for f in fs)
    screen_order = [f["id"] for f in client.post(f"/api/studies/{sid}/findings/screen").json()["shown"]]
    assert screen_order != [f["id"] for f in fs if not f["stale"]]                    # the order really changed



def test_a_location_with_a_fatal_crash_leads_even_when_the_finding_s_own_records_have_none(client):
    # PM review of #290: "fatal first" is the location's fatal crashes (T2 sev_k), as #267 says; the finding's own
    # records only set the "Fatal crash" chip
    from crashiq import profile as profile_mod
    sid = _study(client)
    client.post(f"/api/studies/{sid}/findings/screen")
    fs = client.get(f"/api/studies/{sid}/findings").json()["findings"]
    last = fs[-1]
    real = profile_mod.build
    def build(*a, **k):
        prof = real(*a, **k)
        for t in prof["tables"]:
            if t["id"] == "T2":
                for r in t["rows"]:
                    r["values"]["sev_k"] = 1 if r["key"] == last["location_id"] else 0
        return prof
    import pytest
    mp = pytest.MonkeyPatch()
    mp.setattr(profile_mod, "build", build)
    try:
        again = client.get(f"/api/studies/{sid}/findings").json()["findings"]
    finally:
        mp.undo()
    assert again[0]["location_id"] == last["location_id"] and again[0]["rank"]["location_fatal_crashes"] == 1
    assert again[0]["rank"]["fatal_crashes"] == 0                                    # no "Fatal crash" chip for it


def test_a_finding_s_collision_diagram_draws_only_its_records(client):
    # #268: the N10 diagram of the finding's crashes (not the whole intersection's); numbers and "not drawn" by code
    import re
    sid = _study(client)
    client.post(f"/api/studies/{sid}/findings/screen")
    fs = client.get(f"/api/studies/{sid}/findings").json()["findings"]
    seen = set()
    for f in fs:
        recs = client.get(f"/api/studies/{sid}/findings/{f['id']}/records").json()["records"]
        d = client.get(f"/api/studies/{sid}/findings/{f['id']}/diagram").json()
        seen.add(d["kind"])
        assert d["kind"] == f["meta"]["kind"] and d["records"] == len(recs)
        if d["kind"] != "intersection":
            assert d["diagram"] is None and d["strip"]["location_id"] == f["location_id"]
            assert 0 <= d["strip"]["from_ft"] < d["strip"]["to_ft"] <= d["strip"]["length_ft"]
            assert d["strip"]["name"] and d["strip"]["intersections"] and len(d["strip"]["crashes"]) == len(recs)
            continue
        dg = d["diagram"]
        assert sorted(c["crash_id"] for c in dg["crashes"]) == sorted(r["crash_id"] for r in recs)
        numbers = [int(x) for s in dg["steps"] if s["op"] == "text" and re.fullmatch(r"[\d, ]+", s["t"])
                   for x in s["t"].split(",")]
        assert len(numbers) == len(recs) - sum(dg["not_drawn"].values())
        assert d["table"]["id"] == f"T21@{f['id']}" and len(d["table"]["rows"]) == len(recs)
    assert "intersection" in seen


def test_a_segment_finding_s_strip_names_the_segment_and_its_cross_streets(client):
    # PM review of #293: the strip is labelled (segment name, the corridor's study intersections) and shows its crashes
    sid = _study(client)
    net = client.get(f"/api/studies/{sid}/network").json()
    asg = client.get(f"/api/studies/{sid}/assignment").json()["assignments"]
    seg = next(s for s in net["segments"] if any(a["location_id"] == s["id"] for a in asg))
    body = findings.Finding(id="c7-seg", location_id=seg["id"], text="Segment claim.",
                            evidence_refs={"tables": ["T12"], "records": {"location_id": seg["id"]}},
                            meta={"kind": "segment"}).model_dump_json()
    client.app.state.db.execute("INSERT INTO finding (study_id, id, body, status) VALUES (?, 'c7-seg', ?, 'proposed')",
                                (sid, body))
    d = client.get(f"/api/studies/{sid}/findings/c7-seg/diagram").json()
    st = d["strip"]
    assert d["kind"] == "segment" and st["name"] == seg["name"]
    assert (st["from_ft"], st["to_ft"]) == (seg["from_station_ft"], seg["to_station_ft"])
    assert {i["name"] for i in st["intersections"]} >= {i["name"] for i in net["intersections"] if i.get("is_study")}
    n = sum(a["location_id"] == seg["id"] for a in asg)
    assert len(st["crashes"]) == n == d["records"] and all(c["station_ft"] is not None for c in st["crashes"])
