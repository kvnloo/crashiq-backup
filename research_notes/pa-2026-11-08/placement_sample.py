"""Pennsylvania placement sample, the California way (brief 2026-11-07, statewide brief 2026-11-08).

Input: PennDOT's Statewide_2025.zip (the newest full year), read through the reader itself
(sources/pa_penndot.read_zip), so the street pair is exactly what CrashIQ would get: the first ROADWAY street name
and the first different one. For 2,000 random 2025 crashes per county with both names: hide PennDOT's GPS, place
from the pair on a Census TIGER/Line 2024 network with locate.place, and score against the hidden GPS.

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/pa-2026-11-08/placement_sample.py <scratch>
(<scratch> holds sw_2025.zip and tl_2024_<fips>_{edges,featnames}.zip)
"""

from __future__ import annotations

import collections
import json
import math
import random
import sys
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import pa_penndot

AREAS = {"Philadelphia": ("67", "42101"), "Allegheny (Pittsburgh)": ("02", "42003")}
FT250_M = 250 * 0.3048


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def run(scratch: Path, area: str, county: str, fips: str, n: int = 2000) -> dict:
    allrows = pa_penndot.read_zip(scratch / "sw_2025.zip", lambda r: r["COUNTY"].strip().zfill(2) == county,
                                  pa_penndot.municipalities())
    gps_all = sum(c["lat"] is not None for c in allrows)
    pairs = [c for c in allrows if c["primary_road"] and c["secondary_road"]]
    nogps_pairs = sum(c["lat"] is None for c in pairs)
    rows = [c for c in pairs if c["lat"] is not None]
    random.Random(2026).shuffle(rows)
    rows = rows[:n]
    net = osm.Network(tiger.elements(scratch / f"tl_2024_{fips}_edges.zip", scratch / f"tl_2024_{fips}_featnames.zip"))
    gate = locate.Gate()
    tgate = locate.Gate(tiger_only_auto=True)    # this network is TIGER-only: the default gate never auto-places on it
    tiers, reasons, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    hits = auto = auto_hits = tauto = tauto_hits = 0
    for c in rows:
        pl = locate.place(net, {"primary_road": c["primary_road"], "secondary_road": c["secondary_road"],
                                "offset_ft": None, "offset_dir": None})          # GPS hidden
        tiers[pl.tier] += 1
        if pl.lat is None:
            reasons[pl.note or pl.tier] += 1
            if len(examples[pl.note or pl.tier]) < 6:
                examples[pl.note or pl.tier].append(f"{c['primary_road']} & {c['secondary_road']}")
            continue
        d = osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"]))
        close = d <= FT250_M
        hits += close
        if gate.auto(pl):
            auto += 1
            auto_hits += close
        if tgate.auto(pl):
            tauto += 1
            tauto_hits += close
        if not close and len(examples["placed >250 ft off"]) < 8:
            examples["placed >250 ft off"].append(f"{c['primary_road']} & {c['secondary_road']} [{pl.tier}] "
                                                  f"{d / 0.3048:.0f} ft")
    return {
        "area": f"{area} ({fips}), 2025", "county_crashes": len(allrows),
        "gps_share": round(gps_all / len(allrows), 4),
        "street_pair_share": round(len(pairs) / len(allrows), 4), "no_gps_with_pair": nogps_pairs,
        "no_gps": len(allrows) - gps_all, "n": len(rows), "tiers": dict(tiers),
        "name_placed_share": round((len(rows) - sum(reasons.values())) / len(rows), 4),
        "auto_share": round(auto / len(rows), 4),
        "within_250ft_auto": round(auto_hits / auto, 4) if auto else None,
        "within_250ft_auto_low": round(wilson_low(auto_hits, auto), 4),
        "auto_share_tiger_only_auto": round(tauto / len(rows), 4),
        "within_250ft_tiger_only_auto": round(tauto_hits / tauto, 4) if tauto else None,
        "within_250ft_tiger_only_auto_low": round(wilson_low(tauto_hits, tauto), 4),
        "within_250ft_all_placed": round(hits / (len(rows) - sum(reasons.values())), 4),
        "within_250ft_all_placed_low": round(wilson_low(hits, len(rows) - sum(reasons.values())), 4),
        "not_placed": dict(reasons.most_common(10)), "examples": dict(examples),
    }


if __name__ == "__main__":
    scratch = Path(sys.argv[1])
    out = {a: run(scratch, a, c, f) for a, (c, f) in AREAS.items()}
    print(json.dumps(out, indent=1))
    (Path(__file__).parent / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
