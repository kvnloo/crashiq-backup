"""Run 11 report (#387): reports/testing/run11-2026-11-03.md from the run's outputs in data/statewide (+ data/results):
run11_reconcile.json (coverage, run 10d vs 11), run11_tiers.json (postmile, crossing_rail / crossing_path),
accuracy_by_agency_r11.json (hidden police GPS, per tier) and geocode_{sf,la}_test_union_summary.json (open data).

Recommendation rule (the bar unique_pair was flipped on, #211): flip when the tier's Wilson 95% low bound is at or
above the exact tier's on the same truth and measure, with at least MIN_N test placements; below it, don't; fewer
than MIN_N, can't tell yet.

Run: python tests/statewide/run11_report.py
"""

from __future__ import annotations

import json
import math
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA, RES = ROOT / "data" / "statewide", ROOT / "data" / "results"
OUT = ROOT / "reports" / "testing" / "run11-2026-11-03.md"
MIN_N = 30
RUN10 = {"all": 93.47, "road city street": 89.69, "road state highway (off freeway)": 89.40, "road freeway": 97.99,
         "road county road (outside cities)": 97.57}            # run 10b as published (run10-2026-10-25.md)
ROADS = ("road city street", "road state highway (off freeway)", "road freeway", "road county road (outside cities)")


