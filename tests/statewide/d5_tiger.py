"""#264 source 2: TIGER/Line 2026 ADDRFEAT address ranges, local (data/cache/tiger_addrfeat/2026, downloaded
2026-10-25, user-approved). For each pool crash: the segments of its county whose FULLNAME is the crash's street
(d5_common.same_street) and whose left or right range holds the house number (parity O / E / B respected); the point
is interpolated along the segment from the range's FROM end to its TO end (no side offset). One place within the city
box + 1 km (or the county), as d5_common.one_place.

Run: python tests/statewide/d5_tiger.py   (writes data/statewide/d5_result_tiger.csv)
"""

from __future__ import annotations

import io
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
FOLDER = ROOT / "data" / "cache" / "tiger_addrfeat" / "2026"


def num(v):
    try:
        return int(str(v).strip())
    except ValueError:
        return None


def county_index(code: int) -> dict[str, list]:
    import shapefile

    import d5_common as dc
    z = zipfile.ZipFile(FOLDER / f"tl_2026_06{2 * code - 1:03d}_addrfeat.zip")
    parts = {n[-4:]: io.BytesIO(z.read(n)) for n in z.namelist() if n[-4:] in (".shp", ".dbf", ".shx")}
    r = shapefile.Reader(shp=parts[".shp"], dbf=parts[".dbf"], shx=parts[".shx"])
    idx = defaultdict(list)
    for sr in r.iterShapeRecords():
        rec = sr.record.as_dict()
        name = rec.get("FULLNAME") or ""
        pts = [(y, x) for x, y in sr.shape.points]
        if not name or len(pts) < 2:
            continue
        ranges = []
        for side in ("L", "R"):
            a, b = num(rec.get(f"{side}FROMHN")), num(rec.get(f"{side}TOHN"))
            if a is not None and b is not None:
                ranges.append((a, b, rec.get(f"PARITY{side}") or "B"))
        if not ranges:
            continue
        seg = (name, pts, ranges)
        for k in dc.keys(name):
            idx[k].append(seg)
    return idx


def along(pts, t):
    """The point a fraction t of the way along a polyline."""
    import d5_common as dc
    lens = [dc.ft(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(lens) or 1.0
    goal, acc = t * total, 0.0
    for (a, b), d in zip(zip(pts, pts[1:]), lens):
        if acc + d >= goal and d > 0:
            u = (goal - acc) / d
            return a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])
        acc += d
    return pts[-1]


def locate(idx, street: str, n: int):
    import d5_common as dc
    seen, out = set(), []
    for k in dc.keys(street):
        for seg in idx.get(k, ()):
            if id(seg) in seen:
                continue
            seen.add(id(seg))
            name, pts, ranges = seg
            if not dc.same_street(street, name):
                continue
            for a, b, par in ranges:
                lo, hi = min(a, b), max(a, b)
                if not lo <= n <= hi or (par == "O" and n % 2 == 0) or (par == "E" and n % 2 == 1):
                    continue
                t = 0.5 if a == b else (n - a) / (b - a)
                out.append(along(pts, t))
                break
    return out


def main() -> None:
    import d5_common as dc
    rows = sorted(dc.pools(), key=lambda r: int(r["county_code"] or 0))
    boxes = dc.city_boxes({r["city"] for r in rows})
    out, cur, idx = [], None, {}
    for r in rows:
        code = int(r["county_code"] or 0)
        if code != cur:
            cur, idx = code, (county_index(code) if 1 <= code <= 58 else {})
            print(f"county {code}: {len(idx)} keys", flush=True)
        spot, note = dc.one_place(locate(idx, r["street"], int(r["number"])), boxes.get(r["city"]))
        out.append({"collision_id": r["collision_id"], "pool": r["pool"], "district": r["district"],
                    "placed": int(spot is not None), "lat": f"{spot[0]:.6f}" if spot else "",
                    "lon": f"{spot[1]:.6f}" if spot else "", "note": note})
    dc.write("tiger", out)
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
