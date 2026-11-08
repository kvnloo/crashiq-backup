"""Placement sample, the California way (brief 2026-11-07), for MS or NE: 2,000 random 2024 crashes from the biggest
county, read through the state's reader; GPS present and plausible; then hide the GPS, place street pairs on a
TIGER/Line 2024 network with locate.place, and score against the hidden GPS (within 250 ft, Wilson 95% low).

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/<st>-2026-11-08/placement_sample.py <st> <scratch>
"""

from __future__ import annotations

import collections
import gzip
import json
import math
import random
import sys
from pathlib import Path

from crashiq import locate, osm, tiger

FT250_M = 250 * 0.3048


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def rows(st: str, scratch: Path):
    if st == "ms":                               # the reader's own cache of DPS's 2024 workbook
        recs = json.loads(gzip.decompress(next((scratch / "cache").glob("ms_dps_2024_*.json.gz")).read_bytes()))
        return "Hinds County (28049), 2024", "28049", [c for c in recs if c["county_fips"] == "28049"]
    from crashiq.sources import ne_ntip          # NTIP box over Omaha, 2024 (filter flags don't matter here)
    raw = [c for g in json.loads((scratch / "omaha2024.json").read_text())["CoordGroups"] for c in g["Crashes"]]
    none = {f: set() for f in ne_ntip.FLAGS}
    recs = [r for r in (ne_ntip.crash_record(c, none) for c in raw) if r and r["county_fips"] == "31055"]
    return "Douglas County (31055), 2024", "31055", recs


def run(st: str, scratch: Path, n: int = 2000) -> dict:
    area, fips, recs = rows(st, scratch)
    random.Random(2026).shuffle(recs)
    recs = recs[:n]
    net = osm.Network(tiger.elements(scratch / f"tl_2024_{fips}_edges.zip", scratch / f"tl_2024_{fips}_featnames.zip"))
    gate = locate.Gate(tiger_only_auto=True)     # TIGER-only network: plain Gate() auto-places nothing
    tiers, reasons, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    gps = pairs = placed = auto = hits = auto_hits = 0
    for c in recs:
        la, lo = c["lat"], c["lon"]
        gps += la is not None
        prim, sec = c["primary_road"], c["secondary_road"]
        if not (prim and sec):
            reasons["no cross street in source"] += 1
            continue
        pairs += 1
        pl = locate.place(net, {"primary_road": prim, "secondary_road": sec, "offset_ft": c["offset_ft"],
                                "offset_dir": c["offset_dir"]})          # GPS hidden
        tiers[pl.tier] += 1
        if pl.lat is None:
            reasons[pl.note or pl.tier] += 1
            if len(examples[pl.note]) < 6:
                examples[pl.note].append(f"{prim} & {sec}")
            continue
        placed += 1
        if la is None:
            continue
        close = osm.metres((pl.lat, pl.lon), (la, lo)) <= FT250_M
        hits += close
        if gate.auto(pl):
            auto += 1
            auto_hits += close
        if not close and len(examples["placed >250 ft off"]) < 6:
            examples["placed >250 ft off"].append(
                f"{prim} & {sec} [{pl.tier}] {osm.metres((pl.lat, pl.lon), (la, lo)) / 0.3048:.0f} ft")
    k = len(recs)
    return {"area": area, "n": k, "gps_share": round(gps / k, 4), "street_pair_share": round(pairs / k, 4),
            "tiers": dict(tiers), "name_placed_share": round(placed / k, 4),
            "name_placed_share_of_pairs": round(placed / pairs, 4) if pairs else None,
            "auto_share": round(auto / k, 4), "auto_share_of_pairs": round(auto / pairs, 4) if pairs else None,
            "gate": "Gate() tiers with tiger_only_auto=True (TIGER-only network; plain Gate() auto-places 0 here)",
            "within_250ft": round(auto_hits / auto, 4) if auto else None,
            "within_250ft_low": round(wilson_low(auto_hits, auto), 4),
            "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
            "within_250ft_all_placed_low": round(wilson_low(hits, placed), 4),
            "not_placed": dict(reasons.most_common(8)), "examples": dict(examples)}


if __name__ == "__main__":
    st, scratch = sys.argv[1], Path(sys.argv[2])
    out = run(st, scratch)
    print(json.dumps(out, indent=1))
    (Path(__file__).parent / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