def low(k: int, n: int, z: float = 1.96) -> float | None:
    if not n:
        return None
    p = k / n
    return 100 * (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def kn(k, n) -> str:
    return f"{100 * k / n:.1f}% ({k:,} / {n:,}; low {low(k, n):.1f}%)" if n else "n = 0"


def verdict(k, n, bar) -> str:
    if n < MIN_N:
        return f"can't tell yet (n = {n})"
    return "flip" if low(k, n) >= bar else "don't flip"


def main() -> None:
    rec = json.loads((DATA / "run11_reconcile.json").read_text())
    tiers = json.loads((DATA / "run11_tiers.json").read_text())
    acc = json.loads((DATA / "accuracy_by_agency_r11.json").read_text())
    vg = {c: json.loads(p.read_text()) for c in ("sf", "la") if (p := RES / f"geocode_{c}_test_union_summary.json").exists()}
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "origin/main"], capture_output=True,
                            text=True).stdout.strip()
    pool = {t: Counter() for t in ("exact", "verified_typo")}
    agencies = 0
    for a in acc:
        if a.get("exact_counts"):
            agencies += 1
            for t in pool:
                pool[t].update(a.get(f"{t}_counts") or {})
    ex, vt = pool["exact"], pool["verified_typo"]
    ex_int, ex_pt = low(ex["ok_consistent"], ex["n_consistent"]), low(ex["ok_point"], ex["n"])
    c10, c11 = rec["coverage_10d"], rec["coverage_11"]
    L = [f"# Run 11: statewide placement on today's main + the switched-off tiers (2026-11-03)", "",
         f"Tester session for #387, measure only. App code: main {commit} (since run 10: #212 abbreviations, D3 wording, "
         "#259/#261 freeway fixes, #280 FARS before an approximate spot, #283 NAD house addresses, #318/#319 crossing "
         "and postmile tiers, both off). Basis as run 10: CCRS mirror 2026-10-19, OSM 2026-10-18, TIGER/Line 2026. "
         "Harness:", "", "```", "coverage.py --network box1km --aliases --rule2 --tiger --run11", "```", "",
         "`--run11` = `--run10` plus the app's placement step as it is on main: true freeway connectors held (#261), a "
         "fitting FARS point beats an approximate spot (#280), approximate spots only for crashes with no usable GPS "
         "(PM 2026-10-25), and house-address crashes at their NAD point (#283, approximate). Compared with run 10d "
         "(run 10 with the freeway step redone as #278/#281), counted the same way.", "",
         f"Completeness: all {rec['crashes']:,} crashes in run 10d and run 11.", "", "## Coverage", "",
         "| | Run 10b (published) | Run 10d | **Run 11** | Fatal | Fatal + serious | Police GPS | CrashIQ |",
         "|---|---|---|---|---|---|---|---|"]
    for k in ("all",) + ROADS:
        a, b = c10[k], c11[k]
        L.append(f"| {k.replace('road ', '') if k != 'all' else 'All crashes'} | {RUN10[k]:.2f} | {a['crashes_on_map_pct']:.2f} | "
                 f"**{b['crashes_on_map_pct']:.2f}** | {b['fatal_on_map_pct']} | {b['ksi_on_map_pct']} | "
                 f"{b['police_gps_pct']} | {b['crashiq_pct']} |")
    cs, sh = c11["road city street"]["crashes_on_map_pct"], c11["road state highway (off freeway)"]["crashes_on_map_pct"]
    L += ["", f"**Past 90%?** City streets {cs:.2f}% ({'yes' if cs >= 90 else 'no'}); state highway off freeway "
          f"{sh:.2f}% ({'yes' if sh >= 90 else 'no'}).", "",
          f"Approximate in run 11: {c11['all']['approx']:,} crashes ({rec['approximate_by_kind']}).", "",
          "| District | Run 10d % | Run 11 % | Fatal % | Fatal + serious % | Approximate |", "|---|---|---|---|---|---|"]
    for d in range(1, 13):
        a, b = c10.get(f"district {d}"), c11.get(f"district {d}")
        if a and b:
            L.append(f"| {d} | {a['crashes_on_map_pct']:.2f} | {b['crashes_on_map_pct']:.2f} | {b['fatal_on_map_pct']} | "
                     f"{b['ksi_on_map_pct']} | {b['approx']:,} |")
    L += ["", "What moved (run 10d → 11, crashes onto / off the map; fatal, fatal + serious):", ""]
    for k, v in list(rec["effects"].items())[:10]:
        L.append(f"- {k}: {v['crashes']:,} ({v['fatal']} / {v['ksi']})")
    nia = rec["not_in_app_gps_off_roads"]
    if nia:
        L.append(f"- Not counted (GPS off its roads; the app keeps the officer's GPS): {sum(nia.values()):,} spots found "
                 f"({nia}).")
    g = rec["verified_typo_gain"]
    tot = g.get("all", {})
    L += ["", "## Switched-off tiers", "",
          f"Accuracy bar: the exact tier on the same truth. Hidden police GPS = `accuracy_by_agency.py --tiger` on "
          f"{agencies} agencies (400 crashes each, seed 88): exact right intersection {kn(ex['ok_consistent'], ex['n_consistent'])}"
          f" on self-consistent GPS; exact final point within 250 ft {kn(ex['ok_point'], ex['n'])} on all GPS.", "",
          "| Tier | Crashes gained, no usable GPS (fatal / KSI) | Also GPS off its roads | Hidden police GPS | Open data (SF / LAPD) | Exact on the same truth (low) | Recommendation |",
          "|---|---|---|---|---|---|---|"]
    vg_cell = " / ".join(f"{c.upper()} {kn(round(s['verified_typo']['accuracy'] * s['verified_typo']['n']), s['verified_typo']['n'])}"
                         for c, s in vg.items())
    vg_ex = " / ".join(f"{c.upper()} {100 * s['arms']['A  exact only (default gate)']['wilson_low']:.1f}%" for c, s in vg.items())
    gn, go = g.get("gps none", {}), g.get("gps off", {})
    L.append(f"| verified_typo (#233) | {gn.get('crashes', 0):,} ({gn.get('fatal', 0)} / {gn.get('ksi', 0)}) | "
             f"{go.get('crashes', 0):,} | right intersection {kn(vt['ok_consistent'], vt['n_consistent'])} | {vg_cell} | "
             f"{ex_int:.1f}%; {vg_ex} | {verdict(vt['ok_consistent'], vt['n_consistent'], ex_int)} |")
    for t in ("postmile", "crossing_rail", "crossing_path"):
        r = tiers.get(t, {})
        gd = r.get("gained", {})
        w = r.get("within_250ft", {"k": 0, "n": 0})
        w4, w5 = r.get("within_400ft", {"k": 0, "n": 0}), r.get("within_2640ft", {"k": 0, "n": 0})
        L.append(f"| {t} ({'#319' if t == 'postmile' else '#318'}) | {gd.get('none_all', 0):,} ({gd.get('none_fatal', 0)} / "
                 f"{gd.get('none_ksi', 0)}) | {gd.get('off_roads_all', 0):,} | within 250 ft {kn(w['k'], w['n'])}; "
                 f"400 ft {kn(w4['k'], w4['n'])}; 0.5 mi {kn(w5['k'], w5['n'])} | not tested (see below) | "
                 f"{ex_pt:.1f}% (final point, 250 ft) | {verdict(w['k'], w['n'], ex_pt)} |")
    L += ["", "Notes:",
          "- Gained = crashes run 11 leaves off the map that the tier would place. The headline is crashes with no usable "
          "GPS, the only ones the app sends to these tiers (crashes.pull routes no-GPS reports); \"GPS off its roads\" "
          "is shown apart.",
          "- verified_typo runs inside the locator, so the statewide run records it per crash (`tier` column). Its "
          "hidden-GPS figure is right intersection on self-consistent police GPS, the measure the exact tier's 92% is.",
          "- postmile and the crossings run outside the locator, on a corridor. Statewide (`run11_tiers.py`) the "
          "corridor is the report's other road: for postmile the route it names by number (no number, no spot); for "
          "crossings every OSM way of that name in the city box + 1 km (else the county), with railways and named "
          "paths from the same OSM extract (`crossing_features.py`). A whole street crosses more often than a drawn "
          "stretch, so the crossing gain is a floor. Truth = police GPS that fits the report, hidden; scored as a "
          "point (they place a point, not an intersection), against the exact tier's final point.",
          "- SF DataSF and LAPD open data: these reports are city streets; mile markers and railway / trail reports "
          "barely occur there, so the open-data tests can't speak for postmile or the crossings.", "",
          "Why no spot (bin-2 reports), top reasons:", ""]
    for t in ("postmile", "crossing_rail", "crossing_path"):
        L.append(f"- {t}: {tiers.get(t, {}).get('why_no_spot_bin2', {})}")
    L += ["", "Outputs: `data/statewide/` in the run-11 worktree (`coverage_crashes_r11_*.csv`, `run11_reconcile.json`, "
          "`run11_tiers.json`, `run11_tiers_rows.csv`, `accuracy_by_agency_r11.json`; `data/results/geocode_*_union_*`), "
          "not committed.", ""]
    OUT.write_text("\n".join(L))
    print(OUT.read_text())


if __name__ == "__main__":
    main()
