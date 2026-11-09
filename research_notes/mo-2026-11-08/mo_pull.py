"""Missouri: pull Jackson County (Kansas City) 2023 through the reader's own calls, measure it, run the California-way
placement test (hide the GPS, place the officer's road pair and offset on TIGER/Line 2024 Jackson County), and record
the test fixture.
    PYTHONPATH=backend python research_notes/mo-2026-11-08/mo_pull.py <scratch dir>
"""
import collections
import json
import math
import random
import sys
import urllib.request
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import mo_mshp as mo

out = Path(sys.argv[1])
HERE = Path(__file__).parent
FIPS = "29095"
BOX = json.loads((mo.REF / "county_boxes_mo.json").read_text())["counties"][FIPS]["box"]
FT250_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


got = mo.fetch_contract(BOX, [FIPS], [2023], out)
recs = [c for c in got["crashes"] if c["county_fips"] == FIPS]
n = len(recs)
ids = collections.Counter(c["crash_id"] for c in recs)
res = {"area": "Jackson County (29095), 2023, every row", "n": n, "cleaning": got["cleaning"],
       "gps_share": round(sum(c["lat"] is not None for c in recs) / n, 4),
       "primary_share": round(sum(bool(c["primary_road"]) for c in recs) / n, 4),
       "street_pair_share": round(sum(bool(c["primary_road"] and c["secondary_road"]) for c in recs) / n, 4),
       "offset_share": round(sum(c["offset_ft"] is not None for c in recs) / n, 4),
       "severity": dict(collections.Counter(c["severity"] for c in recs)),
       "freeway_share": round(sum(c["is_freeway"] for c in recs) / n, 4),
       "duplicate_ids": sum(v - 1 for v in ids.values() if v > 1),
       "city": dict(collections.Counter(c["city"] for c in recs).most_common(4))}

for kind in ("edges", "featnames"):
    f = out / f"tl_2024_{FIPS}_{kind}.zip"
    if not f.exists():
        urllib.request.urlretrieve(f"https://www2.census.gov/geo/tiger/TIGER2024/{kind.upper()}/{f.name}", f)
net = osm.Network(tiger.elements(out / f"tl_2024_{FIPS}_edges.zip", out / f"tl_2024_{FIPS}_featnames.zip"))
gate = locate.Gate(tiger_only_auto=True)     # TIGER-only network: plain Gate() auto-places nothing
gps = [c for c in recs if c["lat"] is not None]
random.Random(2026).shuffle(gps)
sample = gps[:2000]
tiers, why, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
pairs = placed = auto = hits = auto_hits = 0
for c in sample:
    if not (c["primary_road"] and c["secondary_road"]):
        why["no cross street in source"] += 1
        continue
    pairs += 1
    pl = locate.place(net, {k: c[k] for k in ("primary_road", "secondary_road", "offset_ft", "offset_dir")})
    tiers[pl.tier] += 1
    if pl.lat is None:
        why[pl.note or pl.tier] += 1
        if len(ex[pl.note]) < 6:
            ex[pl.note].append(f"{c['primary_road']} & {c['secondary_road']}")
        continue
    placed += 1
    close = osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"])) <= FT250_M
    hits += close
    if gate.auto(pl):
        auto += 1
        auto_hits += close
k = len(sample)
nogps = [c for c in recs if c["lat"] is None]
res["placement"] = {"area": "Jackson County (29095), 2023, random 2,000 with GPS (seed 2026)", "n": k,
                    "street_pair_share": round(pairs / k, 4), "tiers": dict(tiers),
                    "name_placed_share": round(placed / k, 4), "auto_share": round(auto / k, 4),
                    "gate": "Gate(tiger_only_auto=True) on a TIGER-only network",
                    "within_250ft": round(auto_hits / auto, 4) if auto else None,
                    "within_250ft_low": round(wilson_low(auto_hits, auto), 4),
                    "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
                    "not_placed": dict(why.most_common(8)), "examples": dict(ex),
                    "no_gps_crashes": len(nogps),
                    "no_gps_with_street_pair": sum(bool(c["primary_road"] and c["secondary_road"]) for c in nogps)}
print(json.dumps(res, indent=1))
(HERE / "placement_sample.json").write_text(json.dumps(res, indent=1) + "\n")

# fixture: raw rows, one per severity x light x At/After/Before, plus ped/bike/freeway/no-GPS/parking-lot/ramp rows
raw = json.loads(next(out.glob("mo_mshp_*.json")).read_text())
pick, seen = [], collections.Counter()
for a in raw:
    c = mo.contract_record(a)
    keys = [("sev", c["severity"], a["LIGHT_COND"], a["INTER_LOC"]), ("ped", c["ped"]), ("bike", c["bike"]),
            ("fwy", c["is_freeway"]), ("gps", c["lat"] is None), ("pp", (a["ON_STREET"] or "")[:3]),
            ("at", (a["AT_STREET"] or "").split(" ")[0])]
    for key in keys:
        if seen[key] < 1:
            seen[key] += 1
            pick.append(a)
pick = list({a["OBJECTID"]: a for a in pick}.values())
fx = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "mo_mshp.json"
fx.write_text(json.dumps({"source": mo.LAYER, "recorded": "2026-11-08", "box": BOX, "rows": pick}, indent=0))
print("fixture rows", len(pick), fx.stat().st_size, "bytes")
