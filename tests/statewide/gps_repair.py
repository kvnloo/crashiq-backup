"""Mistyped police GPS (PM 2026-10-23; measure only, evidence for a user decision). For every difficult crash of run
9A whose police GPS is off the report's roads (buckets.csv gps_off), try simple repairs and see whether the repaired
point fits the report: a road the report names within 400 ft + the stated offset (the coverage's GPS check outside
city maps: Outside.fits, roads from the OSM extract's spatial index, names by fatal.road_match).

Repairs: latitude +/-1, +/-2, +/-3 degrees; longitude without its minus restored; latitude and longitude swapped
(also with the minus restored); the degrees-minutes-seconds reading (coverage.dms_decode). A repaired point must lie in
California's box. A crash is "repaired" when exactly ONE repair fits; also reported: whether that point is in the
crash's own county (the CCRS county code's box), a strong second check.

False-repair control: the same crashes with decoy shifts no typo makes (latitude +/-0.5, +/-1.5, +/-2.5 degrees;
longitude +/-1 degree). How often a decoy fits estimates how often a repair fits a road by chance.

Run: python tests/statewide/gps_repair.py   (writes data/statewide/gps_repair.csv and gps_repair.json)
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
CA = (32.0, -124.6, 42.1, -114.0)


def repairs(la: float, lo: float, dms) -> dict[str, tuple[float, float]]:
    out = {f"lat {d:+d}": (la + d, lo) for d in (-3, -2, -1, 1, 2, 3)}
    if lo > 0:
        out["lon minus restored"] = (la, -lo)
    out["lat/lon swapped"] = (lo, la)
    out["swapped, minus restored"] = (abs(lo), -abs(la))
    a, b = dms(la), dms(lo)
    if a is not None and b is not None:
        out["degrees-minutes-seconds"] = (a, b if b < 0 else -b)
    return {k: p for k, p in out.items() if CA[0] <= p[0] <= CA[2] and CA[1] <= p[1] <= CA[3] and p != (la, lo)}


def decoys(la: float, lo: float) -> dict[str, tuple[float, float]]:
    out = {f"lat {d:+.1f}": (la + d, lo) for d in (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5)}
    out.update({f"lon {d:+d}": (la, lo + d) for d in (-1, 1)})
    return {k: p for k, p in out.items() if CA[0] <= p[0] <= CA[2] and CA[1] <= p[1] <= CA[3]}


def main() -> None:
    from crashiq import aliases as aliases_mod

    import citywide as cw
    import osm_local
    from coverage import Outside, districts, dms_decode

    with open(DATA / "buckets.csv") as f:
        want = {r["collision_id"]: r for r in csv.DictReader(f) if r["gps_off"] == "1"}
    by_city = defaultdict(set)
    for cid, r in want.items():
        by_city[r["city"]].add(cid)
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    _, cname = districts()
    box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            box[code] = r
    outside = Outside(local, box)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    rows, orig_fits = [], 0
    for i, (city, ids) in enumerate(sorted(by_city.items(), key=lambda kv: -len(kv[1]))):
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in ids or cid in seen or c.get("lat") is None:
                continue
            seen.add(cid)
            c = aliases_mod.apply(dict(c))
            la, lo = c["lat"], c["lon"]
            if outside.fits(la, lo, c):
                orig_fits += 1                   # this name check accepts the GPS as is: not a repair case
                continue
            fit = [k for k, p in repairs(la, lo, dms_decode).items() if outside.fits(p[0], p[1], c)]
            dfit = [k for k, p in decoys(la, lo).items() if outside.fits(p[0], p[1], c)]
            # matched control: each repair's own displacement, turned 90, 180 and 270 degrees (same size, wrong way)
            rot = []
            for k, p in repairs(la, lo, dms_decode).items():
                dy, dx = p[0] - la, p[1] - lo
                for ry, rx in ((-dx, dy), (-dy, -dx), (dx, -dy)):
                    q = (la + ry, lo + rx)
                    if CA[0] <= q[0] <= CA[2] and CA[1] <= q[1] <= CA[3]:
                        rot.append((k, outside.fits(q[0], q[1], c)))
            cb = box.get(int(c.get("county_code") or 0))
            in_county = None
            if len(fit) == 1 and cb:
                p = repairs(la, lo, dms_decode)[fit[0]]
                in_county = cb[0] <= p[0] <= cb[2] and cb[1] <= p[1] <= cb[3]
            r = want[cid]
            rows.append({"collision_id": cid, "city": city, "agency": c.get("agency"), "district": r["district"],
                         "bucket": r["bucket"], "lat": la, "lon": lo, "repairs_fitting": "|".join(fit),
                         "unique_repair": fit[0] if len(fit) == 1 else "", "in_own_county": "" if in_county is None
                         else str(int(in_county)), "decoys_fitting": "|".join(dfit), "n_repairs": len(repairs(la, lo, dms_decode)),
                         "n_decoys": len(decoys(la, lo)),
                         "rot_tried": "|".join(k for k, _ in rot), "rot_fit": "|".join(k for k, f in rot if f)})
        if i % 25 == 0:
            print(f"[{i + 1}/{len(by_city)}] {city}: {len(seen)}", flush=True)
    with open(DATA / "gps_repair.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summarize(rows, len(want), orig_fits)
    print("EXIT: finished", flush=True)


def repair_names(r: dict) -> list[str]:
    """The repairs that were tried for this crash (in California's box), recomputed from its GPS."""
    from coverage import dms_decode
    return list(repairs(float(r["lat"]), float(r["lon"]), dms_decode))


def summarize(rows: list[dict], expected: int, orig_fits: int = 0) -> None:
    n = len(rows)
    uniq = [r for r in rows if r["unique_repair"]]
    uniq_cty = [r for r in uniq if r["in_own_county"] == "1"]
    multi = sum(1 for r in rows if r["repairs_fitting"].count("|") >= 1)
    # chance: per tried point, how often a decoy fits vs how often a repair fits
    rep_tries = sum(int(r["n_repairs"]) for r in rows)
    rep_fits = sum(len([x for x in r["repairs_fitting"].split("|") if x]) for r in rows)
    dec_tries = sum(int(r["n_decoys"]) for r in rows)
    dec_fits = sum(len([x for x in r["decoys_fitting"].split("|") if x]) for r in rows)
    chance = dec_fits / dec_tries if dec_tries else 0
    exp_false = sum(int(r["n_repairs"]) for r in rows) * chance       # chance fits expected among all repairs tried
    def per_kind(field):
        c = Counter()
        for r in rows:
            for x in (r[field] or "").split("|"):
                if x:
                    c[x] += 1
        return c
    rt, rf = per_kind("rot_tried"), per_kind("rot_fit")
    rep_t = Counter()
    rep_f = per_kind("repairs_fitting")
    for r in rows:
        for k in repair_names(r):
            rep_t[k] += 1
    matched = {k: {"repair_fit_rate": round(rep_f[k] / rep_t[k], 4) if rep_t[k] else None,
                   "same_size_wrong_way_fit_rate": round(rf[k] / rt[k], 4) if rt[k] else None,
                   "chance_share_of_repair_fits": round((rf[k] / rt[k]) / (rep_f[k] / rep_t[k]), 3)
                   if rt[k] and rep_t[k] and rep_f[k] else None}
               for k in sorted(rep_t)}
    res = {"crashes_with_off_road_gps": expected, "checked": n,
           "matched_control_by_repair": matched,
           "gps_fits_as_is_by_this_name_check": orig_fits,
           "unique_repair": len(uniq), "unique_repair_in_own_county": len(uniq_cty),
           "more_than_one_repair_fits": multi,
           "by_repair": dict(Counter(r["unique_repair"] for r in uniq).most_common()),
           "by_repair_in_own_county": dict(Counter(r["unique_repair"] for r in uniq_cty).most_common()),
           "by_bucket": {b: {"crashes": c, "unique_repair": sum(1 for r in uniq if r["bucket"] == b),
                             "in_own_county": sum(1 for r in uniq_cty if r["bucket"] == b)}
                         for b, c in sorted(Counter(r["bucket"] for r in rows).items())},
           "by_agency_top25": [{"agency": a, "unique_repair": k,
                                "in_own_county": sum(1 for r in uniq_cty if r["agency"] == a)}
                               for a, k in Counter(r["agency"] for r in uniq).most_common(25)],
           "false_repair_control": {"repair_points_tried": rep_tries, "repair_points_fitting": rep_fits,
                                    "decoy_points_tried": dec_tries, "decoy_points_fitting": dec_fits,
                                    "chance_fit_rate_per_point": round(chance, 5),
                                    "expected_chance_fits_among_repairs": round(exp_false),
                                    "share_of_repair_fits_explainable_by_chance": round(exp_false / rep_fits, 3)
                                    if rep_fits else None}}
    (DATA / "gps_repair.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if not k.startswith("by_agency")}, indent=1))


if __name__ == "__main__":
    main()
