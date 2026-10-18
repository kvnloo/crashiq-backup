"""Writes overpass_crenshaw.json: a HAND-BUILT Overpass response for Crenshaw Blvd, Marine Ave → 132nd St.

Why hand-built: the build sandbox can't reach Overpass. Cross-street positions follow the mockup's NODES
(design/mockups/index.html, "approximate the OSM nodes"). It mirrors what Overpass returns for
`overpass_query()`: road ways near the line (`out body`) plus their nodes with tags (`>; out body`).

Real-data check: `backend/scripts/record_fixtures.py` records the live response; compare and replace.

Geometry: Crenshaw is divided (NB carriageway lon -118.32652, SB -118.32672, ~30 ft each side of the
drawn centre line at -118.32662). Cross streets, south → north:
  153rd St      33.8925  outside the study limits (A is Marine) → excluded
  Marine Ave    33.8953  both sides, traffic_signals on the NB crossing node → signal
  147th St      33.8978  west side only (T), stop sign on its approach node → stop
  144th St      33.8999  both sides, no control tags → unknown
  Rosecrans Ave 33.9016  both sides, signals mapped on approach nodes ~50 ft out; an unnamed
                         primary_link slip lane joins the SB carriageway at 33.9020 → same intersection
  135th St      33.9093  both sides, signals
  132nd St      33.9123  both sides, signals (B)
  131st St      33.9140  outside the study limits → excluded
"""
import json
from pathlib import Path

NB, SB, W, E = -118.32652, -118.32672, -118.3300, -118.3230
els, nid = [], [1000]


def node(lat, lon, tags=None):
    nid[0] += 1
    n = {"type": "node", "id": nid[0], "lat": lat, "lon": lon}
    if tags:
        n["tags"] = tags
    els.append(n)
    return nid[0]


ways = []


def way(wid, nodes, tags):
    ways.append({"type": "way", "id": wid, "nodes": nodes, "tags": tags})


CROSS = [  # name, lat, west?, east?, control
    ("West 153rd Street", 33.8925, True, True, None),
    ("Marine Avenue", 33.8953, True, True, "signal_on_node"),
    ("West 147th Street", 33.8978, True, False, "stop"),
    ("West 144th Street", 33.8999, True, True, None),
    ("Rosecrans Avenue", 33.9016, True, True, "signal_approach"),
    ("West 135th Street", 33.9093, True, True, "signal_on_node"),
    ("West 132nd Street", 33.9123, True, True, "signal_on_node"),
    ("West 131st Street", 33.9140, True, True, None),
]
nb_nodes, sb_nodes = [], []   # (lat, id), built bottom → top
wid = 5000
for name, lat, west, east, ctl in CROSS:
    tags_nb = {"highway": "traffic_signals"} if ctl == "signal_on_node" else None
    n_nb = node(lat, NB, tags_nb)
    n_sb = node(lat, SB)
    nb_nodes.append((lat, n_nb))
    sb_nodes.append((lat, n_sb))
    cross = []
    if west:
        w_far = node(lat, W)
        w_app = node(lat, SB - 0.00018, {"highway": "stop"} if ctl == "stop" else
                     {"highway": "traffic_signals"} if ctl == "signal_approach" else None)
        cross += [w_far, w_app, n_sb]
    else:
        cross += [n_sb]
    cross.append(n_nb) if east else None
    if east:
        e_app = node(lat, NB + 0.00018, {"highway": "traffic_signals"} if ctl == "signal_approach" else None)
        e_far = node(lat, E)
        cross += [e_app, e_far]
    wid += 1
    way(wid, cross, {"highway": "secondary" if "Avenue" in name else "residential", "name": name})

# mid-block shape nodes on the carriageways
for lat in (33.9005, 33.9040, 33.9065, 33.9108):
    nb_nodes.append((lat, node(lat, NB)))
    sb_nodes.append((lat, node(lat, SB)))
# Rosecrans slip lane: unnamed primary_link from a SB node at 33.9020 to the west approach
slip = node(33.9020, SB)
sb_nodes.append((33.9020, slip))
ros_west = next(e["nodes"][0] for e in ways if e["tags"]["name"] == "Rosecrans Avenue")
way(6001, [slip, node(33.9018, SB - 0.0003), ros_west], {"highway": "primary_link", "oneway": "yes"})
# extend the corridor past both ends (real carriageways continue)
for lat in (33.8900, 33.9165):
    nb_nodes.append((lat, node(lat, NB)))
    sb_nodes.append((lat, node(lat, SB)))

nb = [n for _, n in sorted(nb_nodes)]
sb = [n for _, n in sorted(sb_nodes, reverse=True)]
crenshaw = {"highway": "primary", "name": "Crenshaw Boulevard", "oneway": "yes"}
# OSM splits ways at many intersections; split each carriageway once in the middle
way(7001, nb[: len(nb) // 2 + 1], crenshaw)
way(7002, nb[len(nb) // 2:], crenshaw)
way(7003, sb[: len(sb) // 2 + 1], crenshaw)
way(7004, sb[len(sb) // 2:], crenshaw)

data = {"version": 0.6, "generator": "hand-built fixture (see make_crenshaw_overpass.py)",
        "elements": ways + els}
Path(__file__).with_name("overpass_crenshaw.json").write_text(json.dumps(data, indent=1))
print(len(ways), "ways,", len(els), "nodes")
