"""Run 8b, statewide coverage: #218 rule 2 (default points and coarse coordinates are no location), with the app's
own rule (crashiq.gps_rules.ignored_reason) on every crash the run-8a coverage placed by police GPS. Those whose GPS
the app now ignores are placed from their street names instead, by the app's locator and gate (current main, box +
1 km network), exactly as the coverage's second step would. GPS-off crashes on default points were already placed from
their names (the coverage's GPS check failed them), so their bin can't change. Rule 1 (snapped GPS + the report's
offset) moves points along the road, never between bins; the corridor run counts it.

Run: python tests/statewide/run8b_rule2.py   (reads coverage_crashes_r8_up.csv; writes coverage_crashes_r8b.csv and
     run8b_rule2.json)
"""

from __future__ import annotations

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


def main() -> None:
    from crashiq import gps_rules, locate, osm

    import citywide as cw
    import corridors
    import osm_local
    from coverage import Outside, districts

    with open(DATA / "coverage_crashes_r8_up.csv") as f:
        rows = list(csv.DictReader(f))
    gps = {r["collision_id"]: r for r in rows if r["outcome"] in ("gps_usable", "gps_usable_dms")}
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    hit: dict[str, tuple[str, str]] = {}               # collision_id -> (reason, city)
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes'").fetchall():
        for cid, la, lo in con.execute(f'SELECT "Collision Id", "Latitude", "Longitude" FROM "{rid}"'):
            if cid is None:
                continue
            k = str(int(cid))
            if k in gps and k not in hit:
                why = gps_rules.ignored_reason(la, lo, {}, fits=lambda: True)   # its GPS fit: that's how it got there
                if why:
                    hit[k] = (why[0], gps[k]["city"])
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    _, cname = districts()
    box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            box[code] = r
    outside = Outside(local, box)
    gate = locate.Gate()
    by_city = defaultdict(set)
    for cid, (_, city) in hit.items():
        by_city[city].add(cid)
    new = {}
    for city, ids in by_city.items():
        b = bounds.get(corridors.norm_city(city)) if city else None
        net = osm.Network(osm_local.network_in_box(local, b["rel"])) if b else None
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in ids or cid in new:
                continue
            q = {**c, "lat": None, "lon": None}
            n_ = net if net is not None else outside.network(q)
            pl = locate.place(n_, q) if n_ is not None else locate.Placement("review", note="no street map")
            new[cid] = ("placed_unique_pair" if pl.tier == "unique_pair" else "placed_exact") if gate.auto(pl) else "review"
    if set(new) != set(hit):
        raise SystemExit(f"re-placed {len(new)} of {len(hit)} (completeness guard)")
    moved = Counter()
    with open(DATA / "coverage_crashes_r8b.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        for r in rows:
            o = new.get(r["collision_id"])
            if o:
                moved[f"{r['outcome']} -> {o} ({hit[r['collision_id']][0]})"] += 1
                r = {**r, "outcome": o, "bin": "1" if o.startswith("placed") else "2",
                     "reason": "" if o.startswith("placed") else "police GPS is a default point or coarse; street names "
                                                                 "held"}
            w.writerow(r)
    res = {"gps_crashes_checked": len(gps), "ignored": dict(Counter(v[0] for v in hit.values())),
           "moves": dict(moved.most_common())}
    (DATA / "run8b_rule2.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
