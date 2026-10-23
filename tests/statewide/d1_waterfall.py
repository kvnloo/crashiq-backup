"""D1 waterfall (PM 2026-10-23; measure only, run 9 basis): each of the D1 (freeway / ramp) difficult crashes of run
9A goes to the FIRST step that would place it, so the steps don't overlap:
  1 GPS repaired       degrees-minutes-seconds or the lost minus restored, one repair only, in its own county (#247;
                       gps_repair.csv, gps_repair_raw.csv)
  2 GPS agrees         police GPS within 400 ft of the spot the report describes (freeway_report_point.csv accept)
  3 report spot        the report's spot can be found (#246 would place it by the report); no GPS agreement
  4 GPS on freeway     no report spot, but the GPS lies on the named freeway or a link joined to it: review only
                       (freeway_gps.csv; its random-shift control shown)
  5 nothing
Each step: crashes, fatal, KSI, and the chance control where there is one.

Step 3's accuracy, measurable now (--accuracy): freeway crashes whose police GPS fits the report's roads (run 9A
gps_usable, road type freeway) are the truth: a seeded sample, the report's spot computed exactly as for D1 with the
GPS unused; right = within 400 ft (and 250 ft) of the police GPS. By kind, with Wilson 95% low bounds.

Run: python tests/statewide/d1_waterfall.py [--accuracy]   (writes data/statewide/d1_waterfall.json / d1_accuracy.json)
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
SAMPLE, SEED = 6000, 246


def load(name, key="collision_id"):
    with open(DATA / name) as f:
        return {r[key]: r for r in csv.DictReader(f)}


def waterfall() -> None:
    d1 = {k: r for k, r in load("buckets.csv").items() if r["bucket"] == "D1"}
    rep = {}
    for name in ("gps_repair.csv", "gps_repair_raw.csv"):
        for k, r in load(name).items():
            if r["unique_repair"] in ("degrees-minutes-seconds", "lon minus restored") and str(r["in_own_county"]) == "1":
                rep[k] = r["unique_repair"]
    rp = load("freeway_report_point.csv")
    fg = load("freeway_gps.csv")
    steps = defaultdict(Counter)
    kinds = defaultdict(Counter)
    for cid, r in d1.items():
        p = rp.get(cid, {})
        g = fg.get(cid, {})
        if cid in rep:
            s = "1 GPS repaired (#247)"
        elif p.get("accept") == "1":
            s = "2 GPS agrees with the report's spot"
        elif p.get("computable") == "1":
            s = "3 report spot found (#246 places it by the report)"
        elif g.get("fits_freeway"):
            s = "4 GPS on the named freeway, no report spot (review only)"
        else:
            s = "5 nothing"
        st = steps[s]
        st["crashes"] += 1
        st["fatal"] += r["killed"] == "1"
        st["ksi"] += r["ksi"] == "1"
        kinds[s][p.get("kind") or g.get("kind") or "?"] += 1
        if s.startswith("2") and p.get("control_accept") == "1":
            st["chance_control"] += 1
        if s.startswith("4") and g.get("control_fits"):
            st["chance_control"] += 1
    res = {"basis": "run 9A D1 bucket (main 5ed6783); measure only", "d1": len(d1),
           "steps": {s: {**dict(v), "by_kind": dict(kinds[s])} for s, v in sorted(steps.items())}}
    if sum(v["crashes"] for v in steps.values()) != len(d1):
        raise SystemExit("waterfall doesn't add up")
    (DATA / "d1_waterfall.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def accuracy() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import names

    import citywide as cw
    from bin2_whatif import wilson_low
    from freeway_report_point import RAMP, Map, ft, report_point
    cov = {}
    for p in sorted(DATA.glob("coverage_crashes_r9a_*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["outcome"] == "gps_usable" and r["road_type"] == "freeway":
                    cov[r["collision_id"]] = r
    ids = sorted(cov, key=int)
    random.Random(SEED).shuffle(ids)
    pick = set(ids[:SAMPLE])
    by_city = defaultdict(set)
    for cid in pick:
        by_city[cov[cid]["city"]].add(cid)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    m = Map()
    res = defaultdict(Counter)
    per = []
    for city, want in sorted(by_city.items()):
        batch, seen = [], set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in want and cid not in seen and c.get("lat") is not None:
                seen.add(cid)
                batch.append(aliases_mod.apply(dict(c)))
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
            p_, s_ = (c.get("primary_road") or "").upper(), (c.get("secondary_road") or "").upper()
            rp_, rs_ = names.ROUTE_ANY.findall(p_), names.ROUTE_ANY.findall(s_)
            kind = ("ramp" if RAMP.search(f"{p_} {s_}") else "f2f" if rp_ and rs_ else
                    "mainline" if rp_ or rs_ else "other")
            k = res[kind]
            k["sample"] += 1
            if kind == "other":
                continue
            pt = report_point(m, {**c, "lat": None, "lon": None}, kind).get("point")
            if not pt:
                continue
            d = ft(pt, (c["lat"], c["lon"]))
            off0 = c.get("offset_ft") or 0.0
            at_cross = None
            if kind == "mainline" and off0:            # the same spot without the offset: is the GPS at the crossing?
                p0 = report_point(m, {**c, "lat": None, "lon": None, "offset_ft": 0}, kind).get("point")
                at_cross = round(ft(p0, (c["lat"], c["lon"]))) if p0 else None
            per.append({"collision_id": str(c["crash_id"]), "kind": kind, "offset_ft": round(off0),
                        "dist_ft": round(d), "gps_to_crossing_ft": at_cross})
            k["spot_found"] += 1
            k["within_400ft"] += d <= 400
            k["within_250ft"] += d <= 250
    out = {"truth": "run 9A freeway crashes whose police GPS fits the report's roads (gps_usable), seeded sample of "
                    f"{SAMPLE}; the report's spot computed with the GPS unused", "by_kind": {}}
    for kind, k in res.items():
        n = k["spot_found"]
        out["by_kind"][kind] = {**dict(k), "pct_within_400ft": round(100 * k["within_400ft"] / n, 1) if n else None,
                                "low_400ft": wilson_low(k["within_400ft"], n) if n else None,
                                "pct_within_250ft": round(100 * k["within_250ft"] / n, 1) if n else None}
    bands = defaultdict(Counter)                        # mainline by stated offset: where is the police GPS?
    for r in per:
        if r["kind"] != "mainline":
            continue
        o = r["offset_ft"]
        band = "0" if o == 0 else "1-400 ft" if o <= 400 else "401-1,320 ft" if o <= 1320 else "over 1,320 ft"
        bnd = bands[band]
        bnd["n"] += 1
        bnd["report_spot_within_400ft"] += r["dist_ft"] <= 400
        if r["gps_to_crossing_ft"] is not None:
            bnd["gps_within_400ft_of_crossing"] += r["gps_to_crossing_ft"] <= 400
    out["mainline_by_offset"] = {b_: {**dict(v), "pct_report_spot_right": round(100 * v["report_spot_within_400ft"]
                                                                                  / v["n"], 1) if v["n"] else None,
                                      "pct_gps_at_crossing": round(100 * v["gps_within_400ft_of_crossing"] / v["n"], 1)
                                      if v["n"] and b_ != "0" else None}
                                 for b_, v in bands.items()}
    with open(DATA / "d1_accuracy_rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["collision_id", "kind", "offset_ft", "dist_ft", "gps_to_crossing_ft"])
        w.writeheader()
        w.writerows(per)
    (DATA / "d1_accuracy.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--accuracy", action="store_true")
    a = ap.parse_args()
    waterfall()
    if a.accuracy:
        accuracy()
