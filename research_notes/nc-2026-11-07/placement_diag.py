"""Why exact placements miss the hidden GPS: distance to the offset point vs. the intersection node, by offset size
and by GPS decimals. Same sample as placement_sample.py. Run: PYTHONPATH=backend python research_notes/nc-2026-11-07/placement_diag.py"""
import json
import random
import statistics
from collections import Counter
from pathlib import Path
from crashiq import locate, osm, tiger

S = Path.home() / ".hermes/cache/scratch/states/nc"
rows = json.loads((S / "raleigh_2025.json").read_text())
named = [r for r in rows if r["lat"] is not None and r["primary_road"] and r["secondary_road"]]
sample = random.Random(20261107).sample(named, 2000)
net = osm.Network(tiger.elements(S / "tl_2024_37183_edges.zip", S / "tl_2024_37183_featnames.zip"))
FT = 0.3048
out = []
for c in sample:
    if locate._house_address(c):
        continue
    pl = locate.place(net, dict(c, lat=None, lon=None))
    if pl.tier != "exact":
        continue
    node = net.coord[pl.node]
    d_pt = osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"])) / FT
    d_node = osm.metres(node, (c["lat"], c["lon"])) / FT
    dec = min(len(str(c["lat"]).split(".")[-1]), len(str(c["lon"]).split(".")[-1]))
    out.append((d_pt, d_node, c["offset_ft"] or 0, dec, c["offset_dir"]))
n = len(out)
print("exact n", n)
print("point<=250", sum(o[0] <= 250 for o in out), "node<=250", sum(o[1] <= 250 for o in out),
      "best-of<=250", sum(min(o[0], o[1]) <= 250 for o in out))
print("median ft point", statistics.median(o[0] for o in out), "node", statistics.median(o[1] for o in out))
print("decimals", Counter(o[3] for o in out))
for lo, hi in ((0, 1), (1, 100), (100, 300), (300, 1000), (1000, 1e9)):
    g = [o for o in out if lo <= o[2] < hi]
    if g:
        print(f"offset {lo}-{hi}: n={len(g)} point<=250 {sum(o[0] <= 250 for o in g)} node<=250 {sum(o[1] <= 250 for o in g)}"
              f" median point {statistics.median(o[0] for o in g):.0f} node {statistics.median(o[1] for o in g):.0f}")
for d in (2, 3, 4, 5):
    g = [o for o in out if o[3] == d]
    if g:
        print("decimals", d, "n", len(g), "point<=250", sum(o[0] <= 250 for o in g))
print("dir", Counter(o[4] for o in out).most_common(10))
