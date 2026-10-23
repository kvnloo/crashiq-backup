"""Run 9: hidden-police-GPS accuracy of placements that rely on TIGER/Line (#229), split as the app splits them:
  tiger_name  a TIGER name on an OSM street (Placement.tiger and not tiger_road): auto-places under its tier
  tiger_road  a road only TIGER has (Placement.tiger_road): held for review unless tiger_only_auto
and, as the yardstick, OSM-only placements on the same truth.

Truth pool: crashes whose police GPS fits the report's roads only once TIGER's names are on the map (run 9B
coverage: gps_usable on the OSM + TIGER network; run 9A, OSM only: not), i.e. exactly the crashes where TIGER
matters; plus, for the yardstick, a seeded sample of crashes whose GPS fits on both. GPS hidden, placed with the app's
locator on the city's OSM + TIGER network (box + 1 km, as the coverage); kept as truth where the GPS is
self-consistent (within 400 ft of a meeting point of the two named streets on that network). Right = the chosen
intersection within 250 ft of the GPS. City maps only.

Run: python tests/statewide/run9_truth.py --shard 0/3 --part t0 ; then --merge t0 t1 t2
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
TOL_M, CONS_M, YARD_PER_CITY, SEED = 250 * 0.3048, 400 * 0.3048, 50, 9


def pools() -> dict[str, dict[str, str]]:
    def load(name):
        out = {}
        for p in sorted(DATA.glob(f"coverage_crashes_{name}_*.csv")):
            with open(p) as f:
                for r in csv.DictReader(f):
                    out[r["collision_id"]] = (r["outcome"], r["city"])
        return out
    a, b = load("r9a"), load("r9b")
    by = defaultdict(dict)
    rng = random.Random(SEED)
    both = defaultdict(list)
    for cid, (o, city) in b.items():
        if o == "gps_usable" and a.get(cid, ("", ""))[0] != "gps_usable":
            by[city][cid] = "needs_tiger"
        elif o == "gps_usable":
            both[city].append(cid)
    for city, ids in both.items():
        ids.sort(key=int)
        for cid in rng.sample(ids, min(YARD_PER_CITY, len(ids))):
            by[city][cid] = "yardstick"
    return by


def main(shard: tuple[int, int], part: str) -> None:
    from crashiq import locate, names, osm
    from crashiq.sources import tiger_files

    import citywide as cw
    import corridors
    import coverage
    import osm_local

    coverage.TIGER = tiger_files.TigerCache(ROOT / "data" / "cache" / "tiger", background=False)
    by = pools()
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    from crashiq import aliases as aliases_mod
    order = sorted((c for c in by if c and bounds.get(corridors.norm_city(c))), key=lambda c: -len(by[c]))
    out = open(DATA / f"run9_truth_{part}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["collision_id", "city", "pool", "tier", "auto", "tiger", "cons", "right"])
    gate = locate.Gate()
    for i, city in enumerate(order):
        if i % shard[1] != shard[0]:
            continue
        raw = coverage.with_tiger(osm_local.network_in_box(local, bounds[corridors.norm_city(city)]["rel"]))
        net = osm.Network(raw)
        want, seen = by[city], set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in want or cid in seen or c.get("lat") is None:
                continue
            seen.add(cid)
            c = aliases_mod.apply(dict(c))
            t = (c["lat"], c["lon"])
            pl = locate.place(net, {**c, "lat": None, "lon": None})
            kp, ks = names.street_key(c.get("primary_road")), names.street_key(c.get("secondary_road"))
            a = locate._same_core_keys(net, kp) if kp else []
            bb = [s for s in (locate._same_core_keys(net, ks) if ks else []) if s not in a]
            meet = locate._shared_nodes(net, a, bb) if a and bb else []
            cons = any(osm.metres(net.coord[n], t) <= CONS_M for n in meet)
            tg = "road" if pl.tiger_road else ("name" if pl.tiger else "")
            ok = pl.node is not None and osm.metres(net.coord[pl.node], t) <= TOL_M
            auto_if = pl.lat is not None and pl.tier in gate.auto_tiers      # auto, or would be with tiger_only_auto
            w.writerow([cid, city, want[cid], pl.tier, int(auto_if), tg, int(cons), int(ok)])
        out.flush()
        print(f"[{i + 1}/{len(order)}] {city}: {len(seen)}", flush=True)
    out.close()
    print("EXIT: finished", flush=True)


def merge(parts: list[str]) -> None:
    from bin2_whatif import wilson_low
    rows = []
    for p in parts:
        with open(DATA / f"run9_truth_{p}.csv") as f:
            rows += list(csv.DictReader(f))
    res = {}
    for label, sel in (("tiger_name (auto under its tier)", lambda r: r["tiger"] == "name"),
                       ("tiger_road (held; if it were auto)", lambda r: r["tiger"] == "road"),
                       ("OSM only (yardstick)", lambda r: r["tiger"] == "")):
        s = [r for r in rows if r["cons"] == "1" and r["auto"] == "1" and sel(r)]
        k, n = sum(r["right"] == "1" for r in s), len(s)
        res[label] = {"k": k, "n": n, "pct": round(100 * k / n, 1) if n else None, "low": wilson_low(k, n),
                      "by_pool": dict(Counter(r["pool"] for r in s))}
    res["truth_crashes"] = {f"{p} / self-consistent {c}": n for (p, c), n in Counter((r["pool"], r["cons"]) for r in rows).items()}
    (DATA / "run9_truth.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


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
