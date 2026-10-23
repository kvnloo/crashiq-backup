"""Run 8 reconciliation (PM 2026-10-22): one row per effect, every crash accounted for (2,057,508 in every stage).

  S0  #199 corrected: app code 5f54c02, city network clipped to the outline (coverage_crashes_199v2.csv)
  S1a box + 1 km network, code before #212 (e2f1633: includes #204/#206, net +127 exact statewide on the old basis):
      S1 with the leading-abbreviation crashes re-placed on e2f1633 (run8_pre212.csv, run8_isolate.py)
  S1  box + 1 km network, current main code (#212 in), gate = exact only (coverage.py --network box1km
      --gate-tiers exact; coverage_crashes_r8_exact.csv)
  S2  S1 + unique_pair auto-places (the app's config since 2026-10-22, #222): a crash whose recorded tier is
      unique_pair and that wasn't placed by police GPS is placed (placed_unique_pair), FARS no longer needed for it
  S3  run 8b, after #218 (rules 1 and 2): added when it merges

Effects: harness network = S1a - S0; #212 = S1 - S1a; unique_pair = S2 - S1.
Writes data/statewide/run8_reconcile.json and coverage_crashes_r8_up.csv (S2 per crash, for coverage.py --merge).
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
BIN1 = {"gps_usable", "gps_usable_dms", "placed_exact", "placed_fars", "placed_unique_pair"}


def load(name: str) -> dict[str, dict]:
    with open(DATA / name) as f:
        return {r["collision_id"]: r for r in csv.DictReader(f)}


def stats(stage: dict[str, dict]) -> dict:
    c, by_d = Counter(), defaultdict(Counter)
    for r in stage.values():
        on = r["outcome"] in BIN1
        c["crashes"] += 1
        c["on_map"] += on
        c["fatal"] += r["killed"] == "1"
        c["fatal_on"] += on and r["killed"] == "1"
        c["ksi"] += r["ksi"] == "1"
        c["ksi_on"] += on and r["ksi"] == "1"
        c[r["outcome"]] += 1
        d = f"District {r['district']}" if r["district"] else "unknown"
        by_d[d]["crashes"] += 1
        by_d[d]["on_map"] += on
    pct = lambda k, n: round(100 * c[k] / c[n], 2) if c[n] else None   # noqa: E731
    return {"crashes": c["crashes"], "on_map": c["on_map"], "on_map_pct": pct("on_map", "crashes"),
            "fatal_on_map_pct": pct("fatal_on", "fatal"), "ksi_on_map_pct": pct("ksi_on", "ksi"),
            "outcomes": {k: v for k, v in c.items() if k in BIN1 or k in ("review", "cant_place")},
            "district_on_map_pct": {d: round(100 * v["on_map"] / v["crashes"], 2) for d, v in sorted(by_d.items())}}


def moves(a: dict[str, dict], b: dict[str, dict]) -> dict:
    m = Counter()
    for cid, r in b.items():
        o = a[cid]["outcome"]
        if o != r["outcome"]:
            m[f"{o} -> {r['outcome']}"] += 1
    return dict(m.most_common())


def main() -> None:
    s0, s1 = load("coverage_crashes_199v2.csv"), load("coverage_crashes_r8_exact.csv")
    if set(s0) != set(s1):
        raise SystemExit(f"completeness guard: S0 {len(s0)} vs S1 {len(s1)} crashes")
    pre = load("run8_pre212.csv")
    s1a = {}
    for cid, r in s1.items():
        p = pre.get(cid)
        if p is None or r["outcome"] in ("gps_usable", "gps_usable_dms"):
            s1a[cid] = r
            continue
        was = r["outcome"] == "placed_exact"
        now = p["tier"] == "exact"
        if was and not now:
            s1a[cid] = {**r, "outcome": "review", "tier": p["tier"], "bin": "2"}
        elif now and not was:
            s1a[cid] = {**r, "outcome": "placed_exact", "tier": "exact", "bin": "1"}
        else:
            s1a[cid] = {**r, "tier": p["tier"]}
    s2 = {}
    for cid, r in s1.items():
        if r["tier"] == "unique_pair" and r["outcome"] in ("review", "cant_place", "placed_fars"):
            s2[cid] = {**r, "outcome": "placed_unique_pair", "bin": "1", "reason": ""}
        else:
            s2[cid] = r
    with open(DATA / "coverage_crashes_r8_up.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(next(iter(s1.values()))))
        w.writeheader()
        w.writerows(s2.values())
    stages = {"S0 #199 corrected (clipped network, 5f54c02)": s0, "S1a box + 1 km network (code e2f1633)": s1a,
              "S1 + #212 leading abbreviations": s1, "S2 + unique_pair auto-places": s2}
    st = {k: stats(v) for k, v in stages.items()}
    keys = list(stages)
    eff = []
    for (ka, a), (kb, b) in zip(list(stages.items())[:-1], list(stages.items())[1:]):
        eff.append({"effect": {keys[1]: "harness network (box + 1 km; also #204/#206 code)", keys[2]: "#212",
                               keys[3]: "unique_pair"}[kb],
                    "on_map_change": st[kb]["on_map"] - st[ka]["on_map"],
                    "on_map_pct": f"{st[ka]['on_map_pct']} -> {st[kb]['on_map_pct']}",
                    "fatal_pct": f"{st[ka]['fatal_on_map_pct']} -> {st[kb]['fatal_on_map_pct']}",
                    "ksi_pct": f"{st[ka]['ksi_on_map_pct']} -> {st[kb]['ksi_on_map_pct']}", "moves": moves(a, b)})
    out = {"stages": st, "effects": eff}
    (DATA / "run8_reconcile.json").write_text(json.dumps(out, indent=1))
    for e in eff:
        print(e["effect"], e["on_map_change"], e["on_map_pct"], "fatal", e["fatal_pct"], "ksi", e["ksi_pct"])
        print("   ", list(e["moves"].items())[:5])


if __name__ == "__main__":
    main()
