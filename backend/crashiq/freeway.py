"""Freeway crashes placed by the report (#246; user decision in principle 2026-10-23, docs/03 D1; method in
knowledge/methods/freeway-crashes.md). Gated: the tier `freeway_offset` auto-places only when config allows it.

CHP describes a freeway crash by the road it was on (PrimaryRoad: the freeway with its travel direction, a ramp, or a
connector "X TO Y"), a reference street (SecondaryRoad) and how far from it, in which compass direction
(SecondaryDistance / SecondaryDirection, read as written). The reference street usually crosses over or under the
freeway, so an intersection matcher never finds the two roads meeting.

- Mainline: start where the reference street crosses the lanes of the stated travel direction; go the stated distance
  along those lanes, toward the stated compass direction.
- Ramp ("NB I5 OFF RAMP"): start at the ramp terminal, where a ramp joined to that route and direction meets the
  reference street; under RAMP_AT_TERMINAL_FT the crash is at the terminal, else that far along the ramp.
- Connector ("I-680 S/B TO SR-4"): read by what the reference street is (#259). The second route (SR-4): on the
  connector, start where it reaches that route and go the stated distance along it (the second route's stated
  direction picks the connector). The first route: the same, from where the connector leaves it. A local street
  (user worked example 4630945, "SR-60 W/B TO I-10" / EUCLID AVENUE): the crash is still on the first route's lanes,
  placed as mainline from that street's crossing (report 'connector_local').
A place found in more than one spot (crossings or terminals further apart than SAME_SPOT_FT) is never guessed.
Works on raw Overpass elements (highway, ref, oneway tags); coordinates are computed here, never by a model.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass

from .geo import LocalProjection
from .names import route_numbers, same_core, street_key

FT_PER_M = 3.28084
RAMP_AT_TERMINAL_FT = 400.0
CROSS_FT = 300.0              # the reference street passes this close to the lanes: it meets them (#259)
DISTINCT_FT = 3300.0          # meeting spots further apart than this are two places, never guessed between (#259)
STRICT = True                 # also skip a street meeting either carriageway in two places (#259, as the reference)
SAME_SPOT_FT = 600.0          # crossings / terminals this close are one place (a wide interchange, two carriageways)
DIRS = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}
TRAVEL = re.compile(r"\b(?:([NSEW])\s*/?\s*B|(NORTH|SOUTH|EAST|WEST)\s*BOUND)\b")
RAMP = re.compile(r"\b(?:ON|OFF)?[\s-]*RAMPS?\b|\bON[\s-]?RAMP\b|\bOFF[\s-]?RAMP\b|\bONR\b|\bOFR\b")
CONNECTOR = re.compile(r"^(?P<a>.+?)\s+TO\s+(?P<b>.+)$")
MOTORWAY = ("motorway", "trunk")
LINK = ("motorway_link", "trunk_link")


@dataclass
class Spot:
    lat: float
    lon: float
    kind: str                # mainline | ramp | connector
    note: str = ""
    report: str = ""         # what the report describes: an "X TO Y" naming a local street is "connector_local"

    def __post_init__(self):
        self.report = self.report or self.kind


def _travel(text: str) -> str | None:
    m = TRAVEL.search(text.upper())
    if not m:
        return None
    return m.group(1) or m.group(2)[0]


def parse(crash: dict) -> dict | None:
    """What the report says, or None when it isn't a freeway description this rule reads."""
    p, s = str(crash.get("primary_road") or "").upper(), str(crash.get("secondary_road") or "").upper()
    if not p or not s:
        return None
    d = str(crash.get("offset_dir") or "").strip()[:1].upper()
    off = float(crash.get("offset_ft") or 0.0)
    m = CONNECTOR.match(p)
    if m and route_numbers(m.group("a")) and route_numbers(m.group("b")):
        x, y, rs = route_numbers(m.group("a")), route_numbers(m.group("b")), route_numbers(s)
        # what the distance is measured from (#259, user worked example 4630945): a local cross street -> its crossing
        # of X, on X's lanes; Y -> along the connector from Y (Martinez); X -> along the connector from X
        frm = "y" if rs & y else "x" if rs & x else "street" if not rs else "y"
        return {"kind": "connector", "route": x, "to": y, "travel": _travel(m.group("a")),
                "to_travel": _travel(m.group("b")), "street": s, "from": frm, "dir": d if d in DIRS else None,
                "offset_ft": off}
    routes = route_numbers(p)
    if not routes:
        return None
    kind = "ramp" if RAMP.search(p) else "mainline"
    if kind == "mainline" and not crash.get("is_freeway"):
        return None              # a route number on a city street (Pacific Coast Hwy) isn't the freeway mainline
    return {"kind": kind, "route": routes, "travel": _travel(p), "street": s, "dir": d if d in DIRS else None,
            "offset_ft": off}


