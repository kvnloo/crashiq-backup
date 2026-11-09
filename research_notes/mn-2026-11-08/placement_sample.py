"""Placement sample, the California way (brief 2026-11-07), Minnesota: 2,000 random 2024 Hennepin County crashes from
the MNCrash statewide 2024 export, read through the reader; GPS present and plausible; then hide the GPS, place the
officer's street pair on a TIGER/Line 2024 network with locate.place, and score against the hidden GPS.

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/mn-2026-11-08/placement_sample.py <export.csv> <tiger dir>
"""

from __future__ import annotations

import collections
import json
import math
import random
import re
import sys
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import mn_mncrash as mn

FT250_M = 250 * 0.3048


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def run(csv_path: Path, tiger_dir: Path, fips: str = "27053", n: int = 2000) -> dict:
    recs = [r for r in map(mn.crash_record, mn.rows(csv_path.read_text(encoding="utf-8-sig"))) if r["county_fips"] == fips]
    random.Random(2026).shuffle(recs)
    recs = recs[:n]
    net = osm.Network(tiger.elements(tiger_dir / f"tl_2024_{fips}_edges.zip", tiger_dir / f"tl_2024_{fips}_featnames.zip"))
    gate = locate.Gate(tiger_only_auto=True)       # TIGER-only network: plain Gate() auto-places nothing
    tiers, reasons, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    gps = pairs = near = placed = auto = hits = auto_hits = 0
    for c in recs:
        la, lo = c["lat"], c["lon"]
        gps += la is not None
        prim, sec = c["primary_road"], c["secondary_road"]
        if not (prim and sec):
            reasons["no cross street in source"] += 1
            continue
        pairs += 1
        near += bool(re.search(r"\snear\s", c["road_text"] or "", re.I))
        pl = locate.place(net, {"primary_road": prim, "secondary_road": sec, "offset_ft": None, "offset_dir": None})
        tiers[pl.tier] += 1
        if pl.lat is None:
            reasons[pl.note or pl.tier] += 1
            if len(examples[pl.note]) < 6:
                examples[pl.note].append(c["road_text"])
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
            examples["placed >250 ft off"].append(f"{c['road_text']} [{pl.tier}] {d / 0.3048:.0f} ft")
    k = len(recs)
    return {"area": "Hennepin County (27053), 2024", "n": k, "gps_share": round(gps / k, 4),
            "street_pair_share": round(pairs / k, 4), "near_share_of_pairs": round(near / pairs, 4),
            "house_address_share": 0.0, "tiers": dict(tiers),
            "name_placed_share": round(placed / k, 4), "name_placed_share_of_pairs": round(placed / pairs, 4),
            "auto_share": round(auto / k, 4), "auto_share_of_pairs": round(auto / pairs, 4),
            "gate": "Gate() tiers with tiger_only_auto=True (TIGER-only network; plain Gate() auto-places 0 here)",
            "within_250ft": round(auto_hits / auto, 4) if auto else None,
            "within_250ft_low": round(wilson_low(auto_hits, auto), 4),
            "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
            "within_250ft_all_placed_low": round(wilson_low(hits, placed), 4),
            "not_placed": dict(reasons.most_common(8)), "examples": dict(examples)}


if __name__ == "__main__":
    out = run(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(out, indent=1))
    (Path(__file__).parent / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
