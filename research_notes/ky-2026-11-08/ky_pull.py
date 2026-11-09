"""Kentucky: pull a Louisville sample through the reader's own calls, measure it, run the California-way placement
test (hide the GPS, place street pairs on TIGER/Line 2024 Jefferson County), and record the test fixture.
    PYTHONPATH=backend python research_notes/ky-2026-11-08/ky_pull.py <scratch dir>
"""
import collections
import json
import math
import random
import sys
import urllib.request
from datetime import date
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import ky_ksp

out = Path(sys.argv[1])
HERE = Path(__file__).parent
BOX = (38.15, -85.80, 38.30, -85.60)                     # central Louisville
FT250_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


cache = out / "louisville_2025q1.json"
if cache.exists():
    d = json.loads(cache.read_text())
    rows, pts = d["rows"], d["points"]
else:
    post = ky_ksp.session()
    rows = ky_ksp.search(post, BOX, date(2025, 1, 1), date(2025, 2, 28))
    pts = ky_ksp.points(post, [r["xIncidentGUID"] for r in rows])
    early = {y: len(ky_ksp.search(post, (38.24, -85.77, 38.26, -85.74), date(y, 1, 1), date(y, 1, 31)))
             for y in (2015, 2016, 2019)}
    cache.write_text(json.dumps({"rows": rows, "points": pts, "early": early}))
    d = {"early": json.loads(cache.read_text())["early"]}
recs = [ky_ksp.contract_record(r, pts.get(r["xIncidentGUID"])) for r in rows]
n = len(recs)
s, w, nn, e = BOX
inbox = sum(c["lat"] is not None and s <= c["lat"] <= nn and w <= c["lon"] <= e for c in recs)
res = {"area": "central Louisville box (38.15,-85.80)-(38.30,-85.60), 2025-01-01..2025-02-28, every row", "n": n,
       "gps_share": round(sum(c["lat"] is not None for c in recs) / n, 4), "gps_inside_query_box": round(inbox / n, 4),
       "primary_share": round(sum(bool(c["primary_road"]) for c in recs) / n, 4),
       "street_pair_share": round(sum(bool(c["primary_road"] and c["secondary_road"]) for c in recs) / n, 4),
       "house_number_share": round(sum(bool(r.get("Street #")) for r in rows) / n, 4),
       "severity": dict(collections.Counter(c["severity"] for c in recs)),
       "county": dict(collections.Counter(c["county_code"] for c in recs).most_common(4)),
       "freeway_share": round(sum(c["is_freeway"] for c in recs) / n, 4),
       "parking_lot_share": round(sum((c["direction_analysis"] or "").startswith("COLLISION IN PARKING LOT")
                                      for c in recs) / n, 4),
       "earliest_years_jan_tiny_box": d.get("early")}

# placement, the California way: hide GPS, place the street pair on TIGER Jefferson County (21111)
for kind in ("edges", "featnames"):
    f = out / f"tl_2024_21111_{kind}.zip"
    if not f.exists():
        urllib.request.urlretrieve(f"https://www2.census.gov/geo/tiger/TIGER2024/{kind.upper()}/{f.name}", f)
net = osm.Network(tiger.elements(out / "tl_2024_21111_edges.zip", out / "tl_2024_21111_featnames.zip"))
gate = locate.Gate(tiger_only_auto=True)     # TIGER-only network: plain Gate() auto-places nothing
jeff = [c for c in recs if c["county_fips"] == "21111" and c["lat"] is not None]
random.Random(2026).shuffle(jeff)
sample = jeff[:2000]
tiers, why, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
pairs = placed = auto = hits = auto_hits = 0
for c in sample:
    if not (c["primary_road"] and c["secondary_road"]):
        why["no cross street in source"] += 1
        continue
    pairs += 1
    pl = locate.place(net, {"primary_road": c["primary_road"], "secondary_road": c["secondary_road"],
                            "offset_ft": None, "offset_dir": None})
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
res["placement"] = {"area": "Jefferson County (21111), 2025-01..02, random 2,000 with GPS (seed 2026)", "n": k,
                    "street_pair_share": round(pairs / k, 4), "tiers": dict(tiers),
                    "name_placed_share": round(placed / k, 4), "auto_share": round(auto / k, 4),
                    "gate": "Gate(tiger_only_auto=True) on a TIGER-only network",
                    "within_250ft": round(auto_hits / auto, 4) if auto else None,
                    "within_250ft_low": round(wilson_low(auto_hits, auto), 4),
                    "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
                    "not_placed": dict(why.most_common(8)), "examples": dict(ex)}
print(json.dumps(res, indent=1))
(HERE / "placement_sample.json").write_text(json.dumps(res, indent=1) + "\n")

# fixture: one row per severity x manner, ped/bike/freeway/parkway rows, and one row with no mapping point
pick, seen = [], collections.Counter()
for r, c in zip(rows, recs):
    for key in [("sev", c["severity"], c["collision_type"]), ("ped", c["ped"]), ("bike", c["bike"]),
                ("fwy", c["is_freeway"], (c["road_number"] or "")[:2]), ("light", c["lighting"])]:
        if seen[key] < 1:
            seen[key] += 1
            pick.append(r)
uniq = list({r["xIncidentGUID"]: r for r in pick}.values())
fx = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "ky_ksp.json"
fx_pts = {g: pts[g] for g in [r["xIncidentGUID"] for r in uniq[:-1]] if g in pts}  # the last row keeps no point
fx.write_text(json.dumps({"source": ky_ksp.BASE, "recorded": "2026-11-08", "box": BOX, "rows": uniq,
                          "points": fx_pts}, indent=0))
print("fixture rows", len(uniq), fx.stat().st_size, "bytes")
