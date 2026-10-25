"""Opposite-side misses and the direction of travel (PM 2026-10-23; measure only). For D1 mainline crashes of the step-3
accuracy sample with a direction of travel in the freeway's name (N/B, SB, EASTBOUND, WESTBOUND ...):
  report side  downstream when the stated direction runs with the travel direction, else upstream (before the crossing)
  GPS side     downstream when the police GPS lies past the crossing in the travel direction (its position along the
               travel bearing from the crossing is positive), else upstream
for the 208 class-(i) misses (d1_misses.csv) and, as the baseline, a seeded sample of HITS_N hits (the report's spot
within 400 ft of the GPS; crossing recomputed). If (i) is lopsided "report upstream, GPS downstream", the GPS may mark
where vehicles or the patrol car stopped, not the impact point. By agency.

Run: python tests/statewide/d1_travel.py   (writes data/statewide/d1_travel.json)
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
HITS_N, SEED = 1000, 4
TRAVEL = re.compile(r"\b(N|S|E|W)\s*/?\s*B\b|\b(NORTH|SOUTH|EAST|WEST)\s*BOUND\b|\b(NORTH|SOUTH|EAST|WEST)BOUND\b")
COMPASS = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}


def travel(text: str) -> float | None:
    m = TRAVEL.search(text.upper())
    if not m:
        return None
    w = next(g for g in m.groups() if g)
    return COMPASS[w[0]]


def along(cross, p, brg) -> float:
    """Signed distance (ft) of p from cross along bearing brg."""
    dy = (p[0] - cross[0]) * 364000
    dx = (p[1] - cross[1]) * 364000 * math.cos(math.radians(cross[0]))
    return dy * math.cos(math.radians(brg)) + dx * math.sin(math.radians(brg))


def sides(t, stated, cross, gps):
    from freeway_report_point import turn
    rep = "downstream" if turn(COMPASS[stated], t) < 90 else "upstream"
    g = "downstream" if along(cross, gps, t) > 0 else "upstream"
    return rep, g


def main() -> None:
    from crashiq import aliases as aliases_mod

    import citywide as cw
    from freeway_report_point import Map, report_point
    pairs = defaultdict(Counter)
    by_ag = defaultdict(Counter)
    with open(DATA / "d1_misses.csv") as f:
        for r in csv.DictReader(f):
            if r["cls"] != "i":
                continue
            t = travel(f"{r['primary']} {r['secondary']}")
            if t is None or r["dir"] not in COMPASS:
                pairs["class i"]["no travel direction"] += 1
                continue
            cross = tuple(map(float, r["crossing"].split(",")))
            gps = tuple(map(float, r["gps"].split(",")))
            rep, g = sides(t, r["dir"], cross, gps)
            pairs["class i"][f"report {rep}, GPS {g}"] += 1
            by_ag[r["agency"]][f"report {rep}, GPS {g}"] += 1
    with open(DATA / "d1_accuracy_rows.csv") as f:
        hits = [r["collision_id"] for r in csv.DictReader(f) if r["kind"] == "mainline" and int(r["dist_ft"]) <= 400
                and int(r["offset_ft"]) > 0]
    hits.sort(key=int)
    pick = set(random.Random(SEED).sample(hits, min(HITS_N, len(hits))))
    cov = {}
    for p in sorted(DATA.glob("coverage_crashes_r9a_*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["collision_id"] in pick:
                    cov[r["collision_id"]] = r["city"]
    by_city = defaultdict(set)
    for cid, city in cov.items():
        by_city[city].add(cid)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    m = Map()
    hit_ag = defaultdict(Counter)
    for city, ids in sorted(by_city.items()):
        batch, seen = [], set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in ids and cid not in seen and c.get("lat") is not None:
                seen.add(cid)
                batch.append(aliases_mod.apply(dict(c)))
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
            t = travel(f"{c.get('primary_road') or ''} {c.get('secondary_road') or ''}")
            d = str(c.get("offset_dir") or "").strip()[:1].upper()
            if t is None or d not in COMPASS:
                pairs["hits"]["no travel direction"] += 1
                continue
            cross = report_point(m, {**c, "lat": None, "lon": None, "offset_ft": 0}, "mainline").get("point")
            if not cross:
                continue
            rep, g = sides(t, d, cross, (c["lat"], c["lon"]))
            pairs["hits"][f"report {rep}, GPS {g}"] += 1
            hit_ag[c.get("agency")][f"report {rep}, GPS {g}"] += 1
        print(f"{city}: {len(batch)}", flush=True)
    res = {"class_i_misses": dict(pairs["class i"]), "hits_sample": dict(pairs["hits"]),
           "class_i_by_agency": {a: dict(v) for a, v in sorted(by_ag.items(), key=lambda kv: -sum(kv[1].values()))[:10]},
           "hits_by_agency": {a: dict(hit_ag[a]) for a in list(dict(sorted(by_ag.items(), key=lambda kv:
                                                                              -sum(kv[1].values()))[:10]))}}
    (DATA / "d1_travel.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
