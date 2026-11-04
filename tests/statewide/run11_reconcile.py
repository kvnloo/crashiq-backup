"""Run 11 reconciliation (#387; measure only). Run 11 = today's main, coverage.py --network box1km --aliases --rule2
--tiger --run11, against run 10d (run 10 with the freeway step redone as #278/#281: true connectors held, FARS before an
approximate spot) in the app's view (an approximate spot for a crash whose GPS is off its roads isn't used: its run-9C
outcome, as run10_reconcile.app_view). Every crash in both runs (completeness guard).

Coverage: on the map = precise (police GPS, repaired GPS, exact / unique_pair, FARS) + approximate (freeway report
#258, NAD house address #283); all / fatal / KSI, by road type and district, police GPS and CrashIQ shares. Moves
between the runs, and the verified_typo tier's gain (#233, off): bin-2 crashes the locator places as verified_typo.
Streams the part files and keeps one short tuple per crash (2 million full rows don't fit in memory here).

Run: python tests/statewide/run11_reconcile.py [r11sample]   (writes data/statewide/run11_reconcile.json)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "data" / "statewide"
GPS = {"gps_usable", "gps_usable_dms", "gps_usable_sign"}
CRASHIQ = {"placed_exact", "placed_unique_pair", "placed_approximate", "placed_address_nad"}
PRECISE = GPS | {"placed_exact", "placed_unique_pair", "placed_fars", "placed_verified_typo"}
APPROX = {"placed_approximate", "placed_address_nad"}
NEW = sys.argv[1] if len(sys.argv) > 1 else "r11"


def rows(prefix: str):
    files = sorted(DATA.glob(f"coverage_crashes_{prefix}_*.csv"))
    assert files, prefix
    for p in files:
        with open(p) as f:
            yield from csv.DictReader(f)


def load(prefix: str, base: dict | None = None) -> dict:
    """cid -> (outcome, district, road_type, killed, ksi, tier, gps, approx); base: run-9C outcomes for app_view."""
    out, it = {}, sys.intern
    for r in rows(prefix):
        o = r["outcome"]
        if base is not None and o == "placed_approximate" and r["approx"].startswith("gps_off_roads"):
            o = base[r["collision_id"]]          # the app keeps the officer's GPS (run10_reconcile.app_view)
        if r["collision_id"] in out:
            raise SystemExit(f"{r['collision_id']} in two part files of {prefix}")
        gps = "off" if r["reason"].startswith("police GPS off") else "none"
        out[r["collision_id"]] = (it(o), it(r["district"]), it(r["road_type"]), r["killed"] == "1", r["ksi"] == "1",
                                  it(r["tier"]), it(gps), it(r["approx"]))
    return out


def pct(k, n):
    return round(100 * k / n, 2) if n else None


def coverage(st: dict) -> dict:
    g = defaultdict(Counter)
    for o, d, rt, kil, ksi, *_ in st.values():
        for key in ("all", f"district {d or 'unknown'}", f"road {rt}"):
            c = g[key]
            for sev, on in (("crashes", True), ("fatal", kil), ("ksi", ksi)):
                if on:
                    c[sev] += 1
                    c[f"{sev}_precise"] += o in PRECISE
                    c[f"{sev}_approx"] += o in APPROX
            c["gps"] += o in GPS
            c["crashiq"] += o in CRASHIQ
    res = {}
    for key, c in sorted(g.items()):
        r = res[key] = {}
        for s in ("crashes", "fatal", "ksi"):
            r[f"{s}_n"] = c[s]
            r[f"{s}_on_map_pct"] = pct(c[f"{s}_precise"] + c[f"{s}_approx"], c[s])
        r.update(precise_pct=pct(c["crashes_precise"], c["crashes"]), approx=c["crashes_approx"],
                 police_gps_pct=pct(c["gps"], c["crashes"]), crashiq_pct=pct(c["crashiq"], c["crashes"]))
    return res


def main() -> None:
    off = {r["collision_id"] for r in rows("r10d") if r["outcome"] == "placed_approximate"
           and r["approx"].startswith("gps_off_roads")}
    base = {r["collision_id"]: r["outcome"] for r in rows("r9c") if r["collision_id"] in off}
    r10, r11 = load("r10d", base), load(NEW)
    if NEW != "r11":                               # a sample run (r11sample: San Francisco): the same crashes of 10d
        r10 = {k: v for k, v in r10.items() if k in r11}
    if set(r10) != set(r11):
        raise SystemExit(f"completeness guard: run 11 {len(r11)} vs run 10d {len(r10)} crashes")
    on = lambda o: o in PRECISE | APPROX           # noqa: E731
    moves, eff = Counter(), defaultdict(Counter)
    for cid, a in r10.items():
        b = r11[cid]
        if a[0] != b[0]:
            moves[f"{a[0]} -> {b[0]}"] += 1
        if on(a[0]) != on(b[0]):
            e = eff[f"{'onto' if on(b[0]) else 'off'} the map: {a[0]} -> {b[0]}"]
            e["crashes"] += 1
            e["fatal"] += b[3]
            e["ksi"] += b[4]
    vt = defaultdict(Counter)                      # verified_typo (#233): what the tier would add, run 11 bins
    for o, d, rt, kil, ksi, tier, gps, _ in r11.values():
        if tier == "verified_typo" and not on(o):
            for key in (f"gps {gps}", f"district {d}", f"road {rt}", "all"):
                vt[key]["crashes"] += 1
                vt[key]["fatal"] += kil
                vt[key]["ksi"] += ksi
    nia = Counter(x[7].split(":")[1] for x in r11.values() if x[7].startswith("nia:"))
    nad = Counter(x[1] for x in r11.values() if x[0] == "placed_address_nad")
    res = {"basis": "run 11: main (git rev in coverage logs), coverage.py --network box1km --aliases --rule2 --tiger "
                    "--run11; vs run 10d (run 10 + #278/#281 freeway redo), app view", "crashes": len(r11),
           "effects": {k: dict(v) for k, v in sorted(eff.items(), key=lambda kv: -kv[1]["crashes"])},
           "moves": dict(moves.most_common()), "verified_typo_gain": {k: dict(v) for k, v in sorted(vt.items())},
           "not_in_app_gps_off_roads": dict(nia), "address_nad_by_district": dict(sorted(nad.items())),
           "approximate_by_kind": dict(Counter(x[7] for x in r11.values() if x[0] in APPROX)),
           "coverage_10d": coverage(r10), "coverage_11": coverage(r11)}
    (DATA / f"run11_reconcile{'' if NEW == 'r11' else '_' + NEW}.json").write_text(json.dumps(res, indent=1))
    for k in ("all", "road city street", "road state highway (off freeway)", "road freeway",
              "road county road (outside cities)"):
        a, b = res["coverage_10d"][k], res["coverage_11"][k]
        print(f"{k:38s} 10d {a['crashes_on_map_pct']:6.2f}  11 {b['crashes_on_map_pct']:6.2f}  fatal {b['fatal_on_map_pct']}"
              f"  ksi {b['ksi_on_map_pct']}")
    print(json.dumps({k: res[k] for k in ("effects", "not_in_app_gps_off_roads")}, indent=1)[:3000])


if __name__ == "__main__":
    main()
