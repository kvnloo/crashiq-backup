"""Freeway GPS rejected by the street check? (PM 2026-10-23; measure only.) The user confirmed that the police GPS of
Martinez crash 1428399 (I-680 S/B TO SR-4, 37.9971, -122.0734) is right, on the connector ramp, yet the crash is
difficult: OSM ramps and connectors (motorway_link) carry no name, or only a ref, so "a named road within 400 ft"
fails.

For every D1 (freeway / ramp) difficult crash of run 9A whose police GPS was rejected (buckets.csv gps_off): does the
GPS lie within 400 ft + the stated offset of a road of the freeway the report names?
  freeway roads  motorway / trunk ways whose ref carries a route number the report names (I-680, SR-4 ...), and
                 motorway_link ways joined to one of them, directly or through up to MAX_HOPS other links
Sub-types as freeway_examples.py: mainline (a route + a cross street + offset), ramp (a ramp word), f2f (two routes),
other. Control: the same check with each GPS point moved SHIFT_M in a seeded random direction (a fit there is chance).

Run: python tests/statewide/freeway_gps.py   (writes data/statewide/freeway_gps.csv and freeway_gps.json)
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
CHECK_FT, MAX_HOPS, SHIFT_M, SEED, REACH_M = 400.0, 3, 2000.0, 23, 3000.0
RAMP = re.compile(r"\b(RAMP|ONRAMP|OFFRAMP|CONNECTOR|TRANSITION)\b")
FWY = re.compile(r"\b(FREEWAY|FWY|EXPRESSWAY)\b")


def seg_ft(p, a, b) -> float:
    k = math.cos(math.radians(p[0]))
    px, py, ax, ay, bx, by = p[1] * k, p[0], a[1] * k, a[0], b[1] * k, b[0]
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy) * 364000


class Roads:
    def __init__(self):
        self.db = sqlite3.connect(ROOT / "data" / "osm" / "ca_osm.sqlite")

    def near(self, p, m):
        d = m / 111_000
        return self.db.execute(
            "SELECT w.id, w.highway, w.tags, w.nodes, w.coords FROM way_box b JOIN ways w ON w.id = b.id WHERE "
            "b.maxlat >= ? AND b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ? AND w.highway IN "
            "('motorway', 'motorway_link', 'trunk', 'trunk_link')",
            (p[0] - d, p[0] + d, p[1] - d * 1.3, p[1] + d * 1.3)).fetchall()

    def fits(self, p, routes: set[str], tol_ft: float) -> str | None:
        """'mainline' / 'link' when a road of these routes runs within tol_ft of p, else None."""
        ways = self.near(p, max(REACH_M, tol_ft * 0.3048 + 200))
        info = {}
        for wid, hw, tags, nids, coords in ways:
            refs = set(re.findall(r"\d+", str(json.loads(tags).get("ref") or "")))
            info[wid] = (hw, refs, json.loads(nids), json.loads(coords))
        main_nodes = {n for wid, (hw, refs, nids, _) in info.items() if hw in ("motorway", "trunk") and refs & routes
                      for n in nids}
        good = set()                                  # links joined to the route, through up to MAX_HOPS links
        frontier = {wid for wid, (hw, refs, nids, _) in info.items() if hw.endswith("_link")
                    and (refs & routes or set(nids) & main_nodes)}
        for _ in range(MAX_HOPS):
            good |= frontier
            nodes = {n for wid in frontier for n in info[wid][2]}
            frontier = {wid for wid, (hw, _, nids, _) in info.items() if hw.endswith("_link") and wid not in good
                        and set(nids) & nodes}
            if not frontier:
                break
        best = None
        for wid, (hw, refs, nids, cs) in info.items():
            ours = (hw in ("motorway", "trunk") and refs & routes) or wid in good
            if not ours:
                continue
            for a, b in zip(cs, cs[1:]):
                if seg_ft(p, a, b) <= tol_ft:
                    kind = "link" if hw.endswith("_link") else "mainline"
                    if best is None or kind == "mainline":
                        best = kind
        return best


def kind_of(p: str, s: str, routes_p, routes_s) -> str:
    if RAMP.search(f"{p} {s}"):
        return "ramp"
    if (routes_p or FWY.search(p)) and (routes_s or FWY.search(s)):
        return "f2f"
    if routes_p or routes_s:
        return "mainline"
    return "other"


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import names

    import citywide as cw
    with open(DATA / "buckets.csv") as f:
        want = {r["collision_id"]: r for r in csv.DictReader(f) if r["bucket"] == "D1" and r["gps_off"] == "1"}
    by_city = defaultdict(set)
    for cid, r in want.items():
        by_city[r["city"]].add(cid)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    roads, rng, rows = Roads(), random.Random(SEED), []
    for city, ids in sorted(by_city.items(), key=lambda kv: -len(kv[1])):
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in ids or cid in seen or c.get("lat") is None:
                continue
            seen.add(cid)
            c = aliases_mod.apply(dict(c))
            p_, s_ = (c.get("primary_road") or "").upper(), (c.get("secondary_road") or "").upper()
            rp, rs = set(names.ROUTE_ANY.findall(p_)), set(names.ROUTE_ANY.findall(s_))
            routes = rp | rs
            tol = CHECK_FT + (c.get("offset_ft") or 0.0)
            g = (c["lat"], c["lon"])
            hit = roads.fits(g, routes, tol) if routes else None
            b = rng.uniform(0, 2 * math.pi)
            q = (g[0] + SHIFT_M / 111_000 * math.cos(b), g[1] + SHIFT_M / 111_000 * math.sin(b) / math.cos(math.radians(g[0])))
            ctl = roads.fits(q, routes, tol) if routes else None
            rows.append({"collision_id": cid, "city": city, "agency": c.get("agency"), "district": want[cid]["district"],
                         "kind": kind_of(p_, s_, rp, rs), "routes": " ".join(sorted(routes)), "primary": p_,
                         "secondary": s_, "offset_ft": c.get("offset_ft") or 0, "lat": g[0], "lon": g[1],
                         "fits_freeway": hit or "", "control_fits": ctl or ""})
        print(f"{city or '(blank)'}: {len(seen)}", flush=True)
    with open(DATA / "freeway_gps.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    by = defaultdict(Counter)
    for r in rows:
        k = by[r["kind"]]
        k["crashes"] += 1
        k["with_route_number"] += bool(r["routes"])
        k["fits"] += bool(r["fits_freeway"])
        k["fits_on_link"] += r["fits_freeway"] == "link"
        k["control_fits"] += bool(r["control_fits"])
    tot = Counter()
    for v in by.values():
        tot.update(v)
    ex = next((r for r in rows if r["collision_id"] == "1428399"), None)
    res = {"d1_gps_rejected": len(want), "checked": len(rows), "total": dict(tot),
           "by_kind": {k: dict(v) for k, v in by.items()},
           "by_agency_top15": Counter(r["agency"] for r in rows if r["fits_freeway"]).most_common(15),
           "martinez_1428399": ex}
    (DATA / "freeway_gps.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
