"""Step 2 (#211) Part A: what's in the difficult bin, by reason x district / county / city / road type / agency /
severity. Reads the per-crash coverage file (coverage_crashes.csv, #199) or, with --main, the bin-2 re-run on current
main (bin2_*.csv, where the reason is recomputed from main's locator answer). Code computes every number; this file
only counts.

Run: python tests/statewide/bin2_report.py [--main]   (writes data/statewide/bin2_partA.json and bin2_partA.md)
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
GPS_OFF = "police GPS off the report's roads; "
REASONS = [  # (key, label, test on the reason text without the GPS-off prefix)
    ("unique_pair", "unique pair held by the gate (#201: the two streets meet only once)",
     lambda r: r.startswith("unique pair")),
    ("relaxed", "relaxed match held by the gate", lambda r: r.startswith("relaxed match")),
    ("dont_meet", "named streets don't meet on the map", lambda r: r.startswith("named streets don't meet")),
    ("no_cross", "no cross street (blank, NOT STATED, UNKNOWN, PRIVATE PROPERTY)", lambda r: r.startswith("no cross street")),
    ("near_fuzzy", "near / fuzzy match held by the gate", lambda r: r.startswith(("near match", "fuzzy match"))),
    ("multi", "streets meet in more than one place", lambda r: r.startswith("streets meet in more than one place")),
    ("no_map", "no street map for this place", lambda r: r.startswith("no street map")),
]
TOP = 25


def reason_key(reason: str) -> tuple[str, bool]:
    gps_off = reason.startswith(GPS_OFF)
    r = reason[len(GPS_OFF):] if gps_off else reason
    for k, _, test in REASONS:
        if test(r):
            return k, gps_off
    return "other", gps_off


def _districts() -> dict[int, str]:
    with open(ROOT / "data" / "reference" / "caltrans_districts.csv") as f:
        return {int(r["ccrs_county_code"]): r["county"] for r in csv.DictReader(f)}


def part_a(rows) -> dict:
    county_name = _districts()
    total, bin2 = 0, 0
    by = defaultdict(lambda: defaultdict(Counter))     # dimension -> value -> reason counter
    gps_off = Counter()
    sev = defaultdict(Counter)
    for r in rows:
        total += 1
        if r["bin"] != "2":
            continue
        bin2 += 1
        k, off = reason_key(r["reason"])
        gps_off[(k, off)] += 1
        dims = {"reason": "all", "district": f"District {r['district']}" if r["district"] else "unknown",
                "county": county_name.get(int(r["county_code"] or 0), "unknown"), "city": r["city"] or "(blank)",
                "road_type": r["road_type"], "agency": r["agency"]}
        for d, v in dims.items():
            by[d][v][k] += 1
            by[d][v]["_gps_off"] += off
            by[d][v]["_n"] += 1
        s_ = "fatal" if r["killed"] == "1" else "serious injury (KSI, not fatal)" if r["ksi"] == "1" else "other"
        sev[s_][k] += 1
        sev[s_]["_gps_off"] += off

    ag = {x["ncic"]: (f"{x['ncic']} {x.get('city') or ''} ({x.get('type')})" if (x.get("n_cities") or 1) <= 3 else
                      f"{x['ncic']} {x.get('city')} + {x.get('n_cities') - 1} more city names ({x.get('type')})")
          for x in json.loads((DATA / "agencies.json").read_text())}

    def table(d, top=None):
        items = sorted(by[d].items(), key=lambda kv: -kv[1]["_n"])
        return [{"name": ag.get(v, v) if d == "agency" else v, "difficult": c["_n"], "gps_off": c["_gps_off"], **{k: c.get(k, 0) for k, _, _ in REASONS},
                 "other": c.get("other", 0)} for v, c in (items[:top] if top else items)]
    return {"crashes": total, "difficult": bin2,
            "reasons": [{"key": k, "reason": lbl, "crashes": sum(v for (kk, _), v in gps_off.items() if kk == k),
                         "with_police_gps_off": gps_off.get((k, True), 0)} for k, lbl, _ in REASONS],
            "district": table("district"), "county": table("county"), "city_top25": table("city", TOP),
            "road_type": table("road_type"), "agency_top25": table("agency", TOP),
            "severity": [{"name": s, "difficult": sum(v for k, v in c.items() if not k.startswith("_")),
                          "gps_off": c["_gps_off"], **{k: c.get(k, 0) for k, _, _ in REASONS}}
                         for s, c in sorted(sev.items(), key=lambda kv: ("fatal", "serious").index(kv[0].split()[0])
                                            if kv[0].split()[0] in ("fatal", "serious") else 9)]}


def markdown(a: dict, basis: str) -> str:
    keys = [k for k, _, _ in REASONS]
    heads = ["unique pair", "relaxed", "don't meet", "no cross", "near/fuzzy", "meet twice+", "no map"]
    pct = lambda n, d: f"{100 * n / d:.1f}%" if d else "-"      # noqa: E731
    out = [f"# Difficult bin, Part A ({basis})", "",
           f"{a['difficult']:,} of {a['crashes']:,} CCRS crashes 2021-2025 ({pct(a['difficult'], a['crashes'])}).", "",
           "| Reason | Crashes | Share of bin | Police GPS present but off the roads |", "|---|---|---|---|"]
    for r in a["reasons"]:
        out.append(f"| {r['reason']} | {r['crashes']:,} | {pct(r['crashes'], a['difficult'])} | "
                   f"{r['with_police_gps_off']:,} |")
    for title, key in (("Caltrans district", "district"), ("Road type", "road_type"), ("Severity", "severity"),
                       ("Top 25 cities (CCRS city name)", "city_top25"), ("Top 25 agencies (NCIC)", "agency_top25")):
        out += ["", f"## {title}", "", "| " + " | ".join([title, "Difficult"] + heads + ["GPS off"]) + " |",
                "|" + "---|" * (len(heads) + 3)]
        rows = a[key]
        if key == "district":
            rows = sorted(rows, key=lambda r: int(r["name"].split()[-1]) if r["name"].split()[-1].isdigit() else 99)
        for r in rows:
            out.append("| " + " | ".join([str(r["name"]), f"{r['difficult']:,}"] + [f"{r[k]:,}" for k in keys]
                                         + [f"{r.get('gps_off', 0):,}" if "gps_off" in r else "-"]) + " |")
    return "\n".join(out) + "\n"


def main_reason(r: dict) -> str:
    """A difficult crash's reason from main's locator answer (bin2.py), keeping the #199 GPS-off prefix."""
    pre = GPS_OFF if r["reason_199"].startswith(GPS_OFF) else ""
    base = r["reason_199"].removeprefix(GPS_OFF)
    if base.startswith(("no cross street", "no street map")):
        return pre + base
    if r["tier"] == "unique_pair":
        return pre + "unique pair held by the gate"
    if r["tier"] in ("relaxed", "near", "fuzzy"):
        return pre + f"{r['tier']} match held by the gate"
    if "more than one place" in (r["note"] or ""):
        return pre + "streets meet in more than one place"
    if r["note"] == "no street map":
        return pre + "no street map for this place"
    return pre + "named streets don't meet on the map"


