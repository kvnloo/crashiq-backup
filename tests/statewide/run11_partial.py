"""Run 11 so far (#387): while the statewide run is going, run 11's crashes written up to now against the same crashes
in run 10d (app view, as run11_reconcile.py), by road type. A partial file may end mid-city; the comparison is per
crash, so that is fine. Read-only; prints only.

Run: python tests/statewide/run11_partial.py
"""

from __future__ import annotations

from collections import Counter

from run11_reconcile import APPROX, PRECISE, load, rows

ON = PRECISE | APPROX


def main() -> None:
    off = {r["collision_id"] for r in rows("r10d") if r["outcome"] == "placed_approximate"
           and r["approx"].startswith("gps_off_roads")}
    base = {r["collision_id"]: r["outcome"] for r in rows("r9c") if r["collision_id"] in off}
    r10 = load("r10d", base)
    t, moves = Counter(), Counter()
    for r in rows("r11"):
        a = r10.get(r["collision_id"])
        if a is None:
            continue
        for key in ("all", r["road_type"]):
            t[(key, "n")] += 1
            t[(key, "10d")] += a[0] in ON
            t[(key, "11")] += r["outcome"] in ON
        if a[0] != r["outcome"]:
            moves[f"{a[0]} -> {r['outcome']}"] += 1
    for key in sorted({k for k, _ in t}):
        n = t[(key, "n")]
        print(f"{key:30s} n={n:8,d}  10d {100 * t[(key, '10d')] / n:6.2f}%  11 {100 * t[(key, '11')] / n:6.2f}%  "
              f"delta {100 * (t[(key, '11')] - t[(key, '10d')]) / n:+.3f} pt")
    print(moves.most_common(15))


if __name__ == "__main__":
    main()
