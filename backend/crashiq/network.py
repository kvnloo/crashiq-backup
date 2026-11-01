"""C2 network: a drawn corridor → ordered study intersections and segments from OpenStreetMap.

Pipeline (all deterministic code):
1. Overpass: road ways within ~40 m of the drawn line (+ their nodes and tags). Cached in SQLite.
2. Corridor ways: ways that run *along* the line (nodes within 80 ft and direction within 25°).
3. Candidate nodes: nodes shared by a corridor way and any other road way, inside the study limits.
4. Cluster candidates along the line (a divided road gives two nodes per cross street) → one intersection each.
5. Control from OSM tags near the intersection: traffic_signals → signal, stop → stop, else unknown. Never guessed.
6. Segments: between adjacent *study* intersections (and the study limits A/B), lengths in feet along the line.

Data © OpenStreetMap contributors (ODbL).
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from typing import Callable

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import study as study_mod
from .db import Database
from .geo import FT_PER_MI, Polyline, angle_diff, buffer_ring
from .names import street_key

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ROAD_CLASSES = ("motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|road|"
                "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link")
QUERY_RADIUS_M = 40       # ways this close to the drawn line are fetched
ALONG_FT = 80             # a node this close to the line is "on" the corridor (covers divided roads)
PARALLEL_DEG = 25         # a way segment within this angle of the line runs along it
CLUSTER_FT = 150          # nodes this close along the line can belong to one intersection
END_TOL_FT = 60           # an intersection this far past A or B still counts as the terminus
STUB_FT = 50              # no segment between a terminus and an intersection closer than this
CONTROL_FT = 120          # signal/stop tags this close to the intersection set its control

DEFAULT_RADIUS_FT = 250.0   # HSM / Caltrans intersection influence area (R2.4)
DEFAULT_BUFFER_FT = 100.0   # corridor buffer each side of the line; provisional default, see PR for #7


class NetworkError(RuntimeError):
    """Overpass failed. Never turned into an empty intersection list."""


# -- Overpass ----------------------------------------------------------------------------------------
def crossing_query(line: list[tuple[float, float]]) -> str:
    """Railways and named paths across the corridor (#318): crossing features, never streets. Whole ways come back
    (all their nodes), so a distance along a path can be walked past the query radius."""
    coords = ",".join(f"{lat:.6f},{lon:.6f}" for lat, lon in line)
    return (f'[out:json][timeout:90];('
            f'way(around:{QUERY_RADIUS_M},{coords})["railway"~"^(rail|light_rail|tram|subway)$"];'
            f'way(around:{QUERY_RADIUS_M},{coords})["highway"~"^(cycleway|path|footway)$"]["name"];'
            f');out body;>;out body qt;')


def overpass_query(line: list[tuple[float, float]]) -> str:
    coords = ",".join(f"{lat:.6f},{lon:.6f}" for lat, lon in line)
    return (f'[out:json][timeout:90];'
            f'way(around:{QUERY_RADIUS_M},{coords})["highway"~"^({ROAD_CLASSES})$"];'
            f'out body;>;out body qt;')


# The cities the corridor enters (#142): OSM admin boundaries containing points along the line and both buffer edges.
# One `is_in` per point; a `make pt` marker before each tells which areas belong to which point.
CITY_STEP_FT = 300


def city_points(line: list[tuple[float, float]], buffer_ft: float) -> list[tuple[float, float]]:
    pl = Polyline([tuple(p) for p in line])
    n = max(1, math.ceil(pl.length_ft / CITY_STEP_FT))
    out = []
    for k in range(n + 1):
        st = pl.length_ft * k / n
        i = min(range(len(pl.cum) - 1), key=lambda j: 0 if pl.cum[j] <= st <= pl.cum[j + 1] else 1)
        (x1, y1), (x2, y2) = pl.xy[i], pl.xy[i + 1]
        seg = math.hypot(x2 - x1, y2 - y1) or 1.0
        nx, ny = -(y2 - y1) / seg, (x2 - x1) / seg              # unit normal
        x, y = pl.proj.to_xy(*pl.point_at(st))
        out += [pl.proj.to_ll(x, y)] + [pl.proj.to_ll(x + sgn * buffer_ft * nx, y + sgn * buffer_ft * ny)
                                         for sgn in (1, -1)]
    return out


def cities_query(line: list[tuple[float, float]], buffer_ft: float) -> str:
    parts = [f'make pt idx="{i}";out;is_in({lat:.6f},{lon:.6f})->.a;'
             f'area.a["boundary"="administrative"]["admin_level"~"^(6|8)$"];out tags;'
             for i, (lat, lon) in enumerate(city_points(line, buffer_ft))]
    return "[out:json][timeout:60];" + "".join(parts)


def corridor_cities(db: Database, line: list[tuple[float, float]], buffer_ft: float,
                    transport: Transport | None = None) -> dict | None:
    """{"cities": incorporated cities (OSM admin level 8) the line + buffer enters, "outside": True when part of it is
    outside every city (unincorporated county), "counties": admin level 6 names there}. None when OSM can't say."""
    try:
        raw = fetch_overpass(db, cities_query(line, buffer_ft), transport=transport)
    except NetworkError:
        return None
    pts: list[list[dict]] = []
    for e in raw.get("elements", []):
        if e.get("type") == "pt":
            pts.append([])
        elif pts and e.get("type") == "area":
            pts[-1].append(e.get("tags") or {})
    if not pts:
        return None
    cities, counties, outside = set(), set(), False
    for areas in pts:
        lvl8 = [a.get("name") for a in areas if a.get("admin_level") == "8" and a.get("name")]
        cities.update(lvl8)
        if not lvl8:
            outside = True
            counties.update(a.get("name") for a in areas if a.get("admin_level") == "6" and a.get("name"))
    return {"cities": sorted(cities), "outside": outside, "counties": sorted(counties)}


def roads_near(db: Database, lat: float, lon: float, radius_m: float, transport: Transport | None = None) -> list[dict]:
    """Tags of the roads within radius_m of a point (#174: is a FARS point on a road the report names?). Same query
    shape and cache as the corridor's; an empty or failed answer = no roads known."""
    q = (f'[out:json][timeout:60];way(around:{radius_m:.0f},{lat:.6f},{lon:.6f},{lat:.6f},{lon:.6f})'
         f'["highway"~"^({ROAD_CLASSES})$"];out body;>;out body qt;')
    try:
        raw = fetch_overpass(db, q, transport=transport, retries=1, backoff_s=1.0)
    except NetworkError:
        return []
    return [e.get("tags") or {} for e in raw.get("elements", []) if e.get("type") == "way"]


def _http_post(url: str, data: bytes, timeout: float) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "CrashIQ/0.1 (+crash safety analysis)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


Transport = Callable[[str, bytes, float], bytes]


def _cached_overpass(db: Database, query: str) -> dict | None:
    hit = db.one("SELECT body FROM http_cache WHERE key = ?", ("overpass:" + hashlib.sha1(query.encode()).hexdigest(),))
    return json.loads(hit["body"]) if hit else None


OSM_TTL_DAYS = 180     # streets change slowly; a cached Overpass answer is refreshed after this (#54)


def fetch_overpass(db: Database, query: str, transport: Transport | None = None, retries: int = 3,
                   backoff_s: float = 2.0, sleep: Callable[[float], None] = time.sleep, allow_empty: bool = False) -> dict:
    """Overpass JSON for `query`, from the SQLite cache when present. Raises NetworkError on failure."""
    key = "overpass:" + hashlib.sha1(query.encode()).hexdigest()
    hit = db.one("SELECT body, (julianday('now') - julianday(created_at)) AS age_days FROM http_cache WHERE key = ?",
                 (key,))
    old = json.loads(hit["body"]) if hit else None
    if old is not None and not old.get("elements") and not allow_empty:
        old = None                           # an empty answer cached before #84 is a miss, never a map
    if old is not None and (hit["age_days"] or 0) < OSM_TTL_DAYS:
        return old
    transport = transport or _http_post
    payload = urllib.parse.urlencode({"data": query}).encode()
    last = "no response"
    for attempt in range(retries + 1):
        wait = backoff_s * 2 ** attempt
        try:
            data = json.loads(transport(OVERPASS_URL, payload, 120))
            if not isinstance(data.get("elements"), list):
                raise ValueError("response has no elements")
            if not data["elements"] and not allow_empty:
                # A drawn corridor always has streets around it; overpass-api.de sometimes answers 0 elements with no
                # remark under load (7 of 14 calls in the statewide run, #84). Retry, and never cache it.
                raise ValueError("Overpass returned no streets (empty answer)")
            remark = str(data.get("remark", ""))
            if "error" in remark.lower():          # Overpass reports timeouts as 200 + remark
                raise ValueError(remark)
            db.execute("INSERT OR REPLACE INTO http_cache (key, source, body) VALUES (?, 'overpass', ?)",
                       (key, json.dumps(data)))
            return data
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in (429, 502, 503, 504):
                break
            ra = (e.headers or {}).get("Retry-After") if hasattr(e, "headers") else None
            if ra and str(ra).strip().isdigit():          # Overpass says how long to back off (#54)
                wait = min(float(ra), 120.0)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last = str(e) or type(e).__name__
        if attempt < retries:
            sleep(wait)
    if old is not None:         # refresh failed: an old (non-empty) map beats no map
        return old
    raise NetworkError(f"Couldn't get streets from OpenStreetMap (Overpass): {last}. Try again in a minute.")


# -- detection ---------------------------------------------------------------------------------------
def _names(tags: dict) -> list[str]:
    out = []
    for t in ("name", "ref"):
        for v in str(tags.get(t, "")).split(";"):
            v = v.strip()
            if v and v not in out:
                out.append(v)
    return out


def _core(name: str) -> str | None:
    k = street_key(name)
    return k.core.replace(" ", "") if k else None


def detect(osm: dict, line_ll: list[tuple[float, float]]) -> dict:
    """Intersections along the drawn line, in order from its start (A) to its end (B)."""
    line = Polyline(line_ll)
    nodes: dict[int, dict] = {}
    ways: list[dict] = []
    for el in osm.get("elements", []):
        if el.get("type") == "node" and "lat" in el:
            nodes[el["id"]] = el
        elif el.get("type") == "way":
            ways.append(el)
    proj = {nid: line.project(n["lat"], n["lon"]) for nid, n in nodes.items()}

    # 2. corridor ways: enough of the way runs along the line
    corridor_ids: set[int] = set()
    along_len: Counter = Counter()
    hw_len: Counter = Counter()
    for w in ways:
        near_len = run_len = 0.0
        for a, b in zip(w.get("nodes", []), w.get("nodes", [])[1:]):
            pa, pb = proj.get(a), proj.get(b)
            if pa is None or pb is None or pa.offset_ft > ALONG_FT or pb.offset_ft > ALONG_FT:
                continue
            seg = math.hypot(pb.x - pa.x, pb.y - pa.y)
            if seg == 0:
                continue
            near_len += seg
            ax, ay = line.proj.to_xy(nodes[a]["lat"], nodes[a]["lon"])
            bx, by = line.proj.to_xy(nodes[b]["lat"], nodes[b]["lon"])
            brg = math.degrees(math.atan2(bx - ax, by - ay)) % 180
            if angle_diff(brg, line.bearing_at(pa.index)) <= PARALLEL_DEG:
                run_len += seg
        if run_len >= 50 and run_len >= 0.5 * near_len:
            corridor_ids.add(w["id"])
            hw_len[w.get("tags", {}).get("highway", "")] += run_len
            for n in _names(w.get("tags", {})):
                along_len[n] += run_len
    corridor_name = along_len.most_common(1)[0][0] if along_len else None
    corridor_cores = {c for c in (_core(n) for n in along_len) if c}
    corridor_highway = hw_len.most_common(1)[0][0] if hw_len else None
    freeway = corridor_highway == "motorway"

    # 3. candidate nodes
    corridor_nodes: set[int] = set()
    for w in ways:
        if w["id"] in corridor_ids:
            corridor_nodes.update(w.get("nodes", []))
    cross_names: dict[int, list[str]] = defaultdict(list)
    cross_sides: dict[int, set[int]] = defaultdict(set)   # sides of the corridor the named cross streets leave on
    is_candidate: set[int] = set()
    for w in ways:
        if w["id"] in corridor_ids:
            continue
        if freeway and str(w.get("tags", {}).get("highway", "")).endswith("_link"):
            continue    # a ramp meeting a freeway corridor is a merge or diverge, not an intersection (N7, #67)
        all_names = _names(w.get("tags", {}))
        names = [n for n in all_names if _core(n) not in corridor_cores]
        if freeway and all_names and not names:
            continue    # a short piece of the freeway itself (too short to count as corridor), not a crossing road
        wn = w.get("nodes", [])
        for k, nid in enumerate(wn):
            if nid in corridor_nodes and nid in proj:
                p = proj[nid]
                if p.offset_ft <= ALONG_FT and -END_TOL_FT <= p.station_ft <= line.length_ft + END_TOL_FT:
                    is_candidate.add(nid)
                    for n in names:
                        if n not in cross_names[nid]:
                            cross_names[nid].append(n)
                    if names:
                        for step in (-1, 1):
                            side = _leaving_side(line, nodes, proj, corridor_nodes, wn, k, step)
                            if side:
                                cross_sides[nid].add(side)

    # 4. cluster along the line
    cands = sorted(is_candidate, key=lambda n: proj[n].station_ft)
    clusters: list[list[int]] = []
    for nid in cands:
        if clusters:
            last = clusters[-1]
            near = proj[nid].station_ft - proj[last[-1]].station_ft <= CLUSTER_FT
            a = {_core(x) for x in cross_names[nid]}
            b = {_core(x) for m in last for x in cross_names[m]}
            same_street = not a or not b or bool(a & b)
            if near and same_street:
                last.append(nid)
                continue
        clusters.append([nid])

    # 5. intersections with control from tags
    tagged = [(n, n.get("tags", {}).get("highway")) for n in nodes.values()]
    signals = [n for n, h in tagged if h == "traffic_signals"]
    stops = [n for n, h in tagged if h == "stop"]
    out = []
    for c in clusters:
        # Position from the nodes where a *named* cross street meets the corridor; unnamed slip lanes and
        # links join the cluster (and its node list) but don't pull the pin off the intersection.
        core = [n for n in c if cross_names[n]] or c
        st = sum(proj[n].station_ft for n in core) / len(core)
        # centroid of the actual OSM nodes (not the foot on the line), so the pin sits on the street
        cx = sum(line.proj.to_xy(nodes[n]["lat"], nodes[n]["lon"])[0] for n in core) / len(core)
        cy = sum(line.proj.to_xy(nodes[n]["lat"], nodes[n]["lon"])[1] for n in core) / len(core)
        lat, lon = line.proj.to_ll(cx, cy)
        names: Counter = Counter()
        for n in c:
            names.update(cross_names[n])
        name = " / ".join(n for n, _ in names.most_common()) or "Unnamed road"

        sides = set().union(*(cross_sides[n] for n in c))
        legs = 2 + len(sides) if sides else None     # 3 = T (cross street on one side), 4 = through cross street
        control = ("signal" if _any_within(line, signals, cx, cy, CONTROL_FT)
                   else "stop" if _any_within(line, stops, cx, cy, CONTROL_FT) else "unknown")
        out.append({
            "id": f"osm-{min(c)}", "name": name, "station_ft": round(max(0.0, min(line.length_ft, st)), 1),
            "lat": round(lat, 7), "lon": round(lon, 7), "osm_node_ids": sorted(c), "control": control,
            "is_study": True, "provenance": "auto", "name_source": "osm", "legs": legs,
        })
    return {"corridor_name": corridor_name, "length_ft": round(line.length_ft, 1), "intersections": out,
            "corridor_highway": corridor_highway, "corridor_names": [n for n, _ in along_len.most_common()],
            "grade_separations": grade_separations(line, nodes, ways, corridor_ids, corridor_nodes, corridor_cores)}


GS_NEAR_FT = 120   # a crossing way with a corridor node this close (along the line) to where it crosses meets at grade


def _level(tags: dict) -> int:
    """Rough vertical level of a way from OSM tags: bridges up, tunnels down, `layer` when given."""
    try:
        return int(str(tags.get("layer", "")).split(";")[0])
    except ValueError:
        pass
    if tags.get("bridge") not in (None, "no"):
        return 1
    if tags.get("tunnel") not in (None, "no") or tags.get("covered") == "yes":
        return -1
    return 0


def grade_separations(line: Polyline, nodes: dict, ways: list[dict], corridor_ids: set[int], corridor_nodes: set[int],
                      corridor_cores: set[str]) -> list[dict]:
    """Roads that cross the corridor without meeting it (N7, #67): an overcrossing, undercrossing or freeway.

    A way crosses where consecutive nodes lie on opposite sides of the drawn line within the study limits. It meets
    the corridor at grade only when it shares a corridor node near that crossing (OSM's rule: roads that meet share
    a node; a bridge over a road doesn't). Crossings of the same road within CLUSTER_FT along the line (two
    carriageways of a freeway) are one grade separation. `relation` says whether the crossing road goes over or
    under the corridor, from bridge/tunnel/layer tags where OSM has them."""
    corridor_spans: list[tuple[float, float, int]] = []   # (from station, to station, level) of corridor way pieces
    for w in ways:
        if w["id"] in corridor_ids:
            lv = _level(w.get("tags", {}))
            st = [line.project(nodes[n]["lat"], nodes[n]["lon"]).station_ft for n in w.get("nodes", []) if n in nodes]
            for a, b in zip(st, st[1:]):
                corridor_spans.append((min(a, b), max(a, b), lv))
    # Nodes of any way carrying the corridor's name, even pieces too short to count as corridor ways (at the drawn
    # ends): a street meeting one of them meets the corridor (Dyer St, Union City, 2026-10-19).
    meet_nodes = set(corridor_nodes)
    for w in ways:
        if any(_core(n) in corridor_cores for n in _names(w.get("tags", {}))):
            meet_nodes.update(w.get("nodes", []))
    found: list[dict] = []
    for w in ways:
        if w["id"] in corridor_ids:
            continue
        tags = w.get("tags", {})
        names = [n for n in _names(tags) if _core(n) not in corridor_cores]
        wn = [n for n in w.get("nodes", []) if n in nodes]
        xy = [line.proj.to_xy(nodes[n]["lat"], nodes[n]["lon"]) for n in wn]
        sides = [line.side_xy(x, y) for x, y in xy]
        for k in range(len(wn) - 1):
            if sides[k] == 0 or sides[k + 1] == 0 or sides[k] == sides[k + 1]:
                continue
            pa, pb = line.project_xy(*xy[k]), line.project_xy(*xy[k + 1])
            t = pa.offset_ft / ((pa.offset_ft + pb.offset_ft) or 1)
            cx, cy = xy[k][0] + t * (xy[k + 1][0] - xy[k][0]), xy[k][1] + t * (xy[k + 1][1] - xy[k][1])
            pc = line.project_xy(cx, cy)
            if pc.offset_ft > ALONG_FT or not (0 <= pc.station_ext <= line.length_ft):
                continue
            meets = any(n in meet_nodes and abs(line.project(nodes[n]["lat"], nodes[n]["lon"]).station_ft
                                                    - pc.station_ft) <= GS_NEAR_FT for n in wn)
            if meets:
                continue
            lv = _level(tags)
            near_corr = [lvl for a, b, lvl in corridor_spans if a <= pc.station_ft <= b]
            clv = max(near_corr, key=abs) if near_corr else 0
            relation = "over" if lv > clv else "under" if lv < clv else "unknown"
            lat, lon = line.proj.to_ll(cx, cy)
            found.append({"name": " / ".join(names) or "Unnamed road", "station_ft": round(pc.station_ft, 1),
                          "lat": round(lat, 7), "lon": round(lon, 7), "highway": tags.get("highway"),
                          "relation": relation, "osm_way_ids": [w["id"]]})
    found.sort(key=lambda g: g["station_ft"])
    merged: list[dict] = []
    for g in found:
        prev = next((m for m in reversed(merged) if g["station_ft"] - m["station_ft"] <= CLUSTER_FT
                     and (m["name"] == g["name"] or "Unnamed road" in (m["name"], g["name"]))), None)
        if prev:
            prev["osm_way_ids"] = sorted(set(prev["osm_way_ids"]) | set(g["osm_way_ids"]))
            if prev["name"] == "Unnamed road":
                prev["name"] = g["name"]
            if prev["relation"] == "unknown":
                prev["relation"] = g["relation"]
            continue
        merged.append(g)
    for i, g in enumerate(merged):
        g["id"] = f"gs-{i + 1}"
    return merged


LEG_MIN_FT = 40.0   # a cross street must leave the corridor by this much to count as a leg on that side


def _leaving_side(line, nodes, proj, corridor_nodes, way_nodes, k, step) -> int:
    """Walk along a cross way from its corridor node; the side of the line it ends up on (0 if it never leaves)."""
    j = k + step
    while 0 <= j < len(way_nodes):
        n = way_nodes[j]
        if n in proj and n not in corridor_nodes and proj[n].offset_ft >= LEG_MIN_FT:
            return line.side_xy(*line.proj.to_xy(nodes[n]["lat"], nodes[n]["lon"]))
        j += step
    return 0


def _any_within(line: Polyline, pts: list[dict], cx: float, cy: float, ft: float) -> bool:
    for p in pts:
        x, y = line.proj.to_xy(p["lat"], p["lon"])
        if math.hypot(x - cx, y - cy) <= ft:
            return True
    return False


def segments(intersections: list[dict], length_ft: float) -> list[dict]:
    """Segments between adjacent study intersections and the study limits A/B, lengths along the line."""
    pts = [{"id": "A", "name": "Study start (A)", "station_ft": 0.0}]
    pts += sorted((i for i in intersections if i["is_study"]), key=lambda i: i["station_ft"])
    pts += [{"id": "B", "name": "Study end (B)", "station_ft": length_ft}]
    if len(pts) > 2 and pts[1]["station_ft"] <= STUB_FT:
        pts.pop(0)
    if len(pts) > 2 and length_ft - pts[-2]["station_ft"] <= STUB_FT:
        pts.pop()
    out = []
    for a, b in zip(pts, pts[1:]):
        ft = b["station_ft"] - a["station_ft"]
        if ft <= 0:
            continue
        out.append({"id": f"seg:{a['id']}:{b['id']}", "from_id": a["id"], "to_id": b["id"],
                    "name": f"{a['name']} – {b['name']}", "from_station_ft": a["station_ft"],
                    "to_station_ft": b["station_ft"], "length_ft": round(ft, 1), "length_mi": round(ft / FT_PER_MI, 4)})
    return out


# -- storage -----------------------------------------------------------------------------------------
def _load(db: Database, sid: str) -> dict | None:
    c = db.one("SELECT * FROM corridor WHERE study_id = ?", (sid,))
    if not c:
        return None
    rows = db.query("SELECT * FROM intersection WHERE study_id = ? ORDER BY station_ft", (sid,))
    ints = [{**r, "is_study": bool(r["is_study"]), "osm_node_ids": json.loads(r["osm_node_ids"])} for r in rows]
    for i in ints:
        i.pop("study_id", None)
    aadt = {r["segment_id"]: r["aadt"] for r in db.query("SELECT * FROM segment_aadt WHERE study_id = ?", (sid,))}
    segs = segments(ints, c["length_ft"])
    for s in segs:
        s["aadt"] = aadt.get(s["id"])
    line = json.loads(c["line_json"])
    hw, gs, cn = c.get("corridor_highway"), c.get("grade_separations_json"), c.get("corridor_names_json")
    if gs is None or cn is None:   # drawn before #67/#53: detect from the cached OSM response, never a new download
        raw = _cached_overpass(db, overpass_query([tuple(p) for p in line]))
        if raw is not None:
            found = detect(raw, [tuple(p) for p in line])
            hw, gs, cn = found["corridor_highway"], json.dumps(found["grade_separations"]), json.dumps(found["corridor_names"])
            db.execute("UPDATE corridor SET corridor_highway = ?, grade_separations_json = ?, corridor_names_json = ? "
                       "WHERE study_id = ?", (hw, gs, cn, sid))
    return {"line": line, "length_ft": c["length_ft"],
            "length_mi": round(c["length_ft"] / FT_PER_MI, 4), "corridor_name": c["corridor_name"],
            "corridor_highway": hw, "is_freeway": hw == "motorway",
            "grade_separations": json.loads(gs) if gs else [],
            "corridor_names": json.loads(cn) if cn else ([c["corridor_name"]] if c["corridor_name"] else []),
            "intersections": ints, "segments": segs, "detected_at": c["detected_at"]}


def network(db: Database, sid: str) -> dict:
    s = study_mod.require(db, sid)
    net = _load(db, sid)
    base = {"radius_ft": s["radius_ft"], "buffer_ft": s["buffer_ft"]}
    if not net:
        return {**base, "line": None, "intersections": [], "segments": [], "buffer_ring": None,
                "grade_separations": [], "is_freeway": False, "corridor_highway": None}
    ring = buffer_ring(Polyline([tuple(p) for p in net["line"]]), s["buffer_ft"])
    return {**base, **net, "buffer_ring": ring}


def save_corridor(db: Database, sid: str, line: list[tuple[float, float]], osm: dict) -> dict:
    found = detect(osm, line)
    with db.transaction() as conn:
        conn.execute("DELETE FROM intersection WHERE study_id = ?", (sid,))
        conn.execute("DELETE FROM segment_aadt WHERE study_id = ?", (sid,))
        conn.execute("INSERT OR REPLACE INTO corridor (study_id, line_json, length_ft, corridor_name, detected_at, "
                     "corridor_highway, grade_separations_json, corridor_names_json) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?)",
                     (sid, json.dumps([list(p) for p in line]), found["length_ft"], found["corridor_name"],
                      found["corridor_highway"], json.dumps(found["grade_separations"]), json.dumps(found["corridor_names"])))
        for i in found["intersections"]:
            conn.execute("INSERT INTO intersection (study_id, id, name, station_ft, lat, lon, osm_node_ids, control, "
                         "is_study, provenance, name_source, legs) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (sid, i["id"], i["name"], i["station_ft"], i["lat"], i["lon"], json.dumps(i["osm_node_ids"]),
                          i["control"], 1, "auto", "osm", i.get("legs")))
    return network(db, sid)


