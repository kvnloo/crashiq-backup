"""OSM + TIGER/Line street network (#229; user decision 2026-10-22, docs/03).

The corridor's OSM ways (Overpass) and the Census TIGER/Line road segments around them become one network, in the
element shape `osm.Network` reads:
- A TIGER segment that runs along an OSM way (sampled every SAMPLE_M along its length, ends left out; at least
  `coincide_share` of the samples within `coincide_m` of OSM) is that way: its names are added to the OSM way(s) it
  follows as `tiger:name`, and the way is marked `crashiq:source = both`. A street is never there twice.
- Otherwise it is a new way (`crashiq:source = tiger`). Its ends join the OSM network: at an OSM node within
  `snap_m`, else spliced into the OSM way passing within `snap_m`; else at its own TIGER node (shared with the other
  TIGER segments that end there). Its points get their own ids, so they are never intersections.
Name provenance (osm / tiger / both) is kept by `osm.Network` per street key and per node.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from .geo import LocalProjection

CONFIG = json.loads((Path(__file__).parent / "config" / "tiger.json").read_text())
SAMPLE_M = 10.0
END_M = 15.0               # a segment's ends touch the streets that cross it: not evidence of running along them
TIGER_NODE = 10 ** 12      # TIGER topology node ids live above OSM's
POINT_NODE = 2 * 10 ** 12  # a TIGER segment's inner points


def _seg_dist(p, a, b):
    """(distance, projected point) from p to segment a-b, in the projection's feet."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    q = (ax + t * dx, ay + t * dy)
    return math.hypot(p[0] - q[0], p[1] - q[1]), q, t


class _Grid:
    def __init__(self, cell_ft: float):
        self.cell, self.items = cell_ft, defaultdict(list)

    def key(self, x, y):
        return int(x // self.cell), int(y // self.cell)

    def add_segment(self, a, b, item):
        steps = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // self.cell) + 1)
        seen = set()
        for i in range(steps + 1):
            t = i / steps
            k = self.key(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            if k not in seen:
                seen.add(k)
                self.items[k].append(item)

    def near(self, x, y):
        cx, cy = self.key(x, y)
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out += self.items.get((cx + dx, cy + dy), [])
        return out


def _samples(pts_xy, step_ft, end_ft):
    """Points every step along the polyline, leaving out end_ft at each end."""
    seglens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts_xy, pts_xy[1:])]
    total = sum(seglens)
    out, s = [], end_ft
    while s <= total - end_ft:
        acc = 0.0
        for (a, b), L in zip(zip(pts_xy, pts_xy[1:]), seglens):
            if acc + L >= s and L > 0:
                t = (s - acc) / L
                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                break
            acc += L
        s += step_ft
    if not out and total > 0:                     # a short segment: its middle
        out.append(((pts_xy[0][0] + pts_xy[-1][0]) / 2, (pts_xy[0][1] + pts_xy[-1][1]) / 2))
    return out


