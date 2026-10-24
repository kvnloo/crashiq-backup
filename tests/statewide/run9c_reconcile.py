"""Run 9C vs 9A (PM 2026-10-23; measure only). 9C = 9A + the OSM + TIGER union with the #243 fix (#250) and TIGER names
outside city maps; tiger_only_auto off. Net crashes onto the map, statewide and by run-9A difficult-bin bucket (D1-D9,
buckets.csv) and by district; crashes that left the map; TIGER-name vs TIGER-road (held) counts.

Run: python tests/statewide/run9c_reconcile.py   (writes data/statewide/run9c_reconcile.json)
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from run8_reconcile import moves, stats
from run9_reconcile import BIN1, DATA, parts


def main() -> None:
    import run8_reconcile
    run8_reconcile.BIN1 = BIN1
    a, c = parts("r9a"), parts("r9c")
    if set(a) != set(c):
        raise SystemExit(f"completeness guard: 9C {len(c)} vs 9A {len(a)} crashes")
    with open(DATA / "buckets.csv") as f:
        bucket = {r["collision_id"]: r["bucket"] for r in csv.DictReader(f)}
    sa, sc = stats(a), stats(c)
    on = lambda r: r["outcome"] in BIN1                    # noqa: E731
    gained, lost = defaultdict(Counter), defaultdict(Counter)
    for cid in a:
        ga, gc = on(a[cid]), on(c[cid])
        if ga == gc:
            continue
        t = gained if gc else lost
        r = c[cid] if gc else a[cid]
        for key in ("all", f"bucket {bucket.get(cid, '(not in a bucket)')}", f"district {r['district']}"):
            t[key]["crashes"] += 1
            t[key]["fatal"] += r["killed"] == "1"
            t[key]["ksi"] += r["ksi"] == "1"
            t[key][f"tiger {c[cid]['tiger'] or 'none'}"] += 1
    keys = sorted(set(gained) | set(lost), key=lambda k: (k.split()[0], k))
    res = {"9A": sa, "9C": sc, "on_map_change": sc["on_map"] - sa["on_map"],
           "moves": moves(a, c),
           "by": {k: {"gained": dict(gained[k]), "lost": dict(lost[k]),
                      "net": gained[k]["crashes"] - lost[k]["crashes"]} for k in keys},
           "tiger_in_9C": {"name_on_map": sum(1 for r in c.values() if r["tiger"] == "name" and on(r)),
                           "road_held": sum(1 for r in c.values() if r["tiger"] == "road"
                                            and r["tier"] in ("exact", "unique_pair") and not on(r))}}
    (DATA / "run9c_reconcile.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "by"}, indent=1))
    for k in keys:
        if not k.startswith("district"):
            print(k, res["by"][k])


if __name__ == "__main__":
    main()
