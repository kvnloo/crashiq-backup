"""County address points (#393): crashes gained and distance to police GPS, per county, like #264 for NAD.

Reads the CCRS mirror and run 11's per-crash outcomes; looks up every house-address crash of the given counties in an
address index built only from the addr_*.csv files in --addr-dir (NAD itself is not included, so the numbers are what
the county files add).

  gained = crashes run 11 left off the map (not GPS, not placed) that the county points now place
  truth  = house-address crashes whose police GPS fits their roads (run 11 outcome gps_usable*): distance from the
           address point to that GPS, the #264 bar being NAD's 86% within 400 ft / 74.5% within 250 ft

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
    a = ap.parse_args()

    outcome = {}
    for f in glob.glob(a.outcomes):
        for r in csv.DictReader(open(f, newline="")):
            outcome[r["collision_id"]] = (r["outcome"], r["killed"] != "0", r["ksi"] != "0")
    idx = nad.NadIndex(a.addr_dir / "nad_ca.sqlite", a.addr_dir / "no_nad_here.csv")   # county files only
    assert idx.ready(), f"no addr_*.csv in {a.addr_dir}"

    db = sqlite3.connect(a.mirror)
    tabs = [t for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if "Collision Id" in [c[1] for c in db.execute(f'PRAGMA table_info("{t}")')]]
    stats = defaultdict(Counter)
    dist = defaultdict(list)
    for t in tabs:
        for cid, cc, city, p, s, lat, lon in db.execute(
                f'SELECT "Collision Id", "County Code", "City Name", PrimaryRoad, SecondaryRoad, Latitude, Longitude '
                f'FROM "{t}" WHERE "County Code" IN ({",".join(map(str, COUNTIES))})'):
            ha = house_address(p, s)
            if not ha:
                continue
            name = COUNTIES[int(cc)]
            o, fatal, ksi = outcome.get(str(cid), ("?", False, False))
            st = stats[name]
            st["house_address"] += 1
            pt = idx.lookup(int(cc), city, ha[1], ha[0])
            if pt:
                st["found"] += 1
            if o.startswith("gps_usable"):
                st["truth_pool"] += 1
                if pt:
                    dist[name].append(nad.ft((pt["lat"], pt["lon"]), (float(lat), float(lon))))
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
    tot = {k: sum(v.get(k, 0) for v in out.values()) for k in ("house_address", "off_map", "gained", "gained_fatal",
                                                                "gained_ksi", "truth_pool", "truth_found")}
    alld = [x for v in dist.values() for x in v]
    tot.update(within_400ft=round(sum(x <= 400 for x in alld) / len(alld), 3) if alld else None,
               within_250ft=round(sum(x <= 250 for x in alld) / len(alld), 3) if alld else None)
    out["ALL"] = tot
    a.out.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
