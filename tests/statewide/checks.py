"""The statewide harness's own street checks (#73), independent of the app's names.py. Pure functions, tested in
tests/tester/test_statewide_harness.py."""

from __future__ import annotations

import math
import re

import osm_local

DIRS = {"N", "S", "E", "W", "NORTH", "SOUTH", "EAST", "WEST", "NB", "SB", "EB", "WB"}
SUFFIX_WORDS = {"ST", "STREET", "AVE", "AV", "AVENUE", "BLVD", "BL", "BOULEVARD", "DR", "DRIVE", "RD", "ROAD", "WAY",
                "WY", "LN", "LANE", "CT", "COURT", "PL", "PLACE", "PKWY", "PARKWAY", "HWY", "HIGHWAY", "CIR", "CIRCLE",
                "TER", "TERRACE", "EXPY", "EXPRESSWAY", "PLZ", "PLAZA", "LOOP", "TRL", "TRAIL"}


def indep_core(name: str | None) -> str:
    """Street core for the Tester's own checks, independent of the app's names.py (v2, run 2 on): letters and digits
    only, leading directions and trailing suffixes dropped ('East Colorado Boulevard' -> 'COLORADO')."""
    toks = re.sub(r"[^A-Z0-9 ]", " ", (name or "").upper()).split()
    while len(toks) > 1 and toks[0] in DIRS:
        toks = toks[1:]
    while len(toks) > 1 and toks[-1] in SUFFIX_WORDS | DIRS:
        toks = toks[:-1]
    return "".join(toks)


_DIR1 = {"N": "N", "NORTH": "N", "S": "S", "SOUTH": "S", "E": "E", "EAST": "E", "W": "W", "WEST": "W"}


def lead_dir(name: str | None) -> str | None:
    """Leading direction of a street name (N/S/E/W), or None."""
    toks = re.sub(r"[^A-Z0-9 ]", " ", (name or "").upper()).split()
    return _DIR1.get(toks[0]) if len(toks) > 1 else None


def names_pair_v3(road_a: str | None, road_b: str | None, core: str, cross_cores: list[str],
                  corridor_dir: str | None = None) -> bool:
    """Silent-drop check v3 (PM, PR #148): one road IS the corridor street and the other IS a study cross street,
    compared as whole street cores ('OLD MIDDLEFIELD WY' is not Middlefield Rd; v2 matched substrings). A road whose
    leading direction is the opposite of the corridor's ('W COLORADO BL' for East Colorado) doesn't count."""
    crosses = {c for c in cross_cores if len(c) >= 3 and c != core}
    if len(core) < 3 or not crosses:
        return False
    for a, b in ((road_a, road_b), (road_b, road_a)):
        d = lead_dir(a)
        if corridor_dir and d and d != corridor_dir:
            continue
        if indep_core(a) == core and indep_core(b) in crosses:
            return True
    return False


def silent_drops_v3(expected: set[str], got: set[str], refiled: list[dict]) -> list[str]:
    """Expected ids the app didn't pull, less refiled copies whose kept twin was pulled (the app's #81 log
    `same_crash_refiled`: [{'kept': id, 'dropped': [ids]}])."""
    twin_pulled = {str(d) for g in refiled if str(g.get("kept")) in got for d in g.get("dropped", [])}
    return sorted(expected - got - twin_pulled)


def clip_inside(roads: dict, rings) -> dict:
    """Corridor list v2 (PM, PR #148): each way cut to its runs of consecutive nodes inside the city (2+ nodes), so
    the picker ranks and draws roads by their length inside the city, not by any node inside (the v1 rule)."""
    out = []
    for w in roads.get("elements", []):
        run: list[dict] = []
        for g in [*w.get("geometry", []), None]:
            if g is not None and osm_local._inside((g["lat"], g["lon"]), rings):
                run.append(g)
                continue
            if len(run) >= 2:
                out.append({**w, "geometry": run})
            run = []
    return {"elements": out}


def inside_share(line, rings) -> float | None:
    """% of a line's vertices inside the rings."""
    if not line:
        return None
    return round(100 * sum(osm_local._inside(tuple(p), rings) for p in line) / len(line), 1)


# ---- silent-drop check v4 (PM, after #149): v3 + the report's stated offset from its cross street ----
# Computed here from the frozen corridor line, OSM cross-street nodes and the CCRS offset fields; nothing is taken
# from the app's own offset handling (a checker must not borrow what it checks).
FT_PER_DEG = 111_320 * 3.28084
MAX_OFFSET_FT = 5280.0         # longer stated offsets are mostly typos (52,800 ft; 317 "miles"): never used to clear
V4_TOLERANCE_FT = 250.0        # band past each end of the stretch where a report still counts (HSM influence radius)
DIRV = {"N": (0.0, 1.0), "S": (0.0, -1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}


def offset_ft(dist, unit) -> float | None:
    """The report's offset in feet, or None when it can't be used (missing, negative, unknown unit, over a mile)."""
    try:
        d = float(dist)
    except (TypeError, ValueError):
        return None
    ft = {"F": d, "M": d * 5280}.get(str(unit or "").strip().upper())
    return ft if ft is not None and 0 <= ft <= MAX_OFFSET_FT else None


def _xy(line):
    lat0 = sum(p[0] for p in line) / len(line)
    k = math.cos(math.radians(lat0))
    return lambda la, lo: ((lo - line[0][1]) * FT_PER_DEG * k, (la - line[0][0]) * FT_PER_DEG)


def _project(line, p) -> tuple[float, tuple[float, float], float]:
    """(station ft along the line, unit direction of the nearest segment, distance ft from the line)."""
    to = _xy(line)
    pts = [to(*q) for q in line]
    x, y = to(*p)
    best, run = None, 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        if L == 0:
            continue
        ux, uy = (bx - ax) / L, (by - ay) / L
        t = (x - ax) * ux + (y - ay) * uy
        tc = min(max(t, 0.0), L)
        d = math.hypot(ax + ux * tc - x, ay + uy * tc - y)
        s = run + (t if (t < 0 and run == 0) or (t > L and (bx, by) == pts[-1]) else tc)   # extend past the ends
        if best is None or d < best[2]:
            best = (s, (ux, uy), d)
        run += L
    return best


def station(line, p) -> float:
    return _project(line, p)[0]


def nearest_to_line(line, nodes):
    """The node closest to the corridor line (where a cross street meets it)."""
    return min(nodes, key=lambda n: _project(line, n)[2]) if nodes else None


def report_station(line, cross_pt, direction: str, dist_ft: float) -> float:
    """Station of a report placed `dist_ft` in compass `direction` from its cross street: the offset's component
    along the corridor at that point (an offset across the corridor doesn't move it)."""
    s, (ux, uy), _ = _project(line, cross_pt)
    dx, dy = DIRV[direction]
    return s + dist_ft * (dx * ux + dy * uy)


def beyond_stretch(s: float, lo: float, hi: float) -> float:
    """How far (ft) a station lies past the stretch [lo, hi]; 0 inside it."""
    return max(lo - s, s - hi, 0.0)
