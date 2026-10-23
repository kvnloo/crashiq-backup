"""Run 8 (PM 2026-10-22): isolate #212 from the run-8 coverage. #212 (leading AVE/AV/ST/MT/FT/BL) can only change the
locator's answer for a crash whose primary or secondary road starts with one of those words, so those crashes are
placed again on the code before #212 (--backend <checkout of e2f1633>/backend), on the same box + 1 km network, and the
answer (tier, node) is written for comparison with the run-8 per-crash file (whose tiers are on current main).

Run: python tests/statewide/run8_isolate.py --backend <pre-#212 checkout>/backend --part pre212
Writes data/statewide/run8_<part>.csv (collision_id, city, tier, node).
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
LEADING = re.compile(r"^\s*(AVE|AV|ST|MT|FT|BL|BLVD)\.?\s+(?!OF\b)[A-Z0-9]", re.I)


def main(backend: Path, part: str) -> None:
    sys.path.insert(0, str(backend.resolve()))
    from crashiq import locate, osm
    assert Path(locate.__file__).resolve().is_relative_to(backend.resolve()), locate.__file__
    sys.path.insert(1, str(HERE))
    import citywide as cw
    import corridors
    import osm_local
    from coverage import Outside, districts

    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    _, cname = districts()
    box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            box[code] = r
    outside = Outside(local, box)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    by_city = defaultdict(set)
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes'").fetchall():
        for cid, city, p, s in con.execute(f'SELECT "Collision Id", "City Name", "PrimaryRoad", "SecondaryRoad" FROM "{rid}"'):
            if cid is not None and (LEADING.match(p or "") or LEADING.match(s or "")):
                by_city[city or ""].add(str(int(cid)))
    out = open(DATA / f"run8_{part}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["collision_id", "city", "tier", "node"])
    for city, ids in sorted(by_city.items(), key=lambda kv: -len(kv[1])):
        b = bounds.get(corridors.norm_city(city)) if city else None
        cw._fuzzy_memo.clear()
        net = osm.Network(osm_local.network_in_box(local, b["rel"])) if b else None
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in ids or cid in seen:
                continue
            seen.add(cid)
            n_ = net if net is not None else outside.network(c)
            pl = locate.place(n_, c) if n_ is not None else locate.Placement("review", note="no street map")
            w.writerow([cid, city, pl.tier, pl.node or ""])
        out.flush()
        print(f"{city or '(blank)'}: {len(seen)}", flush=True)
    out.close()
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", type=Path, required=True)
    ap.add_argument("--part", required=True)
    a = ap.parse_args()
    main(a.backend, a.part)
