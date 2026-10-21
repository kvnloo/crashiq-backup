"""Answer the app's Overpass corridor query from the local OSM extract (osm_extract.py), standard library only.

The app asks (network.overpass_query):
    way(around:40, <line>)["highway"~"^(<classes>)$"]; out body; >; out body qt;
Emulated as: every way of those classes with any segment within 40 m of any segment of the line, in id order,
with its nodes (coordinates from the way, tags for nodes that carry a highway tag). The same JSON shape as
Overpass, handed to the app through its own transport hook (`app.state.overpass`), so network.detect, the pull and
placement run unchanged. How closely this matches real Overpass answers is measured by `validate()` and stated on the
Method sheet.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import urllib.parse
from pathlib import Path

AROUND = re.compile(r"way\(around:(\d+(?:\.\d+)?),([-\d.,]+)\)\[\"highway\"~\"\^\(([^)]*)\)\$\"\]")


def _xy(lat0):
    k = math.cos(math.radians(lat0))
    return lambda la, lo: (lo * 111320 * k, la * 110540)


def _pt_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == dy == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) > 0) != (o(a, b, d) > 0) and (o(c, d, a) > 0) != (o(c, d, b) > 0)


def _seg_seg(a, b, c, d):
    if _cross(a, b, c, d):
        return 0.0
    return min(_pt_seg(a, c, d), _pt_seg(b, c, d), _pt_seg(c, a, b), _pt_seg(d, a, b))


class LocalOSM:
    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.meta = dict(self.db.execute("SELECT key, value FROM meta"))
        self.queries = 0

    # ---- the app's corridor query ----
    def around(self, line: list[tuple[float, float]], radius_m: float, classes: set[str]) -> dict:
        lat0 = sum(p[0] for p in line) / len(line)
        to = _xy(lat0)
        lxy = [to(*p) for p in line]
        segs = list(zip(lxy, lxy[1:])) or [(lxy[0], lxy[0])]
        dlat = radius_m / 110540 + 1e-6
        dlon = radius_m / (111320 * math.cos(math.radians(lat0))) + 1e-6
        rows = self.db.execute(
            "SELECT w.id, w.highway, w.tags, w.nodes, w.coords FROM way_box b JOIN ways w ON w.id = b.id "
            "WHERE b.maxlat >= ? AND b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ?",
            (min(p[0] for p in line) - dlat, max(p[0] for p in line) + dlat,
             min(p[1] for p in line) - dlon, max(p[1] for p in line) + dlon)).fetchall()
        ways, nodes = [], {}
        for wid, hw, tags, nids, coords in sorted(rows):
            if hw not in classes:
                continue
            cs = json.loads(coords)
            wxy = [to(*c) for c in cs]
            wsegs = list(zip(wxy, wxy[1:])) or [(wxy[0], wxy[0])]
            if not any(_seg_seg(a, b, c, d) <= radius_m for a, b in wsegs for c, d in segs):
                continue
            ids = json.loads(nids)
            ways.append({"type": "way", "id": wid, "nodes": ids, "tags": json.loads(tags)})
            for nid, (la, lo) in zip(ids, cs):
                nodes[nid] = {"type": "node", "id": nid, "lat": la, "lon": lo}
        if nodes:
            ids = list(nodes)
            for i in range(0, len(ids), 900):
                chunk = ids[i:i + 900]
                for nid, t in self.db.execute(f"SELECT id, tags FROM nodes WHERE id IN ({','.join('?' * len(chunk))})",
                                              chunk):
                    nodes[nid]["tags"] = json.loads(t)
        return {"version": 0.6, "generator": f"CrashIQ tester local OSM ({self.meta.get('source')}, "
                                             f"{self.meta.get('timestamp')})",
                "elements": ways + [nodes[k] for k in sorted(nodes)]}

    def transport(self, url: str, data: bytes, timeout: float) -> bytes:
        """`app.state.overpass` hook: (url, body, timeout) -> Overpass JSON bytes."""
        q = urllib.parse.parse_qs(data.decode()).get("data", [""])[0]
        m = AROUND.search(q)
        if not m:
            raise ValueError(f"local OSM can't answer this query: {q[:120]}")
        nums = [float(x) for x in m.group(2).split(",")]
        line = list(zip(nums[0::2], nums[1::2]))
        self.queries += 1
        return json.dumps(self.around(line, float(m.group(1)), set(m.group(3).split("|")))).encode()

    # ---- the corridor picker's queries ----
    def boundaries(self) -> list[dict]:
        return [{"rel": i, "name": n, "admin_level": lv, "osm_type": t}
                for i, t, n, lv in self.db.execute("SELECT id, osm_type, name, admin_level FROM areas")]

    def roads_in_area(self, area_id: int, classes=("primary", "secondary", "tertiary")) -> dict:
        """Named ways of these classes with any node inside the boundary: Overpass `way(area.a)` + `out geom`."""
        row = self.db.execute("SELECT rings, minlat, minlon, maxlat, maxlon FROM areas WHERE id = ? "
                              "ORDER BY CAST(admin_level AS INT) DESC LIMIT 1", (area_id,)).fetchone()
        if not row:
            return {"elements": []}
        return self.roads_in_rings([[tuple(p) for p in r] for r in json.loads(row[0])], classes)

    def roads_in_rings(self, rings: list[list[tuple]], classes=("primary", "secondary", "tertiary")) -> dict:
        lats = [p[0] for r in rings for p in r]
        lons = [p[1] for r in rings for p in r]
        row = (None, min(lats), min(lons), max(lats), max(lons))
        cand = self.db.execute(
            "SELECT w.id, w.highway, w.tags, w.coords FROM way_box b JOIN ways w ON w.id = b.id "
            "WHERE b.maxlat >= ? AND b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ? AND w.name IS NOT NULL",
            (row[1], row[3], row[2], row[4])).fetchall()
        out = []
        for wid, hw, tags, coords in sorted(cand):
            if hw not in classes:
                continue
            cs = json.loads(coords)
            if any(_inside(c, rings) for c in cs):
                out.append({"type": "way", "id": wid, "tags": json.loads(tags),
                            "geometry": [{"lat": la, "lon": lo} for la, lo in cs]})
        return {"elements": out}


def _inside(p, rings) -> bool:
    """Point in any outer ring (ray casting; inner rings ignored: a road node in a hole is rare and harmless here)."""
    y, x = p
    for ring in rings:
        c = False
        for (y1, x1), (y2, x2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        if c:
            return True
    return False


def validate(local: LocalOSM, app_db: Path, results_dir: Path) -> dict:
    """Compare local answers with the real Overpass answers cached in the Tester app database, for every corridor
    already run: way-id sets, and the app's own corridor detection on both."""
    import hashlib
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    from crashiq import network
    con = sqlite3.connect(app_db)
    rows = []
    for f in sorted(results_dir.glob("*.json")):
        r = json.loads(f.read_text())
        line = [tuple(p) for p in (r.get("corridor") or {}).get("line", [])]
        if not line:
            continue
        q = network.overpass_query(line)
        hit = con.execute("SELECT body FROM http_cache WHERE key = ?",
                          ("overpass:" + hashlib.sha1(q.encode()).hexdigest(),)).fetchone()
        if not hit:
            continue
        real = json.loads(hit[0])
        if not real.get("elements"):
            continue
        mine = json.loads(local.transport("", urllib.parse.urlencode({"data": q}).encode(), 0))
        rw = {e["id"] for e in real["elements"] if e["type"] == "way"}
        mw = {e["id"] for e in mine["elements"] if e["type"] == "way"}
        dr, dm = network.detect(real, line), network.detect(mine, line)
        rows.append({"city": r["city"], "real_ways": len(rw), "local_ways": len(mw), "both": len(rw & mw),
                     "only_real": len(rw - mw), "only_local": len(mw - rw),
                     "same_corridor_name": dr["corridor_name"] == dm["corridor_name"],
                     "real_intersections": len(dr["intersections"]), "local_intersections": len(dm["intersections"]),
                     "same_intersections": [i["name"] for i in dr["intersections"]] ==
                                           [i["name"] for i in dm["intersections"]]})
    n = len(rows)
    both = sum(x["both"] for x in rows)
    union = sum(x["both"] + x["only_real"] + x["only_local"] for x in rows)
    return {"corridors": n, "way_match_pct": round(100 * both / union, 2) if union else None,
            "same_corridor_name": sum(x["same_corridor_name"] for x in rows),
            "same_intersection_list": sum(x["same_intersections"] for x in rows), "rows": rows}