class _Net:
    """The raw elements as a small graph in feet (one local projection)."""

    def __init__(self, raw: dict):
        els = raw.get("elements", [])
        self.ll = {e["id"]: (e["lat"], e["lon"]) for e in els if e["type"] == "node"}
        self.ways = [e for e in els if e["type"] == "way" and all(n in self.ll for n in e.get("nodes", []))]
        pts = list(self.ll.values())[:1] or [(0.0, 0.0)]
        self.proj = LocalProjection.around(pts)
        self.xy = {n: self.proj.to_xy(*p) for n, p in self.ll.items()}
        self.ways_at: dict[int, list[dict]] = defaultdict(list)
        for w in self.ways:
            for n in w["nodes"]:
                self.ways_at[n].append(w)

    @staticmethod
    def routes(w) -> set[str]:
        t = w.get("tags") or {}
        return route_numbers(" ".join(str(t.get(k) or "") for k in ("ref", "name")))

    def lanes(self, routes: set[str], travel: str | None) -> list[dict]:
        """Main-lane ways of the route whose overall heading matches the travel direction (oneway carriageways)."""
        out = []
        for w in self.ways:
            if (w.get("tags") or {}).get("highway") not in MOTORWAY or not (self.routes(w) & routes):
                continue
            if travel and len(w["nodes"]) > 1:
                a, b = self.xy[w["nodes"][0]], self.xy[w["nodes"][-1]]
                if a != b and _ang(_bearing(a, b), DIRS[travel]) > 75:
                    continue
            out.append(w)
        return out

    def named(self, street: str) -> list[dict]:
        k = street_key(street)
        rn = route_numbers(street)
        out = []
        for w in self.ways:
            t = w.get("tags") or {}
            if t.get("highway") in MOTORWAY + LINK:
                continue
            names = [v for key in ("name", "alt_name", "ref") for v in str(t.get(key) or "").split(";") if v]
            if (k and any((wk := street_key(v)) and same_core(k, wk) for v in names)) or (rn and self.routes(w) & rn):
                out.append(w)
        return out


def _bearing(a, b) -> float:
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360       # xy = (east, north)


def _ang(x: float, y: float) -> float:
    return abs((x - y + 180) % 360 - 180)


