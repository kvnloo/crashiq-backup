"""Run 8: hidden-police-GPS accuracy of the auto-placing tiers (exact, unique_pair) in one Caltrans district, on EVERY
crash there whose GPS fits the report's roads (no per-city sample), with the app's current code and the run-8 network
(box + 1 km). Truth = the police GPS, hidden from the locator, kept only where it is self-consistent with the report
as written (within 400 ft of a meeting point of the two named streets, trailing direction included: bin2.py's rule).
Right = the chosen intersection within 250 ft of the GPS. Wilson 95% low bound.

Run: python tests/statewide/run8_truth.py --district 5   (writes data/statewide/run8_truth_d5.csv / .json)
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
TOL_M, CONS_M = 250 * 0.3048, 400 * 0.3048


def main(district: int) -> None:
    from crashiq import locate, names, osm

    import citywide as cw
    import corridors
    import osm_local
    from bin2_whatif import wilson_low
    from coverage import Outside, districts

    dist, cname = districts()
    counties = {c for c, d in dist.items() if d == district}
    want = defaultdict(set)
    with open(DATA / "coverage_crashes_199v2.csv") as f:           # the corrected #199 file: gps_usable = truth pool
        for r in csv.DictReader(f):
            if r["outcome"] == "gps_usable" and int(r["county_code"] or 0) in counties:
                want[r["city"]].add(r["collision_id"])
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            box[code] = r
    outside = Outside(local, box)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    rows = []
    for city, ids in sorted(want.items(), key=lambda kv: -len(kv[1])):
        b = bounds.get(corridors.norm_city(city)) if city else None
        cw._fuzzy_memo.clear()
        net = osm.Network(osm_local.network_in_box(local, b["rel"])) if b else None
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in ids or cid in seen:
                continue
            seen.add(cid)
            t = (c["lat"], c["lon"])
            q = {**c, "lat": None, "lon": None}
            n_ = net if net is not None else outside.network(q)
            if n_ is None:
                continue
            pl = locate.place(n_, q)
            kp, ks = names.street_key(c.get("primary_road")), names.street_key(c.get("secondary_road"))
            a = locate._same_core_keys(n_, kp) if kp else []
            bb = [s for s in (locate._same_core_keys(n_, ks) if ks else []) if s not in a]
            tp, ts = names.directions(c.get("primary_road"))[1], names.directions(c.get("secondary_road"))[1]
            meet = [n for n in locate._shared_nodes(n_, a, bb)
                    if locate._trail_fits(n_, n, a, tp) and locate._trail_fits(n_, n, bb, ts)] if a and bb else []
            cons = any(osm.metres(n_.coord[n], t) <= CONS_M for n in meet)
            ok = pl.node is not None and osm.metres(n_.coord[pl.node], t) <= TOL_M
            rows.append({"collision_id": cid, "city": city, "tier": pl.tier, "cons": int(cons), "right": int(ok)})
        print(f"{city or '(blank)'}: {len(seen)}", flush=True)
    with open(DATA / f"run8_truth_d{district}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["collision_id", "city", "tier", "cons", "right"])
        w.writeheader()
        w.writerows(rows)
    res = {"district": district, "truth_crashes": sum(r["cons"] for r in rows), "tiers": {}, "cities": {}}
    for tier in ("exact", "unique_pair", "relaxed"):
        sel = [r for r in rows if r["cons"] and r["tier"] == tier]
        k, n = sum(r["right"] for r in sel), len(sel)
        res["tiers"][tier] = {"k": k, "n": n, "pct": round(100 * k / n, 1) if n else None, "low": wilson_low(k, n)}
    per = defaultdict(Counter)
    for r in rows:
        if r["cons"] and r["tier"] in ("exact", "unique_pair"):
            per[r["city"]][r["tier"] + "_n"] += 1
            per[r["city"]][r["tier"] + "_k"] += r["right"]
    res["cities"] = {c: dict(v) for c, v in sorted(per.items(), key=lambda kv: -kv[1].get("unique_pair_n", 0))}
    (DATA / f"run8_truth_d{district}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["tiers"]))
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", type=int, required=True)
    main(ap.parse_args().district)
