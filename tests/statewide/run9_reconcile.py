"""Run 9 reconciliation: one row per change, in order (each row counts only what the earlier ones didn't already do),
every crash accounted for in every stage.

  S3  run 8b (coverage_crashes_r8b.csv)
  S4  + #242 name-cleaner rules: run 9A (main 5ed6783, box + 1 km, #218 rule 2 in the GPS step, OSM only), each crash
      read WITHOUT the approved aliases (its outcome_without_alias where an alias applies, else its outcome)
  S5  + the approved aliases (#235/#241): run 9A as read
  S6  + TIGER/Line (#229/#232): run 9B (the same, on the OSM + TIGER network; tiger_only_auto off, the app's default)
  S7  what if TIGER-only roads auto-placed (tiger_only_auto on): S6 + crashes whose placement relied on a TIGER-only
      road, under an auto tier, that the gate held
Also in S4: #236 (verified_typo tier, gate off: no effect) and the harness running rule 2 inside the GPS step.

Run: python tests/statewide/run9_reconcile.py   (writes data/statewide/run9_reconcile.json, coverage_crashes_r9.csv)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from run8_reconcile import BIN1, load, moves, stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
BIN1 = BIN1 | {"placed_tiger_road"}


def parts(prefix: str) -> dict[str, dict]:
    out = {}
    for p in sorted(DATA.glob(f"coverage_crashes_{prefix}_*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["collision_id"] in out:
                    raise SystemExit(f"{r['collision_id']} in two part files")
                out[r["collision_id"]] = r
    return out


def main() -> None:
    s3 = load("coverage_crashes_r8b.csv")
    a, b = parts("r9a"), parts("r9b")
    for name, st in (("9A", a), ("9B", b)):
        if set(st) != set(s3):
            raise SystemExit(f"completeness guard: {name} {len(st)} vs run 8b {len(s3)} crashes")
    s4 = {cid: ({**r, "outcome": r["outcome_without_alias"]} if r.get("outcome_without_alias") else r)
          for cid, r in a.items()}
    s7 = {cid: ({**r, "outcome": "placed_tiger_road", "bin": "1"}
                if r["tiger"] == "road" and r["tier"] in ("exact", "unique_pair") and r["outcome"] not in BIN1 else r)
          for cid, r in b.items()}
    stages = {"S3 run 8b": s3, "S4 + #242 name-cleaner rules": s4, "S5 + approved aliases": a,
              "S6 + TIGER/Line (names on OSM streets auto; TIGER-only roads held)": b,
              "S7 what if TIGER-only roads auto-placed": s7}
    import run8_reconcile
    run8_reconcile.BIN1 = BIN1
    st = {k: stats(v) for k, v in stages.items()}
    names_ = {list(stages)[1]: "#242 name-cleaner rules", list(stages)[2]: "approved aliases",
              list(stages)[3]: "TIGER/Line (as configured)", list(stages)[4]: "TIGER-only roads, if auto (what-if)"}
    eff = []
    keys = list(stages)
    for ka, kb in zip(keys[:-1], keys[1:]):
        eff.append({"effect": names_[kb], "on_map_change": st[kb]["on_map"] - st[ka]["on_map"],
                    "on_map_pct": f"{st[ka]['on_map_pct']} -> {st[kb]['on_map_pct']}",
                    "fatal_pct": f"{st[ka]['fatal_on_map_pct']} -> {st[kb]['fatal_on_map_pct']}",
                    "ksi_pct": f"{st[ka]['ksi_on_map_pct']} -> {st[kb]['ksi_on_map_pct']}",
                    "moves": moves(stages[ka], stages[kb])})
    tig = {"tiger_name_placed": sum(1 for r in b.values() if r["tiger"] == "name" and r["outcome"] in BIN1),
           "tiger_road_held": sum(1 for r in s7.values() if r["outcome"] == "placed_tiger_road")}
    (DATA / "run9_reconcile.json").write_text(json.dumps({"stages": st, "effects": eff, "tiger": tig}, indent=1))
    with open(DATA / "coverage_crashes_r9.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(next(iter(b.values()))))
        w.writeheader()
        w.writerows(b.values())
    for e in eff:
        print(e["effect"], f"{e['on_map_change']:+}", e["on_map_pct"], "fatal", e["fatal_pct"], "ksi", e["ksi_pct"])
        print("   ", list(e["moves"].items())[:4])
    print(tig)


if __name__ == "__main__":
    main()