def union(osm_raw: dict, tiger_edges: list[dict], line: list[tuple[float, float]], near_m: float) -> tuple[dict, dict]:
    """(elements, counts). `near_m`: TIGER segments with a point this close to the drawn line are used (the same reach
    as the corridor's Overpass query)."""
    M = 3.28084
    proj = LocalProjection.around(line)
    co, cs, sm = CONFIG["coincide_m"] * M, CONFIG["coincide_share"], CONFIG["snap_m"] * M
    nodes = {e["id"]: (e["lat"], e["lon"]) for e in osm_raw.get("elements", []) if e["type"] == "node"}
    ways = [dict(e, nodes=list(e["nodes"]), tags=dict(e.get("tags") or {}))
            for e in osm_raw.get("elements", []) if e["type"] == "way"]
    xy = {n: proj.to_xy(*p) for n, p in nodes.items()}
    lxy = [proj.to_xy(*p) for p in line]
    reach = near_m * M

    def near_line(p):
        return any(_seg_dist(p, a, b)[0] <= reach for a, b in zip(lxy, lxy[1:])) if len(lxy) > 1 else False

    grid = _Grid(max(co, sm) * 2)
    for wi, w in enumerate(ways):
        for i, (a, b) in enumerate(zip(w["nodes"], w["nodes"][1:])):
            if a in xy and b in xy:
                grid.add_segment(xy[a], xy[b], (wi, i))
    node_grid = _Grid(sm * 2)
    on_way = {n for w in ways for n in w["nodes"]}
    for n in on_way:
        if n in xy:
            node_grid.items[node_grid.key(*xy[n])].append(n)

    def nearest_way(p, within):
        best = None
        for wi, i in grid.near(*p):
            w = ways[wi]
            a, b = w["nodes"][i], w["nodes"][i + 1]
            d, q, t = _seg_dist(p, xy[a], xy[b])
            if d <= within and (best is None or d < best[0]):
                best = (d, wi, i, q)
        return best

    counts = Counter()
    extra_names: dict[int, list[str]] = defaultdict(list)
    new_ways, new_nodes = [], {}
    point_id = [POINT_NODE]
    spliced: dict[tuple, int] = {}

    def join(tnid, p_ll):
        p = proj.to_xy(*p_ll)
        best_n = min((n for n in node_grid.near(*p) if math.hypot(xy[n][0] - p[0], xy[n][1] - p[1]) <= sm),
                     key=lambda n: math.hypot(xy[n][0] - p[0], xy[n][1] - p[1]), default=None)
        if best_n is not None:
            return best_n
        hit = nearest_way(p, sm)
        nid = TIGER_NODE + int(tnid)
        if hit is not None:                       # splice into the OSM way (OSM lacks this corner)
            _, wi, i, q = hit
            key = (wi, i, round(q[0]), round(q[1]))
            if key in spliced:
                return spliced[key]
            ll = proj.to_ll(*q)
            new_nodes[nid] = ll
            xy[nid] = q
            spliced[key] = nid
            splices.append((wi, i, q, nid))
            counts["joined_by_splice"] += 1
            return nid
        if nid not in new_nodes:
            new_nodes[nid] = tuple(p_ll)
            xy[nid] = p
        return nid

    splices: list[tuple] = []
    for e in tiger_edges:
        pts = [tuple(p) for p in e["pts"]]
        pxy = [proj.to_xy(*p) for p in pts]
        if not any(near_line(p) for p in pxy + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(pxy, pxy[1:])]):
            continue
        counts["tiger_segments"] += 1
        samples = _samples(pxy, SAMPLE_M * M, END_M * M)
        hits = [nearest_way(p, co) for p in samples]
        matched = [h for h in hits if h]
        if samples and len(matched) / len(samples) >= cs:
            per_way = Counter(h[1] for h in matched)
            for wi, k in per_way.items():
                if k / len(samples) >= 0.3:
                    extra_names[wi] += e["names"]
            counts["coincide_with_osm"] += 1
            continue
        ids = [join(e["tnidf"], pts[0])]
        for p in pts[1:-1]:
            point_id[0] += 1
            new_nodes[point_id[0]] = p
            ids.append(point_id[0])
        ids.append(join(e["tnidt"], pts[-1]))
        names = e["names"]
        new_ways.append({"type": "way", "id": -int(e["tlid"]), "nodes": ids,
                         "tags": {"name": names[0], **({"alt_name": ";".join(names[1:])} if names[1:] else {}),
                                  "crashiq:source": "tiger", "tiger:tlid": str(e["tlid"])}})
        counts["added_from_tiger"] += 1
    # splice joined nodes into their OSM ways: per segment in order along it, last segment first so the earlier
    # indexes stay valid
    by_seg: dict[tuple[int, int], list] = defaultdict(list)
    for wi, i, q, nid in splices:
        a = xy[ways[wi]["nodes"][i]]
        by_seg[(wi, i)].append((math.hypot(q[0] - a[0], q[1] - a[1]), nid))
    for (wi, i) in sorted(by_seg, key=lambda k: (k[0], -k[1])):
        ways[wi]["nodes"][i + 1:i + 1] = [nid for _, nid in sorted(by_seg[(wi, i)])]
    for wi, w in enumerate(ways):
        w["tags"]["crashiq:source"] = "both" if wi in extra_names else "osm"
        if wi in extra_names:
            w["tags"]["tiger:name"] = ";".join(dict.fromkeys(extra_names[wi]))
    els = [{"type": "node", "id": n, "lat": p[0], "lon": p[1]} for n, p in nodes.items()]
    els += [{"type": "node", "id": n, "lat": p[0], "lon": p[1]} for n, p in new_nodes.items()]
    return {"elements": els + ways + new_ways}, dict(counts)


