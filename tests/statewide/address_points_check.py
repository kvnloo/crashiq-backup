"""County address points (#393): crashes gained and distance to police GPS, per county, like #264 for NAD.

Reads the CCRS mirror and run 11's per-crash outcomes; looks up every house-address crash of the given counties in an
address index built only from the addr_*.csv files in --addr-dir (NAD itself is not included, so the numbers are what
the county files add).

  gained = crashes run 11 left off the map (not GPS, not placed) that the county points now place
  truth  = house-address crashes whose police GPS fits their roads (run 11 outcome gps_usable*): distance from the
           address point to that GPS, the #264 bar being NAD's 86% within 400 ft / 74.5% within 250 ft
  snapped = the same, after moving the address point onto the named street (nearest TIGER/Line edge carrying the
           name, as the app moves it onto the corridor); setback = how far the point sat off that street
           (over 100 ft = outside the default corridor buffer, so the app dropped it before #393)

Run:  PYTHONPATH=backend python tests/statewide/address_points_check.py --addr-dir DIR --mirror data/statewide/ccrs_mirror.sqlite \
        --outcomes 'data/statewide/coverage_crashes_r11_*.csv' --out data/statewide/address_points_check.json
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from crashiq import crashes, nad
from crashiq.names import street_key

def house_address(p, s):
    """The app's own D5 reading (crashes.house_address), with the address's street standing in for the corridor:
    a house number on one field, the other blank, a placeholder (NOT STATED) or the same street. Private property
    stays out (#94), as in the app."""
    roads = [p, s]
    for i, rd in enumerate(roads):
        m = crashes._HOUSE.match(crashes.re.sub(r"\(.*?\)", " ", str(rd or "")).strip())
        k = street_key(m.group(2) if m and m.group(1) else m.group(3) if m else None)
        if k and (ha := crashes.house_address(roads, [i], [k])):
            return street_key(ha["street"]), ha["number"]
    return None


COUNTIES = {19: "Los Angeles", 30: "Orange", 33: "Riverside", 39: "San Joaquin", 10: "Fresno", 37: "San Diego"}
# the NAD counties, for the same check on NAD itself (--counties nad, with nad_ca_r24.csv linked as addr_nad.csv)
NAD_COUNTIES = {36: "San Bernardino", 34: "Sacramento", 56: "Ventura", 48: "Solano", 44: "Santa Cruz", 24: "Merced",
                45: "Shasta", 42: "Santa Barbara"}


def _foot(pt, edges):
    """Nearest point to pt on any of the edges (lists of (lat, lon)), and its distance in feet."""
    best = None
    kx = 364000 * math.cos(math.radians(pt[0]))
    for pts in edges:
        for (a, b) in zip(pts, pts[1:]):
            ax, ay, bx, by = (a[1] - pt[1]) * kx, (a[0] - pt[0]) * 364000, (b[1] - pt[1]) * kx, (b[0] - pt[0]) * 364000
            dx, dy = bx - ax, by - ay
            t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
            fx, fy = ax + t * dx, ay + t * dy
            d = math.hypot(fx, fy)
            if best is None or d < best[0]:
                best = (d, (pt[0] + fy / 364000, pt[1] + fx / kx))
    return best


def snap(tiger: sqlite3.Connection, k, pt):
    """pt moved onto the nearest TIGER edge named like street k within ~1,800 ft, with the setback; or None."""
    from crashiq.names import same_core
    r = 0.005
    edges = [json.loads(p) for names, p in tiger.execute(
        "SELECT names, pts FROM edge WHERE minlat <= ? AND maxlat >= ? AND minlon <= ? AND maxlon >= ?",
        (pt[0] + r, pt[0] - r, pt[1] + r, pt[1] - r))
        if any((nk := street_key(n)) and same_core(k, nk) for n in json.loads(names))]
    return _foot(pt, edges) if edges else None


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--addr-dir", type=Path, required=True)
    ap.add_argument("--mirror", type=Path, required=True)
    ap.add_argument("--outcomes", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--counties", choices=("gaps", "nad"), default="gaps")
    ap.add_argument("--tiger", type=Path, help="TIGER/Line county SQLite dir (data/cache/tiger/2026)")
    a = ap.parse_args()
    global COUNTIES
    if a.counties == "nad":
        COUNTIES = NAD_COUNTIES

    outcome = {}
    for f in glob.glob(a.outcomes):
        for r in csv.DictReader(open(f, newline="")):
            outcome[r["collision_id"]] = (r["outcome"], r["killed"] != "0", r["ksi"] != "0")
    idx = nad.NadIndex(a.addr_dir / "nad_ca.sqlite", a.addr_dir / "no_nad_here.csv")   # county files only
    assert idx.ready(), f"no addr_*.csv in {a.addr_dir}"

    db = sqlite3.connect(a.mirror)
    tigers = {c: sqlite3.connect(a.tiger / f"{2 * c - 1:03d}.sqlite") for c in COUNTIES
              if a.tiger and (a.tiger / f"{2 * c - 1:03d}.sqlite").exists()}
    tabs = [t for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if "Collision Id" in [c[1] for c in db.execute(f'PRAGMA table_info("{t}")')]]
    stats = defaultdict(Counter)
    dist = defaultdict(list)
    sdist, setback = defaultdict(list), defaultdict(list)
    for t in tabs:
        for cid, cc, city, p, s, lat, lon in db.execute(
                f'SELECT "Collision Id", "County Code", "City Name", PrimaryRoad, SecondaryRoad, Latitude, Longitude '
                f'FROM "{t}" WHERE "County Code" IN ({",".join(map(str, COUNTIES))})'):
            ha = house_address(p, s)
            if not ha:
                continue
            name = COUNTIES[int(cc)]
            tg = tigers.get(int(cc))
            o, fatal, ksi = outcome.get(str(cid), ("?", False, False))
            st = stats[name]
            st["house_address"] += 1
            pt = idx.lookup(int(cc), city, ha[1], ha[0])
            if pt:
                st["found"] += 1
            if o.startswith("gps_usable"):
                st["truth_pool"] += 1
                if pt:
                    gps = (float(lat), float(lon))
                    dist[name].append(nad.ft((pt["lat"], pt["lon"]), gps))
                    sn = snap(tg, ha[0], (pt["lat"], pt["lon"])) if tg else None
                    if sn:
                        setback[name].append(sn[0])
                        sdist[name].append(nad.ft(sn[1], gps))
            elif not o.startswith("placed") and o != "?":
                st["off_map"] += 1
                if pt:
                    st["gained"] += 1
                    st["gained_fatal"] += fatal
                    st["gained_ksi"] += ksi
    out = {}
    for name in COUNTIES.values():
        d, st = dist[name], stats[name]
        w4, w2 = sum(x <= 400 for x in d), sum(x <= 250 for x in d)
        out[name] = {**st, "truth_found": len(d),
                     "within_400ft": round(w4 / len(d), 3) if d else None, "within_400ft_low": round(wilson_low(w4, len(d)), 3),
                     "within_250ft": round(w2 / len(d), 3) if d else None, "within_250ft_low": round(wilson_low(w2, len(d)), 3),
                     "median_ft": round(sorted(d)[len(d) // 2]) if d else None}
        sd, sb = sdist[name], setback[name]
        if sd:
            k4, k2 = sum(x <= 400 for x in sd), sum(x <= 250 for x in sd)
            out[name].update(snapped_n=len(sd), snapped_within_400ft=round(k4 / len(sd), 3),
                             snapped_within_400ft_low=round(wilson_low(k4, len(sd)), 3),
                             snapped_within_250ft=round(k2 / len(sd), 3),
                             snapped_within_250ft_low=round(wilson_low(k2, len(sd)), 3),
                             setback_median_ft=round(sorted(sb)[len(sb) // 2]),
                             setback_over_100ft=round(sum(x > 100 for x in sb) / len(sb), 3))
    tot = {k: sum(v.get(k, 0) for v in out.values()) for k in ("house_address", "off_map", "gained", "gained_fatal",
                                                                "gained_ksi", "truth_pool", "truth_found")}
    alld = [x for v in dist.values() for x in v]
    alls = [x for v in sdist.values() for x in v]
    if alls:
        tot.update(snapped_within_400ft=round(sum(x <= 400 for x in alls) / len(alls), 3),
                   snapped_within_250ft=round(sum(x <= 250 for x in alls) / len(alls), 3))
    tot.update(within_400ft=round(sum(x <= 400 for x in alld) / len(alld), 3) if alld else None,
               within_250ft=round(sum(x <= 250 for x in alld) / len(alld), 3) if alld else None)
    out["ALL"] = tot
    a.out.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
