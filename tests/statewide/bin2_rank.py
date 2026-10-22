"""Step 2 (#211): the ranked fix table for the user. Every number is read from the measurement outputs:
  bin2_whatif.json     gains on the difficult crashes and accuracy on hidden police GPS (bin2_whatif.py)
  geocode_<city>_test_rows.json / twomaps_<city>_test.json   the open-data tests (backend/scripts/validate_geocode.py
                       on main: SF = DataSF 2023-25, LA = LAPD 2024 open data; test halves; CCRS rows for LA from the
                       Tester's mirror, no network)
  bin2_audit.csv       Part B: root causes on weighted stratified samples (bin2_audit.py); estimated crashes = sum of
                       the sample weights (stratum size / sampled)
  bin2_partA.json      Part A on main

Ranked by crashes gained among fixes whose accuracy holds up against the exact tier (already auto-placed) on the same
truth; fixes that would lower accuracy are listed after, as "not recommended".

Run: python tests/statewide/bin2_rank.py   (writes data/statewide/bin2_rank.json and bin2_rank.md)
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from bin2_whatif import wilson_low

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"


def open_data(city: str) -> dict[str, tuple[int, int]]:
    """Right intersection by code tier on the city's open data: tier -> (k, n)."""
    rows = json.loads((DATA / f"geocode_{city}_test_rows.json").read_text())
    out: dict[str, list[int]] = {}
    for r in rows:
        if r["tier"] in ("review", "address") or r.get("int_ok") is None:
            continue
        k, n = out.setdefault(r["tier"], [0, 0])
        out[r["tier"]] = [k + bool(r["int_ok"]), n + 1]
    return {t: (k, n) for t, (k, n) in out.items()}


def fmt(k: int, n: int) -> str:
    return f"{100 * k / n:.1f}% (low {wilson_low(k, n)}%, n={n:,})" if n else "-"


def audit() -> dict[str, dict[str, float]]:
    est: dict[str, Counter] = {"dont_meet": Counter(), "gps_off": Counter(), "gps_side": Counter()}
    n: Counter = Counter()
    with open(DATA / "coverage_crashes.csv") as f:      # crashes the GPS-check correction moved to bin 1 drop out
        still = {r["collision_id"] for r in csv.DictReader(f) if r["bin"] == "2"}
    with open(DATA / "bin2_audit.csv") as f:
        for r in csv.DictReader(f):
            if r["collision_id"] not in still:
                n["moved_to_bin1"] += 1
                continue
            est[r["sample"]][r["cause"]] += float(r["weight"])
            n[r["sample"]] += 1
            if r["sample"] == "gps_off":
                est["gps_side"][r["gps_side"]] += float(r["weight"])
    return {k: {c: round(v) for c, v in cnt.most_common()} for k, cnt in est.items()} | {"sampled": dict(n)}


