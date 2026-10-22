"""Step 2 (#211) Part C: what-if gains x accuracy for candidate fixes, from the bin-2 re-run on current main (bin2.py).

  gain     - difficult crashes (still not auto-placed on main) a fix would put on the map, statewide and by district
  accuracy - the same fix on hidden police GPS (#88): `truth` rows whose GPS is self-consistent with the report as
             written (cons = 1); right = the chosen intersection within 250 ft of the police GPS; k of n, Wilson 95%
             low bound; the exact tier (already auto-placed) on the same truth as the yardstick

Fixes measured here (the network union and the alias table are sized from the Part B audit instead):
  unique_pair        main's #203 tier (gate off): the two streets, allowing only what the report leaves out, meet once
  relaxed / near / fuzzy  the held tiers, each on its own
  clue_offset_dir    streets that meet in more than one place: exactly one candidate where the primary road leaves in
                     the stated offset direction
  clue_jurisdiction  same, outside cities: exactly one candidate outside every incorporated city (CHP / sheriff area)
  gps_corroborates   police GPS off the roads (beyond 400 ft + offset) but the name-based answer of the held tiers or
                     the unique pair lies within GPS_NEAR_FT of it: two independent sources agree. No hidden-GPS
                     accuracy is possible (the GPS is the clue), so the accuracy column says so.

Run: python tests/statewide/bin2_whatif.py   (reads data/statewide/bin2_*.csv, writes bin2_whatif.json / .md)
"""

from __future__ import annotations

import csv
import glob
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
TOL_M = 250 * 0.3048
GPS_NEAR_FT = 1320            # a quarter mile


def wilson_low(k: int, n: int, z: float = 1.96) -> float | None:
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    return round(100 * (p + z * z / (2 * n) - z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5) / d, 1)


def metres(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))


def _f(x):
    return float(x) if x not in ("", None) else None


def city_polys() -> list[tuple[tuple, list]]:
    """Incorporated city outlines (OSM admin_level 8), with their boxes, for the jurisdiction clue."""
    import sqlite3
    con = sqlite3.connect(ROOT / "data" / "osm" / "ca_osm.sqlite")
    return [((a, b, c, d), json.loads(r)) for r, a, b, c, d in
            con.execute("SELECT rings, minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '8'")]


def inside(p, polys) -> bool:
    for (a, b, c, d), rings in polys:
        if not (a <= p[0] <= c and b <= p[1] <= d):
            continue
        hit = False
        for ring in rings:
            for (y1, x1), (y2, x2) in zip(ring, ring[1:] + ring[:1]):
                if (y1 > p[0]) != (y2 > p[0]) and p[1] < (x2 - x1) * (p[0] - y1) / (y2 - y1) + x1:
                    hit = not hit
        if hit:
            return True
    return False


def pick(rule: str, r: dict, polys) -> tuple | None:
    """The point a fix would place this crash at (an intersection), or None."""
    tier = r["tier"]
    node = (_f(r["node_lat"]), _f(r["node_lon"])) if r.get("node_lat") else None
    if rule in ("unique_pair", "relaxed", "near", "fuzzy"):
        return node if tier == rule and node else None
    if rule.startswith("clue_") and r["clusters"]:
        cl = json.loads(r["clusters"])
        if rule == "clue_offset_dir":
            fit = [c for c in cl if c[2] == 1]
            return (fit[0][0], fit[0][1]) if len(fit) == 1 and len(cl) > 1 else None
        if rule == "clue_jurisdiction" and r["city"] in ("Unincorporated", ""):
            out = [c for c in cl if not inside((c[0], c[1]), polys)]
            return (out[0][0], out[0][1]) if len(out) == 1 else None
    if rule == "gps_corroborates" and r["reason_199"].startswith("police GPS off") and r["gps_lat"] and node \
            and tier in ("unique_pair", "relaxed", "near", "fuzzy"):
        return node if metres(node, (float(r["gps_lat"]), float(r["gps_lon"]))) <= GPS_NEAR_FT * 0.3048 else None
    return None


RULES = ["unique_pair", "relaxed", "near", "fuzzy", "clue_offset_dir", "clue_jurisdiction", "gps_corroborates"]


