"""Pick one test corridor per California city from OpenStreetMap.

Rule (workbook Method sheet): the named primary/secondary road with the most length inside the city's OSM boundary
(admin_level 8); fallback tertiary. Take about 1 mile (1,609 m) of it around its middle. Dual carriageways are
never averaged: the line follows one carriageway's own OSM geometry (shortest path over the road's ways between the
window's two ends). A window is accepted when that path is 0.6-1.6 miles long and no more than 1.35 times the
straight distance (not winding); otherwise the next window, then the next road, is tried. Cities with no boundary or no usable road are listed
with the reason.

Each Overpass response is cached under data/cache/statewide/osm/, so a rerun downloads nothing.
"""

from __future__ import annotations

import heapq
import json
import math
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

# Public Overpass servers, tried in order (overpass-api.de rate-limited this machine during the #73 run; the
# mirrors serve the same OpenStreetMap data, a few minutes apart).
SERVERS = ["https://overpass.kumi.systems/api/interpreter",
           "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
           "https://overpass-api.de/api/interpreter"]
STATS = {"calls": 0, "empty_or_failed_tries": 0, "by_server": {}}


class OverpassUnavailable(RuntimeError):
    """Every server refused or answered empty: the city is 'not tested (Overpass)', never a failure."""


GAP_S = 8.0          # pause between Overpass calls (one worker): be a polite client
_last = [0.0]


def post(body: bytes, timeout: float = 200) -> dict:
    """One Overpass call, gently: each server once, with a pause between calls; a refusal or empty answer moves
    to the next server; if all fail, back off 2 and 5 minutes before giving up with OverpassUnavailable."""
    last = None
    for backoff in (0, 120, 300):
        time.sleep(backoff)
        for url in SERVERS:
            wait = GAP_S - (time.time() - _last[0])
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
            STATS["calls"] += 1
            try:
                with urllib.request.urlopen(urllib.request.Request(url, body, UA), timeout=timeout) as r:
                    data = json.load(r)
                if "error" in str(data.get("remark", "")).lower():
                    raise ValueError(data["remark"])
                if not data.get("elements"):
                    raise ValueError("0 elements")
                STATS["by_server"][url] = STATS["by_server"].get(url, 0) + 1
                return data
            except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
                STATS["empty_or_failed_tries"] += 1
                last = f"{url.split('/')[2]}: {e}"
    raise OverpassUnavailable(f"Overpass unavailable on every server: {last}")


def app_transport(url: str, data: bytes, timeout: float) -> bytes:
    """For the app's `app.state.overpass`: same query, answered by the first server that returns streets."""
    q = urllib.parse.parse_qs(data.decode()).get("data", [""])[0]
    return json.dumps(post(urllib.parse.urlencode({"data": q}).encode(), timeout)).encode()
UA = {"User-Agent": "CrashIQ-tester/0.1 (statewide data test, #73)"}
TARGET_M = 1609.0


