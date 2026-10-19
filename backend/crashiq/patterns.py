"""C7 + C8: which crash patterns are over-represented where, and what they might mean. No AI.

C7 test (decision D2): the HSM beta-binomial "probability of specific crash types exceeding a threshold
proportion" (HSM Part B, Ch. 4). For each pattern and each location:
  p_i  = target crashes / all crashes at the location
  p*   = threshold proportion = sum of target crashes / sum of crashes over the reference sites
         (the corridor's locations of the same kind: intersections with intersections, segments with segments)
  s^2  = HSM sample variance of the site proportions
  alpha = (p*^2 - p*^3 - s^2 p*) / s^2,  beta = alpha / p* - alpha
  P(p_i > p*) = 1 - I_{p*}(alpha + N_target, beta + N_total - N_target)   (regularized incomplete beta)
Flagged when N_target >= 2 and P >= the limiting probability (0.90). When the HSM variance can't be estimated
(fewer than two reference sites, or no spread between sites: in HSM terms the sites agree, which argues *against*
flagging), a conservative pooled prior Beta(p* x N_ref, (1 - p*) x N_ref) is used, N_ref = all reference crashes.
(A uniform prior here flagged far too much on the Crenshaw corridor, 2026-10-18.)

C8: each flagged pattern maps to the pattern library (config/pattern_library.json, a seed awaiting the user's
review): possible factors and field checks, worded as possibilities to verify (D5). Findings are templated text
whose every number is cited to table T12, so the C10 validator checks them like any analyst's finding.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

LIMITING_PROBABILITY = 0.90
MIN_TARGET = 2
LIBRARY = Path(__file__).parent / "config" / "pattern_library.json"

_TYPES = {"broadside": "BROADSIDE", "rear_end": "REAR END", "sideswipe": "SIDE SWIPE", "head_on": "HEAD-ON",
          "hit_object": "HIT OBJECT"}


def _is_dark(c) -> bool:
    return (c.get("lighting") or "").upper().startswith("DARK")


# pattern -> (is this crash a target?, evidence record filter for the validator)
PATTERNS = {
    **{k: (lambda c, t=t: (c.get("collision_type") or "").upper() == t, {"collision_type": [t]}) for k, t in _TYPES.items()},
    "pedestrian": (lambda c: bool(c.get("ped")), {"ped": True}),
    "bicycle": (lambda c: bool(c.get("bike")), {"bike": True}),
    "dark": (_is_dark, {"lighting_dark": True}),
    "ksi": (lambda c: c.get("severity") in ("K", "A"), {"severity": ["K", "A"]}),
}


@lru_cache(maxsize=1)
def library() -> dict:
    return json.loads(LIBRARY.read_text())


# -- regularized incomplete beta I_x(a, b) (continued fraction, Numerical Recipes betacf) ---------------------
def betainc(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(ln) * _betacf(a, b, x) / a
    return 1.0 - math.exp(ln) * _betacf(b, a, 1 - x) / b


def _betacf(a: float, b: float, x: float, eps: float = 1e-12, itmax: int = 500) -> float:
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c if abs(1 + aa / c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c if abs(1 + aa / c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1) < eps:
            break
    return h


def reference(sites: list[tuple[int, int]]) -> dict:
    """Threshold proportion p*, HSM sample variance and beta parameters for (target, total) site counts."""
    used = [(t, n) for t, n in sites if n >= 1]
    tot_t, tot_n = sum(t for t, _ in used), sum(n for _, n in used)
    p = tot_t / tot_n if tot_n else 0.0
    out = {"p_star": p, "sites": len(used), "variance": None, "alpha": None, "beta": None, "pooled_n": tot_n}
    two = [(t, n) for t, n in used if n >= 2]
    if len(two) >= 2 and 0 < p < 1:
        k = len(two)
        s2 = (sum((t * t - t) / (n * n - n) for t, n in two) - (sum(t / n for t, n in two) ** 2) / k) / (k - 1)
        if s2 > 0:
            a = (p * p - p ** 3 - s2 * p) / s2
            b = a / p - a
            if a > 0 and b > 0:
                out.update(variance=s2, alpha=a, beta=b)
    return out


def probability_exceeds(target: int, total: int, ref: dict) -> tuple[float, str]:
    p = ref["p_star"]
    if ref["alpha"] is not None:
        return 1.0 - betainc(ref["alpha"] + target, ref["beta"] + total - target, p), "HSM beta-binomial"
    k = max(ref.get("pooled_n") or 0, 1)
    return (1.0 - betainc(p * k + target, (1 - p) * k + total - target, p),
            "pooled reference prior (HSM variance not estimable)")


def screen(placed: list[dict], locations: list[dict], limit: float = LIMITING_PROBABILITY) -> list[dict]:
    """Flagged (location, pattern) rows. `locations` = T2 rows (key, label, values.kind)."""
    by_loc: dict[str, list[dict]] = {}
    for c in placed:
        by_loc.setdefault(c["location_id"], []).append(c)
    flags = []
    for kind in ("intersection", "segment"):
        locs = [loc for loc in locations if loc["values"].get("kind") == kind]
        for pkey, (is_target, _) in PATTERNS.items():
            counts = {loc["key"]: (sum(is_target(c) for c in by_loc.get(loc["key"], [])), len(by_loc.get(loc["key"], [])))
                      for loc in locs}
            ref = reference(list(counts.values()))
            if not 0 < ref["p_star"] < 1:
                continue
            for loc in locs:
                t, n = counts[loc["key"]]
                if t < MIN_TARGET:
                    continue
                prob, method = probability_exceeds(t, n, ref)
                if prob >= limit:
                    flags.append({"location_id": loc["key"], "location": loc["label"], "kind": kind, "pattern": pkey,
                                  "target": t, "total": n, "share_pct": round(100 * t / n, 1),
                                  "reference_pct": round(100 * ref["p_star"], 1), "reference_sites": ref["sites"],
                                  "probability_pct": round(100 * prob, 1),
                                  "excess_pct": round(100 * (t / n - ref["p_star"]), 1), "method": method})
    return sorted(flags, key=lambda f: (-f["probability_pct"], -f["excess_pct"]))


def table_t12(flags: list[dict]) -> dict:
    lib = library()["patterns"]
    rows = [{"key": f"{f['location_id']}|{f['pattern']}", "label": f"{lib[f['pattern']]['label']} at {f['location']}",
             "values": {k: f[k] for k in ("target", "total", "share_pct", "reference_pct", "probability_pct",
                                          "excess_pct", "reference_sites")} | {"kind": f["kind"], "method": f["method"]}}
            for f in flags]
    return {"id": "T12", "title": "Over-represented crash patterns (HSM threshold-proportion test)",
            "columns": [{"key": k, "label": lbl} for k, lbl in (
                ("target", "Target crashes"), ("total", "All crashes"), ("share_pct", "Share %"),
                ("reference_pct", "Similar sites %"), ("probability_pct", "Probability %"),
                ("excess_pct", "Excess (points)"), ("reference_sites", "Reference sites"))],
            "rows": rows, "provenance": {},
            "method": {"test": "HSM beta-binomial threshold proportion", "limiting_probability": LIMITING_PROBABILITY,
                       "min_target_crashes": MIN_TARGET, "reference": "the corridor's locations of the same kind",
                       "library_version": library()["version"]}}


_DIGITS = re.compile(r"\d")
_ORD = re.compile(r"\b\d+(st|nd|rd|th)\b", re.I)


def _say(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def findings_from(table: dict) -> list[dict]:
    """One templated finding per T12 row; every number cited to its T12 cell."""
    lib = library()["patterns"]
    out = []
    for r in table["rows"]:
        lid, pkey = r["key"].split("|", 1)
        v, e = r["values"], lib[pkey]
        where = r["label"].split(" at ", 1)[1]
        if _DIGITS.search(_ORD.sub("", where)):        # labels with route numbers would read as unverified claims
            where = "this location"
        sites = "intersections" if v["kind"] == "intersection" else "segments"
        factors = e["factors_intersection"] if v["kind"] == "intersection" else e["factors_segment"]
        n = lambda col: {"value": v[col], "table_id": "T12", "cell": f"{r['key']}/{col}"}
        text = (f"{e['phrase']} are over-represented at {where}: {v['target']} of {v['total']} crashes "
                f"({v['share_pct']:.0f}%) compared with {v['reference_pct']:.0f}% at the corridor's other {sites}. "
                f"Probability that this location truly exceeds that share: {v['probability_pct']:.0f}% "
                f"(HSM threshold-proportion test). Possible contributing factors, to verify in the field: "
                f"{_say(factors)}. "
                f"Check: {_say(e['field_checks'])}.")
        out.append({"id": f"auto-{lid}-{pkey}", "location_id": lid, "text": text,
                    "numbers": [n("target"), n("total"), n("share_pct"), n("reference_pct"), n("probability_pct")],
                    "pattern_ref": e["ref"],
                    "evidence_refs": {"tables": ["T12"], "records": {"location_id": lid, **PATTERNS[pkey][1]}}})
    return out