def main() -> None:
    dist = {}
    with open(ROOT / "data" / "reference" / "caltrans_districts.csv") as f:
        for r in csv.DictReader(f):
            dist[int(r["ccrs_county_code"])] = f"District {r['caltrans_district']}"
    polys = city_polys()
    with open(DATA / "coverage_crashes.csv") as f:      # the current bins (after the #199 GPS-check correction)
        still = {r["collision_id"] for r in csv.DictReader(f) if r["bin"] == "2"}
    gain, acc = defaultdict(Counter), defaultdict(Counter)
    base = Counter()
    seen = set()
    for p in sorted(glob.glob(str(DATA / "bin2_*.csv"))):
        if Path(p).name.startswith(("bin2_audit", "bin2_whatif", "bin2_partA")):
            continue
        with open(p) as f:
            for r in csv.DictReader(f):
                key = (r["set"], r["collision_id"])
                if key in seen:
                    raise SystemExit(f"{key} twice")
                seen.add(key)
                d = dist.get(int(r["county_code"] or 0), "unknown")
                if r["set"] == "gain":
                    if r["collision_id"] not in still:
                        base["now_bin1_after_gps_check_fix"] += 1
                        continue
                    base["difficult_199"] += 1
                    if r["auto"] == "1":
                        base["placed_by_main_already"] += 1
                        continue
                    base["difficult_main"] += 1
                    claimed = False
                    for rule in RULES:
                        if pick(rule, r, polys) is not None:
                            gain[rule]["California"] += 1
                            gain[rule][d] += 1
                            gain[rule]["fatal"] += r["killed"] == "1"
                            gain[rule]["ksi"] += r["ksi"] == "1"
                            if not claimed:                 # first rule in RULES order that places it
                                gain[rule]["first"] += 1
                                claimed = True
                elif r["set"] == "truth" and r["gps_lat"] and r["tier"] in ("near", "fuzzy") and r["node_lat"]:
                    # no self-consistent truth exists for these tiers (the named streets don't meet), so all police
                    # GPS that fits the roads is the truth: a lower bound
                    t = (float(r["gps_lat"]), float(r["gps_lon"]))
                    acc[r["tier"]]["n"] += 1
                    acc[r["tier"]]["k"] += metres((float(r["node_lat"]), float(r["node_lon"])), t) <= TOL_M
                if r["set"] == "truth" and r["cons"] == "1" and r["gps_lat"]:
                    t = (float(r["gps_lat"]), float(r["gps_lon"]))
                    if r["tier"] == "exact" and r["node_lat"]:
                        ok = metres((float(r["node_lat"]), float(r["node_lon"])), t) <= TOL_M
                        for key in ("exact (already auto)", "exact (already auto) @" + d):
                            acc[key]["n"] += 1
                            acc[key]["k"] += ok
                    for rule in [x for x in RULES[:-1] if x not in ("near", "fuzzy")]:
                        q = pick(rule, r, polys)
                        if q is not None:
                            acc[rule]["n"] += 1
                            acc[rule]["k"] += metres(q, t) <= TOL_M
                            acc[rule + " @" + d]["n"] += 1
                            acc[rule + " @" + d]["k"] += metres(q, t) <= TOL_M
    rows = []
    for rule in ["exact (already auto)"] + RULES:
        a = acc.get(rule, Counter())
        rows.append({"fix": rule, "gain": gain[rule].get("California", 0), "gain_first": gain[rule].get("first", 0),
                     "gain_fatal": gain[rule].get("fatal", 0), "gain_ksi": gain[rule].get("ksi", 0),
                     "acc_n": a["n"], "acc_k": a["k"], "acc_pct": round(100 * a["k"] / a["n"], 1) if a["n"] else None,
                     "acc_low": wilson_low(a["k"], a["n"]),
                     "by_district": {d: {"gain": v, **({"acc_n": acc[rule + " @" + d]["n"], "acc_k": acc[rule + " @" + d]["k"]}
                                                     if acc.get(rule + " @" + d) else {})}
                                     for d, v in sorted(gain[rule].items()) if d.startswith("District")}})
    exact_by_d = {k.split(" @")[1]: dict(v) for k, v in acc.items() if k.startswith("exact (already auto) @")}
    out = {"exact_by_district": exact_by_d, "basis": "bin2.py on main e2f1633 (backend unchanged since); #199 per-crash file; mirror 2026-10-19; OSM "
                    "2026-10-18", "base": dict(base), "fixes": rows}
    (DATA / "bin2_whatif.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(base))
    for r in rows:
        print(f"{r['fix']:22} gain {r['gain']:>7} (first {r['gain_first']:>7}, fatal {r['gain_fatal']}) | "
              f"acc {r['acc_k']}/{r['acc_n']} = {r['acc_pct']}% low {r['acc_low']}%")


if __name__ == "__main__":
    main()