def _line(db: Database, sid: str) -> Polyline:
    c = db.one("SELECT line_json FROM corridor WHERE study_id = ?", (sid,))
    if not c:
        raise HTTPException(409, "Draw the corridor first.")
    return Polyline([tuple(p) for p in json.loads(c["line_json"])])


def add_intersection(db: Database, sid: str, lat: float, lon: float, name: str) -> dict:
    line = _line(db, sid)
    p = line.project(lat, lon)
    if p.station_ext < -END_TOL_FT or p.station_ext > line.length_ft + END_TOL_FT:
        raise ValueError("That point is outside the study limits (A–B).")
    name = (name or "").strip() or "New intersection"
    iid = "usr-" + uuid.uuid4().hex[:8]
    db.execute("INSERT INTO intersection (study_id, id, name, station_ft, lat, lon, osm_node_ids, control, is_study, "
               "provenance, name_source) VALUES (?,?,?,?,?,?,'[]','unknown',1,'manual','user')",
               (sid, iid, name, round(max(0.0, min(line.length_ft, p.station_ft)), 1), lat, lon))
    return network(db, sid)


def edit_intersection(db: Database, sid: str, iid: str, changes: dict) -> dict:
    cur = db.one("SELECT * FROM intersection WHERE study_id = ? AND id = ?", (sid, iid))
    if not cur:
        raise HTTPException(404, "Intersection not found.")
    sets, vals = [], []
    if "name" in changes:
        name = (changes["name"] or "").strip()
        if not name:
            raise ValueError("The intersection needs a name.")
        sets += ["name = ?", "name_source = 'user'"]
        vals.append(name)
    if "is_study" in changes:
        sets.append("is_study = ?")
        vals.append(int(bool(changes["is_study"])))
    if "legs" in changes:
        v = changes["legs"]
        if v is not None and not 3 <= v <= 6:
            raise ValueError("An intersection has 3 to 6 legs.")
        sets.append("legs = ?")
        vals.append(v)
    for k in ("major_aadt", "minor_aadt"):
        if k in changes:
            v = changes[k]
            if v is not None and v < 0:
                raise ValueError("AADT can't be negative.")
            sets.append(f"{k} = ?")
            vals.append(v)
    if sets:
        db.execute(f"UPDATE intersection SET {', '.join(sets)} WHERE study_id = ? AND id = ?", (*vals, sid, iid))
    return network(db, sid)


