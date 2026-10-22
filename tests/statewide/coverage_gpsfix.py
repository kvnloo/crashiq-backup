"""#199 correction (found in the #211 audit): the police-GPS check inside cities looked up only the exact-name streets
whenever any existed (citywide.City.keys), so GPS on a stretch mapped under a variant of the name ("West Foothill
Boulevard" next to "Foothill Boulevard") was called "off the report's roads". City.keys now returns exact AND same-core
streets. This re-runs ONLY the GPS step of coverage.outcome, with the fixed check, for every #199 crash inside a city
map that has police GPS and wasn't placed by it; a crash whose GPS now fits becomes gps_usable (or gps_usable_dms),
exactly as the first step of outcome() would have made it. Outside cities the check is unchanged (fatal.road_match).

  python tests/statewide/coverage_gpsfix.py --shard 0/3 --part g0 [--exclude "San Diego"] [--only-city X]
  python tests/statewide/coverage_gpsfix.py --apply g0 g1 g2 ...   -> coverage_crashes_gpsfix.csv (then coverage.py
                                                                       --merge it; the #199 file is kept as
                                                                       coverage_crashes_199v1.csv)
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
import citywide as cw  # noqa: E402
import corridors  # noqa: E402
import osm_local  # noqa: E402
from crashiq import osm  # noqa: E402
from coverage import dms_decode  # noqa: E402

GPS = ("gps_usable", "gps_usable_dms")
V1 = DATA / "coverage_crashes_199v1.csv"


def recheck(shard: tuple[int, int], part: str, only_city: str | None, exclude: set[str]) -> None:
    src = V1 if V1.exists() else DATA / "coverage_crashes.csv"
    want: dict[str, dict[str, str]] = defaultdict(dict)
    with open(src) as f:
        for r in csv.DictReader(f):
            if r["outcome"] not in GPS and r["city"]:
                want[r["city"]][r["collision_id"]] = r["outcome"]
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    order = sorted(want, key=lambda c: -len(want[c]))
    out = open(DATA / f"coverage_gpsfix_{part}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["collision_id", "city", "old_outcome", "new_outcome"])
    dms_cache, t0, checked = {}, time.time(), 0
    for i, city in enumerate(order):
        if only_city is not None:
            if city != only_city:
                continue
        elif i % shard[1] != shard[0] or city in exclude:
            continue
        b = bounds.get(corridors.norm_city(city))
        if not b:
            continue                       # outside a city map: the GPS check there is unchanged
        ids = want[city]
        rows = [c for c in cw.mirror_rows(con, "City Name", city)
                if str(c["crash_id"]) in ids and c.get("lat") is not None and c.get("lon") is not None]
        if not rows:
            continue
        cty = cw.City(osm.Network(osm_local.network_in_area(local, b["rel"])))
        seen = set()
        for c in rows:
            cid = str(c["crash_id"])
            if cid in seen:
                continue
            seen.add(cid)
            checked += 1
            new = None
            if cty.fits(c["lat"], c["lon"], c):
                new = "gps_usable"
            else:
                ag = str(c.get("agency") or "")
                if ag not in dms_cache:
                    dms_cache[ag] = cw.dms_years(con, ag)
                if c["year"] in dms_cache[ag]:
                    la, lo = dms_decode(c["lat"]), dms_decode(c["lon"])
                    if la is not None and lo is not None and cty.fits(la, lo, c):
                        new = "gps_usable_dms"
            if new:
                w.writerow([cid, city, ids[cid], new])
        out.flush()
        print(f"[{i + 1}/{len(order)} {time.time() - t0:.0f}s] {city}: {len(seen)} with GPS ({checked} so far)", flush=True)
    out.close()
    print("EXIT: finished", flush=True)


def apply(parts: list[str]) -> None:
    fix = {}
    for p in parts:
        with open(DATA / f"coverage_gpsfix_{p}.csv") as f:
            for r in csv.DictReader(f):
                fix[(r["collision_id"], r["city"])] = r["new_outcome"]
    if not V1.exists():
        shutil.copy(DATA / "coverage_crashes.csv", V1)
    moved = Counter()
    with open(V1) as fi, open(DATA / "coverage_crashes_gpsfix.csv", "w", newline="") as fo:
        rd = csv.DictReader(fi)
        w = csv.DictWriter(fo, rd.fieldnames)
        w.writeheader()
        for r in rd:
            new = fix.get((r["collision_id"], r["city"]))
            if new:
                moved[(r["outcome"], new)] += 1
                r = {**r, "outcome": new, "reason": "", "bin": "1"}
            w.writerow(r)
    for (a, b), n in moved.most_common():
        print(f"{a} -> {b}: {n}")
    print(f"{sum(moved.values())} crashes re-classified -> {DATA / 'coverage_crashes_gpsfix.csv'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--part")
    ap.add_argument("--only-city")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--apply", nargs="*")
    a = ap.parse_args()
    if a.apply:
        apply(a.apply)
    else:
        recheck(tuple(int(x) for x in a.shard.split("/")), a.part, a.only_city, {x for x in a.exclude.split(",") if x})
