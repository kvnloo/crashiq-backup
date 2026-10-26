"""#287: Engineering's join (PR #289, crashiq.aadt.AadtCache.for_crash) on the same SHS crashes as aadt_match.py,
crash by crash. The cache is built from the Tester's copies of the same Caltrans workbooks (get reads them by file name,
no download). The crash's count year comes from its date (October-September). Compared: matched or not, and AADT.

Run: python tests/statewide/aadt_compare_289.py <path to the #289 backend>   (writes data/statewide/aadt_compare_289.json)
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
TC = ROOT / "data" / "cache" / "traffic_census" / "2026-10-26" / "xlsx"
sys.path.insert(0, sys.argv[1])
sys.path.insert(1, str(HERE))


def main() -> None:
    from crashiq import aadt

    import citywide as cw
    assert Path(aadt.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve()), aadt.__file__
    folder = DATA / "aadt289"
    cache = aadt.AadtCache(folder, get=lambda url: (TC / url.rsplit("/", 1)[1]).read_bytes(), background=False)
    cache.ready()
    rows = [r for r in csv.DictReader(open(DATA / "aadt_match.csv")) if r["pm"] != ""]
    want = defaultdict(dict)
    for r in rows:
        want[r["collision_id"]] = r
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    dates = {}
    for rid, _ in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'").fetchall():
        for cid, dt in con.execute(f'SELECT "Collision Id", "Crash Date Time" FROM "{rid}"'):
            if cid is not None and str(int(cid)) in want:
                dates[str(int(cid))] = dt
    t, diff = Counter(), Counter()
    for cid, r in want.items():
        p = {"route": r["route"], "county": r["county"], "pm": float(r["pm"]), "route_suffix": "", "suffix": ""}
        s = cache.for_crash({"postmile": p, "reported_at": dates.get(cid)})
        mine = r["status"] == "segment AADT"
        t[f"tester {'yes' if mine else 'no'} / #289 {'yes' if s else 'no'}"] += 1
        if s and mine:
            a, b = float(r["aadt"]), float(s["aadt"])
            diff["same AADT" if a == b else "within 10%" if abs(a - b) <= 0.1 * max(a, b) else "differs > 10%"] += 1
            t["#289 latest-year fallback"] += bool(s["latest_used"])
            t["#289 prefix change on segment"] += bool(s["prefix_change"])
    res = {"crashes_with_postmile": len(want), "match": dict(t), "aadt_when_both": dict(diff)}
    (DATA / "aadt_compare_289.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    _ = cw


if __name__ == "__main__":
    main()