def remove_intersection(db: Database, sid: str, iid: str) -> dict:
    if db.execute("DELETE FROM intersection WHERE study_id = ? AND id = ?", (sid, iid)) == 0:
        raise HTTPException(404, "Intersection not found.")
    return network(db, sid)


def set_segment_aadt(db: Database, sid: str, seg_id: str, aadt: float | None) -> dict:
    if aadt is not None and aadt < 0:
        raise ValueError("AADT can't be negative.")
    if aadt is None:
        db.execute("DELETE FROM segment_aadt WHERE study_id = ? AND segment_id = ?", (sid, seg_id))
    else:
        db.execute("INSERT OR REPLACE INTO segment_aadt (study_id, segment_id, aadt) VALUES (?,?,?)", (sid, seg_id, aadt))
    return network(db, sid)


def clear_corridor(db: Database, sid: str) -> dict:
    with db.transaction() as conn:
        for t in ("intersection", "segment_aadt", "corridor"):
            conn.execute(f"DELETE FROM {t} WHERE study_id = ?", (sid,))
    return network(db, sid)


# -- API ---------------------------------------------------------------------------------------------
class CorridorIn(BaseModel):
    line: list[tuple[float, float]] = Field(min_length=2, max_length=500)


class IntersectionIn(BaseModel):
    lat: float
    lon: float
    name: str = ""


