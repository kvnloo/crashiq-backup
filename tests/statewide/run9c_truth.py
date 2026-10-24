"""Run 9C, the evidence for the user's TIGER on/off call (PM 2026-10-23): on hidden police GPS, does the OSM + TIGER
union (#243 fixed) lose or flip correct OSM placements, and how accurate are TIGER-name placements?

Truth: police GPS self-consistent with the report as written (within 400 ft of a meeting point of the two named
streets on the union network), hidden. Two pools: every crash whose GPS fits the report only with TIGER (run 9C
gps_usable, run 9A not), and a seeded yardstick sample of crashes whose GPS fits either way (YARD per city; YARD_OUT
for crashes outside city maps). Each crash is placed twice with the app's locator and gate (exact + unique_pair;
tiger_road held, as configured): on the OSM-only network and on the union (city: box + 1 km; outside cities: the
report's named roads, + TIGER's segments of those names in the union). Right = within 250 ft of the GPS.
  lost     OSM alone auto-places it right; the union doesn't auto-place it
  flipped  OSM alone auto-places it right; the union auto-places it somewhere wrong
  gained   the union auto-places it and OSM alone doesn't (right or wrong counted)

Run: python tests/statewide/run9c_truth.py --shard 0/3 --part c0 ; then --merge c0 c1 c2
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
TOL_M, CONS_M, YARD, YARD_OUT, SEED = 250 * 0.3048, 400 * 0.3048, 50, 3000, 91


def pools():
    def load(prefix):
        out = {}
        for p in sorted(DATA.glob(f"coverage_crashes_{prefix}_*.csv")):
            with open(p) as f:
                for r in csv.DictReader(f):
                    out[r["collision_id"]] = (r["outcome"], r["city"], r["district"])
        return out
    a, c = load("r9a"), load("r9c")
    by, both = defaultdict(dict), defaultdict(list)
    for cid, (o, city, d) in c.items():
        if o == "gps_usable" and a.get(cid, ("",))[0] != "gps_usable":
            by[city][cid] = ("needs_tiger", d)
        elif o == "gps_usable":
            both[city].append((cid, d))
    rng = random.Random(SEED)
    for city, ids in both.items():
        ids.sort(key=lambda t: int(t[0]))
        for cid, d in rng.sample(ids, min(YARD_OUT if city == "Unincorporated" else YARD, len(ids))):
            by[city][cid] = ("yardstick", d)
    return by


def main(shard, part) -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import locate, names, osm
    from crashiq.sources import tiger_files

    import citywide as cw
    import corridors
    import coverage
    import osm_local

    tiger = tiger_files.TigerCache(ROOT / "data" / "cache" / "tiger", background=False)
    by = pools()
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    _, cname = coverage.districts()
    box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            box[code] = r
    outside = coverage.Outside(local, box)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    gate = locate.Gate()
    order = sorted(by, key=lambda c: -len(by[c]))
    out = open(DATA / f"run9c_truth_{part}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["collision_id", "city", "district", "pool", "cons", "osm_auto", "osm_right", "union_auto", "union_right",
                "union_tiger"])

    def judge(net, c, t):
        pl = locate.place(net, {**c, "lat": None, "lon": None}) if net is not None else None
        if pl is None:
            return 0, 0, "", None
        ok = pl.node is not None and osm.metres(net.coord[pl.node], t) <= TOL_M
        tg = "road" if pl.tiger_road else ("name" if pl.tiger else "")
        return int(gate.auto(pl)), int(ok), tg, pl
    for i, city in enumerate(order):
        if i % shard[1] != shard[0]:
            continue
        b = bounds.get(corridors.norm_city(city)) if city else None
        n_osm = n_uni = None
        if b:
            coverage.TIGER = None
            raw = osm_local.network_in_box(local, b["rel"])
            n_osm = osm.Network(raw)
            coverage.TIGER = tiger
            n_uni = osm.Network(coverage.with_tiger(raw))
        want, seen = by[city], set()
        batch = []
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in want and cid not in seen and c.get("lat") is not None:
                seen.add(cid)
                batch.append(aliases_mod.apply(dict(c)))
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
            cid, t = str(c["crash_id"]), (c["lat"], c["lon"])
            if not b:
                coverage.TIGER = None
                no = outside.network(c)
                coverage.TIGER = tiger
                nu = outside.network(c)
            else:
                no, nu = n_osm, n_uni
            oa, orr, _, _ = judge(no, c, t)
            ua, ur, tg, _ = judge(nu, c, t)
            cons = 0
            if nu is not None:
                kp, ks = names.street_key(c.get("primary_road")), names.street_key(c.get("secondary_road"))
                a = locate._same_core_keys(nu, kp) if kp else []
                bb = [s for s in (locate._same_core_keys(nu, ks) if ks else []) if s not in a]
                meet = locate._shared_nodes(nu, a, bb) if a and bb else []
                cons = int(any(osm.metres(nu.coord[n], t) <= CONS_M for n in meet))
            pool, d = want[cid]
            w.writerow([cid, city, d, pool, cons, oa, orr, ua, ur, tg])
        out.flush()
        print(f"[{i + 1}/{len(order)}] {city or '(blank)'}: {len(batch)}", flush=True)
    out.close()
    print("EXIT: finished", flush=True)


def merge(parts) -> None:
    from bin2_whatif import wilson_low
    rows = []
    for p in parts:
        with open(DATA / f"run9c_truth_{p}.csv") as f:
            rows += list(csv.DictReader(f))
    t = [r for r in rows if r["cons"] == "1"]

    def tally(sel):
        c = Counter()
        for r in sel:
            c["truth"] += 1
            if r["osm_auto"] == "1" and r["osm_right"] == "1":
                c["osm_right"] += 1
                if r["union_auto"] != "1":
                    c["lost"] += 1
                elif r["union_right"] != "1":
                    c["flipped"] += 1
            if r["union_auto"] == "1" and r["osm_auto"] != "1":
                c["gained"] += 1
                c["gained_right"] += r["union_right"] == "1"
            if r["union_auto"] == "1" and r["union_tiger"] == "name":
                c["tiger_name_auto"] += 1
                c["tiger_name_right"] += r["union_right"] == "1"
            if r["union_tiger"] == "road":
                c["tiger_road_held"] += 1
        return c
    st = tally(t)
    by_d = {d: dict(tally([r for r in t if r["district"] == d])) for d in sorted({r["district"] for r in t},
                                                                              key=lambda x: int(x) if x.isdigit() else 99)}
    res = {"truth_crashes": len(t), "by_pool": dict(Counter(r["pool"] for r in t)), "statewide": dict(st),
           "tiger_name_accuracy": {"k": st["tiger_name_right"], "n": st["tiger_name_auto"],
                                   "pct": round(100 * st["tiger_name_right"] / st["tiger_name_auto"], 1)
                                   if st["tiger_name_auto"] else None,
                                   "low": wilson_low(st["tiger_name_right"], st["tiger_name_auto"])
                                   if st["tiger_name_auto"] else None},
           "by_district": by_d}
    (DATA / "run9c_truth.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "by_district"}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--part")
    ap.add_argument("--merge", nargs="*")
    a = ap.parse_args()
    if a.merge:
        merge(a.merge)
    else:
        main(tuple(int(x) for x in a.shard.split("/")), a.part)
