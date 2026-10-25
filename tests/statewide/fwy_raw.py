"""The raw elements the app's `freeway.place` (#252/#258) needs for one crash, from the local OSM extract (run 10).

In the app, a freeway corridor's Overpass response is the raw. Statewide there's no corridor, and a county-wide raw per
crash would be far too slow (`freeway.place` builds its graph from the raw on every call). So per crash this module
takes, from its county:
  - the main lanes (motorway / trunk) carrying the report's route number(s), both routes for a connector;
  - every motorway / trunk link reachable from those lanes in at most LINK_HOPS link-to-link steps (freeway._linked
    walks 6 hops);
  - the ways named like the reference street (name, alt_name or ref; indexed by street core and by the core without a
    leading direction word, so "Normandie Ave" finds "South Normandie Avenue" as the app's same_core does; route
    numbers for a state route), inside `box` when given (a city's box + 1 km) else the county box. The app's own
    `named()` then decides which of them is the street.
The geometry and every decision are the app's: this only chooses which elements it sees. Not included: TIGER/Line
names on the reference street.
2026-10-25 fix (Engineering, #259): the first version looked streets up by exact core in Outside's name+ref index, so
a reference street mapped with a leading direction word or only as alt_name was missing from the raw.
"""

from __future__ import annotations

import json
from collections import OrderedDict, defaultdict

from crashiq.freeway import LINK, MOTORWAY, parse
from crashiq.names import drop_directional, route_numbers, street_key

LINK_HOPS = 6
KEEP_COUNTIES = 3


class FwyRaw:
    def __init__(self, local, county_box: dict[int, tuple], outside):
        self.local, self.box, self.outside = local, county_box, outside
        self.cache: OrderedDict[int, dict] = OrderedDict()

    def _county(self, county: int) -> dict:
        if county in self.cache:
            self.cache.move_to_end(county)
            return self.cache[county]
        box = self.box[county]
        lanes, links, coords = defaultdict(list), {}, {}
        node_ways = defaultdict(set)
        named = defaultdict(set)
        for wid, tags, nids, cs in self.local.db.execute(
                "SELECT w.id, w.tags, w.nodes, w.coords FROM way_box b JOIN ways w ON w.id = b.id WHERE b.maxlat >= ? "
                "AND b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ?", (box[0], box[2], box[1], box[3])):
            t = json.loads(tags)
            hw = t.get("highway")
            if hw not in MOTORWAY + LINK:
                if hw:
                    for key in ("name", "alt_name", "ref"):
                        for v in str(t.get(key) or "").split(";"):
                            for k in self.keys(v):
                                named[k].add(wid)
                continue
            nl, cl = json.loads(nids), json.loads(cs)
            w = {"type": "way", "id": wid, "nodes": nl, "tags": t}
            coords[wid] = cl
            if hw in MOTORWAY:
                for r in route_numbers(" ".join(str(t.get(k) or "") for k in ("ref", "name"))):
                    lanes[r].append(w)
            else:
                links[wid] = w
                for n in (nl[0], nl[-1]):
                    node_ways[n].add(wid)
        if len(self.cache) >= KEEP_COUNTIES:
            self.cache.popitem(last=False)
        self.cache[county] = {"lanes": lanes, "links": links, "coords": coords, "node_ways": node_ways, "named": named}
        return self.cache[county]

    @staticmethod
    def keys(v: str) -> set[str]:
        k = street_key(v)
        if not k:
            return set()
        return {k.core.replace(" ", ""), drop_directional(k).core.replace(" ", "")}

    def _reach(self, cty: dict, start_ways: list[dict]) -> set[int]:
        """Links joined to the lanes, then to each other, up to LINK_HOPS steps (by shared end or inner node)."""
        node_ways = cty["node_ways"]
        frontier = {n for w in start_ways for n in w["nodes"]}
        seen: set[int] = set()
        for _ in range(LINK_HOPS):
            nxt = set()
            for n in frontier:
                for wid in node_ways.get(n, ()):
                    if wid not in seen:
                        seen.add(wid)
                        nxt |= set(cty["links"][wid]["nodes"])
            if not nxt:
                break
            frontier = nxt
        return seen

    def raw(self, c: dict, box: tuple | None = None) -> dict | None:
        r = parse(c)
        county = int(c.get("county_code") or 0)
        if r is None or county not in self.box:
            return None
        cty = self._county(county)
        routes = set(r["route"]) | set(r.get("to") or ())
        lanes = {w["id"]: w for rt in routes for w in cty["lanes"].get(rt, ())}
        if not lanes:
            return None
        ways = dict(lanes)
        for wid in self._reach(cty, list(lanes.values())):
            ways[wid] = cty["links"][wid]
        coords = {wid: cty["coords"][wid] for wid in ways}
        if r.get("street"):
            ids = set()
            for k in self.keys(r["street"]):
                ids |= cty["named"].get(k, set())
            for rt in route_numbers(r["street"]):
                ids |= {w["id"] for w in cty["lanes"].get(rt, ())}
            ids -= set(ways)
            if ids:
                for wid, tags, nids, cs in self.local.db.execute(
                        f"SELECT id, tags, nodes, coords FROM ways WHERE id IN ({','.join('?' * len(ids))})", list(ids)):
                    cl = json.loads(cs)
                    if box and not any(box[0] <= la <= box[2] and box[1] <= lo <= box[3] for la, lo in cl):
                        continue
                    ways[wid] = {"type": "way", "id": wid, "nodes": json.loads(nids), "tags": json.loads(tags)}
                    coords[wid] = cl
        nodes = {}
        for wid, w in ways.items():
            for n, (la, lo) in zip(w["nodes"], coords[wid]):
                nodes[n] = {"type": "node", "id": n, "lat": la, "lon": lo}
        return {"elements": list(ways.values()) + list(nodes.values())}
