"""Utah: placement sample (Salt Lake County 2024, random 2,000 of every row), service counts, and the offline test
fixture, from UDOT's live Utah Crash Locations service. The California way: GPS present and plausible; then hide the
GPS, place the reported street pair on a TIGER/Line 2024 network with locate.place, and score against the hidden GPS.

Run: PYTHONPATH=backend python research_notes/ut-2026-11-08/ut_pull.py <scratch dir with tl_2024_49035_*.zip>
"""
import collections
import json
import math
import random
import re
import sys
import urllib.request
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import ut_udot

HERE = Path(__file__).parent
FIX = HERE.parents[1] / "tests/fixtures/ut_udot_crashes.json"
op = urllib.request.urlopen
scratch = Path(sys.argv[1])
FT250_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


ids = ut_udot.layers(op)
counts = {y: ut_udot._get(f"/{i}/query", {"where": "1=1", "returnCountOnly": "true"}, op)["count"]
          for y, i in sorted(ids.items())}
utah = {"geometry": "-114.1,36.9,-108.9,42.1", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects"}
in_utah_2024 = ut_udot._get(f"/{ids[2024]}/query", {"where": "1=1", "returnCountOnly": "true", **utah}, op)["count"]

raw, last = [], 0
while True:
    b = ut_udot._get(f"/{ids[2024]}/query", {"where": f"county_name='SALT LAKE' AND OBJECTID>{last}", "outFields": "*",
                                              "outSR": 4326, "orderByFields": "OBJECTID", "resultRecordCount": 2000}, op)
    raw += b["features"]
    if len(b["features"]) < 2000:
        break
    last = b["features"][-1]["attributes"]["OBJECTID"]
recs = [ut_udot.contract_record(f) for f in raw]
random.Random(2026).shuffle(recs)
sample = recs[:2000]

net = osm.Network(tiger.elements(scratch / "tl_2024_49035_edges.zip", scratch / "tl_2024_49035_featnames.zip"))
gate = locate.Gate(tiger_only_auto=True)       # TIGER-only network: plain Gate() auto-places nothing here
tiers, reasons, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
gps = pairs = house = placed = auto = hits = auto_hits = 0
for c in sample:
    la, lo = c["lat"], c["lon"]
    gps += la is not None
    prim, sec = c["primary_road"], c["secondary_road"]
    if prim and not sec and re.match(r"^\d+\s+\D", prim):
        house += 1
        continue
    if not (prim and sec):
        reasons["no cross street in source"] += 1
        continue
    pairs += 1
    pl = locate.place(net, {"primary_road": prim, "secondary_road": sec, "offset_ft": c["offset_ft"],
                            "offset_dir": c["offset_dir"]})
    tiers[pl.tier] += 1
    if pl.lat is None:
        reasons[pl.note or pl.tier] += 1
        if len(examples[pl.note]) < 6:
            examples[pl.note].append(f"{prim} & {sec}")
        continue
    placed += 1
    if la is None:
        continue
    d = osm.metres((pl.lat, pl.lon), (la, lo))
    hits += d <= FT250_M
    if gate.auto(pl):
        auto += 1
        auto_hits += d <= FT250_M
    if d > FT250_M and len(examples["placed >250 ft off"]) < 6:
        examples["placed >250 ft off"].append(f"{prim} & {sec} [{pl.tier}] {d / 0.3048:.0f} ft")
k = len(sample)
out = {"area": "Salt Lake County (49035), 2024, random 2,000 (seed 2026)", "n": k,
       "county_rows_2024": len(raw), "rows_per_year": counts, "rows_2024_with_point_in_utah": in_utah_2024,
       "gps_share": round(gps / k, 4), "street_pair_share": round(pairs / k, 4),
       "house_address_share": round(house / k, 4), "tiers": dict(tiers),
       "name_placed_share": round(placed / k, 4), "name_placed_share_of_pairs": round(placed / pairs, 4) if pairs else None,
       "auto_share": round(auto / k, 4), "gate": "Gate(tiger_only_auto=True) on a TIGER-only network",
       "within_250ft": round(auto_hits / auto, 4) if auto else None, "within_250ft_low": round(wilson_low(auto_hits, auto), 4),
       "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
       "within_250ft_all_placed_low": round(wilson_low(hits, placed), 4),
       "severity": collections.Counter(c["severity"] for c in recs),
       "freeway_share": round(sum(c["is_freeway"] for c in recs) / len(recs), 4),
       "not_placed": dict(reasons.most_common(8)), "examples": dict(examples)}
(HERE / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))

# fixture: a spread of Salt Lake 2024 rows by severity, flag, freeway and cross street, plus one 2026 row
pick, seen = [], set()


def take(fs, n):
    for f in fs[:n]:
        if f["attributes"]["crash_id"] not in seen:
            seen.add(f["attributes"]["crash_id"])
            pick.append(f)


by = list(zip(raw, (ut_udot.contract_record(f) for f in raw)))
for sev in "KABCO":
    take([f for f, c in by if c["severity"] == sev], 8)
for flag in ("ped", "bike", "motorcycle", "heavy_truck", "is_freeway", "secondary_road", "offset_ft"):
    take([f for f, c in by if c[flag]], 4)
take([f for f, c in by if c["primary_road"] and re.match(r"^\d+\s", c["primary_road"])], 3)
take([f for f, c in by if c["collision_type"] == "HIT OBJECT"], 2)
FIX.write_text(json.dumps({"recorded": "2026-11-08", "layers": sorted(ids.items()), "features": pick}))
print(len(pick), "features", FIX.stat().st_size, "bytes")