def norm_city(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()
    s = re.sub(r"\bCITY OF\b", " ", s)
    s = re.sub(r"\bSAINT\b", "ST", s)
    s = re.sub(r"\bST\.?\b", "ST", s)
    return re.sub(r"[^A-Z0-9]", "", s)


def overpass(query: str, cache: Path, pause: float = 1.0) -> dict:
    if cache.exists():
        return json.loads(cache.read_text())
    data = post(urllib.parse.urlencode({"data": query}).encode())
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    time.sleep(pause)
    return data


def boundaries(cache_dir: Path) -> dict[str, dict]:
    """Normalized city name -> {rel, name} for every admin_level 8 boundary in California."""
    q = ('[out:json][timeout:180];area["ISO3166-2"="US-CA"][admin_level=4]->.ca;'
         'rel(area.ca)["boundary"="administrative"]["admin_level"="8"];out tags;')
    d = overpass(q, cache_dir / "ca_cities.json")
    out = {}
    for e in d["elements"]:
        name = e.get("tags", {}).get("name")
        if name:
            out.setdefault(norm_city(name), {"rel": e["id"], "name": name})
    return out


def find_rel(name: str, cache_dir: Path) -> dict | None:
    """Fallback for a city not tagged admin_level 8 (San Francisco is a consolidated city-county, level 6)."""
    safe = name.replace('"', "")
    q = ('[out:json][timeout:120];area["ISO3166-2"="US-CA"][admin_level=4]->.ca;'
         f'rel(area.ca)["boundary"="administrative"]["name"="{safe}"];out tags;')
    d = overpass(q, cache_dir / f"rel_{norm_city(name)}.json")
    els = sorted(d.get("elements", []), key=lambda e: -int(e.get("tags", {}).get("admin_level", "0")))
    return {"rel": els[0]["id"], "name": els[0]["tags"]["name"]} if els else None


def _xy(lat0, lon0):
    k = math.cos(math.radians(lat0))
    return (lambda la, lo: ((lo - lon0) * 111320 * k, (la - lat0) * 110540),
            lambda x, y: (lat0 + y / 110540, lon0 + x / (111320 * k)))


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _simplify(pts, tol):
    """Douglas-Peucker on projected points."""
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    i, d = max(((k, _seg_dist(p, a, b)) for k, p in enumerate(pts[1:-1], 1)), key=lambda t: t[1])
    if d <= tol:
        return [a, b]
    return _simplify(pts[:i + 1], tol)[:-1] + _simplify(pts[i:], tol)


def _candidate_lines(ways: list[dict]):
    """Yield (line_ll, length_m): ~1 mile along the road's own OSM geometry, middle window first.

    Ends are picked on the road's principal axis; the line between them is the shortest path over the road's
    ways (shared nodes have identical coordinates), so it lies on one real carriageway, never in a median."""
    adj: dict[tuple, dict[tuple, float]] = defaultdict(dict)
    allpts = [(g["lat"], g["lon"]) for w in ways for g in w.get("geometry", [])]
    if len(allpts) < 2:
        return
    lat0 = sum(p[0] for p in allpts) / len(allpts)
    lon0 = sum(p[1] for p in allpts) / len(allpts)
    to_xy, to_ll = _xy(lat0, lon0)
    key = {}
    for w in ways:
        g = w.get("geometry", [])
        for p, q in zip(g, g[1:]):
            u, v = (round(p["lat"], 7), round(p["lon"], 7)), (round(q["lat"], 7), round(q["lon"], 7))
            key[u], key[v] = to_xy(*u), to_xy(*v)
            d = math.dist(key[u], key[v])
            adj[u][v] = adj[v][u] = d
    xy = list(key.values())
    mx = sum(p[0] for p in xy) / len(xy)
    my = sum(p[1] for p in xy) / len(xy)
    sxx = sum((p[0] - mx) ** 2 for p in xy)
    syy = sum((p[1] - my) ** 2 for p in xy)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in xy)
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ux, uy = math.cos(ang), math.sin(ang)
    proj = {n: (key[n][0] - mx) * ux + (key[n][1] - my) * uy for n in key}
    lo, hi = min(proj.values()), max(proj.values())
    if hi - lo < 400:
        return
    win = min(TARGET_M, hi - lo)
    mid = (lo + hi) / 2
    starts = [mid - win / 2] + [s for k in range(1, 8) for s in (mid - win / 2 - k * win / 3, mid - win / 2 + k * win / 3)
                                if lo <= s and s + win <= hi]
    for s0 in starts:
        a = min(proj, key=lambda n: abs(proj[n] - s0))
        b = min(proj, key=lambda n: abs(proj[n] - s0 - win))
        dist, prev, todo = {a: 0.0}, {}, [(0.0, a)]
        while todo:
            d, u = heapq.heappop(todo)
            if u == b or d > 3 * win:
                break
            if d > dist.get(u, 1e18):
                continue
            for v, w in adj[u].items():
                if d + w < dist.get(v, 1e18):
                    dist[v], prev[v] = d + w, u
                    heapq.heappush(todo, (d + w, v))
        if b not in dist:
            continue
        path = [b]
        while path[-1] != a:
            path.append(prev[path[-1]])
        length, straight = dist[b], math.dist(key[a], key[b])
        if not (0.6 * win <= length <= 1.6 * win and length <= 1.35 * straight):
            continue
        line = _simplify([key[n] for n in reversed(path)], 4.0)
        yield [tuple(round(v, 6) for v in to_ll(*p)) for p in line], round(length)


def pick(rel: int, cache_dir: Path) -> dict:
    """The test corridor for one city boundary relation, or {'reason': ...}."""
    q = (f'[out:json][timeout:180];area(id:{3600000000 + rel})->.a;'
         f'way(area.a)["highway"~"^(primary|secondary|tertiary)$"]["name"];out geom;')
    d = overpass(q, cache_dir / f"roads_{rel}.json")
    by_name: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for w in d.get("elements", []):
        t = w.get("tags", {})
        cls = "major" if t.get("highway") in ("primary", "secondary") else "tertiary"
        by_name[(cls, t["name"])].append(w)

    def length(ws):
        return sum(math.dist((a["lat"] * 110540, a["lon"] * 92000), (b["lat"] * 110540, b["lon"] * 92000))
                   for w in ws for a, b in zip(w.get("geometry", []), w.get("geometry", [])[1:]))

    ranked = sorted(by_name.items(), key=lambda kv: (kv[0][0] != "major", -length(kv[1])))
    if not ranked:
        return {"reason": "no named primary, secondary or tertiary road inside the OSM city boundary"}
    for (cls, name), ws in ranked[:6]:
        for line, m in _candidate_lines(ws):
            return {"road": name, "road_class": cls, "line": line, "length_m": round(m), "osm_road_m": round(length(ws))}
    return {"reason": "no straight-enough 1-mile stretch on the six longest roads"}
