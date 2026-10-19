"""C7 crosstab: per-location over-representation screen (deterministic; no AI).

For each location and each target crash type (a collision type, crashes after dark, pedestrian, KSI, ...) this
asks: is the share of that type at the location higher than at comparable locations on the corridor, by more than
chance would explain? Method: excess proportion of specific crash types (HSM 1st ed. Part B, Ch. 4 network
screening, after Heydecker & Wu 1991). Reference population = the corridor's locations OF THE SAME KIND
(intersections with intersections, segments with segments):

  p_i  = x_i / n_i                       observed share at site i (x target crashes of n)
  p*   = sum(x) / sum(n)                 threshold proportion over the reference population
  s^2  = 1/(m-1) * [ sum((x^2 - x)/(n^2 - n)) - (1/m) * (sum(x/n))^2 ]   over the m sites with n >= 2
         (HSM's variance: the (x^2 - x)/(n^2 - n) term removes the binomial sampling noise from each site's share)
  alpha = (p*^2 - p*^3 - s^2 p*) / s^2,  beta = (p* - 2p*^2 + p*^3 - s^2 (1 - p*)) / s^2
  P(true share > p*) = 1 - I_p*(alpha + x_i, beta + n_i - x_i)    (I = regularized incomplete beta)
  Sites passing the probability threshold are ranked by excess proportion p_i - p* (HSM ranking measure).

When the moments give no valid beta prior (fewer than 3 sites, no spread, or alpha/beta <= 0) the screen falls back
to an exact one-sided binomial test against p* and labels the value a binomial confidence, not a probability of
excess. Every number lands in table T12, which findings cite. Check the variance form against your HSM copy.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from . import profile as profile_mod

MIN_LOCATION_CRASHES = 5     # decision-needed #34: smallest location the screen reports on
MIN_TARGET_CRASHES = 3       # decision-needed #34: smallest count of the target type at a location
PROB_MODERATE = 0.80         # decision-needed #34: P(true share > corridor share) to report a signal
PROB_STRONG = 0.95
MAX_PER_LOCATION = 2
MAX_SIGNALS = 8
SKIP_TYPES = {"", "OTHER", "NOT STATED"}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "x"


def targets(crashes: list[dict]) -> list[dict]:
    """Target crash types screened on this corridor: each collision type present, plus cross-cutting groups.
    `filter` is the findings RecordFilter that selects exactly these crashes (the evidence)."""
    out = []
    for ct in sorted({(c.get("collision_type") or "").upper() for c in crashes} - SKIP_TYPES):
        out.append({"key": "type_" + slug(ct), "noun": f"{ct.title()} crashes", "pattern": "type_" + slug(ct),
                    "test": (lambda c, ct=ct: (c.get("collision_type") or "").upper() == ct),
                    "filter": {"collision_type": [ct]}})
    out += [
        {"key": "dark_lit", "noun": "Crashes after dark under street lights", "pattern": "dark",
         "test": lambda c: profile_mod.is_dark(c) and not profile_mod.is_unlit(c),
         "filter": {"lighting_dark": True, "lighting_unlit": False}},
        {"key": "dark_unlit", "noun": "Crashes after dark without working street lights", "pattern": "dark_unlit",
         "test": profile_mod.is_unlit, "filter": {"lighting_dark": True, "lighting_unlit": True}},
        {"key": "ped", "noun": "Pedestrian crashes", "pattern": "ped", "test": lambda c: bool(c.get("ped")),
         "filter": {"ped": True}},
        {"key": "bike", "noun": "Bicycle crashes", "pattern": "bike", "test": lambda c: bool(c.get("bike")),
         "filter": {"bike": True}},
        {"key": "motorcycle", "noun": "Motorcycle crashes", "pattern": "motorcycle",
         "test": lambda c: bool(c.get("motorcycle")), "filter": {"motorcycle": True}},
        {"key": "wet", "noun": "Wet-pavement crashes", "pattern": "wet",
         "test": lambda c: (c.get("surface") or "").upper().startswith("WET"), "filter": {"surface_wet": True}},
        {"key": "ksi", "noun": "Fatal and serious-injury crashes", "pattern": "ksi",
         "test": lambda c: c.get("severity") in ("K", "A"), "filter": {"severity": ["K", "A"]}},
    ]
    return out


# -- math -------------------------------------------------------------------------------------------------
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (Lentz's method)."""
    tiny, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b) (the Beta(a, b) CDF at x)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1.0 - x) / b


