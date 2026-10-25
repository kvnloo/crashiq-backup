"""Per-crash comparison for #259 (Engineering; measure only): the Tester's report-spot method
(freeway_report_point.report_point, run 9) vs the app's freeway.place (fwy_raw.FwyRaw raw, run 10) on the d1_waterfall
accuracy sample (6,000 freeway crashes whose police GPS fits the report, seed 246). One row per crash: the police GPS
(truth), each method's point or its reason for none, each one's distance to the GPS.

Run: python tests/statewide/d1_compare.py   (writes data/statewide/d1_compare.csv)
"""

from __future__ import annotations

import csv
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
SAMPLE, SEED = 6000, 246


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import freeway, names

    import citywide as cw
    import osm_local
    from coverage import Outside, districts
    from freeway_report_point import RAMP, Map, ft, report_point
    from fwy_raw import FwyRaw
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
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    _, cname = districts()
    box = {}
    for code, name in cname.items():
        x = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if x:
            box[code] = x
    fr = FwyRaw(local, box, Outside(local, box))
    m = Map()
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    batch = []
    for city, want in sorted(by_city.items()):
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in want and cid not in seen and c.get("lat") is not None:
                seen.add(cid)
                c = aliases_mod.apply(dict(c))
                c["_city"] = city
                batch.append(c)
    fmt = lambda p: f"{p[0]:.6f},{p[1]:.6f}" if p else ""        # noqa: E731
    with open(DATA / "d1_compare.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["collision_id", "city", "county_code", "agency", "primary_road", "secondary_road", "offset_ft",
                    "offset_dir", "tester_kind", "app_kind", "gps", "tester_point", "tester_why", "tester_ft",
                    "app_point", "app_why", "app_ft"])
        for i, c in enumerate(sorted(batch, key=lambda x: int(x.get("county_code") or 0))):
            g = (c["lat"], c["lon"])
            p_, s_ = (c.get("primary_road") or "").upper(), (c.get("secondary_road") or "").upper()
            rp_, rs_ = names.ROUTE_ANY.findall(p_), names.ROUTE_ANY.findall(s_)
            kind = ("ramp" if RAMP.search(f"{p_} {s_}") else "f2f" if rp_ and rs_ else
                    "mainline" if rp_ or rs_ else "other")
            q = {**c, "lat": None, "lon": None}
            t = report_point(m, q, kind) if kind != "other" else {"why": "no route number"}
            tp = t.get("point")
            r = freeway.parse(c)
            raw = fr.raw(c) if r else None
            sp = freeway.place(raw, c) if raw else None
            ap = (sp.lat, sp.lon) if sp else None
            why = "" if sp else ("not a freeway description" if r is None else "route lanes not in the county" if raw is
                                 None else "no single crossing / terminal / connector")
            w.writerow([c["crash_id"], c["_city"], c.get("county_code"), c.get("agency"), c.get("primary_road"),
                        c.get("secondary_road"), c.get("offset_ft"), c.get("offset_dir"), kind,
                        r["kind"] if r else "", fmt(g), fmt(tp), "" if tp else t.get("why", ""),
                        round(ft(tp, g)) if tp else "", fmt(ap), why, round(ft(ap, g)) if ap else ""])
            if i % 500 == 0:
                print(i, flush=True)
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
