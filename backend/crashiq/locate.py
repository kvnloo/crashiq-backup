"""Place a crash from its report's street names (no GPS): intersection match, then offset.

Tiers, cheapest first (each crash records which one placed it):
  exact  – both streets match an OSM street key exactly (after normalization)
  unique_pair – the two streets, allowing only what the report leaves out (a leading or trailing direction, a
           suffix), meet at exactly one intersection: AVENUE J & 20TH ST W can only be West Avenue J & 20th Street
           West in Lancaster (#203; auto-places since the user's decision of 2026-10-22)
  fuzzy  – best-scoring key per street, above a threshold and clearly ahead of the runner-up
  jev    – leftovers only: Jev picks one of the top code-generated candidates, or "none"
  review – nothing confident; a person decides
Coordinates are always computed here, never by a model.
"""

from __future__ import annotations

import re

import json
from dataclasses import dataclass, field
from pathlib import Path

from .names import StreetKey, _flat, directions, drop_directional, same_core, same_street, similarity, street_key
from .osm import Network, bearing, metres, move

FT = 0.3048
CARDINAL = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}
CLUSTER_M = 80.0  # nodes of one intersection (divided roads, wide junctions) lie within this
NEAR_M = 30.0     # streets that never share a node (ramps, medians, plazas) but pass this close "meet"


@dataclass
class Placement:
    tier: str                      # address | exact | unique_pair | relaxed | near | fuzzy | jev | review
    lat: float | None = None
    lon: float | None = None
    node: int | None = None
    note: str = ""
    p: float | None = None         # Jev probability of its pick when tier == jev
    p2: float | None = None        # Jev probability of the runner-up (for the margin check)


def _keys_matching(net: Network, k: StreetKey) -> list[StreetKey]:
    return [s for s in _same_core_keys(net, k) if same_street(k, s)]


def _same_core_keys(net: Network, k: StreetKey) -> list[StreetKey]:
    from .names import drop_directional
    pool = net.by_core.get(k.core.replace(" ", ""), set()) | net.by_core.get(drop_directional(k).core.replace(" ", ""), set())
    return [s for s in pool if same_core(k, s)]


