"""Step 2 (#211): the difficult bin. Re-runs the app's locator (current main, passed as --backend) per crash and records
what each candidate fix would need, so gains (on the difficult crashes) and accuracy (on hidden police GPS) come from
the same code and the same fields:

  gain  - every #199 bin-2 crash (coverage_crashes.csv), police GPS as recorded (it was off the roads or missing)
  truth - per city, a seeded sample of #199 crashes placed by police GPS that fits the report's roads (gps_usable),
          GPS hidden from the locator (#88); `cons` = the GPS is self-consistent with the report as written, trailing
          direction included (within 400 ft of a meeting point of the two named streets)

Per crash: the locator's answer (tier, auto under the Gate, note, node, point); for streets that meet in more than one
place, the candidate intersections (exact/relaxed tier, up to 10) with whether the primary road leaves each in the
stated offset direction; the distance from the police GPS to each named road and to the nearest meeting point.

Run (shards over cities, like coverage.py):
  python tests/statewide/bin2.py --backend <main checkout>/backend --shard 0/3 --part p0 [--exclude "San Diego"]
  python tests/statewide/bin2.py --backend <main checkout>/backend --only-city "San Diego" --split 0/2 --part sd0
(both sets in one pass, so each city's street network is built once)
Writes data/statewide/bin2_<part>.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
TRUTH_PER_CITY, SEED = 200, 211
CONS_M, CLUSTER_GAP_M = 400 * 0.3048, 60.0
DIRS = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315,
        "NORTH": 0, "EAST": 90, "SOUTH": 180, "WEST": 270}
COLS = ["collision_id", "set", "city", "county_code", "agency", "road_type", "killed", "ksi", "outcome_199",
        "reason_199", "tier", "auto", "note", "node", "node_lat", "node_lon", "lat", "lon", "gps_lat", "gps_lon", "cons", "offset_ft",
        "offset_dir", "n_clusters", "clusters", "gps_d_primary_m", "gps_d_secondary_m", "gps_d_meet_m"]


KEEP = ("collision_id", "city", "county_code", "agency", "road_type", "killed", "ksi", "outcome", "reason")


def _crashes() -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """city -> #199 rows: every bin-2 crash (gain), and a seeded sample of gps_usable crashes per city (truth).
    Two passes, so the 1.46 million gps_usable rows are never held in memory."""
    gain, ids = defaultdict(list), defaultdict(list)
    with open(DATA / "coverage_crashes.csv") as f:
        for r in csv.DictReader(f):
            if r["bin"] == "2":
                gain[r["city"]].append({k: r[k] for k in KEEP})
            elif r["outcome"] == "gps_usable":
                ids[r["city"]].append(int(r["collision_id"]))
    rng, pick = random.Random(SEED), set()
    for city in sorted(ids):
        lst = sorted(ids[city])
        rng.shuffle(lst)
        pick.update(str(x) for x in lst[:TRUTH_PER_CITY])
    del ids
    truth = defaultdict(list)
    with open(DATA / "coverage_crashes.csv") as f:
        for r in csv.DictReader(f):
            if r["outcome"] == "gps_usable" and r["collision_id"] in pick:
                truth[r["city"]].append({k: r[k] for k in KEEP})
    return gain, truth


def main(backend: Path, which: str, shard: tuple[int, int], part: str, only_city: str | None,
         exclude: set[str], split: tuple[int, int]) -> None:
    sys.path.insert(0, str(backend.resolve()))
    from crashiq import locate, names, osm
    assert Path(locate.__file__).resolve().is_relative_to(backend.resolve()), locate.__file__
    sys.path.insert(1, str(HERE))
    import sqlite3

    import citywide as cw
    import corridors
    import osm_local
    from coverage import Outside, districts

    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    _, cname = districts()
    county_box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            county_box[code] = r
    outside = Outside(local, county_box)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    gate = locate.Gate()
    sets = ("gain", "truth") if which == "both" else (which,)
    by_set = dict(zip(("gain", "truth"), _crashes()))
    sizes = defaultdict(int)
    for st in sets:
        for c, rows in by_set[st].items():
            sizes[c] += len(rows)
    order = sorted(sizes, key=lambda c: -sizes[c])

    def keys(net, k):
        """The relaxed tier's streets for a name (same core, suffix kept when it can be)."""
        if not k:
            return []
        ks = locate._same_core_keys(net, k)
        keep = [s for s in ks if k.suffix is None or s.suffix is None or s.suffix == k.suffix]
        return keep or ks

    def clusters(net, nodes):
        out = []
        for n in nodes:
            p = net.coord[n]
            for c in out:
                if osm.metres(net.coord[c[0]], p) <= CLUSTER_GAP_M:
                    c.append(n)
                    break
            else:
                out.append([n])
        return out

    def leaves(net, cl, a, deg):
        """Does the primary road leave this intersection within 45 degrees of the stated offset direction?"""
        for n in cl:
            for k in a:
                for m in net.neighbors.get((n, k), ()):
                    b = osm.bearing(net.coord[n], net.coord[m])
                    if abs((b - deg + 180) % 360 - 180) <= 45:
                        return True
        return False

    def nearest(net, ks, p):
        best = None
        for k in ks:
            for n in net.all_nodes_of.get(k, ()):
                d = osm.metres(net.coord[n], p)
                best = d if best is None or d < best else best
        return best

    out = open(DATA / f"bin2_{part}.csv", "w", newline="")
    w = csv.DictWriter(out, COLS)
    w.writeheader()
    t0, done = time.time(), 0
    for i, city in enumerate(order):
        if only_city is not None:
            if city != only_city:
                continue
        elif i % shard[1] != shard[0] or city in exclude:
            continue
        want = {r["collision_id"]: (st, r) for st in sets for r in by_set[st].get(city, ())}
        rows = [c for c in cw.mirror_rows(con, "City Name", city) if str(c["crash_id"]) in want]
        seen = set()
        b = bounds.get(corridors.norm_city(city)) if city else None
        cw._fuzzy_memo.clear()
        net = osm.Network(osm_local.network_in_area(local, b["rel"])) if b else None
        for c in rows:
            cid = str(c["crash_id"])
            if cid in seen or (split[1] > 1 and int(cid) % split[1] != split[0]):
                continue
            seen.add(cid)
            st, r199 = want[cid]
            gps = (c.get("lat"), c.get("lon"))
            q = {**c, "lat": None, "lon": None} if st == "truth" else c
            n_ = net if net is not None else outside.network(q)
            rec = {"collision_id": cid, "set": st, "city": city, "county_code": r199["county_code"],
                   "agency": r199["agency"], "road_type": r199["road_type"], "killed": r199["killed"],
                   "ksi": r199["ksi"], "outcome_199": r199["outcome"], "reason_199": r199["reason"],
                   "gps_lat": gps[0], "gps_lon": gps[1], "offset_ft": c.get("offset_ft"), "offset_dir": c.get("offset_dir")}
            if n_ is None:
                rec.update(tier="review", auto=0, note="no street map")
                w.writerow(rec)
                continue
            pl = locate.place(n_, q)
            nxy = n_.coord[pl.node] if pl.node is not None else ("", "")
            rec.update(tier=pl.tier, auto=int(gate.auto(pl)), note=pl.note or "", node=pl.node or "", node_lat=nxy[0],
                       node_lon=nxy[1], lat=pl.lat or "", lon=pl.lon or "")
            kp, ks = names.street_key(c.get("primary_road")), names.street_key(c.get("secondary_road"))
            a, bb = keys(n_, kp), keys(n_, ks)
            bb = [s for s in bb if s not in a]
            tp, ts = names.directions(c.get("primary_road"))[1], names.directions(c.get("secondary_road"))[1]
            meet = [n for n in locate._shared_nodes(n_, a, bb)
                    if locate._trail_fits(n_, n, a, tp) and locate._trail_fits(n_, n, bb, ts)] if a and bb else []
            cls = clusters(n_, meet)
            rec["n_clusters"] = len(cls)
            if len(cls) > 1:
                deg = DIRS.get(str(c.get("offset_dir") or "").upper())
                rec["clusters"] = json.dumps([[round(n_.coord[cl[0]][0], 6), round(n_.coord[cl[0]][1], 6),
                                               None if deg is None else int(leaves(n_, cl, a, deg))] for cl in cls[:10]])
            if gps[0] is not None and gps[1] is not None:
                rec["gps_d_primary_m"] = round(nearest(n_, a, gps), 1) if a and nearest(n_, a, gps) is not None else ""
                rec["gps_d_secondary_m"] = round(nearest(n_, bb, gps), 1) if bb and nearest(n_, bb, gps) is not None else ""
                dm = min((osm.metres(n_.coord[n], gps) for n in meet), default=None)
                rec["gps_d_meet_m"] = round(dm, 1) if dm is not None else ""
                if st == "truth":
                    rec["cons"] = int(dm is not None and dm <= CONS_M)
            w.writerow(rec)
            done += 1
        out.flush()
        print(f"[{i + 1}/{len(order)} {time.time() - t0:.0f}s] {city or '(blank)'}: {len(seen)} crashes ({done} so far)",
              flush=True)
    out.close()
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", type=Path, required=True)
    ap.add_argument("--set", choices=["gain", "truth", "both"], default="both")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--part", required=True)
    ap.add_argument("--only-city")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--split", default="0/1")
    a = ap.parse_args()
    main(a.backend, a.set, tuple(int(x) for x in a.shard.split("/")), a.part, a.only_city,
         {x for x in a.exclude.split(",") if x}, tuple(int(x) for x in a.split.split("/")))