class IntersectionPatch(BaseModel):
    name: str | None = None
    is_study: bool | None = None
    major_aadt: float | None = None
    minor_aadt: float | None = None
    legs: int | None = None


class SegmentPatch(BaseModel):
    aadt: float | None = None


router = APIRouter()


def _db(request: Request) -> Database:
    return request.app.state.db


@router.get("/studies/{sid}/network")
def get_network(sid: str, request: Request) -> dict:
    return network(_db(request), sid)


@router.put("/studies/{sid}/corridor")
def put_corridor(sid: str, body: CorridorIn, request: Request) -> dict:
    db = _db(request)
    study_mod.require(db, sid)
    for lat, lon in body.line:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Line points must be (lat, lon) in degrees.")
    try:
        st = request.app.state
        osm = fetch_overpass(db, overpass_query(body.line), transport=getattr(st, "overpass", None),
                             retries=getattr(st, "overpass_retries", 3))
    except NetworkError as e:
        raise HTTPException(502, str(e)) from e
    return save_corridor(db, sid, body.line, osm)


@router.delete("/studies/{sid}/corridor")
def delete_corridor(sid: str, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return clear_corridor(_db(request), sid)


@router.post("/studies/{sid}/intersections", status_code=201)
def post_intersection(sid: str, body: IntersectionIn, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return add_intersection(_db(request), sid, body.lat, body.lon, body.name)


@router.patch("/studies/{sid}/intersections/{iid}")
def patch_intersection(sid: str, iid: str, body: IntersectionPatch, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return edit_intersection(_db(request), sid, iid, body.model_dump(exclude_unset=True))


@router.delete("/studies/{sid}/intersections/{iid}")
def delete_intersection(sid: str, iid: str, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return remove_intersection(_db(request), sid, iid)


@router.patch("/studies/{sid}/segments/{seg_id}")
def patch_segment(sid: str, seg_id: str, body: SegmentPatch, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return set_segment_aadt(_db(request), sid, seg_id, body.aadt)
