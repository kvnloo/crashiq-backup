"""Crashes at a street's crossing with a railway or a trail or path (#318; user decision 2026-11-01, docs/03 "Railway
and trail crossings, and mile markers").

A no-GPS report naming the corridor street and a railway ("FRANCIS ST & RAIL ROAD") or a named trail or path ("MANGO
AVE & PACIFIC ELECTRIC TRL") is placed where the corridor crosses that feature. A stated distance ("817 ft W of CITRUS
AV" on "ESCONDIDO CREEK BIKE PATH") is walked from the crossing along the path, in the stated direction. Two or more
possible crossings go to review with the reason, never the nearest guess; no crossing, likewise.

- Features: OSM railway=rail/light_rail/tram/subway and highway=cycleway/path/footway with a name, fetched across the
  corridor (network.crossing_query), kept apart from the street graph: they never become streets.
- A railroad named generically (RAIL ROAD, RR TRACKS, UPRR...) matches any railway; a trail or path matches by name.
- A bike lane on the road itself is the road (names.NOISE drops "BIKE LANE"); a crash on a separate bike-only path
  (the path is the report's primary road) is pending the user's confirmation: its spot is only a suggestion
  (config/placement.json `crossing_on_path`, false).
- Behind tiers `crossing_rail` / `crossing_path`, off (not in auto_tiers): while off the spot is the review suggestion.
"""

from __future__ import annotations

import math
import re

from .geo import Polyline

RAIL = re.compile(r"\b(?:RAIL\s*ROAD|RAILROAD|RAILWAY|RAIL\s*TRACKS?|R\s*/\s*R|RR(?:\s+(?:TRACKS?|XING|CROSSING))?|UPRR|"
                  r"BNSF|SPRR|AMTRAK|METROLINK|LIGHT\s*RAIL|TRAIN\s+TRACKS?|TRACKS)\b")
PATH = re.compile(r"\b(?:BIKE\s*PATH|BIKE\s*TRAIL|BIKEWAY|TRL|TRAIL|GREENWAY|PATHWAY|PATH|CYCLE\s*TRACK)\b")
PATH_WORDS = {"BIKE", "PATH", "TRAIL", "TRL", "BIKEWAY", "GREENWAY", "PATHWAY", "CYCLE", "TRACK", "THE", "MULTI",
              "USE", "RECREATION", "RECREATIONAL", "BIKEPATH"}