def _cross(p1, p2, q1, q2):
    """Where segment p1-p2 crosses q1-q2 (xy), or None."""
    d = (p2[0] - p1[0]) * (q2[1] - q1[1]) - (p2[1] - p1[1]) * (q2[0] - q1[0])
    if abs(d) < 1e-9:
        return None
    t = ((q1[0] - p1[0]) * (q2[1] - q1[1]) - (q1[1] - p1[1]) * (q2[0] - q1[0])) / d
    u = ((q1[0] - p1[0]) * (p2[1] - p1[1]) - (q1[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return None


def _one_spot(points: list) -> tuple | None:
    """The points are one place (within SAME_SPOT_FT of each other): their middle; else None (never a guess)."""
    if not points:
        return None
    if any(math.hypot(a[0] - b[0], a[1] - b[1]) > SAME_SPOT_FT for a in points for b in points):
        return None
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def _walk(net: _Net, ways: list[dict], start, dist_ft: float, compass: str | None):
    """From `start` (xy, on one of `ways`), go dist_ft along them: first toward the compass direction (as written),
    then along the road as it bends."""
    if not dist_ft or not compass:
        return start
    want = DIRS[compass]
    # the polyline segments of these ways, as (a, b) in xy
    segs = [(net.xy[a], net.xy[b]) for w in ways for a, b in zip(w["nodes"], w["nodes"][1:])]
    cell = 200.0                     # segments by grid cell: each step looks only at the ones near it
    grid: dict[tuple, list] = defaultdict(list)
    for a, b in segs:
        for gx in range(int(min(a[0], b[0]) // cell), int(max(a[0], b[0]) // cell) + 1):
            for gy in range(int(min(a[1], b[1]) // cell), int(max(a[1], b[1]) // cell) + 1):
                grid[(gx, gy)].append((a, b))
    pos, left, prev = start, dist_ft, None
    for _ in range(500):
        best = None
        gx, gy = int(pos[0] // cell), int(pos[1] // cell)
        for a, b in {s for dx in (-1, 0, 1) for dy in (-1, 0, 1) for s in grid.get((gx + dx, gy + dy), ())}:
            for x, y in ((a, b), (b, a)):              # either way along a segment, toward the target direction
                if x == y:
                    continue
                d, q, t = _seg_point(pos, x, y)
                if d > 3.0:
                    continue
                head = _bearing(q, y)
                # the first step heads toward the compass direction; then the road is followed where it bends, the
                # continuation that turns least (#259: stopping at a bend left long offsets short, as Tester's
                # reference walk does not)
                if q == y or (prev is None and _ang(head, want) > 90) or (prev is not None and _ang(head, prev) > 100):
                    continue
                score = _ang(head, want) if prev is None else _ang(head, prev)
                if best is None or score < best[0]:
                    best = (score, q, y, head)
        if best is None:
            return pos
        _, q, y, head = best
        step = math.hypot(y[0] - q[0], y[1] - q[1])
        if step >= left:
            f = left / step
            return (q[0] + f * (y[0] - q[0]), q[1] + f * (y[1] - q[1]))
        pos, left, prev = y, left - step, head
    return pos


def _seg_point(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    q = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - q[0], p[1] - q[1]), q, t


def _hits(net: _Net, lanes: list[dict], streets: list[dict]) -> list:
    """(distance, point on the lanes): every crossing (0) and every closest approach within CROSS_FT."""
    cell = CROSS_FT
    grid: dict[tuple, list] = defaultdict(list)
    for v in streets:
        for c, d in zip(v["nodes"], v["nodes"][1:]):
            q1, q2 = net.xy[c], net.xy[d]
            for gx in range(int(min(q1[0], q2[0]) // cell) - 1, int(max(q1[0], q2[0]) // cell) + 2):
                for gy in range(int(min(q1[1], q2[1]) // cell) - 1, int(max(q1[1], q2[1]) // cell) + 2):
                    grid[(gx, gy)].append((q1, q2))
    hits = []
    for w in lanes:
        for a, b in zip(w["nodes"], w["nodes"][1:]):
            p1, p2 = net.xy[a], net.xy[b]
            near = {s for gx in range(int(min(p1[0], p2[0]) // cell), int(max(p1[0], p2[0]) // cell) + 1)
                    for gy in range(int(min(p1[1], p2[1]) // cell), int(max(p1[1], p2[1]) // cell) + 1)
                    for s in grid.get((gx, gy), ())}
            for q1, q2 in near:
                x = _cross(p1, p2, q1, q2)
                if x:
                    hits.append((0.0, x))
                    continue
                # closest approach of two segments that don't cross: an end of one to the other, kept on the lanes
                for d, q in (_seg_point(q1, p1, p2)[:2], _seg_point(q2, p1, p2)[:2],
                             _end_on(p1, q1, q2), _end_on(p2, q1, q2)):
                    if d <= CROSS_FT:
                        hits.append((d, q))
    return hits


def _places(net: _Net, lanes: list[dict], streets: list[dict]) -> int:
    """How many places DISTINCT_FT apart the street meets these lanes."""
    spots: list = []
    for _, q in sorted(_hits(net, lanes, streets), key=lambda h: h[0]):
        if all(math.hypot(q[0] - c[0], q[1] - c[1]) > DISTINCT_FT for c in spots):
            spots.append(q)
    return len(spots)


def _meeting(net: _Net, lanes: list[dict], streets: list[dict]):
    """Where the reference street meets the lanes. Where it crosses them: those crossings, when they are one place
    (SAME_SPOT_FT). Where it never crosses them (the map often draws an overpass without a crossing segment): its
    closest approach within CROSS_FT, when every approach is within DISTINCT_FT of it. Otherwise None, never a guess."""
    hits = _hits(net, lanes, streets)
    crossings = [q for d, q in hits if d == 0.0]
    if crossings:                    # the street crosses the lanes: those crossings, one place or none (as before #259)
        return _one_spot(crossings)
    if not hits:
        return None
    hits.sort(key=lambda h: h[0])
    first = hits[0][1]
    if any(math.hypot(q[0] - first[0], q[1] - first[1]) > DISTINCT_FT for _, q in hits):
        return None
    return first


def _end_on(p, q1, q2):
    """A lane vertex p within reach of street segment q1-q2: its distance, and p itself (it is on the lanes)."""
    return _seg_point(p, q1, q2)[0], p


def _linked(net: _Net, start_ways: list[dict], hops: int = 6) -> set[int]:
    """Ids of the ramp (link) ways reachable from these ways through shared nodes."""
    seen, frontier = set(), list(start_ways)
    for _ in range(hops):
        nxt = []
        for w in frontier:
            for n in w["nodes"]:
                for v in net.ways_at[n]:
                    if v["id"] not in seen and (v.get("tags") or {}).get("highway") in LINK:
                        seen.add(v["id"])
                        nxt.append(v)
        frontier = nxt
    return seen


def place(raw: dict, crash: dict) -> Spot | None:
    """The spot the report describes, or None (not a freeway description, nothing found, or more than one place)."""
    r = parse(crash)
    if r is None:
        return None
    net = _Net(raw)
    if r["kind"] == "mainline" or r.get("from") == "street":
        lanes = net.lanes(r["route"], r["travel"])
        streets = net.named(r["street"])
        other = route_numbers(r["street"]) - r["route"]
        if other:                    # the reference road is another freeway (I-5 / SR-91): its main lanes too (#259)
            # (not the ways carrying both numbers: where the routes run together they don't cross)
            streets += [w for w in net.lanes(other, None) if not (net.routes(w) & r["route"])]
        start = _meeting(net, lanes, streets)
        if start is None or (STRICT and _places(net, net.lanes(r["route"], None), streets) > 1):
            return None
        # the middle of several crossings (two carriageways, a split way) can lie between the lanes: walk from the
        # nearest point on them (#259: otherwise the walk never started and the offset was lost)
        start = min((_seg_point(start, net.xy[a], net.xy[b]) for w in lanes for a, b in zip(w["nodes"], w["nodes"][1:])),
                    key=lambda h: h[0])[1]
        end = _walk(net, lanes, start, r["offset_ft"], r["dir"])
        return Spot(*net.proj.to_ll(*end), "mainline", f"{r['offset_ft']:g} ft {r['dir'] or ''} of the crossing".strip(),
                    report="connector_local" if r["kind"] == "connector" else r["kind"])
    if r["kind"] == "ramp":
        lanes = net.lanes(r["route"], r["travel"])
        ramps = _linked(net, lanes)
        streets = net.named(r["street"])
        street_nodes = {n for v in streets for n in v["nodes"]}
        terms = [net.xy[n] for w in net.ways if w["id"] in ramps for n in (w["nodes"][0], w["nodes"][-1])
                 if n in street_nodes]
        start = _one_spot(terms)
        if start is None:
            return None
        if r["offset_ft"] < RAMP_AT_TERMINAL_FT:
            return Spot(*net.proj.to_ll(*start), "ramp", "at the ramp terminal")
        ramp_ways = [w for w in net.ways if w["id"] in ramps]
        end = _walk(net, ramp_ways, start, r["offset_ft"], r["dir"])
        return Spot(*net.proj.to_ll(*end), "ramp", f"{r['offset_ft']:g} ft {r['dir'] or ''} along the ramp".strip())
    # connector: the links from the first route's lanes that reach the second route's lanes
    first = net.lanes(r["route"], r["travel"])
    from_first = _linked(net, first)
    joins: list = []
    # the second freeway's stated direction ("TO I-110 S/B") picks the connector that joins those lanes (#259: the
    # Tester's connector misses joined the other carriageway); both directions only when that finds no join
    for travel in dict.fromkeys((r["to_travel"], None)):
        second = net.lanes(r["to"], travel)
        from_second = _linked(net, second)
        conn = [w for w in net.ways if w["id"] in from_first and w["id"] in from_second]
        # measured from Y (where the connector reaches it), or from X when the cross street is X (where it leaves X)
        anchor = {n for w in (first if r["from"] == "x" else second) for n in w["nodes"]}
        joins = [net.xy[n] for w in conn for n in (w["nodes"][0], w["nodes"][-1]) if n in anchor]
        if joins:
            break
    if not joins:
        return None
    # a route usually has a connector to each direction of the other (I-680 S/B to SR-4 east and west): they reach
    # SR-4 far apart but share the trunk the crash is on. The spot is used when walking back from every join agrees
    ends = [_walk(net, conn, j, r["offset_ft"], r["dir"]) for j in joins]
    if r["offset_ft"] and r["dir"]:
        # a connector the stated direction doesn't follow (it leaves SR-4 east-west, the report says north) isn't
        # the one the crash is on: only walks that went most of the stated distance count
        ends = [e for j, e in zip(joins, ends) if math.hypot(e[0] - j[0], e[1] - j[1]) >= 0.5 * r["offset_ft"]]
    end = _one_spot(ends)
    if end is None:
        return None
    return Spot(*net.proj.to_ll(*end), "connector", f"{r['offset_ft']:g} ft {r['dir'] or ''} along the connector".strip())
