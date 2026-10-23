"""The report wins over GPS (PM 2026-10-23; measure only). For every D1 (freeway / ramp) difficult crash of run 9A,
compute the point the REPORT describes, the user's method in #246, then ask:
  - accept: does the police GPS (where there is any) lie within ACCEPT_FT of that point?
  - control: the same, with the GPS moved CONTROL_M in a seeded random direction (a match there is chance)
  - #246: a crash whose report point can be computed is one #246's report-only placement would place, so every
    accepted GPS is already placed by #246: the GPS check confirms, it doesn't add crashes.

The report's point, on the OSM extract (roads by `ref` route number; cross streets by name in the crash's county):
  mainline  a route + a local cross street: where the cross street crosses the route (closest approach within
            CROSS_FT; one crossing only, else ambiguous), then the stated distance along the route in the stated
            compass direction
  ramp      a ramp word: the ramp terminal where a ramp joined to the route (motorway_link, up to MAX_HOPS links) ends
            at the cross street (terminals within TERMINAL_SPREAD_FT of each other: their middle; else ambiguous); a
            stated distance over ACCEPT_FT is applied along the compass direction
  f2f       two routes: from the crossing of the two routes, the stated distance along the primary route; for
            "X TO Y" also the gore option (#246 C): where the X-to-Y connector leaves X
Nothing here is a placement rule. Results show what #246 could place and how often police GPS agrees with it.

Run: python tests/statewide/freeway_report_point.py   (writes data/statewide/freeway_report_point.csv / .json)
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
ACCEPT_FT, CROSS_FT, TERMINAL_SPREAD_FT, MAX_HOPS, CONTROL_M, SEED, DISTINCT_FT = 400.0, 300.0, 800.0, 3, 2000.0, 7, 3300.0
RAMP = re.compile(r"\b(RAMP|ONRAMP|OFFRAMP)\b")
DIRS = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}
FT_DEG = 364000.0


def ft(a, b) -> float:
    return math.hypot((a[0] - b[0]) * FT_DEG, (a[1] - b[1]) * FT_DEG * math.cos(math.radians(a[0])))


def bearing(a, b) -> float:
    return math.degrees(math.atan2((b[1] - a[1]) * math.cos(math.radians(a[0])), b[0] - a[0])) % 360


def move(p, brg, d_ft):
    d = d_ft / FT_DEG
    return (p[0] + d * math.cos(math.radians(brg)), p[1] + d * math.sin(math.radians(brg)) / math.cos(math.radians(p[0])))


def turn(a, b) -> float:
    return abs((a - b + 180) % 360 - 180)


class Map:
    def __init__(self):
        from crashiq import names
        self.names = names
        self.db = sqlite3.connect(ROOT / "data" / "osm" / "ca_osm.sqlite")
        with open(ROOT / "data" / "reference" / "caltrans_districts.csv") as f:
            cn = {int(r["ccrs_county_code"]): r["county"] for r in csv.DictReader(f)}
        self.box = {}
        for code, name in cn.items():
            r = self.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                                (f"{name} County",)).fetchone()
            if r:
                self.box[code] = r

    @lru_cache(maxsize=2)                               # crashes come county by county
    def county_ways(self, county: int) -> tuple:
        """(route ways, link ways, named ways) in the county's box: (id, highway, refs, name core, nodes, coords)."""
        b = self.box.get(county)
        if not b:
            return (), (), {}
        route, link, named = [], [], defaultdict(list)
        for wid, hw, name, tags, nids, coords in self.db.execute(
                "SELECT w.id, w.highway, w.name, w.tags, w.nodes, w.coords FROM way_box x JOIN ways w ON w.id = x.id "
                "WHERE x.maxlat >= ? AND x.minlat <= ? AND x.maxlon >= ? AND x.minlon <= ?", (b[0], b[2], b[1], b[3])):
            t = json.loads(tags)
            refs = frozenset(re.findall(r"\d+", str(t.get("ref") or "")))
            row = (wid, hw, refs, None, tuple(json.loads(nids)), tuple(map(tuple, json.loads(coords))))
            if hw in ("motorway", "trunk") and refs:
                route.append(row)
            elif hw in ("motorway_link", "trunk_link"):
                link.append(row)
            if name:
                k = self.names.street_key(name)
                if k:
                    core = self.names.drop_directional(k).core.replace(" ", "")
                    named[core].append((wid, hw, refs, core, row[4], row[5]))
        return tuple(route), tuple(link), dict(named)

    @lru_cache(maxsize=512)
    def route(self, county, nums):
        return [w for w in self.county_ways(county)[0] if w[2] & nums]

    def street(self, county, raw):
        k = self.names.street_key(raw)
        if not k:
            return []
        core = self.names.drop_directional(k).core.replace(" ", "")
        return [w for w in self.county_ways(county)[2].get(core, ()) if w[1] not in ("motorway", "motorway_link")]

    @lru_cache(maxsize=512)
    def links_of(self, county, nums):
        ways = self.route(county, nums)
        nodes = {n for w in ways for n in w[4]}
        links = self.county_ways(county)[1]
        good, frontier = [], [w for w in links if set(w[4]) & nodes]
        seen = {w[0] for w in frontier}
        for _ in range(MAX_HOPS):
            good += frontier
            nn = {n for w in frontier for n in w[4]}
            frontier = [w for w in links if w[0] not in seen and set(w[4]) & nn]
            seen |= {w[0] for w in frontier}
        return good