RAIL_TAGS = {"rail", "light_rail", "tram", "subway"}
PATH_TAGS = {"cycleway", "path", "footway"}
ONE_CROSSING_FT = 150.0      # crossing points this close are one crossing (double track, a divided road)
MIN_OFFSET_FT = 25.0
COMPASS = {"N": (0.0, 1.0), "S": (0.0, -1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}


def read(text: str | None) -> dict | None:
    """{"kind": "rail" | "path", "name": core words or None} the road field names as a crossing feature, or None."""
    t = re.sub(r"\(.*?\)", " ", str(text or "").upper())
    if re.search(r"\bBIKE\s*LANE\b", t):
        return None                                          # a bike lane is on the road: the road
    if RAIL.search(t):
        return {"kind": "rail", "name": None}
    if PATH.search(t):
        words = [w for w in re.findall(r"[A-Z0-9]+", t) if w not in PATH_WORDS and not w.isdigit()]
        return {"kind": "path", "name": " ".join(words) or None}
    return None


def _core(name: str) -> str:
    return " ".join(w for w in re.findall(r"[A-Z0-9]+", str(name or "").upper()) if w not in PATH_WORDS)


def features(osm: dict, want: dict) -> list[list[tuple[float, float]]]:
    """The polylines (lat, lon) of the ways that match the report's feature, end-to-end ways joined."""
    nodes = {e["id"]: (e["lat"], e["lon"]) for e in osm.get("elements", []) if e["type"] == "node"}
    ways = []
    for w in (e for e in osm.get("elements", []) if e["type"] == "way"):
        tags = w.get("tags", {})
        if want["kind"] == "rail":
            ok = tags.get("railway") in RAIL_TAGS
        else:
            ok = tags.get("highway") in PATH_TAGS and tags.get("name") and (
                want["name"] is None or _core(tags["name"]) == want["name"])
        if ok:
            ids = [n for n in w.get("nodes", []) if n in nodes]
            if len(ids) >= 2:
                ways.append(ids)
    chains: list[list[int]] = []                             # join ways that share an end node
    for ids in ways:
        for ch in chains:
            if ch[-1] == ids[0]:
                ch.extend(ids[1:])
                break
            if ch[0] == ids[-1]:
                ch[:0] = ids[:-1]
                break
        else:
            chains.append(list(ids))
    return [[nodes[n] for n in ch] for ch in chains]


def _cross(p, q, r, s):
    """Where segment p-q meets segment r-s: (t along p-q, u along r-s) or None."""
    d = (q[0] - p[0]) * (s[1] - r[1]) - (q[1] - p[1]) * (s[0] - r[0])
    if abs(d) < 1e-9:
        return None
    t = ((r[0] - p[0]) * (s[1] - r[1]) - (r[1] - p[1]) * (s[0] - r[0])) / d
    u = ((r[0] - p[0]) * (q[1] - p[1]) - (r[1] - p[1]) * (q[0] - p[0])) / d
    return (t, u) if 0 <= t <= 1 and 0 <= u <= 1 else None


def crossings(line: Polyline, paths: list[list[tuple[float, float]]]) -> list[dict]:
    """The distinct places the corridor crosses these features: {"xy", "path", "seg", "u"} (the first of each group)."""
    hits = []
    for k, pts in enumerate(paths):
        xy = [line.proj.to_xy(*p) for p in pts]
        for i, (a, b) in enumerate(zip(xy, xy[1:])):
            for c, d in zip(line.xy, line.xy[1:]):
                got = _cross(a, b, c, d)
                if got:
                    t = got[0]
                    hits.append({"xy": (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), "path": k, "seg": i, "t": t})
    out: list[dict] = []
    for h in hits:
        if all(math.dist(h["xy"], o["xy"]) > ONE_CROSSING_FT for o in out):
            out.append(h)
    return out


def _walk(xy: list[tuple[float, float]], seg: int, t: float, dist: float, forward: bool) -> tuple[float, float] | None:
    """The point `dist` feet from (seg, t) along the polyline, forward or back; None when it runs off the end."""
    cur = (xy[seg][0] + t * (xy[seg + 1][0] - xy[seg][0]), xy[seg][1] + t * (xy[seg + 1][1] - xy[seg][1]))
    i = seg + 1 if forward else seg
    left = dist
    while 0 <= i < len(xy):
        nxt = xy[i]
        d = math.dist(cur, nxt)
        if d >= left:
            f = left / d if d else 0.0
            return cur[0] + f * (nxt[0] - cur[0]), cur[1] + f * (nxt[1] - cur[1])
        left -= d
        cur = nxt
        i = i + 1 if forward else i - 1
    return None


def place(c: dict, net: dict, osm: dict) -> dict:
    """{"lat", "lon", "kind", "on_path", "note"} at the crossing (plus a distance along the path), or {"why": ...}."""
    got = next(((f, read(c.get(f))) for f in ("primary_road", "secondary_road") if read(c.get(f))), None)
    if got is None:
        return {"why": "no railway or path in the report"}
    field, want = got
    what = "a railway" if want["kind"] == "rail" else f"the {want['name'].title() if want['name'] else 'named'} path"
    line = Polyline([tuple(p) for p in net["line"]])
    paths = features(osm, want)
    found = crossings(line, paths)
    if not found:
        return {"why": f"the corridor doesn't cross {what} on the map"}
    if len(found) > 1:
        return {"why": f"the corridor crosses {what} in {len(found)} places"}
    x = found[0]
    pt, note = x["xy"], f"where the corridor crosses {what}"
    off, d = float(c.get("offset_ft") or 0.0), str(c.get("offset_dir") or "").upper()[:1]
    if off >= MIN_OFFSET_FT and d in COMPASS:
        xy = [line.proj.to_xy(*p) for p in paths[x["path"]]]
        ends = [e for e in (_walk(xy, x["seg"], x["t"], off, True), _walk(xy, x["seg"], x["t"], off, False)) if e]
        cx, cy = COMPASS[d]
        good = [e for e in ends if ((e[0] - pt[0]) * cx + (e[1] - pt[1]) * cy) / off > math.cos(math.radians(60))]
        if not good:
            return {"why": f"{off:g} ft {d} from the crossing doesn't follow {what}"}
        pt, note = good[0], note + f", {off:g} ft {d} along it"
    lat, lon = line.proj.to_ll(*pt)
    return {"lat": lat, "lon": lon, "kind": want["kind"], "on_path": want["kind"] == "path" and field == "primary_road",
            "note": note}
