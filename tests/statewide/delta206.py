"""#206 per-city delta: which exact placements of the #199 coverage run (app code 5f54c02) differ at a later commit.

#204 (unique-pair tier, gate off) and #206 (a stated trailing direction must match, every tier) can only change the
locator's answer for a crash whose primary or secondary road writes a trailing direction (20TH ST W). So the
candidates are the #199 crashes the locator ran on (not placed by police GPS) with a trailing direction on either road,
and each is placed twice, once per backend, in separate processes:

  python tests/statewide/delta206.py --backend <main checkout>/backend --tag main     (also writes the candidate list)
  python tests/statewide/delta206.py --backend backend --tag base --ids data/statewide/delta206_main.csv
  python tests/statewide/delta206.py --compare base main

Writes data/statewide/delta206_<tag>.csv (collision_id, city, tier, auto, node) and delta206.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
PARTS = ["part0", "s0b", "s1", "s2", "s3", "sd0", "sd1", "sd2", "blank"]
LOCATOR_RAN = {"placed_exact", "placed_fars", "review", "cant_place"}


def _ran() -> dict[str, str]:
    """collision_id -> city name, for every #199 crash the locator ran on."""
    out = {}
    for p in PARTS:
        with open(DATA / f"coverage_crashes_{p}.csv") as f:
            for r in csv.DictReader(f):
                if r["outcome"] in LOCATOR_RAN:
                    out[r["collision_id"]] = r["city"]
    return out


def place(backend: Path, tag: str, ids_file: Path | None) -> None:
    sys.path.insert(0, str(backend.resolve()))
    from crashiq import locate, names, osm  # noqa: F401  (cached before coverage.py adds the worktree's backend)
    assert Path(locate.__file__).resolve().is_relative_to(backend.resolve()), locate.__file__
    sys.path.insert(1, str(HERE))
    import citywide as cw
    import corridors
    import osm_local
    import sqlite3
    from coverage import Outside, districts
    if ids_file:
        with open(ids_file) as f:
            want = {r["collision_id"]: r["city"] for r in csv.DictReader(f)}
    else:
        want = None
        ran = _ran()
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    _, cname = districts()
    county_box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            county_box[code] = r
    outside = Outside(local, county_box)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    gate = locate.Gate()
    trail = lambda road: names.directions(road)[1] if hasattr(names, "directions") else None  # noqa: E731
    by_city = defaultdict(list)
    if want is not None:
        for cid, city in want.items():
            by_city[city].append(cid)
    else:
        for cid, city in ran.items():
            by_city[city].append(cid)
    out = open(DATA / f"delta206_{tag}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["collision_id", "city", "tier", "auto", "node"])
    n_done = 0
    for city_name, cids in sorted(by_city.items(), key=lambda kv: -len(kv[1])):
        cids = set(cids)
        rows = [c for c in cw.mirror_rows(con, "City Name", city_name) if str(c["crash_id"]) in cids]
        if want is None:
            rows = [c for c in rows if trail(c.get("primary_road")) or trail(c.get("secondary_road"))]
        if not rows:
            continue
        b = bounds.get(corridors.norm_city(city_name)) if city_name else None
        cw._fuzzy_memo.clear()
        net = osm.Network(osm_local.network_in_area(local, b["rel"])) if b else None
        for c in rows:
            n_ = net if net is not None else outside.network(c)
            pl = locate.place(n_, c) if n_ is not None else locate.Placement("review", note="no street map")
            w.writerow([c["crash_id"], city_name, pl.tier, int(gate.auto(pl)), pl.node or ""])
        n_done += len(rows)
        out.flush()
        print(f"{city_name or '(blank)'}: {len(rows)} candidates ({n_done} so far)", flush=True)
    out.close()
    print("EXIT: finished", flush=True)


def compare(a: str, b: str) -> None:
    def load(t):
        with open(DATA / f"delta206_{t}.csv") as f:
            return {r["collision_id"]: r for r in csv.DictReader(f)}
    base, new = load(a), load(b)
    assert set(base) == set(new), "candidate lists differ"
    per = defaultdict(Counter)
    for cid, r0 in base.items():
        r1 = new[cid]
        c = per[r0["city"] or "(blank)"]
        c["candidates"] += 1
        e0, e1 = r0["auto"] == "1", r1["auto"] == "1"
        c["exact_before"] += e0
        c["exact_after"] += e1
        if e0 and not e1:
            c["lost"] += 1
        elif e1 and not e0:
            c["gained"] += 1
        elif e0 and e1 and r0["node"] != r1["node"]:
            c["moved"] += 1
        if r1["tier"] == "unique_pair":
            c["unique_pair_held"] += 1
    rows = [{"city": k, **{f: v.get(f, 0) for f in ("candidates", "exact_before", "exact_after", "lost", "gained",
                                                    "moved", "unique_pair_held")}} for k, v in per.items()]
    rows.sort(key=lambda r: -(r["lost"] + r["gained"] + r["moved"]))
    tot = {f: sum(r[f] for r in rows) for f in rows[0] if f != "city"}
    (DATA / "delta206.json").write_text(json.dumps({"base": a, "new": b, "total": tot, "cities": rows}, indent=1))
    print(json.dumps(tot))
    for r in rows:
        if r["lost"] + r["gained"] + r["moved"]:
            print(r)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", type=Path)
    ap.add_argument("--tag")
    ap.add_argument("--ids", type=Path)
    ap.add_argument("--compare", nargs=2)
    a = ap.parse_args()
    if a.compare:
        compare(*a.compare)
    else:
        place(a.backend, a.tag, a.ids)
