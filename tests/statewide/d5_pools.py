"""#264 step 1 (measure only): the two crash pools for the address-source comparison, with each crash's address.

  d5     the D5 bucket ("house number as location", run 9A buckets.csv) still in the difficult bin in run 10b: a road
         field carrying a house number (BROADWAY 7346, 7346 BROADWAY) that the map doesn't have as a street
  truth  crashes of the same kind whose police GPS fits the report (run 10b gps_usable, city street or county road):
         a road field carrying a house number, by the same rule as buckets.py; seeded sample of TRUTH_N. The GPS is
         the hidden truth (it lies within 400 ft + offset of a road the report names)
Address = house number + street (the field), city (the crash's city; blank outside cities) and county. Both pools are
written to data/statewide/d5_pools.csv (local only; the address strings alone may go to the Census Geocoder).

Run: python tests/statewide/d5_pools.py
"""

from __future__ import annotations

import csv
import random
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
TRUTH_N, SEED = 10000, 264
LEAD = re.compile(r"^(\d{2,6})\s+([A-Z].*)$")
TRAIL = re.compile(r"^(.*[A-Z.])\s*(\d{2,6})$")


def address(raw: str):
    """(house number, street) from a road field carrying one, by buckets.py's rule, or None."""
    from buckets import HOUSE_NO, NUMBERED
    s = re.sub(r"\s+", " ", re.sub(r"[.,#'\"]", " ", (raw or "").upper())).strip()      # buckets.py's norm
    if not s or not HOUSE_NO.search(s) or re.search(r"\d+(ST|ND|RD|TH)$", s) or NUMBERED.match(s):
        return None
    m = LEAD.match(s)
    if m:
        return int(m.group(1)), m.group(2).strip()
    m = TRAIL.match(s)
    if m:
        return int(m.group(2)), m.group(1).strip()
    return None


def main() -> None:
    from crashiq import aliases as aliases_mod

    import citywide as cw
    from coverage import districts
    from run9_reconcile import parts
    _, cname = districts()
    r10 = parts("r10b")
    with open(DATA / "buckets.csv") as f:
        d5 = {r["collision_id"] for r in csv.DictReader(f) if r["bucket"] == "D5"}
    d5 = {cid for cid in d5 if r10.get(cid, {}).get("bin") == "2"}
    truth_c = {cid for cid, r in r10.items() if r["outcome"] == "gps_usable"
               and r["road_type"] in ("city street", "county road (outside cities)")}
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    cities = sorted({r["city"] for r in r10.values()})
    rows, truth_rows = [], []
    for city in cities:
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in seen or (cid not in d5 and cid not in truth_c):
                continue
            seen.add(cid)
            c = aliases_mod.apply(dict(c))
            for fld in ("primary_road", "secondary_road"):
                a = address(c.get(fld) or "")
                if a:
                    break
            if not a:
                continue
            county = int(c.get("county_code") or 0)
            r = r10[cid]
            row = {"collision_id": cid, "pool": "d5" if cid in d5 else "truth", "district": r["district"],
                   "county_code": county, "county": cname.get(county, ""), "city": city, "number": a[0],
                   "street": a[1], "other_road": c.get("secondary_road" if fld == "primary_road" else "primary_road"),
                   "gps": f"{c['lat']:.6f},{c['lon']:.6f}" if cid in truth_c and c.get("lat") is not None else ""}
            (rows if cid in d5 else truth_rows).append(row)
        print(f"{city or '(blank)'}: {len(rows)} d5, {len(truth_rows)} truth candidates", flush=True)
    truth_rows.sort(key=lambda r: int(r["collision_id"]))
    truth = random.Random(SEED).sample(truth_rows, min(TRUTH_N, len(truth_rows)))
    with open(DATA / "d5_pools.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows + truth)
    print(f"d5 {len(rows)} (of {len(d5)} D5 still difficult); truth sample {len(truth)} of {len(truth_rows)}")
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
