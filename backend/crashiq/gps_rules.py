"""Police GPS vs the report's own description (#218; user decision 2026-10-22, docs/03).

1. Snapped GPS: the point sits at the intersection the report names (within `snap_ft`), but the report states a
   distance (> `offset_min_ft`) and a direction from it: the crash is placed at that intersection plus the offset,
   along the named road (`apply_offsets`, provenance `gps_offset_applied`).
2. Default / dispatch points and coarse coordinates are not a location: the crash is placed by its street names, and
   the ignored point is kept on the crash (`gps_ignored`).
   - A pile: one exact point (5 decimals) shared by >= 10 crashes naming >= 5 street pairs, < 50% of which fit it
     (the Tester's statewide rule, pooled across agencies, #219). Known piles statewide are listed in
     data/reference/gps_piles.json; piles inside a corridor's search box are also found from the pull itself.
   - Coarse: 2 decimals or fewer in latitude or longitude (~1 km).
Thresholds: config/gps.json."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .settings import ROOT

CONFIG = json.loads((Path(__file__).parent / "config" / "gps.json").read_text())
PILES_FILE = ROOT / "data" / "reference" / "gps_piles.json"


def decimals(v) -> int:
    t = str(v if v is not None else "").strip()
    if "e" in t.lower():
        t = f"{float(t):.10f}".rstrip("0")
    return len(t.split(".", 1)[1].rstrip("0")) if "." in t else 0


def coarse(lat, lon) -> bool:
    """A coordinate written with too few decimals to be a location (2 or fewer, ~1 km)."""
    if lat in (None, "") or lon in (None, ""):
        return False
    n = CONFIG["coarse_max_decimals"]
    return decimals(lat) <= n or decimals(lon) <= n


def point_key(lat, lon) -> tuple[float, float]:
    d = CONFIG["pile"]["decimals"]
    return round(float(lat), d), round(float(lon), d)


@lru_cache(maxsize=1)
def listed_piles() -> dict[tuple[float, float], int]:
    """Known pile points statewide -> crashes on them (the Tester's scan)."""
    data = json.loads(PILES_FILE.read_text())
    return {point_key(p["lat"], p["lon"]): p["crashes"] for p in data["points"]}


def pair_key(c: dict) -> tuple:
    from .names import street_key
    ks = sorted(str(street_key(r) or (r or "").strip().upper()) for r in (c.get("primary_road"), c.get("secondary_road")))
    return tuple(ks)


def find_piles(crashes: list[dict], fits) -> dict[tuple[float, float], int]:
    """Pile points among these GPS crashes: {point: crashes on it}. `fits(c)` is the street check for one crash."""
    by_pt: dict[tuple, list[dict]] = defaultdict(list)
    for c in crashes:
        by_pt[point_key(c["lat"], c["lon"])].append(c)
    rule, out = CONFIG["pile"], {}
    for pt, cs in by_pt.items():
        if len(cs) < rule["min_crashes"] or len({pair_key(c) for c in cs}) < rule["min_street_pairs"]:
            continue
        if sum(bool(fits(c)) for c in cs) / len(cs) < rule["max_fit_share"]:
            out[pt] = len(cs)
    return out


# -- SQL for the name search of rows whose GPS is a known pile or coarse (the pull's second no-GPS query) --------------
def sql_condition(lat_expr: str, lon_expr: str) -> str:
    """Rows at a listed pile point (matched on rounded latitude and longitude separately, then exactly in code) or with
    coarse coordinates. Short enough for the URL limit: two IN lists of ~50 numbers."""
    d, n = CONFIG["pile"]["decimals"], CONFIG["coarse_max_decimals"]
    lats = ", ".join(sorted({f"{a:.{d}f}".rstrip("0").rstrip(".") for a, _ in listed_piles()}))
    lons = ", ".join(sorted({f"{b:.{d}f}".rstrip("0").rstrip(".") for _, b in listed_piles()}))
    rl = lambda e, k: f"ROUND(CAST({e} AS numeric), {k})"
    pile = f"({rl(lat_expr, d)} IN ({lats}) AND {rl(lon_expr, d)} IN ({lons}))"
    crs = f"({rl(lat_expr, n)} = CAST({lat_expr} AS numeric) OR {rl(lon_expr, n)} = CAST({lon_expr} AS numeric))"
    return f"({pile} OR {crs})"


def ignored_reason(lat, lon, piles: dict) -> tuple[str, int] | None:
    """('coarse', 0) | ('default_point', crashes on it) | None for one raw coordinate."""
    if coarse(lat, lon):
        return "coarse", 0
    try:
        pt = point_key(lat, lon)
    except (TypeError, ValueError):
        return None
    n = piles.get(pt) or listed_piles().get(pt)
    return ("default_point", n) if n else None


# -- 1. snapped GPS + the report's offset -------------------------------------------------------------------------
CARDINAL = ("N", "E", "S", "W")


def apply_offsets(onet, net: dict, crashes: list[dict]) -> int:
    """Move GPS snapped to the named study intersection by the report's offset, along the primary road. Returns the
    number moved. `onet` is the corridor's OSM network (locate's)."""
    from .assign import _stated_intersection
    from .geo import Polyline
    from .crashes import GPS_SOURCES
    from . import grade
    line = Polyline([tuple(p) for p in net["line"]])
    studies = [i for i in net.get("intersections", []) if i.get("is_study") and i.get("lat") is not None]
    if not studies:
        return 0
    ck = grade.corridor_keys(net)
    moved = 0
    for c in crashes:
        if c.get("location_source") not in ("gps", "gps_dms_corrected") or c.get("lat") is None or c.get("exclude_rule"):
            continue
        off, d = c.get("offset_ft") or 0.0, str(c.get("offset_dir") or "").strip()[:1].upper()
        if off <= CONFIG["offset_min_ft"] or d not in CARDINAL:
            continue
        st = _stated_intersection(c, studies, ck)
        if st is None:
            continue
        (x, y), (sx, sy) = line.proj.to_xy(c["lat"], c["lon"]), line.proj.to_xy(st["lat"], st["lon"])
        if math.hypot(x - sx, y - sy) > CONFIG["snap_ft"]:
            continue                                    # not snapped: the point is where police put it
        node = _node_for(onet, st)
        if node is None:
            continue
        pt = _along_named_road(onet, node, c, off, d)
        if pt is None:
            continue                  # neither named road runs that way from the intersection: the GPS stays
        lat, lon = pt
        c["gps_as_reported"] = [c["lat"], c["lon"]]
        c.update(lat=lat, lon=lon, location_source="gps_offset_applied")
        moved += 1
    assert "gps_offset_applied" in GPS_SOURCES
    return moved


def _along_named_road(onet, node: int, c: dict, dist_ft: float, d: str) -> tuple[float, float] | None:
    """The point dist_ft from the intersection along the named road that runs in direction d: the primary road first
    (CHP's distance is measured along it), else the cross street ("CRENSHAW BLVD | 132ND ST, 206 ft E" on a
    north-south Crenshaw is on 132nd). None when neither runs within 60 degrees of d."""
    from . import locate
    from .names import street_key
    from .osm import bearing, move
    want = locate.CARDINAL[d]
    p0 = onet.coord[node]
    for road in (c.get("primary_road"), c.get("secondary_road")):
        k = street_key(road)
        keys = (locate._keys_matching(onet, k) or locate._same_core_keys(onet, k)) if k else []
        nbrs = {m for s in keys for m in onet.neighbors.get((node, s), ()) if m in onet.coord}
        brgs = [bearing(p0, onet.coord[m]) for m in nbrs]
        ok = [b for b in brgs if abs((b - want + 180) % 360 - 180) <= 60]
        if ok:
            brg = min(ok, key=lambda b: abs((b - want + 180) % 360 - 180))
            return move(p0, brg, dist_ft * locate.FT)
    return None


def _node_for(onet, it: dict) -> int | None:
    from .osm import metres
    nodes = [n for n in (it.get("osm_node_ids") or []) if n in onet.coord]
    if nodes:
        return min(nodes, key=lambda n: metres(onet.coord[n], (it["lat"], it["lon"])))
    near = [n for n in onet.intersections if metres(onet.coord[n], (it["lat"], it["lon"])) <= 30]
    return min(near, key=lambda n: metres(onet.coord[n], (it["lat"], it["lon"]))) if near else None