def binom_sf(x: int, n: int, p: float) -> float:
    """P(X >= x) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(x, n + 1))


def hsm_variance(sites: list[tuple[int, int]]) -> float | None:
    """HSM excess-proportion variance over sites (x target, n total) with n >= 2; None with fewer than 3 sites."""
    use = [(x, n) for x, n in sites if n >= 2]
    m = len(use)
    if m < 3:
        return None
    a = sum((x * x - x) / (n * n - n) for x, n in use)
    b = sum(x / n for x, n in use) ** 2 / m
    return (a - b) / (m - 1)


def beta_prior(sites: list[tuple[int, int]], p_star: float) -> tuple[float, float] | None:
    """Method-of-moments beta prior (HSM) from the reference sites, or None when it isn't valid."""
    if not 0 < p_star < 1:
        return None
    s2 = hsm_variance(sites)
    if s2 is None or s2 <= 0:
        return None
    a = (p_star ** 2 - p_star ** 3 - s2 * p_star) / s2
    b = (p_star - 2 * p_star ** 2 + p_star ** 3 - s2 * (1 - p_star)) / s2
    return (a, b) if a > 0 and b > 0 else None


def kind_of(location_id: str) -> str:
    return "segment" if str(location_id).startswith("seg") else "intersection"


PLURAL = {"intersection": "intersections", "segment": "segments"}


# -- the screen -------------------------------------------------------------------------------------------
def screen(placed: list[dict], locations: list[tuple[str, str]]) -> dict:
    """placed: crashes with location_id. locations: (id, label) in corridor order.
    Returns {"table": T12, "signals": [...]} — every reported location × target type, strongest first."""
    by_loc: dict[str, list[dict]] = {lid: [] for lid, _ in locations}
    for c in placed:
        if c.get("location_id") in by_loc:
            by_loc[c["location_id"]].append(c)
    label = dict(locations)
    rows, signals, tests_run = [], [], 0
    for t in targets(placed):
        x_all = {lid: sum(1 for c in cs if t["test"](c)) for lid, cs in by_loc.items()}
        n_all = {lid: len(cs) for lid, cs in by_loc.items()}
        for kind in ("intersection", "segment"):
            pop = [lid for lid, _ in locations if kind_of(lid) == kind]
            ref_x, ref_n = sum(x_all[k] for k in pop), sum(n_all[k] for k in pop)
            if not ref_n or ref_x == 0:
                continue
            p_star = ref_x / ref_n
            prior = beta_prior([(x_all[k], n_all[k]) for k in pop], p_star)
            for lid in pop:
                x, n = x_all[lid], n_all[lid]
                if n < MIN_LOCATION_CRASHES or x < MIN_TARGET_CRASHES or x / n <= p_star:
                    continue
                tests_run += 1
                if prior:
                    prob, method = 1.0 - betainc(prior[0] + x, prior[1] + n - x, p_star), "beta"
                else:
                    prob, method = 1.0 - binom_sf(x, n, p_star), "binomial"
                if prob < PROB_MODERATE:
                    continue
                share, ref = profile_mod.pct(x, n), profile_mod.pct(ref_x, ref_n)
                key = f"{lid}~{t['key']}"
                rows.append(profile_mod._row(
                    key, f"{label[lid]} · {t['noun'].lower()}", location=label[lid], crash_type=t["noun"],
                    reference=f"corridor {PLURAL[kind]}", target_crashes=x, location_crashes=n, share_pct=share,
                    reference_share_pct=ref, excess_pct=round(share - ref, 1),
                    probability=min(round(prob, 2), 0.99), strength="Strong" if prob >= PROB_STRONG else "Moderate",
                    method=("HSM excess proportion (beta prior from reference sites)" if method == "beta"
                            else "Binomial test vs reference share (a confidence, not a probability of excess)"),
                    reference_target=ref_x, reference_crashes=ref_n))
                signals.append({"row": key, "location_id": lid, "location": label[lid], "target": t["key"],
                                "noun": t["noun"], "pattern": t["pattern"], "kind": kind,
                                "filter": {"location_id": lid, **t["filter"]},
                                "probability": prob, "excess": share - ref, "method": method})
    signals.sort(key=lambda s: (-s["excess"], -s["probability"], s["row"]))   # HSM: rank passing sites by excess
    per_loc, kept = Counter(), []
    for s in signals:
        if per_loc[s["location_id"]] < MAX_PER_LOCATION and len(kept) < MAX_SIGNALS:
            per_loc[s["location_id"]] += 1
            kept.append(s)
    order = {s["row"]: i for i, s in enumerate(signals)}
    rows.sort(key=lambda r: order[r["key"]])
    table = profile_mod._table("T12", "Over-represented crash types (excess-proportion screen)", [
        ("location", "Location"), ("crash_type", "Crash type"), ("reference", "Compared with"),
        ("target_crashes", "Crashes of this type"), ("location_crashes", "All crashes here"),
        ("share_pct", "Share here %"), ("reference_share_pct", "Reference share %"), ("excess_pct", "Excess (points)"),
        ("probability", "P(share > reference) or binomial confidence, max 0.99"), ("strength", "Strength"),
        ("method", "Method"), ("reference_target", "Reference crashes of this type"),
        ("reference_crashes", "Reference crashes")],
        rows, [c for cs in by_loc.values() for c in cs])
    return {"table": table, "signals": kept, "tests_run": tests_run}
