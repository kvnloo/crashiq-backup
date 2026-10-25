"""Run 10b (2026-10-25; measure only): run 10's freeway step again with the fixed fwy_raw (reference streets found
the way the app's same_core finds them: leading direction words, alt_name; Engineering's #259 finding). Only the
freeway step changed, so only the crashes that reached it are redone: freeway crashes (IsFreeway) that run 10 left
without police GPS that fits and without an exact / unique_pair placement. Each gets the app's freeway.place on the
fixed raw (city box + 1 km in a city, else the county); a spot makes it placed_approximate (no_gps / gps_off_roads as
in run 10), no spot leaves its run-10 outcome, or its run-9C outcome where run 10 had placed it approximately (such a
crash has no GPS repair, else it would be gps_usable). Writes coverage_crashes_r10b_<part>.csv, one per run-10 part,
for run10_reconcile.py --prefix r10b.

Run: python tests/statewide/run10_fwy_redo.py
"""

from __future__ import annotations

import csv
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
AUTO = ("gps_usable", "gps_usable_dms", "gps_usable_sign", "placed_exact", "placed_unique_pair")


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import freeway

    import citywide as cw
    import corridors
    import osm_local
    from coverage import Outside, districts
    from fwy_raw import FwyRaw
    from run9_reconcile import parts
    c9 = parts("r9c")
    files = sorted(DATA.glob("coverage_crashes_r10_*.csv"))
    todo, by_city = {}, defaultdict(set)
    for p in files:
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["road_type"] == "freeway" and r["outcome"] not in AUTO:
                    todo[r["collision_id"]] = r
                    by_city[r["city"]].add(r["collision_id"])
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    _, cname = districts()
    box = {}
    for code, name in cname.items():
        x = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if x:
            box[code] = x
    fr = FwyRaw(local, box, Outside(local, box))
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    new, tally = {}, Counter()
    for city, ids in sorted(by_city.items(), key=lambda kv: -len(kv[1])):
        b = bounds.get(corridors.norm_city(city)) if city else None
        cbox = None
        if b:
            row = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE id = ? "
                                   "ORDER BY CAST(admin_level AS INT) DESC LIMIT 1", (b["rel"],)).fetchone()
            if row:
                dlat = 1.0 / 111.32
                dlon = dlat / max(0.2, math.cos(math.radians((row[0] + row[2]) / 2)))
                cbox = (row[0] - dlat, row[1] - dlon, row[2] + dlat, row[3] + dlon)
        batch, seen = [], set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in ids and cid not in seen:
                seen.add(cid)
                batch.append(aliases_mod.apply(dict(c)))
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
            cid = str(c["crash_id"])
            r = todo[cid]
            if freeway.parse(c) is None:
                continue
            raw = fr.raw(c, cbox)
            sp = freeway.place(raw, c) if raw else None
            was = r["outcome"] == "placed_approximate"
            if sp is not None:
                how = (r["approx"].split(":")[0] if was else
                       "gps_off_roads" if r["reason"].startswith("police GPS off") else "no_gps")
                new[cid] = {"outcome": "placed_approximate", "bin": "1", "reason": "", "approx": f"{how}:{sp.kind}"}
                tally["still approximate" if was else f"newly approximate ({how})"] += 1
            elif was:
                b9 = c9[cid]
                new[cid] = {"outcome": b9["outcome"], "bin": b9["bin"], "reason": b9["reason"], "approx": ""}
                tally["no longer approximate"] += 1
        print(f"{city or '(blank)'}: {len(batch)}", flush=True)
    for p in files:
        out = DATA / p.name.replace("_r10_", "_r10b_")
        with open(p) as fi, open(out, "w", newline="") as fo:
            rd = csv.DictReader(fi)
            w = csv.DictWriter(fo, rd.fieldnames)
            w.writeheader()
            for r in rd:
                w.writerow({**r, **new.get(r["collision_id"], {})})
    print(dict(tally))
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
