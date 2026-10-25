"""Run 10 reconciliation (PM 2026-10-25; measure only). Basis: main 2d110db (#250, #251, #252, #254, #258: TIGER
union on, approximate freeways on, freeway_move_gps off), coverage.py --run10. Against run 9C (the same union, before
#251 and #258), one row per effect, every crash in both runs (completeness guard):

  GPS repair (#251)      crashes onto the map whose GPS is read as DMS outside the #143 agency-years (dms_new) or
                         had its longitude's minus restored (lon_sign)
  approximate freeways   crashes onto the map as placed_approximate (#258) with no usable GPS: what the app does
  not in the app         freeway crashes whose GPS is off the report's roads that the report's spot would place: the
                         harness's convention only (the app keeps the officer's GPS, freeway_move_gps off), so they are
                         counted as difficult, reported on their own line, and kept out of coverage and claims (PM)
  other                  any other change (expected 0)

Coverage: on the map = precise (police GPS, repaired GPS, exact / unique_pair, FARS) + approximate; overall, fatal,
KSI, by district and road type. Also the GPS-repair count vs the run-9A estimate (4,567).

Run: python tests/statewide/run10_reconcile.py   (writes data/statewide/run10_reconcile.json)
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict

from run9_reconcile import DATA, parts

PRECISE = {"gps_usable", "gps_usable_dms", "gps_usable_sign", "placed_exact", "placed_unique_pair", "placed_fars",
           "placed_verified_typo"}
APPROX = {"placed_approximate"}
ESTIMATE = 4567


def app_view(st: dict, base: dict) -> dict:
    """Outcomes as the app has them (PM 2026-10-25): an approximate spot for a crash whose GPS is off its roads isn't
    used. Its outcome is then what it would be without the freeway step; such a crash had no GPS repair (else it would
    be gps_usable), so that is its run-9C outcome (review, cant_place, or FARS for a fatal crash). Marked `nia`."""
    out = {}
    for cid, r in st.items():
        if r["outcome"] == "placed_approximate" and r.get("approx", "").startswith("gps_off_roads"):
            b = base[cid]
            r = {**r, "outcome": b["outcome"], "bin": b["bin"], "reason": b["reason"], "nia": "1"}
        out[cid] = r
    return out


def pct(k, n):
    return round(100 * k / n, 2) if n else None


def coverage(st: dict) -> dict:
    g = defaultdict(Counter)
    for r in st.values():
        for key in ("all", f"district {r['district'] or 'unknown'}", f"road {r['road_type']}"):
            for sev in ("crashes", "fatal", "ksi"):
                if sev != "crashes" and r["killed" if sev == "fatal" else "ksi"] != "1":
                    continue
                c = g[key]
                c[f"{sev}"] += 1
                c[f"{sev}_precise"] += r["outcome"] in PRECISE
                c[f"{sev}_approx"] += r["outcome"] in APPROX
    out = {}
    for key, c in g.items():
        o = {}
        for sev in ("crashes", "fatal", "ksi"):
            n = c[sev]
            o[sev] = n
            o[f"{sev}_precise_pct"] = pct(c[f"{sev}_precise"], n)
            o[f"{sev}_approx_pct"] = pct(c[f"{sev}_approx"], n)
            o[f"{sev}_on_map_pct"] = pct(c[f"{sev}_precise"] + c[f"{sev}_approx"], n)
        o["on_map"] = c["crashes_precise"] + c["crashes_approx"]
        o["approximate"] = c["crashes_approx"]
        out[key] = o
    return out


def main() -> None:
    c9, r10_all = parts("r9c"), parts("r10")
    r10 = app_view(r10_all, c9)
    if set(c9) != set(r10):
        raise SystemExit(f"completeness guard: run 10 {len(r10)} vs 9C {len(c9)} crashes")
    on9 = lambda r: r["outcome"] in PRECISE | APPROX     # noqa: E731
    eff = defaultdict(Counter)
    moves = Counter()
    for cid, a in c9.items():
        b = r10[cid]
        if a["outcome"] != b["outcome"]:
            moves[f"{a['outcome']} -> {b['outcome']}"] += 1
        if on9(a) == on9(b):
            continue
        if on9(b):
            if b["repair"] in ("dms_new", "lon_sign"):
                k = f"GPS repair (#251): {b['repair']}"
            elif b["outcome"] == "placed_approximate":
                k = f"approximate freeway (#258): {b['approx'].split(':')[0]}"
            else:
                k = f"other onto map: {b['outcome']}"
        else:
            k = f"left the map: {a['outcome']} -> {b['outcome']}"
        e = eff[k]
        e["crashes"] += 1
        e["fatal"] += b["killed"] == "1"
        e["ksi"] += b["ksi"] == "1"
    repairs = Counter(r["repair"] for r in r10.values() if r["repair"])
    approx_kind = Counter(r["approx"] for r in r10_all.values() if r["approx"])
    nia = [r for r in r10.values() if r.get("nia")]
    not_in_app = {"crashes": len(nia), "fatal": sum(r["killed"] == "1" for r in nia),
                  "ksi": sum(r["ksi"] == "1" for r in nia), "was_in_9C": dict(Counter(c9[r["collision_id"]]["outcome"]
                                                                                       for r in nia))}
    res = {"basis": "main 2d110db, coverage.py --network box1km --aliases --rule2 --tiger --run10; vs run 9C",
           "crashes": len(r10), "effects": {k: dict(v) for k, v in sorted(eff.items())},
           "moves": dict(moves.most_common()),
           "gps_repair": {"all_repaired_on_map": dict(repairs), "new_in_run10": sum(
               v for k, v in repairs.items() if k in ("dms_new", "lon_sign")), "estimate_run9a": ESTIMATE},
           "approximate_by_kind": dict(approx_kind),
           "not_in_app_gps_off_roads_approximate": not_in_app,
           "coverage_9C": coverage(c9), "coverage_10": coverage(r10)}
    (DATA / "run10_reconcile.json").write_text(json.dumps(res, indent=1))
    a, b = res["coverage_9C"]["all"], res["coverage_10"]["all"]
    print(json.dumps({k: res[k] for k in ("effects", "gps_repair", "approximate_by_kind")}, indent=1))
    print("9C", a["crashes_on_map_pct"], a["fatal_on_map_pct"], a["ksi_on_map_pct"])
    print("10", b["crashes_on_map_pct"], "precise", b["crashes_precise_pct"], "approx", b["crashes_approx_pct"],
          "fatal", b["fatal_on_map_pct"], b["fatal_approx_pct"], "ksi", b["ksi_on_map_pct"], b["ksi_approx_pct"])


if __name__ == "__main__":
    main()
