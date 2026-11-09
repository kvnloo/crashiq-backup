"""Alabama: placement accuracy split by how CARE got the crash's point (HasCoord), on the same 2,000-crash sample
as al_pull.py (Jefferson County 2024, seed 2026). CARE derives most points from its own node, link or route-milepost
location, so only officer-entered GPS is a fair hidden truth.
    PYTHONPATH=backend python research_notes/al-2026-11-08/al_accuracy_by_source.py <scratch dir>
"""
import collections
import json
import random
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import al_care

out = Path(sys.argv[1])
HERE = Path(__file__).parent
raw = al_care.fetch_raw("County='Jefferson' AND Year='2024'", out)
recs = [(a["OBJECTID"], al_care.contract_record(a)) for a in raw]
gps = [(o, c) for o, c in recs if c["lat"] is not None and c["severity"]]
random.Random(2026).shuffle(gps)
sample = gps[:2000]


def has_coord(ids):
    got = {}
    for i in range(0, len(ids), 400):
        q = urllib.parse.urlencode({"where": f"OBJECTID IN ({','.join(map(str, ids[i:i + 400]))})",
                                    "outFields": "OBJECTID,HasCoord", "returnGeometry": "false", "f": "json"})
        req = urllib.request.Request(al_care.LAYER + "/query", data=q.encode(), headers={"User-Agent": "CrashIQ/0.1"})
        got.update({f["attributes"]["OBJECTID"]: f["attributes"]["HasCoord"]
                    for f in json.load(urllib.request.urlopen(req, timeout=300))["features"]})
    return got


src = has_coord([o for o, _ in sample])
net = osm.Network(tiger.elements(out / "tl_2024_01073_edges.zip", out / "tl_2024_01073_featnames.zip"))
gate = locate.Gate(tiger_only_auto=True)
by = collections.defaultdict(lambda: [0, 0, 0])                    # crashes, auto-placed, auto within 250 ft
for o, c in sample:
    k = src.get(o) or "?"
    by[k][0] += 1
    if not (c["primary_road"] and c["secondary_road"]):
        continue
    pl = locate.place(net, {"primary_road": c["primary_road"], "secondary_road": c["secondary_road"],
                            "offset_ft": None, "offset_dir": None})
    if pl.lat is not None and gate.auto(pl):
        by[k][1] += 1
        by[k][2] += osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"])) <= 250 * 0.3048
res = {k: {"n": n, "auto": a, "within_250ft": round(h / a, 4) if a else None} for k, (n, a, h) in by.items()}
print(json.dumps(res, indent=1))
d = json.loads((HERE / "placement_sample.json").read_text())
d["placement"]["accuracy_by_point_source"] = res
(HERE / "placement_sample.json").write_text(json.dumps(d, indent=1) + "\n")
