"""OSM + TIGER/Line street network (#229; user decision 2026-10-22, docs/03).

The corridor's OSM ways (Overpass) and the Census TIGER/Line road segments around them become one network, in the
element shape `osm.Network` reads:
- A TIGER segment that runs along an OSM way (sampled every SAMPLE_M along its length, ends left out; at least
  `coincide_share` of the samples within `coincide_m` of OSM) is that way: its names are added to the OSM way(s) it
  follows as `tiger:name`, and the way is marked `crashiq:source = both`. A street is never there twice.
- OSM first (#243, run 9): a TIGER segment running loosely along an OSM way of the same name (within `copy_m`, same
  direction, half its length) is TIGER's copy of that street and adds nothing: no way, node or meeting point. TIGER
  never adds a name OSM already has on another street here, neither onto an OSM way nor as a road of its own.
- Otherwise it is a new way (`crashiq:source = tiger`). Its ends join the OSM network: at an OSM node within
  `snap_m`, else spliced into the OSM way passing within `snap_m`; else at its own TIGER node (shared with the other
  TIGER segments that end there). Its points get their own ids, so they are never intersections. A join never
  makes a meeting point between two streets OSM already has meeting anywhere: TIGER adds only corners OSM lacks.
Name provenance (osm / tiger / both) is kept by `osm.Network` per street key and per node.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from .geo import LocalProjection

CONFIG = json.loads((Path(__file__).parent / "config" / "tiger.json").read_text())


def enabled() -> bool:
    """The OSM + TIGER union is on (config/tiger.json `union`). Off since run 9 (#243): OSM only."""
    return bool(CONFIG.get("union"))
SAMPLE_M = 10.0
PARALLEL_DEG = 20.0        # a TIGER road runs along an OSM way only in the same direction: a cross street next to a
                           # divided road's far carriageway (Masonic at Geary) is near it, not along it
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
    """(point, direction in degrees) every step along the polyline, leaving out end_ft at each end."""
    seglens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts_xy, pts_xy[1:])]
    total = sum(seglens)
    out, s = [], end_ft
    while s <= total - end_ft:
        acc = 0.0
        for (a, b), L in zip(zip(pts_xy, pts_xy[1:]), seglens):
            if acc + L >= s and L > 0:
                t = (s - acc) / L
                out.append(((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), _dir(a, b)))
                break
            acc += L
        s += step_ft
    if not out and total > 0:                     # a short segment: its middle
        out.append((((pts_xy[0][0] + pts_xy[-1][0]) / 2, (pts_xy[0][1] + pts_xy[-1][1]) / 2), _dir(pts_xy[0], pts_xy[-1])))
    return out


def _dir(a, b) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180


def _parallel(d1: float, d2: float) -> bool:
    return min(abs(d1 - d2), 180 - abs(d1 - d2)) <= PARALLEL_DEG


