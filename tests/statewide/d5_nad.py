"""#264 source 3: USDOT National Address Database r24 (public domain; downloaded 2026-10-25, user-approved),
California rows (data/cache/nad/nad_ca_r24.csv, filtered locally from the national text file). For each pool crash:
the address points of its county with the same house number on the crash's street (d5_common.same_street against
StNam_Full, and against the bare St_Name when StNam_Full doesn't match), one place within the city box + 1 km (or the
county). County coverage (points per county) is reported separately from the summary file.

Run: python tests/statewide/d5_nad.py   (writes data/statewide/d5_result_nad.csv, d5_nad_coverage.json)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
SRC = ROOT / "data" / "cache" / "nad" / "nad_ca_r24.csv"


def main() -> None:
    import d5_common as dc
    from coverage import districts
    _, cname = districts()
    code_of = {v.upper(): k for k, v in cname.items()}
    rows = dc.pools()
    want = defaultdict(set)                       # (county, number) wanted, to keep memory small
    for r in rows:
        want[int(r["county_code"] or 0)].add(int(r["number"]))
    idx = defaultdict(list)                       # (county, number, street key) -> [(lat, lon, full, bare)]
    per_county = defaultdict(int)
    with open(SRC) as f:
        for p in csv.DictReader(f):
            cty = code_of.get((p["County"] or "").upper().replace(" COUNTY", "").strip(), 0)
            per_county[cname.get(cty, p["County"] or "(blank)")] += 1
            try:
                n = int(p["Add_Number"])
                lat, lon = float(p["Latitude"]), float(p["Longitude"])
            except ValueError:
                continue
            if n not in want.get(cty, ()):
                continue
            for k in dc.keys(p["StNam_Full"]) | dc.keys(p["St_Name"]):
                idx[(cty, n, k)].append((lat, lon, p["StNam_Full"], p["St_Name"]))
    boxes = dc.city_boxes({r["city"] for r in rows})
    out = []
    for r in rows:
        cty, n = int(r["county_code"] or 0), int(r["number"])
        cand, seen = [], set()
        for k in dc.keys(r["street"]):
            for q in idx.get((cty, n, k), ()):
                if id(q) not in seen and (dc.same_street(r["street"], q[2]) or dc.same_street(r["street"], q[3])):
                    seen.add(id(q))
                    cand.append(q[:2])
        spot, note = dc.one_place(cand, boxes.get(r["city"]))
        out.append({"collision_id": r["collision_id"], "pool": r["pool"], "district": r["district"],
                    "placed": int(spot is not None), "lat": f"{spot[0]:.6f}" if spot else "",
                    "lon": f"{spot[1]:.6f}" if spot else "", "note": note})
    dc.write("nad", out)
    (dc.DATA / "d5_nad_coverage.json").write_text(json.dumps(dict(sorted(per_county.items(),
                                                                          key=lambda kv: -kv[1])), indent=1))
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