def closest(a_ways, b_ways, limit_ft):
    """Clusters of closest-approach points between two sets of ways (points within limit_ft)."""
    pts = []
    bpts = [p for w in b_ways for p in w[5]]
    grid = defaultdict(list)
    for p in bpts:
        grid[(round(p[0] / 0.002), round(p[1] / 0.002))].append(p)
    for w in a_ways:
        for p in w[5]:
            g = (round(p[0] / 0.002), round(p[1] / 0.002))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for q in grid.get((g[0] + dy, g[1] + dx), ()):
                        d = ft(p, q)
                        if d <= limit_ft:
                            pts.append((d, p))
    clusters = []
    for d, p in sorted(pts):
        for c in clusters:
            if ft(c[1], p) <= DISTINCT_FT:
                break
        else:
            clusters.append((d, p))
    return clusters


def walk(ways, start, compass: float, dist_ft: float):
    """From `start` (a point on one of `ways`), go dist_ft along the ways, first heading within 90 deg of compass,
    then always the continuation that turns least."""
    adj = defaultdict(list)                       # point -> neighbouring points along the ways
    for w in ways:
        for a, b in zip(w[5], w[5][1:]):
            adj[a].append(b)
            adj[b].append(a)
    if start not in adj:
        return None
    opts = [q for q in adj[start] if turn(bearing(start, q), compass) <= 90]
    if not opts:
        return None
    prev, cur = start, min(opts, key=lambda q: turn(bearing(start, q), compass))
    left = dist_ft
    for _ in range(5000):
        seg = ft(prev, cur)
        if seg >= left:
            return move(prev, bearing(prev, cur), left)
        left -= seg
        nxt = [q for q in adj[cur] if q != prev]
        if not nxt:
            return cur
        h = bearing(prev, cur)
        prev, cur = cur, min(nxt, key=lambda q: turn(bearing(cur, q), h))
    return cur


