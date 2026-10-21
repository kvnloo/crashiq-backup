"""Placement accuracy by agency: the hidden-GPS test (#88), statewide.

For every local police agency (not CHP, not a multi-city sheriff) with at least MIN_N street crashes with GPS in
2021-2024: take a random sample of those crashes, hide the GPS, run the app's own locator (`locate.place`, no
address index, no aliases) on the agency's city street network from the local OSM extract, and score the result
against the hidden point. Correct = within 250 ft (76.2 m), the PR #16 definition, scored two ways: at the chosen
intersection (the matcher's job: is it the crash's intersection?) and at the final point after the officer's
stated distance and direction (which many agencies' GPS can't confirm, because their GPS sits at the intersection
even when the report says hundreds of feet away; Concord 2026-10-20: 92% vs 73%). Reported per locator tier
(exact auto-places under the gate; relaxed / near / fuzzy are suggestions held for review), with Wilson 95% lower
bounds, on all GPS and (intersection accuracy) on self-consistent GPS only (the point lies within 400 ft of an
intersection of the two streets the report names, the GPS-check distance of decision #77).

Run: python tests/statewide/accuracy_by_agency.py   (writes data/statewide/accuracy_by_agency.json)
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
import corridors  # noqa: E402
import osm_local  # noqa: E402
from crashiq import locate, osm  # noqa: E402
from crashiq.names import same_core, street_key  # noqa: E402
from crashiq.sources import ca_ccrs as cc  # noqa: E402

DATA = ROOT / "data" / "statewide"
MIN_N, SAMPLE, SEED = 200, 400, 88
TOL_M, CONSIST_M = 250 * 0.3048, 400 * 0.3048
TIERS = ("exact", "relaxed", "near", "fuzzy")
COLS = ("Collision Id", "Report Version", "NCIC Code", "Crash Date Time", "Latitude", "Longitude", "PrimaryRoad",
        "SecondaryRoad", "SecondaryDistance", "SecondaryDirection", "SecondaryUnitOfMeasure", "IsFreeway", "IsDeleted")


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def street_crashes(con, ncic: str) -> list[dict]:
    """Latest version per Collision Id, 2021-2024, not freeway, valid GPS."""
    best: dict[str, dict] = {}
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes' AND year <= 2024"):
        q = f'SELECT {", ".join(chr(34) + c + chr(34) for c in COLS)} FROM "{rid}" WHERE "NCIC Code" = ?'
        for r in con.execute(q, (ncic,)):
            rec = dict(zip(COLS, r))
            if str(rec["IsDeleted"]) == "True" or str(rec["IsFreeway"]) == "True":
                continue
            la, lo = rec["Latitude"], rec["Longitude"]
            if not (isinstance(la, (int, float)) and isinstance(lo, (int, float)) and 32 <= la <= 42.1
                    and -124.5 <= lo <= -114):
                continue
            cid = str(int(rec["Collision Id"]))
            if cid not in best or (rec["Report Version"] or 0) > (best[cid]["Report Version"] or 0):
                best[cid] = rec
    out = []
    for rec in best.values():
        c = cc._normalize({**rec, "IsFreeway": "False"})
        c["truth"] = (rec["Latitude"], rec["Longitude"])
        c["lat"] = c["lon"] = None                         # hidden from the locator
        out.append(c)
    return out


class Grid:
    def __init__(self, net, cell=0.002):
        self.cell, self.net, self.g = cell, net, defaultdict(list)
        for n in net.intersections:
            la, lo = net.coord[n]
            self.g[(int(la / cell), int(lo / cell))].append(n)

    def near(self, p, m):
        i, j = int(p[0] / self.cell), int(p[1] / self.cell)
        return [n for di in (-1, 0, 1) for dj in (-1, 0, 1) for n in self.g.get((i + di, j + dj), [])
                if osm.metres(self.net.coord[n], p) <= m]


def consistent(net, grid, c) -> bool | None:
    kp, ks = street_key(c.get("primary_road")), street_key(c.get("secondary_road"))
    if not kp or not ks:
        return None
    for n in grid.near(c["truth"], CONSIST_M):
        keys = net.keys_at[n]
        if any(same_core(kp, k) for k in keys) and any(same_core(ks, k) for k in keys):
            return True
    return False


def run() -> list[dict]:
    agencies = json.loads((DATA / "agencies.json").read_text())
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    out = []
    cands = [a for a in agencies if a["type"] == "local" and a["n_cities"] <= 3
             and a["street_crashes"] * a["street_gps_pct"] / 100 >= MIN_N]
    for i, a in enumerate(sorted(cands, key=lambda a: -a["crashes"]), 1):
        row = {"ncic": a["ncic"], "city": a["city"], "county": a["county"], "street_gps_pct": a["street_gps_pct"]}
        b = bounds.get(corridors.norm_city(a["city"]))
        if not b:
            out.append({**row, "status": "no OSM boundary for the agency's city"})
            continue
        crashes = street_crashes(con, a["ncic"])
        if len(crashes) < MIN_N:
            out.append({**row, "status": f"only {len(crashes)} street crashes with GPS in 2021-2024"})
            continue
        random.Random(SEED).shuffle(crashes)
        sample = crashes[:SAMPLE]
        net = osm.Network(osm_local.network_in_area(local, b["rel"]))
        grid = Grid(net)
        t = Counter()
        for c in sample:
            pl = locate.place(net, c)
            ok = pl.lat is not None and osm.metres((pl.lat, pl.lon), c["truth"]) <= TOL_M
            ok_node = pl.node is not None and osm.metres(net.coord[pl.node], c["truth"]) <= TOL_M
            t[(pl.tier, "ok_node")] += ok_node
            if (c.get("offset_ft") or 0) > 0:
                t[(pl.tier, "n_off")] += 1
                t[(pl.tier, "ok_off")] += ok
            cons = consistent(net, grid, c)
            t[(pl.tier, "n")] += 1
            t[(pl.tier, "ok")] += ok
            t["consistent"] += bool(cons)
            t["checkable"] += cons is not None
            if cons:
                t[(pl.tier, "n_c")] += 1
                t[(pl.tier, "ok_c")] += ok_node
        res = {**row, "status": "tested", "gps_street_crashes": len(crashes), "sample": len(sample),
               "gps_self_consistent_pct": round(100 * t["consistent"] / t["checkable"], 1) if t["checkable"] else None,
               "review_pct": round(100 * t[("review", "n")] / len(sample), 1)}
        for tier in TIERS:
            n, k, nc, kc = t[(tier, "n")], t[(tier, "ok")], t[(tier, "n_c")], t[(tier, "ok_c")]
            res[f"{tier}_n"] = n
            res[f"{tier}_counts"] = {"n": n, "ok_point": k, "ok_intersection": t[(tier, "ok_node")],
                                     "n_consistent": nc, "ok_consistent": kc}   # raw counts, for pooling
            res[f"{tier}_share_pct"] = round(100 * n / len(sample), 1)
            res[f"{tier}_acc_pct"] = round(100 * k / n, 1) if n else None
            res[f"{tier}_acc_low_pct"] = round(100 * wilson_low(k, n), 1) if n else None
            kn, no, ko = t[(tier, "ok_node")], t[(tier, "n_off")], t[(tier, "ok_off")]
            res[f"{tier}_intersection_acc_pct"] = round(100 * kn / n, 1) if n else None
            res[f"{tier}_intersection_acc_low_pct"] = round(100 * wilson_low(kn, n), 1) if n else None
            res[f"{tier}_point_acc_with_distance_pct"] = round(100 * ko / no, 1) if no else None
            res[f"{tier}_acc_consistent_pct"] = round(100 * kc / nc, 1) if nc else None
            res[f"{tier}_acc_consistent_low_pct"] = round(100 * wilson_low(kc, nc), 1) if nc else None
        out.append(res)
        print(f"[{i}/{len(cands)}] {a['city']} ({a['ncic']}): exact {res['exact_share_pct']}% "
              f"(intersection {res['exact_intersection_acc_pct']}%, point {res['exact_acc_pct']}%), relaxed "
              f"{res['relaxed_share_pct']}% (intersection {res['relaxed_intersection_acc_pct']}%), "
              f"review {res['review_pct']}%, GPS consistent {res['gps_self_consistent_pct']}%", flush=True)
    (DATA / "accuracy_by_agency.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run()
