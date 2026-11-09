"""Colorado: placement sample (Denver County 2024, random 2,000 of every row) and the offline test fixture, from CDOT's
live 2024 Statewide Crash Data Listing (read through sources/co_cdot.py and its cache). The California way: GPS present
and plausible; then hide the GPS, place the reported street pair on a TIGER/Line 2024 network with locate.place, and
score against the hidden GPS (within 250 ft, Wilson 95% low).

Run: PYTHONPATH=backend python research_notes/co-2026-11-08/co_pull.py <scratch dir with cache/ and tl_2024_08031_*.zip>
"""
import collections
import json
import math
import random
import sys
from pathlib import Path

import openpyxl

from crashiq import locate, osm, tiger
from crashiq.sources import co_cdot

HERE = Path(__file__).parent
FIX = HERE.parents[1] / "tests/fixtures/co_cdot_2024.xlsx"
scratch = Path(sys.argv[1])
FT250_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


ids = co_cdot.docids()
stats = {}
for y in (2021, 2022, 2023, 2024):
    rows = co_cdot.year_rows(y, ids[y], scratch / "cache")
    recs = [co_cdot.contract_record(a) for a in rows]
    stats[y] = {"rows": len(rows), "gps_share": round(sum(c["lat"] is not None for c in recs) / len(recs), 4),
                "street_pair_share": round(sum(bool(c["primary_road"] and c["secondary_road"]) for c in recs)
                                           / len(recs), 4),
                "severity": collections.Counter(c["severity"] for c in recs),
                "no_county": sum(not c["county_fips"] for c in recs)}
rows = co_cdot.year_rows(2024, ids[2024], scratch / "cache")
den = [(a, co_cdot.contract_record(a)) for a in rows if a.get("County") == "DENVER"]
sample = [c for _, c in den]
random.Random(2026).shuffle(sample)
sample = sample[:2000]

net = osm.Network(tiger.elements(scratch / "tl_2024_08031_edges.zip", scratch / "tl_2024_08031_featnames.zip"))
gate = locate.Gate(tiger_only_auto=True)       # TIGER-only network: plain Gate() auto-places nothing here
tiers, reasons, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
gps = pairs = placed = auto = hits = auto_hits = 0
for c in sample:
    la, lo = c["lat"], c["lon"]
    gps += la is not None
    prim, sec = c["primary_road"], c["secondary_road"]
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
nogps = [c for _, c in den if c["lat"] is None]
out = {"area": "Denver County (08031), 2024, random 2,000 (seed 2026)", "n": k, "county_rows_2024": len(den),
       "years": stats, "gps_share": round(gps / k, 4), "street_pair_share": round(pairs / k, 4),
       "house_address_share": 0.0, "tiers": dict(tiers),
       "name_placed_share": round(placed / k, 4), "name_placed_share_of_pairs": round(placed / pairs, 4),
       "auto_share": round(auto / k, 4), "gate": "Gate(tiger_only_auto=True) on a TIGER-only network",
       "within_250ft": round(auto_hits / auto, 4) if auto else None, "within_250ft_low": round(wilson_low(auto_hits, auto), 4),
       "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
       "within_250ft_all_placed_low": round(wilson_low(hits, placed), 4),
       "denver_no_gps": len(nogps),
       "denver_no_gps_with_street_pair": sum(bool(c["primary_road"] and c["secondary_road"]) for c in nogps),
       "not_placed": dict(reasons.most_common(8)), "examples": dict(examples)}
(HERE / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))

# fixture: a spread of 2024 rows (Denver and elsewhere) by severity, road user, system, link form and no GPS
pick, seen = [], set()


def take(pairs_, n):
    for a, _ in pairs_[:n]:
        if a["CUID"] not in seen:
            seen.add(a["CUID"])
            pick.append(a)


allp = [(a, co_cdot.contract_record(a)) for a in rows[::7]]
for sev in "KABCO":
    take([p for p in den if p[1]["severity"] == sev], 6)
for flag in ("ped", "bike", "escooter", "motorcycle", "heavy_truck", "is_freeway", "offset_ft", "hit_run"):
    take([p for p in allp if p[1][flag]], 3)
take([p for p in allp if p[1]["lat"] is None], 4)
take([p for p in allp if (p[0].get("Location 2") or "").startswith("MM ")], 3)
take([p for p in allp if p[1]["collision_type"] == "HIT OBJECT"], 2)
wb = openpyxl.Workbook()
ws = wb.active
ws.append(list(co_cdot.KEEP))
for a in pick:
    ws.append([a.get(k) for k in co_cdot.KEEP])
wb.save(FIX)
print(len(pick), "rows", FIX.stat().st_size, "bytes")
