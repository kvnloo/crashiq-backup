"""Companion to gps_repair.py: difficult crashes (run 9A) whose CCRS record has coordinates the crash reader drops as
outside California (a lost minus, swapped latitude / longitude, ...), so they count as "no GPS". The same repairs and
the same matched control are tried on the raw values; a repaired point must fit the report (Outside.fits).

Run: python tests/statewide/gps_repair_raw.py   (writes data/statewide/gps_repair_raw.json)
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
from gps_repair import CA, repairs  # noqa: E402


def main() -> None:
    import osm_local
    from coverage import Outside, districts, dms_decode
    with open(DATA / "buckets.csv") as f:
        b2 = {r["collision_id"]: r for r in csv.DictReader(f)}
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    raw = {}
    cols = ["Collision Id", "Report Version", "Latitude", "Longitude", "PrimaryRoad", "SecondaryRoad",
            "SecondaryDistance", "SecondaryUnitOfMeasure", "NCIC Code", "County Code"]
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes'").fetchall():
        for row in con.execute(f'SELECT {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{rid}"'):
            r = dict(zip(cols, row))
            if r["Collision Id"] is None:
                continue
            cid = str(int(r["Collision Id"]))
            if cid not in b2 or (cid in raw and (raw[cid]["Report Version"] or 0) >= (r["Report Version"] or 0)):
                continue
            raw[cid] = r
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    _, cname = districts()
    box = {}
    for code, name in cname.items():
        x = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if x:
            box[code] = x
    outside = Outside(local, box)
    out = Counter()
    kinds, kinds_cty = Counter(), Counter()
    rot_t, rot_f, rep_t, rep_f = Counter(), Counter(), Counter(), Counter()
    by_bucket = Counter()
    per = []
    for cid, r in raw.items():
        la, lo = r["Latitude"], r["Longitude"]
        if not isinstance(la, (int, float)) or not isinstance(lo, (int, float)) or (la == 0 and lo == 0):
            continue
        if CA[0] <= la <= CA[2] and CA[1] <= lo <= CA[3]:
            continue                                   # inside California: gps_repair.py's case
        out["outside_california"] += 1
        try:
            off = float(r["SecondaryDistance"] or 0)
        except ValueError:
            off = 0.0
        unit = str(r["SecondaryUnitOfMeasure"] or "").upper()
        c = {"primary_road": r["PrimaryRoad"], "secondary_road": r["SecondaryRoad"],
             "offset_ft": off * 5280 if unit.startswith("M") and off < 50 else off}
        reps = repairs(la, lo, dms_decode)
        fit = [k for k, p in reps.items() if outside.fits(p[0], p[1], c)]
        for k, p in reps.items():
            rep_t[k] += 1
            rep_f[k] += k in fit
            dy, dx = p[0] - la, p[1] - lo
            for q in ((p[0], lo - dx) if dx else (la - dy, lo),):      # mirror image of the repair: same size, wrong way
                if CA[0] <= q[0] <= CA[2] and CA[1] <= q[1] <= CA[3]:
                    rot_t[k] += 1
                    rot_f[k] += outside.fits(q[0], q[1], c)
        if len(fit) == 1:
            out["unique_repair"] += 1
            kinds[fit[0]] += 1
            by_bucket[b2[cid]["bucket"]] += 1
            cb = box.get(int(r["County Code"] or 0))
            p = reps[fit[0]]
            inc = bool(cb and cb[0] <= p[0] <= cb[2] and cb[1] <= p[1] <= cb[3])
            if inc:
                out["unique_repair_in_own_county"] += 1
                kinds_cty[fit[0]] += 1
            per.append({"collision_id": cid, "bucket": b2[cid]["bucket"], "unique_repair": fit[0],
                        "in_own_county": int(inc)})
        elif len(fit) > 1:
            out["more_than_one_repair_fits"] += 1
    res = {**out, "by_repair": dict(kinds), "by_repair_in_own_county": dict(kinds_cty), "by_bucket": dict(by_bucket),
           "repair_fit_rate": {k: round(rep_f[k] / rep_t[k], 4) for k in rep_t if rep_t[k]},
           "control_fit_rate": {k: round(rot_f[k] / rot_t[k], 4) for k in rot_t if rot_t[k]}}
    (DATA / "gps_repair_raw.json").write_text(json.dumps(res, indent=1))
    with open(DATA / "gps_repair_raw.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["collision_id", "bucket", "unique_repair", "in_own_county"])
        w.writeheader()
        w.writerows(per)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
