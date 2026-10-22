"""#206 per-city delta: which exact placements of the #199 coverage run (app code 5f54c02) differ at a later commit.

#204 (unique-pair tier, gate off) and #206 (a stated trailing direction must match, every tier) can only change the
locator's answer for a crash whose primary or secondary road writes a trailing direction (20TH ST W). So the
candidates are the #199 crashes the locator ran on (not placed by police GPS) with a trailing direction on either road,
and each is placed twice, once per backend, in separate processes:

  python tests/statewide/delta206.py --backend <main checkout>/backend --tag main     (also writes the candidate list)
  python tests/statewide/delta206.py --backend backend --tag base --ids data/statewide/delta206_main.csv
  python tests/statewide/delta206.py --compare base main

Truth check (#205 closing, PM 2026-10-22): the changed crashes themselves have no usable police GPS (the locator only
runs where GPS is missing or off the report's roads), so the hidden-GPS test (#88) runs on the same kind of crash
where truth is usable: trailing-direction reports whose police GPS fits the named roads (#199 outcome gps_usable).
GPS hidden, placed on both codes, right intersection = chosen intersection within 250 ft of the police GPS:

  python tests/statewide/delta206.py --truth --backend <main checkout>/backend --tag tmain
  python tests/statewide/delta206.py --truth --backend backend --tag tbase --ids data/statewide/delta206_tmain.csv
  python tests/statewide/delta206.py --truth-compare tbase tmain

Writes data/statewide/delta206_<tag>.csv (collision_id, city, tier, auto, node[, truth and node coordinates]) and
delta206.json / delta206_truth.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
PARTS = ["part0", "s0b", "s1", "s2", "s3", "sd0", "sd1", "sd2", "blank"]
LOCATOR_RAN = {"placed_exact", "placed_fars", "review", "cant_place"}


TOL_M = 250 * 0.3048


def _ran(outcomes: set[str] = LOCATOR_RAN) -> dict[str, str]:
    """collision_id -> city name, for every #199 crash with one of these outcomes."""
    out = {}
    for p in PARTS:
        with open(DATA / f"coverage_crashes_{p}.csv") as f:
            for r in csv.DictReader(f):
                if r["outcome"] in outcomes:
                    out[r["collision_id"]] = r["city"]
    return out


def place(backend: Path, tag: str, ids_file: Path | None, truth: bool = False) -> None:
    sys.path.insert(0, str(backend.resolve()))
    from crashiq import locate, names, osm  # noqa: F401  (cached before coverage.py adds the worktree's backend)
    assert Path(locate.__file__).resolve().is_relative_to(backend.resolve()), locate.__file__
    sys.path.insert(1, str(HERE))
    import citywide as cw
    import corridors
    import osm_local
    import sqlite3
    from coverage import Outside, districts
    if ids_file:
        with open(ids_file) as f:
            want = {r["collision_id"]: r["city"] for r in csv.DictReader(f)}
    else:
        want = None
        ran = _ran({"gps_usable"} if truth else LOCATOR_RAN)
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
    trail = lambda road: names.directions(road)[1] if hasattr(names, "directions") else None  # noqa: E731
    by_city = defaultdict(list)
    if want is not None:
        for cid, city in want.items():
            by_city[city].append(cid)
    else:
        for cid, city in ran.items():
            by_city[city].append(cid)
    out = open(DATA / f"delta206_{tag}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["collision_id", "city", "tier", "auto", "node"]
               + (["truth_lat", "truth_lon", "node_lat", "node_lon"] if truth else []))
    n_done = 0
    for city_name, cids in sorted(by_city.items(), key=lambda kv: -len(kv[1])):
        cids = set(cids)
        rows = [c for c in cw.mirror_rows(con, "City Name", city_name) if str(c["crash_id"]) in cids]
        if want is None:
            rows = [c for c in rows if trail(c.get("primary_road")) or trail(c.get("secondary_road"))]
        if not rows:
            continue
        b = bounds.get(corridors.norm_city(city_name)) if city_name else None
        cw._fuzzy_memo.clear()
        net = osm.Network(osm_local.network_in_area(local, b["rel"])) if b else None
        for c in rows:
            t = (c.get("lat"), c.get("lon"))
            if truth:
                c = {**c, "lat": None, "lon": None}            # hidden from the locator (#88)
            n_ = net if net is not None else outside.network(c)
            pl = locate.place(n_, c) if n_ is not None else locate.Placement("review", note="no street map")
            xy = n_.coord[pl.node] if (truth and pl.node is not None) else ("", "")
            w.writerow([c["crash_id"], city_name, pl.tier, int(gate.auto(pl)), pl.node or ""]
                       + ([t[0], t[1], xy[0], xy[1]] if truth else []))
        n_done += len(rows)
        out.flush()
        print(f"{city_name or '(blank)'}: {len(rows)} candidates ({n_done} so far)", flush=True)
    out.close()
    print("EXIT: finished", flush=True)