def main_rows():
    """Every crash, bins as on main: #199 bin 1 as it was (less the exact placements #206 drops, delta206.py), #199
    bin 2 from the re-run on main (placed if main's gate auto-places it, else its reason on main)."""
    rerun = {}
    for p in sorted(DATA.glob("bin2_*.csv")):
        if p.name.startswith(("bin2_audit", "bin2_whatif", "bin2_partA")):
            continue
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["set"] == "gain":
                    rerun[r["collision_id"]] = r
    lost = {}
    with open(DATA / "delta206_base.csv") as fb, open(DATA / "delta206_main.csv") as fm:
        base = {r["collision_id"]: r for r in csv.DictReader(fb)}
        for r in csv.DictReader(fm):
            if base[r["collision_id"]]["auto"] == "1" and r["auto"] != "1":
                lost[r["collision_id"]] = r
    n2 = 0
    with open(DATA / "coverage_crashes.csv") as f:
        for r in csv.DictReader(f):
            cid = r["collision_id"]
            if r["bin"] == "2":
                n2 += 1
                g = rerun.get(cid)
                if g is None:
                    raise SystemExit(f"bin-2 crash {cid} missing from the re-run (completeness guard)")
                if g["auto"] == "1":
                    yield {**r, "bin": "1", "outcome": "placed_exact", "reason": ""}
                else:
                    yield {**r, "reason": main_reason(g)}
            elif cid in lost:
                m = lost[cid]
                yield {**r, "bin": "2", "outcome": "review",
                       "reason": main_reason({"reason_199": "", "tier": m["tier"], "note": ""})}
            else:
                yield r
    if n2 > len(rerun):
        raise SystemExit(f"re-run has {len(rerun)} bin-2 crashes, the coverage file {n2} (completeness guard)")


def main(use_main: bool) -> None:
    if use_main:
        a = part_a(main_rows())
        basis = "current main e2f1633 (backend unchanged since): #199 file re-placed with bin2.py, CCRS mirror 2026-10-19"
    else:
        with open(DATA / "coverage_crashes.csv") as f:
            a = part_a(csv.DictReader(f))
        basis = "#199 run: app code 5f54c02, CCRS mirror 2026-10-19, OSM 2026-10-18"
    a["basis"] = basis
    (DATA / "bin2_partA.json").write_text(json.dumps(a, indent=1))
    (DATA / "bin2_partA.md").write_text(markdown(a, basis))
    print(f"{a['difficult']} difficult of {a['crashes']} -> {DATA / 'bin2_partA.md'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", action="store_true")
    main(ap.parse_args().main)
