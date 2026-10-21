"""The statewide harness's own street checks (#73), independent of the app's names.py. Pure functions, tested in
tests/tester/test_statewide_harness.py."""

from __future__ import annotations

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
