"""Run 12 (#393, #397; measure only): reconcile run 12 (coverage.py ... --run12) with run 11 crash by crash and write
reports/testing/run12-<date>.md + data/statewide/run12_headline.md. Counted as run 11 (run11_reconcile.coverage).
A crash newly at a house address is put down to the county points (#399) when an address source other than NAD
placed it, else to private property (#402) when the report says PRIVATE PROPERTY, else to the harness now reading
addresses with the app's parser (run 11 used locate._house_address and undercounted D5: PR #392).

Run: python tests/statewide/run12_report.py [<sample prefix> <run-11 prefix>]   (a sample, e.g. r12sf r11sample: prints only)
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from run11_reconcile import APPROX, DATA, PRECISE, coverage, load

ROOT = DATA.parents[1]
NEW, OLD = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("r12", "r11")
ROADS = ("city street", "state highway (off freeway)", "freeway", "county road (outside cities)")
sys.path.insert(0, str(ROOT / "backend"))
from crashiq import nad  # noqa: E402


def on(o: str) -> bool:
    return o in PRECISE or o in APPROX


def cause(a: tuple, b: tuple) -> str:
    if b[0] == "placed_address_nad":
        src = b[7].split(":")[-1]
        if src != nad.SOURCE:
            return f"county address points (#399): {src}"
        if ":private:" in b[7]:
            return "private property with a house address (#402)"
        return "house address the app reads that run 11's harness missed (PR #392)"
    return f"other: {a[0]} -> {b[0]}"


def main() -> None:
    r11, r12 = load(OLD), load(NEW)
    if NEW != "r12":
        r11 = {k: v for k, v in r11.items() if k in r12}
    if set(r11) != set(r12):
        raise SystemExit(f"completeness guard: {NEW} {len(r12)} vs {OLD} {len(r11)} crashes")
    eff = defaultdict(Counter)
    for cid, a in r11.items():
        b = r12[cid]
        if on(a[0]) != on(b[0]):
            e = eff[("onto the map: " if on(b[0]) else "off the map: ") + cause(a, b)]
            e["crashes"] += 1
            e["fatal"] += b[3]
            e["ksi"] += b[4]
    sug = Counter(x[7].split(":")[-1] for x in r12.values() if x[7].startswith("suggest:") and not on(x[0]))
    nia = sum(x[7] == "nia:address_nad" for x in r12.values())
    c11, c12 = coverage(r11), coverage(r12)
    (DATA / f"run12_reconcile{'' if NEW == 'r12' else '_' + NEW}.json").write_text(json.dumps(
        {"crashes": len(r12), "effects": {k: dict(v) for k, v in eff.items()}, "suggest_only": dict(sug),
         "gps_off_roads_address": nia, "coverage_11": c11, "coverage_12": c12}, indent=1))
    pc = lambda k: c12[k]["crashes_on_map_pct"]  # noqa: E731
    cs, sh = pc("road city street"), pc("road state highway (off freeway)")
    yes = lambda v: "yes" if v > 90 else "no"  # noqa: E731
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    ans = (f"City streets {cs:.2f}% (run 11 {c11['road city street']['crashes_on_map_pct']:.2f}%): {yes(cs)}; state "
           f"highway off freeway {sh:.2f}% (run 11 {c11['road state highway (off freeway)']['crashes_on_map_pct']:.2f}%): "
           f"{yes(sh)}.")
    print(ans)
    for k, v in sorted(eff.items(), key=lambda kv: -kv[1]["crashes"]):
        print(f"  {k}: {v['crashes']:,} ({v['fatal']} / {v['ksi']})")
    print("suggest only:", dict(sug), "GPS off roads:", nia)
    if NEW != "r12":
        return
    day = datetime.date.today().isoformat()
    a11, a12 = c11["all"], c12["all"]
    L = [f"# Run 12: statewide placement with county address points and private-property addresses ({day})", "",
         f"Tester session for #393 and #397, measure only. App code: main {commit}. Placement changes since run 11 "
         "(c53b23a): #399 county address points where NAD has none (Los Angeles and San Diego place by themselves; "
         "Orange, Fresno, Riverside and San Joaquin only suggest a point for review), #402 PRIVATE PROPERTY with a "
         "house address on the street placed at that address, #391 'Unnamed road' corridor pieces (corridor only, "
         "nothing to measure statewide). Basis as run 11: CCRS mirror 2026-10-19, OSM 2026-10-18, TIGER/Line 2026, "
         "NAD r24; county points downloaded 2026-11-06. Harness:", "",
         "```", "coverage.py --network box1km --aliases --rule2 --tiger --run12", "```", "",
         "`--run12` = `--run11` plus two fixes so the harness measures the app: house addresses are read with the "
         "app's own parser (`crashes.house_address`; run 11 used a stricter look-alike and missed some, PR #392), "
         "and an address point places only when its source is set to place by itself (`nad.auto_sources()`).", "",
         "Statewide there is no drawn corridor, so a house-address crash counts as on the map when an auto-source "
         "point is found under the app's rules (house number, street, city). The app's setback cap (a point too far "
         "off the corridor line isn't used) needs a corridor, so it can't be applied here: a few of these crashes "
         "could still be refused in a real study.", "",
         f"Completeness: all {len(r12):,} crashes in run 11 and run 12.", "", "## Coverage", "",
         "| | Run 11 | **Run 12** | Fatal | Fatal + serious | Police GPS | CrashIQ |", "|---|---|---|---|---|---|---|"]
    for k, lab in [("all", "All crashes")] + [(f"road {r}", r) for r in ROADS]:
        a, b = c11[k], c12[k]
        L.append(f"| {lab} | {a['crashes_on_map_pct']:.2f} | **{b['crashes_on_map_pct']:.2f}** | {b['fatal_on_map_pct']}"
                 f" | {b['ksi_on_map_pct']} | {b['police_gps_pct']} | {b['crashiq_pct']} |")
    L += ["", f"**Past 90%?** {ans}", "",
          "| District | Run 11 % | Run 12 % | Fatal % | Fatal + serious % | Approximate |", "|---|---|---|---|---|---|"]
    for d in sorted((k for k in c12 if k.startswith("district ") and k[9:].isdigit()), key=lambda k: int(k[9:])):
        a, b = c11[d], c12[d]
        L.append(f"| {d[9:]} | {a['crashes_on_map_pct']:.2f} | {b['crashes_on_map_pct']:.2f} | {b['fatal_on_map_pct']} | "
                 f"{b['ksi_on_map_pct']} | {b['approx']} |")
    L += ["", "What moved (run 11 → 12, crashes onto / off the map; fatal, fatal + serious):", ""]
    L += [f"- {k}: {v['crashes']:,} ({v['fatal']} / {v['ksi']})"
          for k, v in sorted(eff.items(), key=lambda kv: -kv[1]["crashes"])] or ["- nothing"]
    L += [f"- Not counted (GPS off its roads; the app keeps the officer's GPS): {nia:,} house-address points found.",
          "- Found only in a suggest-only county layer (on the review list with the point as the suggestion, not on "
          "the map): " + (", ".join(f"{s} {n:,}" for s, n in sug.most_common()) or "none") + ".", "",
          f"Outputs: `data/statewide/` in the run-12 worktree (`coverage_crashes_r12_*.csv`, `run12_reconcile.json`), "
          "not committed.", ""]
    (ROOT / "reports" / "testing" / f"run12-{day}.md").write_text("\n".join(L))
    (DATA / "run12_headline.md").write_text(
        f"Run 12 on main {commit} (statewide, measure only): on the map {a12['crashes_on_map_pct']:.2f}% (run 11 "
        f"{a11['crashes_on_map_pct']:.2f}%), fatal {a12['fatal_on_map_pct']}%, KSI {a12['ksi_on_map_pct']}%.\n\n{ans}\n\n"
        + "\n".join(f"- {k}: {v['crashes']:,} ({v['fatal']} / {v['ksi']})"
                    for k, v in sorted(eff.items(), key=lambda kv: -kv[1]["crashes"])[:6])
        + f"\n\nReport: reports/testing/run12-{day}.md\n")


if __name__ == "__main__":
    main()
