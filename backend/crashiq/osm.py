"""OpenStreetMap street network (via Overpass) indexed for crash location. Data © OSM contributors, ODbL."""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from .names import StreetKey, directions, street_key

OVERPASS = "https://overpass-api.de/api/interpreter"
HIGHWAYS = ("motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|"
            "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|pedestrian|road|"
            "footway|path|steps|cycleway")  # named plazas and malls connect streets (Fulton St plaza at Hyde)
NAME_TAGS = ("name", "alt_name", "old_name", "official_name", "short_name", "ref")


def fetch(area_wikidata: str, cache_dir: Path) -> dict:
    """Named roads inside one jurisdiction (an OSM boundary, by Wikidata id: San Francisco = Q62).
    Matching is limited to the reporting agency's jurisdiction so a same-named street in the next
    city can't win. Cached as raw Overpass JSON."""
    cache = cache_dir / f"osm_{area_wikidata}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    q = (f'[out:json][timeout:300];rel["wikidata"="{area_wikidata}"]["boundary"="administrative"];map_to_area->.a;'
         f'(way["highway"~"^({HIGHWAYS})$"]["name"](area.a);way["highway"~"^({HIGHWAYS})$"]["ref"][!"name"](area.a););'
         'out body;>;out skel qt;')
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": "CrashIQ/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=400) as r:
        data = json.load(r)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def fetch_addresses(area_wikidata: str, cache_dir: Path) -> list[tuple[str, str, float, float]]:
    """(street, housenumber, lat, lon) for every OSM address in the jurisdiction, cached."""
    cache = cache_dir / f"osm_addr_{area_wikidata}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    q = (f'[out:json][timeout:600];rel["wikidata"="{area_wikidata}"]["boundary"="administrative"];map_to_area->.a;'
         'nwr["addr:housenumber"]["addr:street"](area.a);out tags center qt;')
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": "CrashIQ/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=700) as r:
        data = json.load(r)
    out = []
    for el in data["elements"]:
        t, c = el.get("tags", {}), el.get("center") or el
        if "lat" in c:
            out.append((t["addr:street"], t["addr:housenumber"], c["lat"], c["lon"]))
    cache.write_text(json.dumps(out))
    return out


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Haversine distance between (lat, lon) points."""
    R, la1, la2 = 6371008.8, math.radians(a[0]), math.radians(b[0])
    dla, dlo = la2 - la1, math.radians(b[1] - a[1])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, la2, dlo = math.radians(a[0]), math.radians(b[0]), math.radians(b[1] - a[1])
    y = math.sin(dlo) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlo)
    return math.degrees(math.atan2(y, x)) % 360


def move(p: tuple[float, float], brg: float, dist_m: float) -> tuple[float, float]:
    la, lo, br, d = math.radians(p[0]), math.radians(p[1]), math.radians(brg), dist_m / 6371008.8
    la2 = math.asin(math.sin(la) * math.cos(d) + math.cos(la) * math.sin(d) * math.cos(br))
    lo2 = lo + math.atan2(math.sin(br) * math.sin(d) * math.cos(la), math.cos(d) - math.sin(la) * math.sin(la2))
    return (math.degrees(la2), math.degrees(lo2))


class Network:
    """Streets, their keys, and every node where two differently named streets meet."""

    def __init__(self, data: dict):
        self.coord: dict[int, tuple[float, float]] = {}
        ways = []
        for el in data["elements"]:
            if el["type"] == "node":
                self.coord[el["id"]] = (el["lat"], el["lon"])
            elif el["type"] == "way":
                ways.append(el)
        self.keys_at: dict[int, set[StreetKey]] = defaultdict(set)   # node -> street keys through it
        self.label: dict[StreetKey, str] = {}                          # key -> a readable OSM name
        self.neighbors: dict[tuple[int, StreetKey], set[int]] = defaultdict(set)
        # trailing direction of the ways of a key through a node ("20th Street West" -> W; None when not written).
        # The key drops it, so 20th St East and West share one; the unique-pair tier tells them apart (#203)
        self.trail_at: dict[tuple[int, StreetKey], set[str | None]] = defaultdict(set)
        # where each name comes from (#229): "osm"; "tiger_name", a TIGER/Line name on an OSM way; "tiger", a road only
        # TIGER/Line has. Per street key and per node
        self.key_source: dict[StreetKey, set[str]] = defaultdict(set)
        self.src_at: dict[tuple[int, StreetKey], set[str]] = defaultdict(set)
        for w in ways:
            tags = w.get("tags", {})
            way_src = "tiger" if tags.get("crashiq:source") == "tiger" else "osm"
            names = []
            for t in NAME_TAGS + ("tiger:name",):
                src = "tiger_name" if t == "tiger:name" else way_src   # a TIGER name on an OSM way
                for v in str(tags.get(t, "")).split(";"):
                    k = street_key(v)
                    if k:
                        names.append((k, directions(v)[1], src))
                        self.label.setdefault(k, v.strip())
                        self.key_source[k].add(src)
            nodes = w["nodes"]
            for i, n in enumerate(nodes):
                for k, trail, src in names:
                    self.keys_at[n].add(k)
                    self.trail_at[(n, k)].add(trail)
                    self.src_at[(n, k)].add(src)
                    if i > 0:
                        self.neighbors[(n, k)].add(nodes[i - 1])
                    if i < len(nodes) - 1:
                        self.neighbors[(n, k)].add(nodes[i + 1])
        # Intersections: nodes shared by streets with different cores.
        self.intersections = [n for n, ks in self.keys_at.items()
                              if len({k.core.replace(" ", "") for k in ks}) >= 2 and n in self.coord]
        self.streets: set[StreetKey] = set(self.label)
        # Index by core (spaces removed, and with any leading directional dropped) for O(1) name lookups.
        from .names import drop_directional
        self.by_core: dict[str, set[StreetKey]] = defaultdict(set)
        for k in self.streets:
            self.by_core[k.core.replace(" ", "")].add(k)
            self.by_core[drop_directional(k).core.replace(" ", "")].add(k)
        self.all_nodes_of: dict[StreetKey, set[int]] = defaultdict(set)
        for n, ks in self.keys_at.items():
            if n in self.coord:
                for k in ks:
                    self.all_nodes_of[k].add(n)
        # Routes (US 101) are often tagged only on the freeway, not its ramps; give each route the
        # nodes of ways whose name mentions it ("US 101 N ON RAMP") is out of scope here.
        self.nodes_of: dict[StreetKey, list[int]] = defaultdict(list)
        for n in self.intersections:
            for k in self.keys_at[n]:
                self.nodes_of[k].append(n)

    def tiger_only(self, node: int, keys, road: bool = False) -> bool:
        """The street (these keys) is at this node only by a TIGER/Line name or road (#229); with `road`, only by a
        road OSM doesn't have."""
        srcs = set().union(*(self.src_at.get((node, k), set()) for k in keys)) if keys else set()
        return bool(srcs) and (srcs == {"tiger"} if road else "osm" not in srcs)

    def name(self, k: StreetKey) -> str:
        return self.label.get(k, k.core)