def compare(a: str, b: str) -> None:
    def load(t):
        with open(DATA / f"delta206_{t}.csv") as f:
            return {r["collision_id"]: r for r in csv.DictReader(f)}
    base, new = load(a), load(b)
    assert set(base) == set(new), "candidate lists differ"
    per = defaultdict(Counter)
    for cid, r0 in base.items():
        r1 = new[cid]
        c = per[r0["city"] or "(blank)"]
        c["candidates"] += 1
        e0, e1 = r0["auto"] == "1", r1["auto"] == "1"
        c["exact_before"] += e0
        c["exact_after"] += e1
        if e0 and not e1:
            c["lost"] += 1
        elif e1 and not e0:
            c["gained"] += 1
        elif e0 and e1 and r0["node"] != r1["node"]:
            c["moved"] += 1
        if r1["tier"] == "unique_pair":
            c["unique_pair_held"] += 1
    rows = [{"city": k, **{f: v.get(f, 0) for f in ("candidates", "exact_before", "exact_after", "lost", "gained",
                                                    "moved", "unique_pair_held")}} for k, v in per.items()]
    rows.sort(key=lambda r: -(r["lost"] + r["gained"] + r["moved"]))
    tot = {f: sum(r[f] for r in rows) for f in rows[0] if f != "city"}
    (DATA / "delta206.json").write_text(json.dumps({"base": a, "new": b, "total": tot, "cities": rows}, indent=1))
    print(json.dumps(tot))
    for r in rows:
        if r["lost"] + r["gained"] + r["moved"]:
            print(r)