def union(osm_raw: dict, tiger_edges: list[dict], line: list[tuple[float, float]] | None, near_m: float) -> tuple[dict, dict]:
    """(elements, counts). `near_m`: TIGER segments with a point this close to the drawn line are used (the same reach
    as the corridor's Overpass query). `line` None: every segment given (a whole city, validate_geocode)."""
    M = 3.28084
    first = [(e["lat"], e["lon"]) for e in osm_raw.get("elements", []) if e["type"] == "node"][:1]
    proj = LocalProjection.around(line or first or [tuple(tiger_edges[0]["pts"][0])])
    co, cs, sm = CONFIG["coincide_m"] * M, CONFIG["coincide_share"], CONFIG["snap_m"] * M
    nodes = {e["id"]: (e["lat"], e["lon"]) for e in osm_raw.get("elements", []) if e["type"] == "node"}
    ways = [dict(e, nodes=list(e["nodes"]), tags=dict(e.get("tags") or {}))
            for e in osm_raw.get("elements", []) if e["type"] == "way"]
    xy = {n: proj.to_xy(*p) for n, p in nodes.items()}
    lxy = [proj.to_xy(*p) for p in line] if line else []
    reach = near_m * M

    def near_line(p):
        if not line:
            return True
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

    def nearest_way(p, within, direction=None):
        best = None
        for wi, i in grid.near(*p):
            w = ways[wi]
            a, b = w["nodes"][i], w["nodes"][i + 1]
            if direction is not None and not _parallel(direction, _dir(xy[a], xy[b])):
                continue
            d, q, t = _seg_dist(p, xy[a], xy[b])
            if d <= within and (best is None or d < best[0]):
                best = (d, wi, i, q)
        return best

    # OSM first (#243): the street names on each OSM way and node, and the pairs of streets OSM already has meeting
    from .names import _flat, drop_directional, street_key
    from .osm import NAME_TAGS

    def cores_of(names) -> set[str]:
        """Street names as compared here: flat core, a leading direction dropped (South Hill Street = Hill St)."""
        return {_flat(drop_directional(k).core) for k in (street_key(v) for nm in names for v in str(nm or "").split(";"))
                if k}
    way_cores = [cores_of((w.get("tags") or {}).get(t) for t in NAME_TAGS) for w in ways]
    node_cores: dict[int, set[str]] = defaultdict(set)
    for wi, w in enumerate(ways):
        for n in w["nodes"]:
            node_cores[n] |= way_cores[wi]
    osm_pairs = {frozenset((x, y)) for cs in node_cores.values() for x in cs for y in cs if x != y}
    osm_names = set().union(*way_cores) if way_cores else set()      # every street name OSM has here

    def keys_of(names) -> set[tuple[str, str | None]]:
        return {(_flat(drop_directional(k).core), k.suffix)
                for k in (street_key(v) for nm in names for v in str(nm or "").split(";")) if k}
    way_keys = [keys_of((w.get("tags") or {}).get(t) for t in NAME_TAGS) for w in ways]

    def same(a, b) -> bool:
        return a[0] == b[0] and (a[1] is None or b[1] is None or a[1] == b[1])

    by_core: dict[str, list[tuple[str | None, int]]] = defaultdict(list)    # core -> (street type, OSM way)
    for wi, ks in enumerate(way_keys):
        for c, suf in ks:
            by_core[c].append((suf, wi))

    def own_name(name: str, wi: int) -> bool:
        """The way's own name again, give or take a direction ("N Whitley Ave" on OSM's Whitley Avenue): it adds no
        street, and as a different key it would make a node where two Whitleys merge look like a corner (#243)."""
        return all(any(same(t, k) for k in way_keys[wi]) for t in keys_of([name]))

    def other_osm_street(name: str, wi: int) -> bool:
        """The name belongs to another OSM street here, so it is never added to this way (#243): Market St isn't
        given to OSM's Clayton Street, and Griffith Park Dr (OSM's Griffith Park Drive) isn't given to OSM's
        Griffith Park Road. A name OSM doesn't have, or this way's own name in another type, may be added."""
        for t in keys_of([name]):
            if any(same(t, k) for k in way_keys[wi]):
                continue                                   # this way already carries it
            if any(wj != wi and same(t, (t[0], suf)) for suf, wj in by_core.get(t[0], ())):
                return True                                # another OSM way carries it
        return False

    def osm_meets(tcores: set[str], ocores: set[str]) -> bool:
        return any(frozenset((t, o)) in osm_pairs for t in tcores for o in ocores if t != o)

    def copy_of_osm(samples, tcores: set[str]) -> bool:
        """The segment runs along an OSM way of the same name, if loosely (within COPY_M, same direction): TIGER's
        copy of a street OSM has. It adds nothing, so it can't add a node or a meeting point (#243)."""
        if not samples:
            return False
        hit = 0
        for p, d in samples:
            for wi, i in grid_copy.near(*p):
                w = ways[wi]
                a, b = w["nodes"][i], w["nodes"][i + 1]
                if way_cores[wi] & tcores and _parallel(d, _dir(xy[a], xy[b])) \
                        and _seg_dist(p, xy[a], xy[b])[0] <= copy_ft:
                    hit += 1
                    break
        return hit / len(samples) >= 0.5

    copy_ft = CONFIG.get("copy_m", 60) * M
    grid_copy = _Grid(copy_ft)
    for wi, w in enumerate(ways):
        for i, (a, b) in enumerate(zip(w["nodes"], w["nodes"][1:])):
            if a in xy and b in xy:
                grid_copy.add_segment(xy[a], xy[b], (wi, i))

    counts = Counter()
    extra_names: dict[int, list[str]] = defaultdict(list)
    along: set[int] = set()                 # OSM ways a TIGER segment runs along (geometry in both)
    new_ways, new_nodes = [], {}
    point_id = [POINT_NODE]
    spliced: dict[tuple, int] = {}

    def join(tnid, p_ll, tcores):
        p = proj.to_xy(*p_ll)
        nid = TIGER_NODE + int(tnid)

        def alone():
            if nid not in new_nodes:
                new_nodes[nid] = tuple(p_ll)
                xy[nid] = p
            return nid
        best_n = min((n for n in node_grid.near(*p) if math.hypot(xy[n][0] - p[0], xy[n][1] - p[1]) <= sm),
                     key=lambda n: math.hypot(xy[n][0] - p[0], xy[n][1] - p[1]), default=None)
        if best_n is not None:
            if osm_meets(tcores, node_cores.get(best_n, set())):
                counts["join_refused_osm_meets"] += 1     # OSM already has these two streets meeting (#243)
                return alone()
            return best_n
        hit = nearest_way(p, sm)
        if hit is not None and osm_meets(tcores, way_cores[hit[1]]):
            counts["join_refused_osm_meets"] += 1
            return alone()
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
        return alone()

    splices: list[tuple] = []
    for e in tiger_edges:
        pts = [tuple(p) for p in e["pts"]]
        pxy = [proj.to_xy(*p) for p in pts]
        if not any(near_line(p) for p in pxy + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(pxy, pxy[1:])]):
            continue
        counts["tiger_segments"] += 1
        samples = _samples(pxy, SAMPLE_M * M, END_M * M)
        hits = [nearest_way(p, co, d) for p, d in samples]
        matched = [h for h in hits if h]
        if samples and len(matched) / len(samples) >= cs:
            per_way = Counter(h[1] for h in matched)
            for wi, k in per_way.items():
                if k / len(samples) >= 0.5 or k >= 3:       # the way(s) it runs along, not one it brushes
                    along.add(wi)
                    # a name another OSM street has is never given to this one (#243: TIGER's "Market St" along
                    # OSM's Clayton Street made Market meet Clayton all along it)
                    new = [n for n in e["names"] if not own_name(n, wi)]
                    keep = [n for n in new if not other_osm_street(n, wi)]
                    if len(keep) < len(new):
                        counts["names_refused_osm_has"] += len(new) - len(keep)
                    if keep:
                        extra_names[wi] += keep
            counts["coincide_with_osm"] += 1
            continue
        tcores = cores_of(e["names"])
        if copy_of_osm(samples, tcores):
            counts["copy_of_osm_street"] += 1
            continue
        if tcores & osm_names:
            # a road under a name OSM already has here: a copy elsewhere or another street of that name; adding it
            # would let it meet streets in a second place (#243: TIGER's Hill St in Santa Monica beat OSM's
            # South Hill Street downtown). TIGER adds only streets OSM lacks
            counts["same_name_as_osm_street"] += 1
            continue
        ids = [join(e["tnidf"], pts[0], tcores)]
        for p in pts[1:-1]:
            point_id[0] += 1
            new_nodes[point_id[0]] = p
            ids.append(point_id[0])
        ids.append(join(e["tnidt"], pts[-1], tcores))
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
        w["tags"]["crashiq:source"] = "both" if wi in along else "osm"
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
