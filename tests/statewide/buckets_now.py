"""D1-D9 recount on the current basis (PM 2026-10-26; measure only): run 10's per-crash files with the freeway step on
main (#278, #281: coverage_crashes_r10d_*), read as the app does (an approximate spot for a crash whose GPS is off its
roads isn't used). Each crash still difficult keeps its run-9A bucket (buckets.csv, the same rules); a crash difficult
now but not in 9A's difficult bin is "newly difficult". D1 is split into: the report spot found but GPS off its roads
(not in the app: the officer's GPS is kept), true connectors whose spot is held for review (re-placed here with the
app's freeway.place to know which), and the rest.

Run: python tests/statewide/buckets_now.py   (writes data/statewide/buckets_now.json, buckets_now.csv)
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
LABEL = {"D1": "freeway / ramp reference", "D2": "no cross street", "D3": "street missing from the map",
         "D4": "near-miss streets", "D5": "house number as location", "D6": "named streets don't cross",
         "D7": "spelling held", "D8": "meet in more than one place", "D9": "no street map"}


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import freeway
    from crashiq.placement import FWY_AUTO_KINDS

    import citywide as cw
    import osm_local
    from coverage import Outside, districts
    from fwy_raw import FwyRaw
    from run9_reconcile import parts
    with open(DATA / "buckets.csv") as f:
        b9 = {r["collision_id"]: r["bucket"] for r in csv.DictReader(f)}
    a9, now = parts("r9a"), parts("r10d")
    diff = {}
    for cid, r in now.items():
        nia = r["outcome"] == "placed_approximate" and r["approx"].startswith("gps_off_roads")
        if r["bin"] == "2" or nia:
            diff[cid] = {"bucket": b9.get(cid, "newly difficult"), "nia": nia, "r": r}
    # true connectors among D1 still difficult: re-place them to find the held spots
    cands = {cid for cid, d in diff.items() if d["bucket"] == "D1" and not d["nia"]}
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
    by_city = defaultdict(set)
    for cid in cands:
        by_city[now[cid]["city"]].add(cid)
    held = set()
    for city, ids in by_city.items():
        batch, seen = [], set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in ids and cid not in seen:
                seen.add(cid)
                c = aliases_mod.apply(dict(c))
                r = freeway.parse(c)
                if r and r["kind"] == "connector" and r.get("from") != "street":
                    batch.append(c)
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
            raw = fr.raw(c)
            sp = freeway.place(raw, c) if raw else None
            if sp is not None and sp.report not in FWY_AUTO_KINDS:
                held.add(str(c["crash_id"]))
    t = defaultdict(Counter)
    rows = []
    for cid, d in diff.items():
        r = d["r"]
        b = d["bucket"]
        sub = ("GPS off its roads, report spot found (not in the app)" if d["nia"] else
               "true connector, spot held for review" if cid in held else "") if b == "D1" else ""
        for k in (b, f"{b}: {sub}") if sub else (b,):
            t[k]["now"] += 1
            t[k]["fatal"] += r["killed"] == "1"
            t[k]["ksi"] += r["ksi"] == "1"
        rows.append({"collision_id": cid, "bucket": b, "d1_split": sub, "killed": r["killed"], "ksi": r["ksi"]})
    for cid, b in b9.items():
        t[b]["in_9a"] += 1
        t[b]["fatal_9a"] += a9[cid]["killed"] == "1"
        t[b]["ksi_9a"] += a9[cid]["ksi"] == "1"
    out = {}
    for k in sorted(t, key=lambda k: (k[:2] if k.startswith("D") else "Z", k)):
        v = t[k]
        out[k] = {"label": LABEL.get(k[:2], k), **dict(v)}
        if "in_9a" in v:
            out[k]["change"] = v["now"] - v["in_9a"]
    out["total"] = {"now": len(diff), "in_9a": len(b9), "change": len(diff) - len(b9),
                    "fatal": sum(r["r"]["killed"] == "1" for r in diff.values()),
                    "ksi": sum(r["r"]["ksi"] == "1" for r in diff.values())}
    with open(DATA / "buckets_now.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (DATA / "buckets_now.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
