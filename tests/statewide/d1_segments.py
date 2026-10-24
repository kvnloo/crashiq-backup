"""D1 step 3 at segment level (PM 2026-10-24; measure only). For the mainline / freeway-to-freeway crashes of the
d1_waterfall.py accuracy sample (d1_accuracy_rows.csv), recompute the report's spot (GPS unused), snap it and the police
GPS to the nearest Caltrans postmile point (SHN Postmiles Tenth, 2026-10-24) of the crash's named route(s), and ask
whether both fall in the same 0.5-mile segment: same route, county, postmile prefix and floor(PM / 0.5). Snaps farther
than SNAP_FT from a postmile point count as "no snap". Also within one segment either way (adjacent segment).

Run: python tests/statewide/d1_segments.py   (writes data/statewide/d1_segments.json, d1_segments.csv)
"""

from __future__ import annotations

import csv
import json
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
LAYER = ROOT / "data" / "cache" / "postmiles" / "shn_postmiles_tenth_2026-10-24.csv"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
SNAP_FT, CELL = 1000.0, 0.01


class Snap:
    def __init__(self):
        self.grid = defaultdict(list)
        with open(LAYER) as f:
            for r in csv.DictReader(f):
                if r["lat"]:
                    la, lo = float(r["lat"]), float(r["lon"])
                    self.grid[(int(la / CELL), int(lo / CELL))].append(
                        (la, lo, r["Route"].lstrip("0"), r["County"], r["PMPrefix"], float(r["PM"])))

    def near(self, p, routes):
        from freeway_report_point import ft
        i, j = int(p[0] / CELL), int(p[1] / CELL)
        best = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for q in self.grid.get((i + di, j + dj), ()):
                    if q[2] in routes:
                        d = ft(p, q[:2])
                        if best is None or d < best[0]:
                            best = (d, q)
        return best if best and best[0] <= SNAP_FT else None


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import names

    import citywide as cw
    from bin2_whatif import wilson_low
    from freeway_report_point import Map, report_point
    with open(DATA / "d1_accuracy_rows.csv") as f:
        want = {r["collision_id"]: r for r in csv.DictReader(f) if r["kind"] in ("mainline", "f2f")}
    cov = {}
    for p in sorted(DATA.glob("coverage_crashes_r9a_*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["collision_id"] in want:
                    cov[r["collision_id"]] = r["city"]
    by_city = defaultdict(set)
    for cid, city in cov.items():
        by_city[city].add(cid)
    snap = Snap()
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    m = Map()
    rows = []
    for city, ids in sorted(by_city.items()):
        batch, seen = [], set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in ids and cid not in seen and c.get("lat") is not None:
                seen.add(cid)
                batch.append(aliases_mod.apply(dict(c)))
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
            cid = str(c["crash_id"])
            kind = want[cid]["kind"]
            pt = report_point(m, {**c, "lat": None, "lon": None}, kind).get("point")
            if not pt:
                continue
            roads = f"{c.get('primary_road') or ''} {c.get('secondary_road') or ''}".upper()
            routes = {"".join(x for x in (r if isinstance(r, str) else "".join(r)) if x.isdigit()).lstrip("0")
                      for r in names.ROUTE_ANY.findall(roads)}
            a, g = snap.near(pt, routes), snap.near((c["lat"], c["lon"]), routes)
            row = {"collision_id": cid, "kind": kind, "dist_ft": want[cid]["dist_ft"], "seg": "no snap"}
            if a and g:
                qa, qg = a[1], g[1]
                if qa[2:5] == qg[2:5]:
                    sa, sg = math.floor(qa[5] / 0.5), math.floor(qg[5] / 0.5)
                    row["seg"] = "same" if sa == sg else "adjacent" if abs(sa - sg) == 1 else "farther"
                else:
                    row["seg"] = "other route/county/prefix"
                row["pm_gap_mi"] = round(abs(qa[5] - qg[5]), 2) if qa[2:5] == qg[2:5] else ""
            rows.append(row)
        print(f"{city or '(blank)'}: {len(batch)}", flush=True)
    with open(DATA / "d1_segments.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["collision_id", "kind", "dist_ft", "seg", "pm_gap_mi"])
        w.writeheader()
        w.writerows(rows)
    res = {}
    for kind in ("mainline", "f2f", "mainline+f2f"):
        sel = [r for r in rows if r["kind"] in kind.split("+")]
        c = Counter(r["seg"] for r in sel)
        snapped = sum(v for k, v in c.items() if k != "no snap")
        res[kind] = {"n": len(sel), "segments": dict(c), "snapped": snapped,
                     "same_pct_of_snapped": round(100 * c["same"] / snapped, 1) if snapped else None,
                     "same_low": wilson_low(c["same"], snapped) if snapped else None,
                     "same_or_adjacent_pct": round(100 * (c["same"] + c["adjacent"]) / snapped, 1) if snapped else None,
                     "same_or_adjacent_low": wilson_low(c["same"] + c["adjacent"], snapped) if snapped else None}
    (DATA / "d1_segments.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
