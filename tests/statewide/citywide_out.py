"""Outputs of the citywide coverage test (#199): the tracker's per-agency CSV and a California county outline for its
map. Reads data/statewide/citywide.json (citywide.py); writes data/statewide/tracker/citywide.csv and
data/statewide/tracker/ca_counties.json. Every number comes from citywide.json; this file only arranges them.

Run: python tests/statewide/citywide_out.py
"""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import corridors

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
OUT = DATA / "tracker"
SIMPLIFY_DEG = 0.01            # ~1 km: plenty for a statewide map, keeps the file small

COLS = ["ncic", "agency", "type", "county", "crashes", "police_gps_pct", "crashiq_placed_pct", "on_map_pct",
        "review_pct", "cant_place_pct", "not_run_pct", "accuracy", "fatal_crashes", "fatal_on_map", "lat", "lon"]


def _dp(pts, tol):
    """Douglas-Peucker line simplification (degrees)."""
    if len(pts) < 3:
        return pts
    (ax, ay), (bx, by) = pts[0], pts[-1]
    dx, dy = bx - ax, by - ay
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
    far, idx = 0.0, 0
    for i, (x, y) in enumerate(pts[1:-1], 1):
        d = abs(dy * x - dx * y + bx * ay - by * ax) / norm
        if d > far:
            far, idx = d, i
    if far <= tol:
        return [pts[0], pts[-1]]
    return _dp(pts[:idx + 1], tol)[:-1] + _dp(pts[idx:], tol)


def _ring(r: list) -> list:
    """Simplify a closed ring as two open halves (Douglas-Peucker needs distinct end points)."""
    pts = [tuple(p) for p in r]
    if len(pts) < 8:
        return pts
    h = len(pts) // 2
    return _dp(pts[:h + 1], SIMPLIFY_DEG)[:-1] + _dp(pts[h:], SIMPLIFY_DEG)


def counties(db: Path) -> list[dict]:
    con = sqlite3.connect(db)
    out = []
    ca = {r["county"] for r in csv.DictReader(open(Path(__file__).resolve().parents[2] / "data" / "reference" /
                                                  "caltrans_districts.csv"))}
    for name, rings, minlat, maxlon in con.execute("SELECT name, rings, minlat, maxlon FROM areas WHERE admin_level = '6'"):
        base = (name or "").removeprefix("City and County of ").removesuffix(" County")
        if base not in ca or minlat < 32.4 or maxlon > -114.0:
            continue
        name = f"{base} County"
        simple = [[[round(p[0], 4), round(p[1], 4)] for p in _ring(r)] for r in json.loads(rings)]
        out.append({"name": name, "rings": [r for r in simple if len(r) >= 4]})
    return out


def centroids(db: Path) -> dict[str, tuple[float, float]]:
    con = sqlite3.connect(db)
    out = {}
    for name, a, b, c, d in con.execute("SELECT name, minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '8'"):
        out.setdefault(corridors.norm_city(name or ""), (round((a + c) / 2, 4), round((b + d) / 2, 4)))
    return out


def main() -> None:
    cw = json.loads((DATA / "citywide.json").read_text())
    osm_db = ROOT / "data" / "osm" / "ca_osm.sqlite"
    where = centroids(osm_db)
    rows = []
    for a in cw["agencies"]:
        ll = where.get(corridors.norm_city(a["agency"] or "")) if a["type"] == "local" else None
        f = a.get("fatal") or {}
        rows.append({**{k: a.get(k) for k in COLS}, "fatal_crashes": f.get("crashes", 0), "fatal_on_map": f.get("on_map", 0),
                     "lat": ll[0] if ll else None, "lon": ll[1] if ll else None})
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "citywide.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, COLS)
        w.writeheader()
        w.writerows(rows)
    (OUT / "ca_counties.json").write_text(json.dumps(counties(osm_db), separators=(",", ":")))
    print(f"{len(rows)} agencies ({'complete' if cw.get('complete') else 'partial'}) -> {OUT}")


if __name__ == "__main__":
    main()