# -- the study's network: OSM (Overpass, cached) + the TIGER segments of the counties the line is in --------------------
def corridor_network(db, net: dict, tiger) -> tuple[dict, dict]:
    """(elements, info) for the locator and the name checks. `tiger`: a TigerCache, or None (OSM only)."""
    from . import network as network_mod
    from .sources import tiger_files
    line = [tuple(p) for p in net["line"]]
    raw = network_mod.fetch_overpass(db, network_mod.overpass_query(line))
    info = {"sources": ["osm"], "tiger_vintage": None, "tiger_counties": [], "tiger_pending": {}, "tiger_errors": {}}
    if tiger is None:
        return raw, info
    info["tiger_vintage"] = tiger.vintage
    pad = network_mod.QUERY_RADIUS_M / 111_000 * 2
    s, n = min(p[0] for p in line) - pad, max(p[0] for p in line) + pad
    w, e = min(p[1] for p in line) - pad * 1.25, max(p[1] for p in line) + pad * 1.25
    edges = []
    for fips in tiger_files.counties_for(line):
        if tiger.ready(fips):
            edges += tiger.edges_in(fips, (s, w, n, e))
            info["tiger_counties"].append(fips)
        else:
            info["tiger_pending"][f"tiger_{tiger.vintage}_{fips}"] = str(tiger.path(fips))
            if tiger.error(fips):
                info["tiger_errors"][fips] = tiger.error(fips)
    if info["tiger_counties"]:
        raw, counts = union(raw, edges, line, network_mod.QUERY_RADIUS_M)
        info.update(sources=["osm", "tiger"], **counts)
    return raw, info


def alt_names(raw: dict, net: dict) -> dict:
    """TIGER names for the corridor (names on the corridor's OSM ways) and for each study intersection (names of the
    roads through it, TIGER ways included), beyond what OSM calls them: {"corridor": [...], "intersections": {id: []}}."""
    from . import grade
    from .names import same_core, street_key
    from .osm import metres
    ck = grade.corridor_keys(net)
    on_corridor = lambda nm: (k := street_key(nm)) is not None and any(same_core(k, x) for x in ck)   # noqa: E731
    nodes = {e["id"]: (e["lat"], e["lon"]) for e in raw.get("elements", []) if e["type"] == "node"}
    ways = [e for e in raw.get("elements", []) if e["type"] == "way"]
    corridor = []
    for w in ways:
        t = w.get("tags") or {}
        osm_names = [t.get(k) for k in ("name", "ref") if t.get(k)]
        if t.get("tiger:name") and any(on_corridor(nm) for nm in osm_names):
            corridor += [x for x in t["tiger:name"].split(";") if x and not on_corridor(x)]
    tiger_names = {}
    for w in ways:
        t = w.get("tags") or {}
        if t.get("crashiq:source") == "tiger":
            names = [t["name"]] + [x for x in str(t.get("alt_name") or "").split(";") if x]
        else:
            names = [x for x in str(t.get("tiger:name") or "").split(";") if x]
        if names:
            for n in w["nodes"]:
                tiger_names.setdefault(n, []).extend(names)
    out = {}
    for it in net.get("intersections") or []:
        if not it.get("is_study") or it.get("lat") is None:
            continue
        own = grade.keys_of([it.get("name")])
        near = set(it.get("osm_node_ids") or []) | {n for n in tiger_names if n in nodes
                                                     and metres(nodes[n], (it["lat"], it["lon"])) <= 25}
        found = []
        for n in near:
            for nm in tiger_names.get(n, []):
                k = street_key(nm)
                if k and not on_corridor(nm) and not any(same_core(k, x) for x in own) and nm not in found:
                    found.append(nm)
        if found:
            out[it["id"]] = found
    return {"corridor": list(dict.fromkeys(corridor)), "intersections": out}


def with_alt(net: dict, alt: dict | None) -> dict:
    """The study network with the TIGER names a pull found (the pull and the assignment use the same ones)."""
    if not alt:
        return net
    its = [{**i, "alt_names": alt["intersections"].get(i["id"], [])} if i["id"] in alt["intersections"] else i
           for i in net.get("intersections") or []]
    return {**net, "intersections": its, "corridor_alt_names": alt.get("corridor") or []}


def tiger_roads_near(tiger, lat: float, lon: float, radius_m: float) -> list[dict]:
    """Tags ({name, alt_name}) of the TIGER/Line roads within radius_m of a point (#229; for the FARS road check)."""
    from .sources import tiger_files
    if tiger is None:
        return []
    d = radius_m / 111_000
    proj = LocalProjection.around([(lat, lon)])
    p, r = proj.to_xy(lat, lon), radius_m * 3.28084
    out = []
    for fips in tiger_files.counties_for([(lat, lon)]):
        if not tiger.path(fips).exists():
            continue
        for e in tiger.edges_in(fips, (lat - d, lon - d * 1.25, lat + d, lon + d * 1.25)):
            xy = [proj.to_xy(*q) for q in e["pts"]]
            if any(_seg_dist(p, a, b)[0] <= r for a, b in zip(xy, xy[1:])):
                out.append({"name": e["names"][0], "alt_name": ";".join(e["names"][1:])})
    return out
