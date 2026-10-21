"""Load a Geofabrik OpenStreetMap extract into SQLite, so the statewide run answers the app's Overpass query locally
(Overpass rate-limited this machine during #73; user OK for the download, 2026-10-20).

Runs under the Tester-only venv with pyosmium (.venv-osm), separate from the app's venv:
    .venv-osm/bin/python tests/statewide/osm_extract.py data/osm/california-latest.osm.pbf data/osm/ca_osm.sqlite

Tables:
  ways(id, highway, name, tags json, nodes json, coords json) + R-tree way_box: every way whose highway tag is one
      the app or the corridor picker asks for.
  nodes(id, lat, lon, tags json): nodes carrying a highway tag (signals, stops, crossings), which the app reads
      for intersection control.
  areas(id, osm_type, name, admin_level, rings json, minlat, minlon, maxlat, maxlon): administrative boundaries,
      levels 6 and 8 (cities; San Francisco is level 6).
  meta(key, value): source file, its replication timestamp, counts.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import osmium
import osmium.filter

HIGHWAYS = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street",
            "road", "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}


def build(pbf: Path, db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE ways (id INTEGER PRIMARY KEY, highway TEXT, name TEXT, tags TEXT, nodes TEXT, coords TEXT);
        CREATE VIRTUAL TABLE way_box USING rtree(id, minlat, maxlat, minlon, maxlon);
        CREATE TABLE nodes (id INTEGER PRIMARY KEY, lat REAL, lon REAL, tags TEXT);
        CREATE TABLE areas (id INTEGER, osm_type TEXT, name TEXT, admin_level TEXT, rings TEXT,
                            minlat REAL, minlon REAL, maxlat REAL, maxlon REAL);
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
    """)
    idx_path = db_path.with_suffix(".nodeidx")
    fp = (osmium.FileProcessor(str(pbf))
          .with_locations(osmium.index.create_map(f"sparse_file_array,{idx_path}"))
          .with_areas(osmium.filter.TagFilter(("boundary", "administrative"))))
    ways, nodes, areas = [], [], []
    n_w = n_n = n_a = 0
    for o in fp:
        if o.is_node():
            if "highway" in o.tags and o.location.valid():
                nodes.append((o.id, o.location.lat, o.location.lon, json.dumps(dict(o.tags))))
        elif o.is_way():
            hw = o.tags.get("highway")
            if hw in HIGHWAYS:
                try:
                    coords = [(round(n.lat, 7), round(n.lon, 7)) for n in o.nodes]
                except osmium.InvalidLocationError:
                    continue
                ways.append((o.id, hw, o.tags.get("name"), json.dumps(dict(o.tags)),
                             json.dumps([n.ref for n in o.nodes]), json.dumps(coords),
                             min(c[0] for c in coords), max(c[0] for c in coords),
                             min(c[1] for c in coords), max(c[1] for c in coords)))
        elif o.is_area():
            # Rosemead's boundary is tagged admin=8 instead of admin_level=8 (OSM typo, found 2026-10-20)
            lvl = o.tags.get("admin_level") or o.tags.get("admin")
            if lvl in ("6", "8") and o.tags.get("name"):
                rings = [[(round(n.lat, 6), round(n.lon, 6)) for n in ring] for ring in o.outer_rings()]
                if rings:
                    lats = [p[0] for r in rings for p in r]
                    lons = [p[1] for r in rings for p in r]
                    areas.append((o.orig_id(), "relation" if o.from_way() is False else "way", o.tags.get("name"),
                                  lvl, json.dumps(rings), min(lats), min(lons), max(lats), max(lons)))
        if len(ways) >= 50000:
            _flush_ways(con, ways)
            n_w += len(ways)
            ways = []
        if len(nodes) >= 50000:
            con.executemany("INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)", nodes)
            n_n += len(nodes)
            nodes = []
    _flush_ways(con, ways)
    n_w += len(ways)
    con.executemany("INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)", nodes)
    n_n += len(nodes)
    con.executemany("INSERT INTO areas VALUES (?,?,?,?,?,?,?,?,?)", areas)
    n_a = len(areas)
    con.execute("CREATE INDEX ix_areas_name ON areas(name)")
    header = osmium.io.Reader(str(pbf), osmium.osm.osm_entity_bits.NOTHING).header()
    stamp = header.get("osmosis_replication_timestamp", "")
    con.executemany("INSERT INTO meta VALUES (?,?)", [("source", pbf.name), ("timestamp", stamp),
                                                      ("ways", str(n_w)), ("nodes", str(n_n)), ("areas", str(n_a))])
    con.commit()
    con.close()
    if idx_path.exists():
        idx_path.unlink()
    print(f"ways {n_w:,} · highway nodes {n_n:,} · boundaries {n_a:,} · extract timestamp {stamp}")


def _flush_ways(con, ways):
    con.executemany("INSERT OR REPLACE INTO ways VALUES (?,?,?,?,?,?)", [w[:6] for w in ways])
    con.executemany("INSERT OR REPLACE INTO way_box VALUES (?,?,?,?,?)", [(w[0], *w[6:]) for w in ways])


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]))
