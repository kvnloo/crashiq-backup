"""Tester (#176): golden T12 on LIVE data. The over-representation screen (HSM excess-proportion test) recounted from
the raw recorded CCRS rows with code that shares nothing with signals.py: target membership read from CHP's own
fields, p*, the HSM variance, the method-of-moments beta prior, and P(true share > p*) from a numerically integrated
beta density (no continued fraction). The app decides which crashes are placed at which location (T2, tested in
test_golden_live); this file checks what T12 does with them.

Fixtures: tests/fixtures/live/ (Crenshaw Blvd, Union City Blvd), the same as test_golden_live."""

from __future__ import annotations

import math
import re
from collections import defaultdict

import pytest

from test_golden_live import _ref_road_users, raw_tables, reference, run, table

MIN_N, MIN_X, PROB_REPORT, PROB_STRONG = 5, 3, 0.80, 0.95      # docs/03 #34 thresholds, as the issue states them
SKIP = {"", "OTHER", "NOT STATED", "NOT_STATED"}
MOTO = re.compile(r"Motorcycle|MotorDrivenCycle", re.I)         # CHP vehicle types: motorcycle, moped/scooter


def _beta_sf(a: float, b: float, x: float, steps: int = 20000) -> float:
    """P(Beta(a, b) > x) by Simpson's rule on the density, in log space (independent of the app's betainc)."""
    lb = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)

    def pdf(t):
        if t <= 0 or t >= 1:
            return 0.0
        return math.exp((a - 1) * math.log(t) + (b - 1) * math.log1p(-t) - lb)
    # integrate on [x, 1] with a substitution that handles the endpoint singularities when a or b < 1
    h = (1 - x) / steps
    s = pdf(x + 1e-12) + pdf(1 - 1e-12)
    for i in range(1, steps):
        s += (4 if i % 2 else 2) * pdf(x + i * h)
    return s * h / 3


def _binom_ge(x: int, n: int, p: float) -> float:
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(x, n + 1))


def _targets(name, crash, sev):
    """Target crash sets from CHP's raw fields (the reference's own reading)."""
    raw = raw_tables(name)
    veh = defaultdict(list)
    for r in raw["Parties"]:
        veh[str(r["CollisionId"])].append(str(r.get("Vehicle1TypeDesc") or ""))
    ped, bike, ebike, escooter = _ref_road_users(name, crash)
    ct = lambda r: str(r.get("Collision Type Description") or "").replace("PEDESTRAIN", "PEDESTRIAN").strip().upper()
    light = lambda r: str(r.get("LightingDescription") or "").upper()
    out = {}
    for t in sorted({ct(r) for r in crash.values()} - SKIP):
        out["type_" + re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")] = {c for c, r in crash.items() if ct(r) == t}
    unlit = {c for c, r in crash.items() if light(r).startswith("DARK") and ("NO STREET" in light(r)
                                                                              or "NOT FUNCTION" in light(r))}
    out["dark_lit"] = {c for c, r in crash.items() if light(r).startswith("DARK")} - unlit
    out["dark_unlit"] = unlit
    out["ped"], out["bike"] = ped, bike
    out["motorcycle"] = {c for c in crash if any(MOTO.search(v) for v in veh[c])}
    out["wet"] = {c for c, r in crash.items() if str(r.get("RoadwaySurfaceCode") or "") == "B"}
    out["ksi"] = {c for c in crash if sev[c] in "KA"}
    return out


def _expected(name, a, crash, sev, loc_keys):
    loc = {x["crash_id"]: x["location_id"] for x in a["assignments"] if x["kind"] in ("intersection", "segment")}
    by = defaultdict(set)
    for c, lid in loc.items():
        by[lid].add(c)
    rows = {}
    for tkey, members in _targets(name, crash, sev).items():
        for kind in ("intersection", "segment"):
            pop = [k for k in loc_keys if str(k).startswith("seg") == (kind == "segment")]
            xs = {k: len(by[k] & members) for k in pop}
            ns = {k: len(by[k]) for k in pop}
            X, N = sum(xs.values()), sum(ns.values())
            if not N or not X:
                continue
            p = X / N
            use = [(xs[k], ns[k]) for k in pop if ns[k] >= 2]
            prior = None
            if len(use) >= 3 and 0 < p < 1:
                m = len(use)
                s2 = (sum((x * x - x) / (n * n - n) for x, n in use) - sum(x / n for x, n in use) ** 2 / m) / (m - 1)
                if s2 > 0:
                    al = (p ** 2 - p ** 3 - s2 * p) / s2
                    be = (p - 2 * p ** 2 + p ** 3 - s2 * (1 - p)) / s2
                    prior = (al, be) if al > 0 and be > 0 else None
            for k in pop:
                x, n = xs[k], ns[k]
                if n < MIN_N or x < MIN_X or x / n <= p:
                    continue
                prob = (_beta_sf(prior[0] + x, prior[1] + n - x, p) if prior else 1 - _binom_ge(x, n, p))
                if prob >= PROB_REPORT:
                    share, ref = round(100 * x / n, 1), round(100 * X / N, 1)
                    rows[f"{k}~{tkey}"] = {"target_crashes": x, "location_crashes": n, "share_pct": share,
                                           "reference_share_pct": ref, "excess_pct": round(share - ref, 1),
                                           "probability": min(round(prob, 2), 0.99),
                                           "strength": "Strong" if prob >= PROB_STRONG else "Moderate",
                                           "beta": prior is not None, "reference_target": X, "reference_crashes": N}
    return rows


@pytest.fixture(scope="module", params=["crenshaw", "unioncity"])
def golden(request):
    mp = pytest.MonkeyPatch()
    try:
        net, pull, a, p = run(request.param, mp)
    finally:
        mp.undo()
    ids = {x["crash_id"] for x in a["assignments"] if x["kind"] in ("intersection", "segment")}
    crash, sev, _ = reference(request.param, ids)
    loc_keys = list(table(p, "T2"))
    return request.param, p, _expected(request.param, a, crash, sev, loc_keys)


def test_T12_flags_exactly_the_reference_rows(golden):
    name, p, want = golden
    assert set(table(p, "T12")) == set(want), name


def test_T12_numbers_match_the_reference(golden):
    name, p, want = golden
    got = table(p, "T12")
    for key, w in want.items():
        g = got[key]
        for k in ("target_crashes", "location_crashes", "share_pct", "reference_share_pct", "excess_pct",
                  "probability", "strength", "reference_target", "reference_crashes"):
            assert g[k] == w[k], (name, key, k, g[k], w[k])
        assert g["method"].startswith("HSM excess proportion") == w["beta"], (name, key, g["method"])


def test_T12_has_something_to_check(golden):
    name, p, want = golden
    assert want, f"{name}: no row passes the screen, so this golden test checks nothing"
