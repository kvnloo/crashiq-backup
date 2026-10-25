"""Who is wrong in a step-3 miss (PM 2026-10-23; measure only)? For the mainline misses of d1_waterfall.py's accuracy
sample (the report's spot more than 400 ft from police GPS that fits the report), recompute the geometry: the crossing
(the report's spot with no offset), our point (the stated distance along the route in the stated direction), the
mirror point (the same distance the other way), the route's bearing at the crossing. One class each, first match wins:
  v   other route / carriageway  the GPS isn't within ROUTE_FT of the named route at all
  ii  another crossing           the GPS is within ROUTE_FT of the cross street but over FAR_FT from this crossing
  i   opposite side              the GPS is nearer the mirror point than our point (miss ~ 2 x offset)
  iii direction across the road  the stated direction is 60-120 degrees from the route's bearing (angle given)
  iv  same side, short           the miss is less than the stated offset
  vi  other                      same side, farther than stated
(i) is broken down by agency. Ten misses, mostly (i) and (iii), go to a file for the user to judge by hand.

Run: python tests/statewide/d1_misses.py   (writes data/statewide/d1_misses.json, d1_misses.csv, d1_miss_examples.md)
"""

from __future__ import annotations

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
ROUTE_FT, FAR_FT, SEED = 400.0, 2000.0, 1213
LABEL = {"i": "opposite side of the crossing", "ii": "another crossing of the same street",
         "iii": "stated direction across the freeway", "iv": "same side, shorter than stated",
         "v": "other route or carriageway", "vi": "same side, farther than stated"}


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import names

    import citywide as cw
    from freeway_report_point import DIRS, Map, bearing, ft, report_point, turn, walk
    with open(DATA / "d1_accuracy_rows.csv") as f:
        miss = {r["collision_id"]: r for r in csv.DictReader(f) if r["kind"] == "mainline" and int(r["dist_ft"]) > 400}
    cov = {}
    for p in sorted(DATA.glob("coverage_crashes_r9a_*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["collision_id"] in miss:
                    cov[r["collision_id"]] = r
    by_city = defaultdict(set)
    for cid, r in cov.items():
        by_city[r["city"]].add(cid)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    m = Map()
    rows = []
    for city, ids in sorted(by_city.items()):
        batch, seen = [], set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in ids and cid not in seen and c.get("lat") is not None:
                seen.add(cid)
                batch.append(aliases_mod.apply(dict(c)))
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
            g = (c["lat"], c["lon"])
            q = {**c, "lat": None, "lon": None}
            ours = report_point(m, q, "mainline").get("point")
            cross = report_point(m, {**q, "offset_ft": 0}, "mainline").get("point")
            if not ours or not cross:
                continue
            county = int(c.get("county_code") or 0)
            p_, s_ = (c.get("primary_road") or "").upper(), (c.get("secondary_road") or "").upper()
            rp, rs = set(names.ROUTE_ANY.findall(p_)), set(names.ROUTE_ANY.findall(s_))
            nums = rp or rs
            cross_raw = s_ if rp else p_
            rw = m.route(county, frozenset(nums))
            st = m.street(county, cross_raw)
            d = str(c.get("offset_dir") or "").strip()[:1].upper()
            off = c.get("offset_ft") or 0.0
            mirror = walk(rw, min((q_ for w in rw for q_ in w[5]), key=lambda z: ft(z, cross)), (DIRS[d] + 180) % 360,
                          off) if off and d in DIRS else cross
            near = min((ft(cross, z) for w in rw for z in w[5]), default=None)
            seg = None                                     # the route's bearing at the crossing
            for w in rw:
                for a, b in zip(w[5], w[5][1:]):
                    dd = min(ft(a, cross), ft(b, cross))
                    if seg is None or dd < seg[0]:
                        seg = (dd, bearing(a, b))
            ang = round(min(turn(seg[1], DIRS[d]), turn((seg[1] + 180) % 360, DIRS[d]))) if seg and d in DIRS else None
            g_route = min((ft(g, z) for w in rw for z in w[5]), default=1e9)
            g_street = min((ft(g, z) for w in st for z in w[5]), default=1e9)
            dm, dours = ft(g, mirror) if mirror else 1e9, ft(g, ours)
            if g_route > ROUTE_FT:
                cls = "v"
            elif g_street <= ROUTE_FT and ft(g, cross) > FAR_FT:
                cls = "ii"
            elif dm < dours:
                cls = "i"
            elif ang is not None and 60 <= ang <= 120:
                cls = "iii"
            elif dours < off:
                cls = "iv"
            else:
                cls = "vi"
            rows.append({"collision_id": str(c["crash_id"]), "agency": c.get("agency"), "city": c.get("city"),
                         "primary": c.get("primary_road"), "secondary": c.get("secondary_road"),
                         "offset_ft": round(off), "dir": d, "cls": cls, "angle": ang, "miss_ft": round(dours),
                         "gps_to_mirror_ft": round(dm), "gps_to_crossing_ft": round(ft(g, cross)),
                         "gps": f"{g[0]:.6f},{g[1]:.6f}", "ours": f"{ours[0]:.6f},{ours[1]:.6f}",
                         "crossing": f"{cross[0]:.6f},{cross[1]:.6f}", "route_gap_ft": round(near or 0)})
        print(f"{city or '(blank)'}: {len(batch)}", flush=True)
    with open(DATA / "d1_misses.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n = len(rows)
    cls = Counter(r["cls"] for r in rows)
    i_ag = Counter(r["agency"] for r in rows if r["cls"] == "i")
    all_ag = Counter(r["agency"] for r in rows)
    ratio = sorted(r["miss_ft"] / max(1, r["offset_ft"]) for r in rows if r["cls"] == "i" and r["offset_ft"])
    res = {"misses_classified": n, "of_sample_misses": len(miss),
           "classes": {f"{k} {LABEL[k]}": {"crashes": v, "share_pct": round(100 * v / n, 1)} for k, v in
                       sorted(cls.items())},
           "opposite_side_miss_over_offset_median": round(ratio[len(ratio) // 2], 2) if ratio else None,
           "angles_class_iii": dict(Counter(f"{10 * (r['angle'] // 10)}-{10 * (r['angle'] // 10) + 9} deg"
                                            for r in rows if r["cls"] == "iii")),
           "opposite_side_by_agency": [{"agency": a, "opposite_side": k, "misses": all_ag[a],
                                        "share_pct": round(100 * k / all_ag[a], 1)} for a, k in i_ag.most_common(12)]}
    (DATA / "d1_misses.json").write_text(json.dumps(res, indent=1))
    rng = random.Random(SEED)
    pick = []
    for k, want in (("i", 5), ("iii", 4), ("ii", 1)):
        pool = sorted((r for r in rows if r["cls"] == k), key=lambda r: r["collision_id"])
        pick += rng.sample(pool, min(want, len(pool)))
    gm = lambda s: f"https://www.google.com/maps?q={s}"     # noqa: E731
    md = ["# Freeway misses for the user to judge (D1 mainline, step 3)", "",
          "Our point = where the report's description lands (crossing of the cross street with the freeway, then the "
          "stated distance in the stated direction along the freeway). Police GPS = the officer's point, which fits "
          "the report's roads. Coordinates use a plain ASCII minus; paste them into Google Maps.", ""]
    for i, r in enumerate(pick, 1):
        md += [f"## {i}. {r['primary']} & {r['secondary']}: {LABEL[r['cls']]}", "",
               f"- Record {r['collision_id']} ({r['city']}, agency {r['agency']}); stated {r['offset_ft']} ft {r['dir']}",
               f"- Crossing: {r['crossing']} ({gm(r['crossing'])})",
               f"- Our point: {r['ours']} ({gm(r['ours'])})",
               f"- Police GPS: {r['gps']} ({gm(r['gps'])})",
               f"- GPS is {r['miss_ft']:,} ft from our point, {r['gps_to_crossing_ft']:,} ft from the crossing, "
               f"{r['gps_to_mirror_ft']:,} ft from the same distance the other way"
               + (f"; stated direction is {r['angle']} deg from the freeway's line" if r["angle"] is not None else ""),
               ""]
    (DATA / "d1_miss_examples.md").write_text("\n".join(md) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