def consistent(backend: Path, tag: str) -> None:
    """Which hidden-GPS crashes have truth that agrees with the report as written, trailing direction included (the
    #88 self-consistency rule plus direction): the police GPS lies within 400 ft of a node shared by a way named like
    the primary road and a way named like the secondary road, each carrying the stated trailing direction or none.
    The coverage GPS check ignores trailing directions (the street key drops them), so without this a report saying
    185TH STREET EAST with its GPS at 185th Street West would count as truth for the wrong street."""
    sys.path.insert(0, str(backend.resolve()))
    from crashiq import names, osm
    sys.path.insert(1, str(HERE))
    import citywide as cw
    import sqlite3
    with open(DATA / f"delta206_{tag}.csv") as f:
        rows = list(csv.DictReader(f))
    by_city = defaultdict(set)
    for r in rows:
        by_city[r["city"]].add(r["collision_id"])
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    odb = sqlite3.connect(ROOT / "data" / "osm" / "ca_osm.sqlite")
    rad, d = 400 * 0.3048, 0.002

    def ok(c) -> bool:
        kp, ks = names.street_key(c.get("primary_road")), names.street_key(c.get("secondary_road"))
        if not kp or not ks:
            return False
        tp, ts = names.directions(c.get("primary_road"))[1], names.directions(c.get("secondary_road"))[1]
        t = (c["lat"], c["lon"])
        near_p, near_s = set(), set()
        for tags, nids, coords in odb.execute(
                "SELECT w.tags, w.nodes, w.coords FROM way_box b JOIN ways w ON w.id = b.id WHERE b.minlat <= ? AND "
                "b.maxlat >= ? AND b.minlon <= ? AND b.maxlon >= ?", (t[0] + d, t[0] - d, t[1] + d, t[1] - d)):
            tg = json.loads(tags)
            vals = [v for k in osm.NAME_TAGS for v in str(tg.get(k, "")).split(";") if v.strip()]
            close = {n for n, (la, lo) in zip(json.loads(nids), json.loads(coords)) if osm.metres((la, lo), t) <= rad}
            if not close:
                continue
            for v in vals:
                k, tr = names.street_key(v), names.directions(v)[1]
                if k and names.same_core(kp, k) and (tp is None or tr in (tp, None)):
                    near_p |= close
                if k and names.same_core(ks, k) and (ts is None or tr in (ts, None)):
                    near_s |= close
        return bool(near_p & near_s)
    out = open(DATA / "delta206_consistent.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["collision_id", "consistent"])
    n = 0
    for city, ids in by_city.items():
        for c in cw.mirror_rows(con, "City Name", city):
            if str(c["crash_id"]) in ids and c.get("lat") is not None:
                w.writerow([c["crash_id"], int(ok(c))])
                n += 1
        out.flush()
    out.close()
    print(f"{n} crashes checked\nEXIT: finished", flush=True)


def truth_compare(a: str, b: str) -> None:
    """Right intersection before vs after, on every crash either code auto-places, and on those whose answer changed."""
    import math

    def load(t):
        with open(DATA / f"delta206_{t}.csv") as f:
            return {r["collision_id"]: r for r in csv.DictReader(f)}

    def ok(r):
        if r["auto"] != "1" or not r["node_lat"]:
            return False
        la, lo, tl, tn = (float(r[k]) for k in ("node_lat", "node_lon", "truth_lat", "truth_lon"))
        return math.hypot((la - tl) * 111320, (lo - tn) * 111320 * math.cos(math.radians(tl))) <= TOL_M
    base, new = load(a), load(b)
    assert set(base) == set(new), "candidate lists differ"
    cons = DATA / "delta206_consistent.csv"
    if cons.exists():                       # self-consistent truth only (see consistent())
        with open(cons) as f:
            keep = {r["collision_id"] for r in csv.DictReader(f) if r["consistent"] == "1"}
        base = {k: v for k, v in base.items() if k in keep}
    tot, chg = Counter(), Counter()
    per = defaultdict(Counter)
    for cid, r0 in base.items():
        r1 = new[cid]
        e0, e1 = r0["auto"] == "1", r1["auto"] == "1"
        o0, o1 = ok(r0), ok(r1)
        tot.update({"crashes": 1, "exact_before": e0, "exact_after": e1, "right_before": o0, "right_after": o1})
        kind = ("lost" if e0 and not e1 else "gained" if e1 and not e0 else
                "moved" if e0 and e1 and r0["node"] != r1["node"] else None)
        if kind:
            chg.update({kind: 1, f"{kind}_right_before": o0, f"{kind}_right_after": o1})
            per[r0["city"] or "(blank)"].update({kind: 1, "right_before": o0, "right_after": o1})
    out = {"base": a, "new": b, "truth": "police GPS that fits the report's roads (#199 gps_usable), hidden"
           + ("; self-consistent with the report's streets as written, trailing direction included" if cons.exists()
              else "") + "; right intersection = within 250 ft", "total": dict(tot), "changed": dict(chg),
           "cities": [{"city": k, **v} for k, v in sorted(per.items(), key=lambda kv: -sum(kv[1].values()))]}
    (DATA / "delta206_truth.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"total": out["total"], "changed": out["changed"]}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", type=Path)
    ap.add_argument("--tag")
    ap.add_argument("--ids", type=Path)
    ap.add_argument("--compare", nargs=2)
    ap.add_argument("--truth", action="store_true")
    ap.add_argument("--truth-compare", nargs=2)
    ap.add_argument("--consistent")
    a = ap.parse_args()
    if a.compare:
        compare(*a.compare)
    elif a.consistent:
        consistent(a.backend, a.consistent)
    elif a.truth_compare:
        truth_compare(*a.truth_compare)
    else:
        place(a.backend, a.tag, a.ids, a.truth)