def main() -> None:
    w = json.loads((DATA / "bin2_whatif.json").read_text())
    fx = {r["fix"]: r for r in w["fixes"]}
    la, sf = open_data("la"), open_data("sf")
    tm = {c: json.loads((DATA / f"twomaps_{c}_test.json").read_text())["results"] for c in ("la", "sf")}
    au = audit()
    with open(DATA / "coverage_crashes.csv") as f:
        still = {r["collision_id"] for r in csv.DictReader(f) if r["bin"] == "2"}
    dm = au["dont_meet"]
    ex = fx["exact (already auto)"]

    def row(name, fix_key, tier, effort, decision):
        f = fx[fix_key]
        return {"fix": name, "gain": f["gain"], "gain_fatal": f["gain_fatal"], "gain_ksi": f["gain_ksi"],
                "hidden_gps": fmt(f["acc_k"], f["acc_n"]), "la_open_data": fmt(*la.get(tier, (0, 0))),
                "sf_open_data": fmt(*sf.get(tier, (0, 0))), "effort": effort, "decision": decision}
    yard = {"fix": "(yardstick) exact tier, already auto-placed", "gain": None, "gain_fatal": None, "gain_ksi": None,
            "hidden_gps": fmt(ex["acc_k"], ex["acc_n"]), "la_open_data": fmt(*la.get("exact", (0, 0))),
            "sf_open_data": fmt(*sf.get("exact", (0, 0))), "effort": "-", "decision": "-"}
    rec = [
        row("1. Auto-place unique_pair (#201/#203: the two streets, allowing only what the report leaves out, meet "
            "once)", "unique_pair", "unique_pair", "config: add unique_pair to the gate (tier exists on main)",
            "user: gate change (docs/03 98% bar)"),
        {"fix": "2. Fix #212: expand leading abbreviations (AVE M = Avenue M; ST/MT/FT)", "gain": None,
         "gain_upper": len(set(json.loads((DATA / "bin2_leading_abbrev_ids.json").read_text())) & still),
         "gain_fatal": None, "gain_ksi": None,
         "hidden_gps": "measure after the fix (same tiers as today, on more names)", "la_open_data": "-",
         "sf_open_data": "-", "effort": "normalizer bug fix (Engineering)", "decision": "none (bug)"},
        {"fix": "3. OSM + TIGER street-network union (#17)", "gain": None,
         "gain_audit_estimate": dm.get("street missing from the map", 0),
         "hidden_gps": "-", "la_open_data": f"placed {100 * tm['la']['osm']['coverage']:.1f}% -> "
                                         f"{100 * tm['la']['union']['coverage']:.1f}%, accuracy "
                                         f"{100 * tm['la']['osm']['accuracy']:.1f}% -> {100 * tm['la']['union']['accuracy']:.1f}% (all tiers, point)",
         "sf_open_data": f"placed {100 * tm['sf']['osm']['coverage']:.1f}% -> {100 * tm['sf']['union']['coverage']:.1f}%, "
                         f"low {100 * tm['sf']['osm']['wilson_low']:.1f}% -> {100 * tm['sf']['union']['wilson_low']:.1f}%",
         "effort": "build the union for every county; TIGER download for the other 56 counties (user OK needed)",
         "decision": "user: build it, and approve the downloads"},
        {"fix": "4. Alias / spelling table learned from the audit (PROPOSAL only)", "gain": None,
         "gain_audit_estimate": sum(dm.get(c, 0) for c in ("misspelling or abbreviation", "route number vs street name",
                                                           "travel direction in the name", "two streets in one field")),
         "hidden_gps": "-", "la_open_data": "-", "sf_open_data": "-",
         "effort": "table + review UI; every entry approved by the user (CLAUDE.md)", "decision": "user: approve the table"},
    ]
    held = [
        row("Auto-place relaxed (suffix differs)", "relaxed", "relaxed", "config", "below the bar on the low bound"),
        row("Auto-place fuzzy (spelling)", "fuzzy", "fuzzy", "config", "not recommended"),
        row("Auto-place near (streets pass within 30 m)", "near", "near", "config", "not recommended"),
        row("Clue: offset direction picks one of several meeting points", "clue_offset_dir", "-", "code",
            "not recommended (about a coin toss)"),
        row("Clue: jurisdiction (one candidate outside every city)", "clue_jurisdiction", "-", "code", "negligible"),
    ]
    other = {
        "gps_corroborates": {"gain": fx["gps_corroborates"]["gain"], "note": "police-GPS-off crashes whose name-based "
                             "answer (unique_pair / held tiers) lies within a quarter mile of the GPS; all are already in "
                             "the rows above, so this adds confidence, not crashes"},
        "gps_off_sides": au["gps_side"],
        "no_cross_street": {"crashes": next(r["crashes"] for r in json.loads((DATA / "bin2_partA.json").read_text())
                                            ["reasons"] if r["key"] == "no_cross"),
                            "note": "no intersection to place at; FARS already places fatal ones; stays on review"},
        "freeway_or_ramp_in_dont_meet": dm.get("freeway or ramp", 0),
        "audit": au,
    }
    out = {"basis": w["basis"], "base": w["base"], "recommended": rec, "yardstick": yard, "held": held, "other": other}
    (DATA / "bin2_rank.json").write_text(json.dumps(out, indent=1))
    md = ["| Fix | Crashes gained (fatal / KSI) | Hidden police GPS, right intersection | LAPD open data | "
          "SF open data | Effort | Decision |", "|---|---|---|---|---|---|---|"]
    for r in [yard] + rec + held:
        g = (f"{r['gain']:,} ({r['gain_fatal']} / {r['gain_ksi']})" if r.get("gain") is not None else
             f"up to {r['gain_upper']:,}" if r.get("gain_upper") else
             f"~{r['gain_audit_estimate']:,} (audit estimate)" if r.get("gain_audit_estimate") is not None else "-")
        md.append(f"| {r['fix']} | {g} | {r['hidden_gps']} | {r['la_open_data']} | {r['sf_open_data']} | "
                  f"{r['effort']} | {r['decision']} |")
    up = fx["unique_pair"]["by_district"]
    md += ["", "unique_pair by Caltrans district (gain on the difficult crashes; right intersection on hidden police GPS, "
           "self-consistent truth; LAPD open data is District 7, DataSF District 4):", "",
           "| District | Crashes gained | unique_pair, hidden police GPS | exact tier on the same truth |", "|---|---|---|---|"]
    for d in sorted(up, key=lambda x: int(x.split()[-1])):
        v = up[d]
        e = w.get("exact_by_district", {}).get(d, {})
        md.append(f"| {d} | {v['gain']:,} | {fmt(v.get('acc_k', 0), v.get('acc_n', 0))} | {fmt(e.get('k', 0), e.get('n', 0))} |")
    k, n = sf.get("unique_pair", (0, 0))
    md += ["", f"SF DataSF (where the 98% bar was set): unique_pair placed only {n} test-half crashes ({k} right; "
           f"Wilson low {wilson_low(k, n)}%). San Francisco's report names don't leave out what OSM writes, so the tier "
           "almost never fires there and the bar can't be tested on SF for it. LAPD's open data (Los Angeles: report "
           "names without the direction OSM writes) is where the tier is exercised."]
    out["unique_pair_by_district"] = up
    out["exact_by_district"] = w.get("exact_by_district", {})
    out["unique_pair_sf"] = {"k": k, "n": n, "low": wilson_low(k, n)}
    (DATA / "bin2_rank.json").write_text(json.dumps(out, indent=1))
    (DATA / "bin2_rank.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