def report_point(m: Map, c: dict, kind: str) -> dict:
    names = m.names
    county = int(c.get("county_code") or 0)
    p, s = (c.get("primary_road") or "").upper(), (c.get("secondary_road") or "").upper()
    rp, rs = set(names.ROUTE_ANY.findall(p)), set(names.ROUTE_ANY.findall(s))
    off = c.get("offset_ft") or 0.0
    d = str(c.get("offset_dir") or "").strip()[:1].upper()
    out = {}
    if kind == "ramp":
        nums = rp | rs
        cross_raw = s if rp else p
        if not nums:
            return {"why": "no route number"}
        rw = m.route(county, frozenset(nums))
        st = m.street(county, cross_raw)
        if not rw or not st:
            return {"why": "route or cross street not on the map"}
        terms = [e for w in m.links_of(county, frozenset(nums)) for e in (w[5][0], w[5][-1])
                 if any(ft(e, q) <= 150 for x in st for q in x[5])]
        if not terms:
            return {"why": "no ramp terminal at the cross street"}
        if max(ft(a, b) for a in terms for b in terms) > TERMINAL_SPREAD_FT:
            return {"why": "ramp terminals too far apart (ambiguous)"}
        t = (sum(e[0] for e in terms) / len(terms), sum(e[1] for e in terms) / len(terms))
        out["point"] = move(t, DIRS[d], off) if off > ACCEPT_FT and d in DIRS else t
        return out
    if kind == "f2f":
        if not rp or not rs:
            return {"why": "two route numbers not found"}
        a, b = m.route(county, frozenset(rp)), m.route(county, frozenset(rs))
        if not a or not b:
            return {"why": "a route not on the map"}
        cl = closest(a, b, CROSS_FT)
        if len(cl) == 1 and d in DIRS:
            out["point"] = walk(a, cl[0][1], DIRS[d], off) if off else cl[0][1]
        elif len(cl) != 1:
            out["why"] = "routes cross more than once or not at all"
        if " TO " in f" {p} ":                         # gore option: where the X-to-Y connector leaves X
            ln = m.links_of(county, frozenset(rp))
            bn = {n for w in b for n in w[4]}
            an = {n for w in a for n in w[4]}
            gore = [w for w in ln if set(w[4]) & an and any(set(x[4]) & bn for x in ln if set(x[4]) & set(w[4]))
                    or (set(w[4]) & an and set(w[4]) & bn)]
            gp = [next(q for n, q in zip(w[4], w[5]) if n in an) for w in gore]
            if gp and max(ft(x, y) for x in gp for y in gp) <= TERMINAL_SPREAD_FT and d in DIRS:
                g0 = (sum(x[0] for x in gp) / len(gp), sum(x[1] for x in gp) / len(gp))
                snap = min((q for w in a for q in w[5]), key=lambda q: ft(q, g0))
                out["gore_point"] = walk(a, snap, DIRS[d], off) if off else snap
        return out
    nums = rp or rs                                     # mainline
    cross_raw = s if rp else p
    rw = m.route(county, frozenset(nums))
    st = m.street(county, cross_raw)
    if not rw or not st:
        return {"why": "route or cross street not on the map"}
    cl = closest(rw, st, CROSS_FT)
    if len(cl) != 1:
        return {"why": "cross street meets the route more than once or not at all"}
    if d not in DIRS:
        return {"why": "no compass direction"}
    out["point"] = walk(rw, cl[0][1], DIRS[d], off) if off else cl[0][1]
    return out


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import names

    import citywide as cw
    with open(DATA / "buckets.csv") as f:
        want = {r["collision_id"]: r for r in csv.DictReader(f) if r["bucket"] == "D1"}
    with open(DATA / "freeway_gps.csv") as f:
        kinds = {r["collision_id"]: r["kind"] for r in csv.DictReader(f)}
    by_city = defaultdict(set)
    county_of = {}
    for cid, r in want.items():
        by_city[r["city"]].add(cid)
        county_of.setdefault(r["city"], int(r["county_code"] or 0))
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    m, rng, rows = Map(), random.Random(SEED), []
    for city, ids in sorted(by_city.items(), key=lambda kv: (county_of[kv[0]], kv[0])):
        seen, batch = set(), []
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in ids or cid in seen:
                continue
            seen.add(cid)
            batch.append(aliases_mod.apply(dict(c)))
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):     # one county's roads at a time
            cid = str(c["crash_id"])
            p_, s_ = (c.get("primary_road") or "").upper(), (c.get("secondary_road") or "").upper()
            kind = kinds.get(cid)
            if kind is None:                            # D1 without GPS: classify as freeway_gps.py does
                rp, rs = names.ROUTE_ANY.findall(p_), names.ROUTE_ANY.findall(s_)
                kind = ("ramp" if RAMP.search(f"{p_} {s_}") or "CONNECTOR" in f"{p_} {s_}" else
                        "f2f" if rp and rs else "mainline" if rp or rs else "other")
            rp_ = report_point(m, c, kind) if kind != "other" else {"why": "no route number"}
            g = (c["lat"], c["lon"]) if c.get("lat") is not None else None
            row = {"collision_id": cid, "city": city, "kind": kind, "gps_off": want[cid]["gps_off"],
                   "computable": int("point" in rp_), "gore_computable": int("gore_point" in rp_),
                   "why": rp_.get("why", ""), "has_gps": int(g is not None)}
            for key, col in (("point", ""), ("gore_point", "gore_")):
                pt = rp_.get(key)
                if pt and g:
                    bb = rng.uniform(0, 2 * math.pi)
                    q = (g[0] + CONTROL_M / 111_000 * math.cos(bb),
                         g[1] + CONTROL_M / 111_000 * math.sin(bb) / math.cos(math.radians(g[0])))
                    row[f"{col}gps_ft"] = round(ft(g, pt))
                    row[f"{col}accept"] = int(ft(g, pt) <= ACCEPT_FT)
                    row[f"{col}control_accept"] = int(ft(q, pt) <= ACCEPT_FT)
            rows.append(row)
        print(f"{city or '(blank)'}: {len(seen)}", flush=True)
    cols = ["collision_id", "city", "kind", "gps_off", "computable", "gore_computable", "why", "has_gps", "gps_ft",
            "accept", "control_accept", "gore_gps_ft", "gore_accept", "gore_control_accept"]
    with open(DATA / "freeway_report_point.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    res = {"d1": len(want), "checked": len(rows), "by_kind": {}}
    for k in ("mainline", "ramp", "f2f", "other"):
        s = [r for r in rows if r["kind"] == k]
        rej = [r for r in s if r["gps_off"] == "1" and r.get("accept") is not None]
        gr = [r for r in s if r["gps_off"] == "1" and r.get("gore_accept") is not None]
        res["by_kind"][k] = {
            "crashes": len(s), "report_point_computable (#246 would place)": sum(r["computable"] for r in s),
            "gore_computable": sum(r["gore_computable"] for r in s),
            "rejected_gps_with_report_point": len(rej), "gps_accepted_within_400ft": sum(r["accept"] for r in rej),
            "control_accepted": sum(r["control_accept"] for r in rej),
            "gore: rejected_gps_with_point": len(gr), "gore: accepted": sum(r["gore_accept"] for r in gr),
            "gore: control": sum(r["gore_control_accept"] for r in gr),
            "not computable, why": dict(Counter(r["why"] for r in s if not r["computable"]).most_common(5))}
    (DATA / "freeway_report_point.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
