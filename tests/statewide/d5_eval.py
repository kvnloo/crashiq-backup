"""#264 scoring: per address source (d5_result_<source>.csv), on the D5 pool how many it places, and on the truth pool
(same kind of crash, police GPS that fits the report, hidden) how many it places and how many of those land within
250 ft and 400 ft of the GPS, with Wilson 95% low bounds; statewide and by Caltrans district.

Run: python tests/statewide/d5_eval.py census tiger nad   (writes data/statewide/d5_eval.json)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))


def main(sources) -> None:
    import d5_common as dc
    from bin2_whatif import wilson_low
    gps = {r["collision_id"]: tuple(map(float, r["gps"].split(","))) for r in dc.pools() if r["gps"]}
    city = {r["collision_id"]: r["city"] for r in dc.pools()}
    res = {}
    for s in sources:
        t = defaultdict(Counter)
        with open(dc.DATA / f"d5_result_{s}.csv") as f:
            for r in csv.DictReader(f):
                where = "outside cities" if city.get(r["collision_id"]) in ("Unincorporated", "") else "in cities"
                for key in ("California", f"District {r['district']}", f"California, {where}"):
                    c = t[key]
                    c[f"{r['pool']}_n"] += 1
                    c[f"{r['pool']}_placed"] += r["placed"] == "1"
                    if r["pool"] == "truth" and r["placed"] == "1":
                        d = dc.ft((float(r["lat"]), float(r["lon"])), gps[r["collision_id"]])
                        c["within_250"] += d <= 250
                        c["within_400"] += d <= 400
                        c["over_1000"] += d > 1000
        out = {}
        for key, c in t.items():
            p = c["truth_placed"]
            out[key] = {"d5": c["d5_n"], "d5_placed": c["d5_placed"],
                        "d5_placed_pct": round(100 * c["d5_placed"] / c["d5_n"], 1) if c["d5_n"] else None,
                        "truth": c["truth_n"], "truth_placed": p,
                        "truth_placed_pct": round(100 * p / c["truth_n"], 1) if c["truth_n"] else None,
                        "within_250ft_pct": round(100 * c["within_250"] / p, 1) if p else None,
                        "within_250ft_low": wilson_low(c["within_250"], p) if p else None,
                        "within_400ft_pct": round(100 * c["within_400"] / p, 1) if p else None,
                        "within_400ft_low": wilson_low(c["within_400"], p) if p else None,
                        "over_1000ft": c["over_1000"]}
        res[s] = dict(sorted(out.items(), key=lambda kv: (kv[0] != "California",
                                                           int(kv[0].split()[1]) if kv[0] != "California"
                                                           and kv[0].split()[1].isdigit() else 99)))
    (dc.DATA / "d5_eval.json").write_text(json.dumps(res, indent=1))
    for s in sources:
        print(s, json.dumps(res[s]["California"]))


if __name__ == "__main__":
    main(sys.argv[1:])
