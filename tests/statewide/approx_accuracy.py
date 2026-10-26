"""The approximate tier's accuracy (#258; run 10, measure only): the app's own `freeway.place` on freeway crashes whose
police GPS fits the report (run 9A gps_usable, road type freeway), GPS hidden. The same seeded 6,000-crash sample as
d1_waterfall.py --accuracy (SEED 246), so it compares with the Tester's own method (73.5% / 94.6%). Raw elements per
crash from fwy_raw.FwyRaw (lanes of the route, links within 6 hops, the reference street in the county). Right
within 400 ft, 1,000 ft, 0.25 mi, 0.5 mi (the label's band), 1 mi; by kind, Wilson 95% low bounds.

Run: python tests/statewide/approx_accuracy.py   (writes data/statewide/approx_accuracy.json)
"""

from __future__ import annotations

import csv
import json
import random
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
SAMPLE, SEED = 6000, 246
BANDS = (("400 ft", 400), ("1,000 ft", 1000), ("0.25 mi", 1320), ("0.5 mi", 2640), ("1 mi", 5280))


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import freeway
    from crashiq.osm import metres

    import citywide as cw
    import osm_local
    from bin2_whatif import wilson_low
    from coverage import Outside, districts
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
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    t = defaultdict(Counter)
    rows = []
    batch = []
    for city, want in sorted(by_city.items()):
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in want and cid not in seen and c.get("lat") is not None:
                seen.add(cid)
                batch.append(aliases_mod.apply(dict(c)))
    for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
        r = freeway.parse(c)
        raw = fr.raw(c) if r else None
        sp = freeway.place(raw, c) if raw else None
        # by what the report describes (#278: an X TO Y naming a local street is connector_local); a report the rule
        # doesn't place is counted under its parsed kind
        kind = sp.report if sp else (("connector" if r["kind"] == "connector" and r.get("from") != "street" else
                                      "connector_local" if r["kind"] == "connector" else r["kind"])
                                     if r else "not a freeway description")
        k = t[kind]
        k["sample"] += 1
        if sp is None:
            continue
        d = metres((sp.lat, sp.lon), (c["lat"], c["lon"])) * 3.28084
        k["placed"] += 1
        for lab, ft in BANDS:
            k[lab] += d <= ft
        rows.append({"collision_id": str(c["crash_id"]), "kind": sp.report, "dist_ft": round(d)})
    out = {"truth": f"run 9A freeway crashes whose police GPS fits the report, seeded sample of {SAMPLE} (seed {SEED}); "
                    "the app's freeway.place with the GPS hidden", "by_kind": {}}
    from crashiq.placement import FWY_AUTO_KINDS
    tot, auto = Counter(), Counter()
    for kind, k in sorted(t.items()):
        tot.update(k)
        if kind in FWY_AUTO_KINDS:
            auto.update(k)
        out["by_kind"][kind] = summary(k, wilson_low)
    out["all"] = summary(tot, wilson_low)
    out["auto_placed_kinds"] = sorted(FWY_AUTO_KINDS)
    out["auto"] = summary(auto, wilson_low)
    with open(DATA / "approx_accuracy_rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["collision_id", "kind", "dist_ft"])
        w.writeheader()
        w.writerows(rows)
    (DATA / "approx_accuracy.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def summary(k, wilson_low) -> dict:
    n = k["placed"]
    o = {"sample": k["sample"], "placed": n, "placed_pct": round(100 * n / k["sample"], 1) if k["sample"] else None}
    for lab, _ in BANDS:
        o[lab] = {"k": k[lab], "pct": round(100 * k[lab] / n, 1) if n else None,
                  "low": wilson_low(k[lab], n) if n else None}
    return o


if __name__ == "__main__":
    main()
