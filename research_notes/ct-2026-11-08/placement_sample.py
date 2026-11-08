"""Connecticut placement sample, the California way (brief 2026-11-07).

Input: every 2024 Hartford crash, person and vehicle row from the CTCDR public MapServer (pull.py-style scratch JSON:
crash_Hartford_2024.json ...). Read through sources/ct_uconn.records (the pack's own reader). For 2,000 random crashes:
GPS present and plausible; then, on those naming a road and an intersecting road, hide the GPS, place from the two
names on a TIGER/Line 2024 network of the Capitol Planning Region (09110) with locate.place, score against the GPS.
Route roads come as "CT 187" from the reader; when that fails, retry TIGER's own form ("STATE RTE 187").

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/ct-2026-11-08/placement_sample.py <scratch>
"""

from __future__ import annotations

import collections
import json
import math
import random
import re
import sys
from pathlib import Path

from crashiq import locate, names, osm, tiger
from crashiq.sources import ct_uconn

FT250_M = 250 * 0.3048
TIGER_FORM = {"CT": "STATE RTE", "US": "US HWY", "I": "I"}


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def tiger_form(road: str | None) -> str | None:
    m = re.match(r"^(CT|US|I) (\d+[A-Z]?)$", road or "")
    return f"{TIGER_FORM[m[1]]} {m[2]}" if m else None


def run(scratch: Path, n: int = 2000) -> dict:
    raw = {k: json.load(open(scratch / f"{k}_Hartford_2024.json")) for k in ("crash", "person", "vehicle")}
    recs = ct_uconn.records(raw)
    sev_all = collections.Counter(c["severity"] for c in recs)
    random.Random(2026).shuffle(recs)
    rows = recs[:n]
    net = osm.Network(tiger.elements(scratch / "tl_2024_09110_edges.zip", scratch / "tl_2024_09110_featnames.zip"))
    gate = locate.Gate()
    gate_tiger = locate.Gate(tiger_only_auto=True)   # the sample's network is TIGER only; the app's is OSM + TIGER
    tiers, reasons, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    named = hits = auto = auto_hits = retry_used = auto_t = auto_t_hits = 0
    gps = sum(c["lat"] is not None for c in rows)
    for c in rows:
        prim, sec = c["primary_road"], c["secondary_road"]
        if not (prim and sec):
            reasons["no intersecting road in source"] += 1
            continue
        named += 1
        crash = {"primary_road": prim, "secondary_road": sec, "offset_ft": None, "offset_dir": None}   # GPS hidden
        pl = locate.place(net, crash)
        if pl.lat is None and (tiger_form(prim) or tiger_form(sec)):
            alt = locate.place(net, {**crash, "primary_road": tiger_form(prim) or prim,
                                     "secondary_road": tiger_form(sec) or sec})
            if alt.lat is not None:
                pl, retry_used = alt, retry_used + 1
        tiers[pl.tier] += 1
        if pl.lat is None:
            reasons[pl.note or pl.tier] += 1
            if len(examples[pl.note or pl.tier]) < 6:
                examples[pl.note or pl.tier].append(f"{c['road_as_reported']} | {prim} & {sec}")
            continue
        if c["lat"] is None:
            continue
        d = osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"]))
        close = d <= FT250_M
        hits += close
        if gate.auto(pl):
            auto += 1
            auto_hits += close
        if gate_tiger.auto(pl):
            auto_t += 1
            auto_t_hits += close
        if not close and len(examples["placed >250 ft off"]) < 8:
            examples["placed >250 ft off"].append(f"{prim} & {sec} [{pl.tier}] {d / 0.3048:.0f} ft")
    placed = sum(v for k, v in tiers.items() if k != "review")
    return {
        "area": "Hartford (town, Capitol Planning Region 09110), 2024", "n": len(rows), "town_year_rows": len(recs),
        "severity_town_year": dict(sev_all), "gps_share": round(gps / len(rows), 4),
        "street_pair_share": round(named / len(rows), 4), "tiers": dict(tiers),
        "name_placed_share": round(placed / len(rows), 4),
        "name_placed_share_of_pairs": round(placed / named, 4) if named else None,
        "auto_share": round(auto / len(rows), 4), "auto_share_of_pairs": round(auto / named, 4) if named else None,
        "tiger_route_retry_used": retry_used,
        "auto_share_if_tiger_only_auto": round(auto_t / len(rows), 4),
        "auto_share_of_pairs_if_tiger_only_auto": round(auto_t / named, 4) if named else None,
        "within_250ft_auto_if_tiger_only_auto": round(auto_t_hits / auto_t, 4) if auto_t else None,
        "within_250ft_auto_if_tiger_only_auto_low": round(wilson_low(auto_t_hits, auto_t), 4),
        "within_250ft_auto": round(auto_hits / auto, 4) if auto else None,
        "within_250ft_auto_low": round(wilson_low(auto_hits, auto), 4),
        "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
        "within_250ft_all_placed_low": round(wilson_low(hits, placed), 4),
        "street_key_examples": {r: names.street_key(r) for r in ("CT 187", "STATE RTE 187", "I 84", "US 44", "MAIN ST")},
        "not_placed": dict(reasons.most_common(10)), "examples": dict(examples),
    }


if __name__ == "__main__":
    out = run(Path(sys.argv[1]))
    print(json.dumps(out, indent=1))
    (Path(__file__).parent / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
