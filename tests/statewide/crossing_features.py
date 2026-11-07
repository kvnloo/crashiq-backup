"""Run 11 (#387; measure only): the railways and named trails / paths the app's crossing tiers (#318) look for, taken
from the same California OSM extract as the local street map (data/osm/california-latest.osm.pbf; ca_osm.sqlite keeps
roads only). The same filter as network.crossing_query + crossings.features: railway=rail/light_rail/tram/subway, and
highway=cycleway/path/footway with a name. Writes data/statewide/crossing_features.sqlite (ways + an R-tree box), read by
run11_tiers.py as the Overpass answer around a corridor.

Needs pyosmium (not an app dependency): run with a venv that has it, e.g.
  ~/.hermes/cache/scratch/osmvenv/bin/python tests/statewide/crossing_features.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import osmium

ROOT = Path(__file__).resolve().parents[2]
PBF = ROOT / "data" / "osm" / "california-latest.osm.pbf"
OUT = ROOT / "data" / "statewide" / "crossing_features.sqlite"
RAIL, PATH = {"rail", "light_rail", "tram", "subway"}, {"cycleway", "path", "footway"}


def main() -> None:
    ways = {}
    for w in osmium.FileProcessor(str(PBF), osmium.osm.WAY):
        t = w.tags
        if t.get("railway") in RAIL or (t.get("highway") in PATH and t.get("name")):
            ways[w.id] = ({k: v for k, v in t if k in ("railway", "highway", "name")}, [n.ref for n in w.nodes])
    print(f"{len(ways)} ways", flush=True)
    need = {n for _, ns in ways.values() for n in ns}
    loc = {}
    for n in osmium.FileProcessor(str(PBF), osmium.osm.NODE).with_filter(osmium.filter.IdFilter(need)):
        loc[n.id] = (n.location.lat, n.location.lon)
    print(f"{len(loc)} of {len(need)} nodes", flush=True)
    OUT.unlink(missing_ok=True)
    con = sqlite3.connect(OUT)
    con.execute("CREATE TABLE ways (id INTEGER PRIMARY KEY, tags TEXT, nodes TEXT, coords TEXT)")
    con.execute("CREATE VIRTUAL TABLE way_box USING rtree(id, minlat, maxlat, minlon, maxlon)")
    for wid, (tags, ns) in ways.items():
        ns = [n for n in ns if n in loc]
        if len(ns) < 2:
            continue
        cs = [loc[n] for n in ns]
        con.execute("INSERT INTO ways VALUES (?, ?, ?, ?)", (wid, json.dumps(tags), json.dumps(ns), json.dumps(cs)))
        con.execute("INSERT INTO way_box VALUES (?, ?, ?, ?, ?)", (wid, min(c[0] for c in cs), max(c[0] for c in cs),
                                                                 min(c[1] for c in cs), max(c[1] for c in cs)))
    con.commit()
    print("EXIT: finished", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