def _similar_pool(net: Network, k: StreetKey) -> list[StreetKey]:
    """Streets worth scoring for a typo: similar length (SequenceMatcher can't reach 0.6 otherwise)."""
    n = len(k.core.replace(" ", ""))
    return [s for s in net.streets if abs(len(s.core.replace(" ", "")) - n) <= max(3, n // 2)]


def _fuzzy(net: Network, k: StreetKey, min_score: float, margin: float) -> list[StreetKey]:
    scored = sorted(((similarity(k, s), s) for s in _similar_pool(net, k)), key=lambda t: -t[0])
    if not scored or scored[0][0] < min_score:
        return []
    best = scored[0][0]
    top = [s for sc, s in scored if sc >= best - 1e-9]
    runner = next((sc for sc, s in scored if sc < best - 1e-9), 0.0)
    if best - runner < margin and not all(t.core.replace(" ", "") == top[0].core.replace(" ", "") for t in top):
        return []
    return top


def _near_nodes(net: Network, a: list[StreetKey], b: list[StreetKey]) -> list[int]:
    """Closest node of street a to street b, if they pass within NEAR_M (one grid cell ~ 30 m)."""
    cell = lambda p: (round(p[0] / 0.0003), round(p[1] / 0.0003))
    grid: dict = {}
    for k in b:
        for n in net.all_nodes_of.get(k, ()):
            grid.setdefault(cell(net.coord[n]), []).append(n)
    best, bd = None, NEAR_M
    for k in a:
        for n in net.all_nodes_of.get(k, ()):
            cx, cy = cell(net.coord[n])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for m in grid.get((cx + dx, cy + dy), ()):
                        d = metres(net.coord[n], net.coord[m])
                        if d < bd:
                            best, bd = n, d
    return [best] if best is not None else []


def _shared_nodes(net: Network, a: list[StreetKey], b: list[StreetKey]) -> list[int]:
    na = {n for k in a for n in net.nodes_of.get(k, ())}
    nb = {n for k in b for n in net.nodes_of.get(k, ())}
    return sorted(na & nb)


def _one_intersection(net: Network, nodes: list[int]) -> int | None:
    """The node set must be one physical intersection; streets that cross twice are ambiguous."""
    if not nodes:
        return None
    pts = [net.coord[n] for n in nodes]
    if max(metres(pts[0], q) for q in pts) > CLUSTER_M * 2 or any(metres(p, q) > CLUSTER_M * 2 for p in pts for q in pts):
        return None
    lat = sum(p[0] for p in pts) / len(pts)
    lon = sum(p[1] for p in pts) / len(pts)
    return min(nodes, key=lambda n: metres(net.coord[n], (lat, lon)))


def _variants(net: Network, k: StreetKey) -> list[StreetKey]:
    """The streets a report's name can be when only what it leaves out may differ: a leading direction or a suffix
    it doesn't write is free; one it writes must match, or be absent on the map (#203)."""
    lead = k.core.split(" ", 1)[0] if drop_directional(k) != k else None
    out = []
    for s in _same_core_keys(net, k):
        if _flat(drop_directional(s).core) != _flat(drop_directional(k).core):
            continue
        s_lead = s.core.split(" ", 1)[0] if drop_directional(s) != s else None
        if lead and s_lead and s_lead != lead:
            continue
        if k.suffix and s.suffix and k.suffix != s.suffix:
            continue
        out.append(s)
    return out


def _trail_fits(net: Network, node: int, keys: list[StreetKey], trail: str | None) -> bool:
    """A trailing direction the report writes (20TH ST W) must be on a way through the node, or the way has none."""
    if trail is None:
        return True
    ways = [net.trail_at[(node, s)] for s in keys if (node, s) in net.trail_at]
    return not ways or any(w & {trail, None} for w in ways)      # near tier: the street may only pass close by


def _unique_pair(net: Network, crash: dict, kp: StreetKey, ks: StreetKey, aliases) -> Placement | None:
    a, b = _variants(net, kp), _variants(net, ks)
    b = [s for s in b if s not in a]
    if not a or not b:
        return None
    tp, ts = directions(crash.get("primary_road"), aliases)[1], directions(crash.get("secondary_road"), aliases)[1]
    nodes = [n for n in _shared_nodes(net, a, b) if _trail_fits(net, n, a, tp) and _trail_fits(net, n, b, ts)]
    node = _one_intersection(net, nodes)       # two or more places: not unique, the later tiers decide as before
    if node is None:
        return None
    lat, lon = offset(net, node, a, crash.get("offset_ft"), crash.get("offset_dir"))
    return Placement("unique_pair", lat, lon, node)


def offset(net: Network, node: int, primary: list[StreetKey], dist_ft: float | None, direction: str | None) -> tuple[float, float]:
    """Move dist_ft from the intersection along the primary road, toward the reported direction."""
    p0 = net.coord[node]
    if not dist_ft or not direction or direction[:1].upper() not in CARDINAL:
        return p0
    want = CARDINAL[direction[:1].upper()]
    nbrs = {m for k in primary for m in net.neighbors.get((node, k), ()) if m in net.coord}
    if nbrs:
        brgs = [bearing(p0, net.coord[m]) for m in nbrs]
        brg = min(brgs, key=lambda b: abs((b - want + 180) % 360 - 180))
        if abs((brg - want + 180) % 360 - 180) > 60:   # road doesn't run that way: fall back to compass
            brg = want
    else:
        brg = want
    return move(p0, brg, dist_ft * FT)


HOUSE = re.compile(r"^\s*(\d{1,5})\s+(.+)$|^(.+?)\s+(\d{1,5})\s*$")


class AddressIndex:
    """House-number lookup per street (OSM addresses), for reports that give an address, not a cross street."""

    def __init__(self, rows: list):
        self.by_street: dict[StreetKey, list[tuple[int, float, float]]] = {}
        for street, num, lat, lon in rows:
            k, m = street_key(street), re.match(r"\d+", str(num))
            if k and m:
                self.by_street.setdefault(k, []).append((int(m.group()), lat, lon))
        for v in self.by_street.values():
            v.sort()

    def lookup(self, k: StreetKey, number: int, max_gap: int = 60) -> tuple[float, float] | None:
        pts = [p for s, lst in self.by_street.items() if same_street(k, s) for p in lst]
        same_side = [p for p in pts if p[0] % 2 == number % 2] or pts
        if not same_side:
            return None
        lo = max((p for p in same_side if p[0] <= number), default=None)
        hi = min((p for p in same_side if p[0] >= number), default=None)
        if lo and hi and hi[0] - lo[0] <= max_gap * 2:
            f = 0 if hi[0] == lo[0] else (number - lo[0]) / (hi[0] - lo[0])
            return (lo[1] + f * (hi[1] - lo[1]), lo[2] + f * (hi[2] - lo[2]))
        near = min(same_side, key=lambda p: abs(p[0] - number))
        return (near[1], near[2]) if abs(near[0] - number) <= max_gap else None


def _house_address(crash: dict) -> tuple[StreetKey, int] | None:
    """'GENEVA AV 1677' or '975 3RD ST' in either field, on the same street as the other field (or alone)."""
    for f, other in (("secondary_road", "primary_road"), ("primary_road", "secondary_road")):
        m = HOUSE.match(crash.get(f) or "")
        if not m:
            continue
        num, street = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        k, ko = street_key(street), street_key(crash.get(other))
        if k and (not ko or same_core(k, ko)) and not re.fullmatch(r"\d+(ST|ND|RD|TH)", k.core):
            return k, int(num)
    return None


def place(net: Network, crash: dict, fuzzy_min: float = 0.88, fuzzy_margin: float = 0.05,
          addresses: AddressIndex | None = None, aliases: dict[str, str] | None = None) -> Placement:
    if addresses is not None:
        addr = _house_address(crash)
        if addr:
            pt = addresses.lookup(*addr)
            if pt:
                return Placement("address", pt[0], pt[1], note=f"{addr[1]} {addr[0].core}")
            return Placement("review", note="address not found")
    kp, ks = street_key(crash.get("primary_road"), aliases), street_key(crash.get("secondary_road"), aliases)
    if not kp or not ks:
        return Placement("review", note="missing street name")
    # Relax one thing at a time (2026-10-18, Atlantic Av & Atlantic Pl in Long Beach): first the leading
    # directional only, keeping the suffix ("ATLANTIC PL" -> North Atlantic Place); only then any suffix.
    def relaxed(k):
        keep_suffix = [s for s in _same_core_keys(net, k) if k.suffix is None or s.suffix is None or s.suffix == k.suffix]
        return keep_suffix or _same_core_keys(net, k)
    fuzzy = lambda k: _keys_matching(net, k) or relaxed(k) or _fuzzy(net, k, fuzzy_min, fuzzy_margin)
    tp, ts = directions(crash.get("primary_road"), aliases)[1], directions(crash.get("secondary_road"), aliases)[1]
    for tier, find, meet in (("exact", lambda k: _keys_matching(net, k), _shared_nodes),
                             ("relaxed", relaxed, _shared_nodes),
                             ("near", relaxed, _near_nodes),
                             ("fuzzy", fuzzy, _shared_nodes)):
        a, b = find(kp), find(ks)
        b = [s for s in b if s not in a]   # the two streets of a crash are never the same street
        if not a or not b:
            up = _unique_pair(net, crash, kp, ks, aliases) if tier == "exact" else None
            if up:
                return up
            continue
        nodes = meet(net, a, b)
        # the key drops a trailing direction: 20TH ST W must never land on 20th Street East, in any tier (#205)
        nodes = [n for n in nodes if _trail_fits(net, n, a, tp) and _trail_fits(net, n, b, ts)]
        node = _one_intersection(net, nodes)
        if node is None:
            up = _unique_pair(net, crash, kp, ks, aliases) if tier == "exact" else None
            if up:
                return up
            if nodes:
                return Placement("review", note=f"{tier}: streets meet in more than one place")
            continue
        lat, lon = offset(net, node, a, crash.get("offset_ft"), crash.get("offset_dir"))
        return Placement(tier, lat, lon, node)
    return Placement("review", note="no intersection of the two named streets")


def candidates(net: Network, crash: dict, k: int = 5, aliases: dict[str, str] | None = None) -> list[tuple[int, str, float]]:
    """Top-k intersections by combined name similarity, for a Jev choice. (node, label, score).
    Pairs that share a node, or pass within NEAR_M (ramps, medians, plazas), are both candidates."""
    kp, ks = street_key(crash.get("primary_road"), aliases), street_key(crash.get("secondary_road"), aliases)
    if not kp or not ks:
        return []
    def best_streets(key):
        sc = sorted(((max(similarity(key, s), 0.97 if same_core(key, s) else 0), s) for s in _similar_pool(net, key)),
                    key=lambda t: -t[0])[:10]
        return [(s, v) for v, s in sc if v >= 0.6]
    pa, pb = best_streets(kp), best_streets(ks)
    seen, out = set(), []
    for sa, va in pa:
        for sb, vb in pb:
            if sa == sb or same_core(sa, sb):
                continue
            nodes = _shared_nodes(net, [sa], [sb])
            node = _one_intersection(net, nodes) if nodes else _one_intersection(net, _near_nodes(net, [sa], [sb]))
            if node is None or any(metres(net.coord[node], net.coord[m]) < CLUSTER_M for m in seen):
                continue
            seen.add(node)
            out.append((node, f"{net.name(sa)} & {net.name(sb)}", (va + vb) / 2))
    return sorted(out, key=lambda t: -t[2])[:k]


def place_with_jev(net: Network, crash: dict, picker, city: str, k: int = 5,
                   aliases: dict[str, str] | None = None) -> Placement:
    """Leftovers only: Jev chooses among top-k code-generated candidate intersections, code places the point.
    The result is a *suggestion*; `Gate.auto` decides whether it may auto-place."""
    cands = candidates(net, crash, k, aliases)
    if not cands:
        return Placement("review", note="no candidates")
    labels = {}
    for node, label, _ in cands:
        labels.setdefault(label, node)   # same label at two nodes: keep the best-scored one
    choice, p, p2 = picker.pick(city, crash.get("primary_road") or "", crash.get("secondary_road") or "", list(labels))
    if choice is None or choice not in labels:
        return Placement("review", note="jev: none of these", p=p, p2=p2)
    node = labels[choice]
    kp = street_key(crash.get("primary_road"), aliases)
    prim = [s for s in net.streets if kp and similarity(kp, s) >= 0.6 and node in net.all_nodes_of.get(s, ())]
    lat, lon = offset(net, node, prim, crash.get("offset_ft"), crash.get("offset_dir"))
    return Placement("jev", lat, lon, node, note=choice, p=p, p2=p2)


CONFIG = Path(__file__).parent / "config" / "placement.json"


def configured_tiers() -> frozenset:
    return frozenset(json.loads(CONFIG.read_text())["auto_tiers"])


@dataclass
class Gate:
    """Seam 1 (docs/04 §2): which placements may auto-place. Thresholds are user decisions, kept as config.
    The tiers come from config/placement.json, each one a user decision (docs/03): `exact`, proven >= 98% (95% Wilson
    lower bound) on held-out data, and `unique_pair` (user, 2026-10-22: on statewide). Jev never auto-places."""
    auto_tiers: frozenset = field(default_factory=lambda: configured_tiers())
    jev_tau: float | None = None     # Jev pick probability needed to auto-place; None = never
    jev_margin: float = 0.0          # and its lead over the runner-up

    def auto(self, pl: Placement) -> bool:
        if pl.lat is None:
            return False
        if pl.tier == "jev":
            return self.jev_tau is not None and (pl.p or 0) >= self.jev_tau and (pl.p or 0) - (pl.p2 or 0) >= self.jev_margin
        return pl.tier in self.auto_tiers
