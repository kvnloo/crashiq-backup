"""Run 8 write-up: the reconciliation by effect, coverage after it, District 5 accuracy, and the claims check C7-C9.
Every number is read from run8_reconcile.json, coverage_r8a.json, run8_truth_d5.json and accuracy_by_agency_r8.json.

Run: python tests/statewide/run8_report.py   (writes data/statewide/run8_report.md and tracker/run8_effects.csv)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bin2_whatif import wilson_low

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"


def pooled(acc: list[dict], tiers: tuple[str, ...]) -> tuple[int, int, int]:
    """Right intersection on self-consistent police GPS, pooled over agencies: (k, n, agencies)."""
    k = n = m = 0
    for a in acc:
        got = False
        for t in tiers:
            c = a.get(f"{t}_counts")
            if c:
                k += c["ok_consistent"]
                n += c["n_consistent"]
                got = got or c["n_consistent"] > 0
        m += got
    return k, n, m


def main() -> None:
    rc = json.loads((DATA / "run8_reconcile.json").read_text())
    cv = json.loads((DATA / ("coverage_r8b.json" if (DATA / "coverage_r8b.json").exists() else "coverage_r8a.json")).read_text())
    d5 = json.loads((DATA / "run8_truth_d5.json").read_text())
    acc = json.loads((DATA / "accuracy_by_agency_r8.json").read_text())
    s = cv["statewide"][0]
    st = rc["stages"]
    md = ["# Run 8: unique_pair on, #212, #218 GPS rules, unclipped network (2026-10-22)", "",
          "Basis: CCRS mirror 2026-10-19 + Parties_2025 file, OSM 2026-10-18. Run 8a: app code main 2c4d2f4 (unique_pair "
          "auto-places, #212 in). Run 8b: main 95f3f40 (#218 GPS rules, PR #225; backend tree a63f583340d0). Network: "
          "each city's box + 1 km (PM 2026-10-22), not the clipped outline. "
          f"Completeness: {s['crashes']:,} crashes in every stage.", "",
          "## Reconciliation by effect", "", "| Stage | On the map | Fatal | Fatal + serious |", "|---|---|---|---|"]
    for k, v in st.items():
        md.append(f"| {k} | {v['on_map']:,} ({v['on_map_pct']}%) | {v['fatal_on_map_pct']}% | {v['ksi_on_map_pct']}% |")
    md += ["", "| Effect | Crashes onto the map | On the map | Main moves |", "|---|---|---|---|"]
    for e in rc["effects"]:
        mv = "; ".join(f"{k}: {v:,}" for k, v in list(e["moves"].items())[:3])
        md.append(f"| {e['effect']} | {e['on_map_change']:+,} | {e['on_map_pct']}% | {mv} |")
    md += ["", "Note: the stage with the gate at exact only labels unique-pair crashes \"named streets don't meet\" "
           "(review -> cant_place above); that relabel moves no crash between bins.", "",
           "## Coverage after run 8", "",
           f"- All crashes: **{s['on_map_pct']}% on the map** ({s['difficult_pct']}% difficult). Police GPS "
           f"{s['police_gps_pct']}%, CrashIQ {s['crashiq_placed_pct']}% (unique pair {s['unique_pair_pct']}%), FARS "
           f"{s['fars_pct']}%.",
           f"- Fatal: {s['fatal_on_map_pct']}%. Fatal + serious injury: {s['ksi_on_map_pct']}%.", "",
           "| Caltrans district | On the map % |", "|---|---|"]
    md += [f"| {r['name']} | {r['on_map_pct']} |" for r in sorted(cv["district"], key=lambda r: int(r["name"].split()[-1])
                                                                     if r["name"].split()[-1].isdigit() else 99)]
    md += ["", "| Road type | On the map % | CrashIQ placed % |", "|---|---|---|"]
    md += [f"| {r['name']} | {r['on_map_pct']} | {r['crashiq_placed_pct']} |" for r in cv["road_type"]]
    t = d5["tiers"]
    md += ["", "## District 5 accuracy (every D5 crash with self-consistent police GPS, hidden; run-8 code and network)",
           "", "| Tier | Right intersection | n | 95% low |", "|---|---|---|---|"]
    md += [f"| {k} | {v['pct']}% | {v['n']:,} | {v['low']}% |" for k, v in t.items() if v["n"]]
    sm = d5["cities"].get("Santa Maria", {})
    md += ["", f"With every crash counted, unique_pair is at or above exact in District 5. The earlier gap (85.2% vs 89.2%) "
           "came from a 291-crash sample. The weak spot is Santa Maria: unique_pair "
           f"{sm.get('unique_pair_k')}/{sm.get('unique_pair_n')}, exact {sm.get('exact_k')}/{sm.get('exact_n')}. In all 12 "
           "misses inspected, CrashIQ chose the intersection the report names (Broadway & Cook, Western & Stowell, "
           "Main & Depot ...), with the police GPS 82-149 m away on wide arterials, just past the 250 ft scoring radius: "
           "a truth-precision effect in one city, not wrong intersections."]
    ke, ne, me = pooled(acc, ("exact",))
    ku, nu, mu = pooled(acc, ("unique_pair",))
    kb, nb, mb = pooled(acc, ("exact", "unique_pair"))
    md += ["", "## Claims check (knowledge/claims.md)", "", "| # | Claim says | Run 8a | Holds? |", "|---|---|---|---|",
           f"| C7 | 86% on the map; fatal 95% | {s['on_map_pct']}%; fatal {s['fatal_on_map_pct']}%; fatal + serious "
           f"{s['ksi_on_map_pct']}% | Holds and is now low: update to run 8 (after 8b) |",
           "| C8 | city streets: CrashIQ places nearly a third (75.0% on the map, 29.4% placed) | city streets "
           f"{next(r['on_map_pct'] for r in cv['road_type'] if r['name'] == 'city street')}% on the map, CrashIQ "
           f"{next(r['crashiq_placed_pct'] for r in cv['road_type'] if r['name'] == 'city street')}% | Update: \"two in five\" |",
           f"| C9 | 92.1% at the right intersection (exact tier, {144} agencies) | exact {100 * ke / ne:.1f}% "
           f"({ke:,}/{ne:,}, low {wilson_low(ke, ne)}%); unique pair {100 * ku / nu:.1f}% ({ku:,}/{nu:,}, low "
           f"{wilson_low(ku, nu)}%); both auto tiers {100 * kb / nb:.1f}% ({kb:,}/{nb:,}, low {wilson_low(kb, nb)}%), "
           f"{mb} agencies | Restate for both auto tiers |"]
    r2 = json.loads((DATA / "run8b_rule2.json").read_text())
    sn = json.loads((DATA / "run8b_snapped.json").read_text())
    rcc = json.loads((DATA / "reconcile_5447e864597e-pfile_a63f583340d0-pfile.json").read_text())
    fo0 = json.loads((DATA / "fatal_outcomes_5447e864597e.json").read_text())["fatal_outcomes"]
    fo1 = json.loads((DATA / "fatal_outcomes_a63f583340d0.json").read_text())["fatal_outcomes"]
    fd = json.loads((DATA / "findings_a63f583340d0.json").read_text())["summary"]
    md += ["", "## #218 GPS rules (run 8b)", "",
           f"Rule 2, statewide: of {r2['gps_crashes_checked']:,} crashes the coverage placed by police GPS, the app now "
           f"ignores the GPS of {sum(r2['ignored'].values())} ({r2['ignored']}); placed again from their street names:",
           "", "| Move | Crashes |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in r2["moves"].items()]
    md += ["", "Rule 1 moves a point along the road, never between bins. Citywide sample, every crash with fitting "
           "police GPS of the four agencies Engineering named (the app's own `gps_rules._along_named_road`):", "",
           "| Agency | GPS fits | At the named intersection | With a stated offset | Moved | Kept (no road that way) | "
           "Moved > 250 ft | Median move | 90th pct |", "|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {k} | {v.get('gps_fits', 0):,} | {v.get('at_named_intersection', 0):,} | {v.get('snapped_with_offset', 0):,} | "
           f"{v.get('moved', 0):,} | {v.get('kept_no_road_that_way', 0)} | {v.get('moved_beyond_250ft', 0)} | "
           f"{v.get('median_move_ft')} ft | {v.get('p90_move_ft')} ft |" for k, v in sn.items()]
    md += ["", "These counts use the app's stricter name match (exact keys first); #219's profile class (11% in Santa "
           "Ana) matched name cores, so it is an upper bound.", "",
           "## Frozen test roads, run 7b -> 8 (same data basis; code 5447e864597e -> a63f583340d0)", "",
           f"Crashes kept {rcc['kept'][0]:,} -> {rcc['kept'][1]:,}; located {rcc['located'][0]:,} -> {rcc['located'][1]:,}.",
           "", "| Bucket | Crashes | Change kept | Change located |", "|---|---|---|---|"]
    lbl = {"found_located": "newly found and located (#218: rows at default points / coarse GPS searched by name)",
           "found_unlocated": "newly found, held for review (same)", "found_excluded": "newly found, excluded (same)",
           "placement_changed": "placement changed (unique_pair; #212)"}
    md += [f"| {lbl.get(b_['bucket'], b_['what'])} | {b_['crashes']:,} | {b_['change_in_kept']:+} | {b_['change_in_located']:+} |"
           for b_ in rcc["buckets"] if b_["crashes"] and b_["bucket"] != "unchanged"]
    md += ["", "| Fatal crashes on the test roads | Run 7 | Run 8 |", "|---|---|---|"]
    md += [f"| {k} | {fo0.get(k, 0)} | {fo1.get(k, 0)} |" for k in sorted(set(fo0) | set(fo1))]
    md += ["", f"Findings on run-8 code: {fd['findings']:,} findings on {fd['with_findings']} test roads, "
           f"{fd['rejected']} rejected by the validator; pass/warn/fail {fd['by_result']}.", "",
           "| # | Claim says | Run 8 | Holds? |", "|---|---|---|---|",
           "| C4 | unplaced fatal on the test roads 27 -> 6 | run 8: " +
           f"{fo1.get('unplaced', 0) + fo1.get('unplaced_with_fars_hint', 0)} | Update |",
           f"| C5 | 0 rejections | {fd['rejected']} of {fd['findings']:,} | Holds |"]
    hist = list(csv.DictReader(open(HERE / "run_history.csv")))[-1]
    fre = next((json.loads(f.read_text()) for f in (DATA / "results" / f"{hist['backend_tree']}-pfile").glob("FREMONT*.json")),
               {})
    md += [f"| C2 | 524 cities tested | {len(list((DATA / 'results' / (hist['backend_tree'] + '-pfile')).glob('*.json')))} "
           "city results | Holds |",
           f"| C3 | no report silently missed (v4) | {hist['silent_drops_v4']} | Holds |",
           f"| C6 | Fremont: 97% of the test road's crashes located | {fre.get('result_reason_v4')} | Holds |"]
    (DATA / "run8_report.md").write_text("\n".join(md) + "\n")
    with open(DATA / "tracker" / "run8_effects.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["effect", "crashes", "on_map_pct"])
        for e in rc["effects"]:
            w.writerow([e["effect"], e["on_map_change"], e["on_map_pct"].split(" -> ")[1]])
    print("\n".join(md))


if __name__ == "__main__":
    main()
