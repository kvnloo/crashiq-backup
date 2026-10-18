"""Weighted-clue placement (the user's method, 2026-10-18): every candidate location gets points from each clue
that agrees with it, weighted by how often that clue is right (log-odds, measured in clue_reliability.py on
Long Beach hidden GPS). The top candidate wins only if it is clearly ahead; otherwise review.

Clues used now: primary street, cross street, beat (patrol area). Beat territory is learned from crashes with a
known location in the *other* half of the data, never from the crash being placed.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from . import locate
from .names import same_core, same_street, similarity, street_key
from .osm import Network, metres

# ln(p / (1 - p)) from knowledge/methods/geocoding.md (Long Beach PD, 2023-25).
WEIGHTS = {"primary": 1.9, "secondary": 2.1, "beat": 2.9}


def name_evidence(k, keys) -> float:
    """+1 exact, +0.8 same name any suffix/directional, scaled typo match, -1 when nothing at the spot resembles it."""
    if not k:
        return 0.0
    best = -1.0
    for s in keys:
        if same_street(k, s):
            return 1.0
        if same_core(k, s):
            best = max(best, 0.8)
        else:
            sim = similarity(k, s)
            if sim >= 0.6:
                best = max(best, (sim - 0.6) / 0.4 * 0.7)
    return best


class BeatMap:
    """Which patrol beat a location belongs to, from (lat, lon, beat) of crashes with known locations."""

    CELL = 0.004  # ~400 m grid for neighbour lookup

    def __init__(self, points):
        self.grid = defaultdict(list)
        for lat, lon, beat in points:
            if beat:
                self.grid[(round(lat / self.CELL), round(lon / self.CELL))].append((lat, lon, str(beat).strip()))

    def majority(self, lat, lon, k=15):
        cx, cy = round(lat / self.CELL), round(lon / self.CELL)
        near = [p for dx in (-1, 0, 1) for dy in (-1, 0, 1) for p in self.grid.get((cx + dx, cy + dy), ())]
        if len(near) < 5:
            return None, 0.0
        near.sort(key=lambda p: metres((lat, lon), p[:2]))
        beat, n = Counter(p[2] for p in near[:k]).most_common(1)[0]
        return beat, n / min(k, len(near))


def keys_near(net: Network, node: int, r: float = 40.0) -> set:
    """Street names within r metres of a node (divided roads and plazas put the two streets on different nodes)."""
    grid = getattr(net, "_node_grid", None)
    if grid is None:
        grid = defaultdict(list)
        for m in net.keys_at:
            if m in net.coord:
                la, lo = net.coord[m]
                grid[(round(la / 0.0005), round(lo / 0.0005))].append(m)
        net._node_grid = grid
    la, lo = net.coord[node]
    cx, cy = round(la / 0.0005), round(lo / 0.0005)
    return {k for dx in (-1, 0, 1) for dy in (-1, 0, 1) for m in grid.get((cx + dx, cy + dy), ())
            if metres(net.coord[m], (la, lo)) <= r for k in net.keys_at[m]}


@dataclass
class Scored:
    node: int
    score: float
    parts: dict


def candidate_nodes(net: Network, crash: dict, aliases=None) -> set[int]:
    """Every intersection the street names could plausibly mean (shared nodes on any matching tier + typo candidates)."""
    kp, ks = street_key(crash.get("primary_road"), aliases), street_key(crash.get("secondary_road"), aliases)
    nodes = set()
    if kp and ks:
        a, b = locate._same_core_keys(net, kp), locate._same_core_keys(net, ks)
        b = [s for s in b if s not in a]
        if a and b:
            nodes |= set(locate._shared_nodes(net, a, b))
            if not nodes:
                nodes |= set(locate._near_nodes(net, a, b))
    nodes |= {n for n, _, _ in locate.candidates(net, crash, k=8, aliases=aliases)}
    # collapse nodes of one physical intersection
    out = []
    for n in sorted(nodes):
        if all(metres(net.coord[n], net.coord[m]) > locate.CLUSTER_M for m in out):
            out.append(n)
    return set(out)


def score(net: Network, crash: dict, beats: BeatMap | None, aliases=None) -> list[Scored]:
    kp, ks = street_key(crash.get("primary_road"), aliases), street_key(crash.get("secondary_road"), aliases)
    beat = str(crash.get("beat") or "").strip()
    out = []
    for n in candidate_nodes(net, crash, aliases):
        here = keys_near(net, n)
        parts = {"primary": WEIGHTS["primary"] * name_evidence(kp, here),
                 "secondary": WEIGHTS["secondary"] * name_evidence(ks, here)}
        if beats and beat:
            maj, share = beats.majority(*net.coord[n])
            if maj is not None and share >= 0.6:
                parts["beat"] = WEIGHTS["beat"] * (1 if maj == beat else -1)
        out.append(Scored(n, sum(parts.values()), parts))
    return sorted(out, key=lambda s: -s.score)


def place_scored(net: Network, crash: dict, beats: BeatMap | None, min_score: float, min_lead: float,
                 aliases=None) -> locate.Placement:
    ranked = score(net, crash, beats, aliases)
    if not ranked:
        return locate.Placement("review", note="scored: no candidates")
    top = ranked[0]
    lead = top.score - (ranked[1].score if len(ranked) > 1 else -10.0)
    if top.score < min_score or lead < min_lead:
        return locate.Placement("review", note=f"scored: top {top.score:.1f}, lead {lead:.1f}", p=top.score, p2=lead)
    kp = street_key(crash.get("primary_road"), aliases)
    prim = [s for s in net.keys_at[top.node] if kp and (same_core(kp, s) or similarity(kp, s) >= 0.75)]
    lat, lon = locate.offset(net, top.node, prim, crash.get("offset_ft"), crash.get("offset_dir"))
    return locate.Placement("scored", lat, lon, top.node, note=str({k: round(v, 1) for k, v in top.parts.items()}),
                            p=top.score, p2=lead)
