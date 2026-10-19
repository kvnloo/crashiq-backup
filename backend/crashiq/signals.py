"""C7 crosstab: per-location over-representation screen (deterministic; no AI).

For each location and each target crash type (a collision type, crashes after dark, pedestrian, KSI, ...) this
asks: is the share of that type at the location higher than along the corridor as a whole, by more than chance
would explain? Method: excess proportion of specific crash types (HSM Part B network screening, after Heydecker &
Wu 1991), with the corridor's locations as the reference population:

  p_i  = x_i / n_i                  observed share at location i (x target crashes of n)
  p*   = sum(x) / sum(n)            threshold share = corridor-wide share
  s^2  = sum((p_i - p*)^2) / (m-1)  over the m locations with at least 2 crashes
  alpha = (p*^2 - p*^3 - s^2 p*) / s^2,  beta = (p* - 2p*^2 + p*^3 - s^2 (1 - p*)) / s^2   (method of moments)
  P(true share > p*) = 1 - I_p*(alpha + x_i, beta + n_i - x_i)    (I = regularized incomplete beta)

When the moments give no valid beta prior (too few locations, no spread, or alpha/beta <= 0) the screen falls back
to an exact one-sided binomial test against p* and says so. Every number lands in table T12, which findings cite.
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
        {"key": "dark", "noun": "Crashes after dark", "pattern": "dark", "test": profile_mod.is_dark,
         "filter": {"lighting_dark": True}},
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


def beta_prior(shares: list[float], p_star: float) -> tuple[float, float] | None:
    """Method-of-moments beta prior from the reference locations' shares, or None when it isn't valid."""
    m = len(shares)
    if m < 3 or not 0 < p_star < 1:
        return None
    s2 = sum((p - p_star) ** 2 for p in shares) / (m - 1)
    if s2 <= 0:
        return None
    a = (p_star ** 2 - p_star ** 3 - s2 * p_star) / s2
    b = (p_star - 2 * p_star ** 2 + p_star ** 3 - s2 * (1 - p_star)) / s2
    return (a, b) if a > 0 and b > 0 else None


# -- the screen -------------------------------------------------------------------------------------------
def screen(placed: list[dict], locations: list[tuple[str, str]]) -> dict:
    """placed: crashes with location_id. locations: (id, label) in corridor order.
    Returns {"table": T12, "signals": [...]} — every reported location × target type, strongest first."""
    by_loc: dict[str, list[dict]] = {lid: [] for lid, _ in locations}
    for c in placed:
        if c.get("location_id") in by_loc:
            by_loc[c["location_id"]].append(c)
    label = dict(locations)
    total = sum(len(v) for v in by_loc.values())
    rows, signals = [], []
    for t in targets(placed):
        x_all = {lid: sum(1 for c in cs if t["test"](c)) for lid, cs in by_loc.items()}
        n_all = {lid: len(cs) for lid, cs in by_loc.items()}
        corr_x = sum(x_all.values())
        if not total or corr_x == 0:
            continue
        p_star = corr_x / total
        prior = beta_prior([x_all[k] / n_all[k] for k in by_loc if n_all[k] >= 2], p_star)
        for lid, _ in locations:
            x, n = x_all[lid], n_all[lid]
            if n < MIN_LOCATION_CRASHES or x < MIN_TARGET_CRASHES or x / n <= p_star:
                continue
            if prior:
                prob, method = 1.0 - betainc(prior[0] + x, prior[1] + n - x, p_star), "beta"
            else:
                prob, method = 1.0 - binom_sf(x, n, p_star), "binomial"
            if prob < PROB_MODERATE:
                continue
            share, corr = profile_mod.pct(x, n), profile_mod.pct(corr_x, total)
            key = f"{lid}~{t['key']}"
            rows.append(profile_mod._row(
                key, f"{label[lid]} · {t['noun'].lower()}", location=label[lid], crash_type=t["noun"],
                target_crashes=x, location_crashes=n, share_pct=share, corridor_target=corr_x,
                corridor_crashes=total, corridor_share_pct=corr, excess_pct=round(share - corr, 1),
                probability=min(round(prob, 2), 0.99), strength="Strong" if prob >= PROB_STRONG else "Moderate",
                method="Beta prior from corridor locations" if method == "beta" else "Binomial test vs corridor share"))
            signals.append({"row": key, "location_id": lid, "location": label[lid], "target": t["key"],
                            "noun": t["noun"], "pattern": t["pattern"], "filter": {"location_id": lid, **t["filter"]},
                            "probability": prob, "excess": share - corr, "method": method})
    signals.sort(key=lambda s: (-s["probability"], -s["excess"], s["row"]))
    per_loc, kept = Counter(), []
    for s in signals:
        if per_loc[s["location_id"]] < MAX_PER_LOCATION and len(kept) < MAX_SIGNALS:
            per_loc[s["location_id"]] += 1
            kept.append(s)
    order = {s["row"]: i for i, s in enumerate(signals)}
    rows.sort(key=lambda r: order[r["key"]])
    table = profile_mod._table("T12", "Over-represented crash types (excess-proportion screen)", [
        ("location", "Location"), ("crash_type", "Crash type"), ("target_crashes", "Crashes of this type"),
        ("location_crashes", "All crashes here"), ("share_pct", "Share here %"),
        ("corridor_share_pct", "Corridor share %"), ("excess_pct", "Excess (points)"),
        ("probability", "P(share > corridor), max 0.99"), ("strength", "Strength"), ("method", "Method"),
        ("corridor_target", "Corridor crashes of this type"), ("corridor_crashes", "Corridor crashes")],
        rows, [c for cs in by_loc.values() for c in cs])
    return {"table": table, "signals": kept}
