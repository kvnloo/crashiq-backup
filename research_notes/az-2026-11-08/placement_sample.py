"""Placement sample, the California way (brief 2026-11-07), for the two open city feeds of gated states.

NV: City of Las Vegas "CLV Traffic Crashes" 2020 (NDOT export layout: Primary_St, Distance, Dir, Secondary_), which has
    no GPS (rows carry ward polygons only), so only the placed and auto shares can be measured, not accuracy.
AZ: City of Tempe "1.08 Crash Data Report" 2025 (ACIS-style StreetName, CrossStreet, Distance, no offset direction),
    which has GPS: it is hidden, the crash is placed from the two names, and scored against it.
Network: TIGER/Line 2024 EDGES + FEATNAMES for the county (Clark 32003, Maricopa 04013), clipped to the city box.

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/<st>-2026-11-08/placement_sample.py <az|nv> <scratch>
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

FT250_M = 250 * 0.3048
# NDOT writes routes run together with a direction: IR15N, US95S, SR159, CC215S; "X TO Y INTnn" is a ramp.
NV_ROUTE = re.compile(r"^(IR|US|SR|CC)\s*(\d+)[NSEW]?$")
NV_FORMS = {"IR": ["I-{}"], "US": ["US {}", "US Hwy {}"], "SR": ["NV {}", "State Rte {}", "State Hwy {}"],
            "CC": ["Clark County {}", "I-{}", "Co Rd {}"]}
BOX = {"nv": (35.95, 36.40, -115.45, -114.95), "az": (33.28, 33.50, -112.01, -111.85)}
TIGER = {"nv": "32003", "az": "04013"}


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def forms(road: str | None) -> list[str]:
    """Every spelling to try for a road, the reader's first."""
    road = (road or "").strip()
    m = NV_ROUTE.match(road)
    return [f.format(m[2]) for f in NV_FORMS[m[1]]] if m else [road]


def rows_for(st: str, scratch: Path) -> list[dict]:
    if st == "nv":
        out = []
        for r in json.load(open(scratch / "nv/clv_2020.json")):
            at = r["Dir"] in (None, "AT INT")
            out.append({"primary": r["Primary_St"], "secondary": r["Secondary_"], "lat": None, "lon": None,
                        "offset_ft": None if at else float(r["Distance"] or 0) or None,
                        "offset_dir": None if at else r["Dir"], "ramp": " TO " in (r["Primary_St"] or "")})
        return out
    return [{"primary": r["StreetName"], "secondary": r["CrossStreet"], "lat": r["Latitude"], "lon": r["Longitude"],
             "offset_ft": None, "offset_dir": None, "dist": r["Distance"] or 0, "ramp": False}
            for r in json.load(open(scratch / "az/tempe_2025.json"))]


def run(st: str, scratch: Path, n: int = 2000) -> dict:
    s, nn, w, e = BOX[st]
    c = TIGER[st]
    net = osm.Network(tiger.elements(scratch / st / f"tl_2024_{c}_edges.zip", scratch / st / f"tl_2024_{c}_featnames.zip",
                                     keep=lambda lat, lon: s <= lat <= nn and w <= lon <= e))
    rows = rows_for(st, scratch)
    random.Random(2026).shuffle(rows)
    rows = rows[:n]
    gate, gate_t = locate.Gate(), locate.Gate(tiger_only_auto=True)   # TIGER-only network; the app's is OSM + TIGER
    tiers, reasons, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    named = placed = auto = auto_t = hits = auto_t_hits = scored = near_hits = near_n = retry = 0
    for r in rows:
        if not (r["primary"] and r["secondary"]) or r["ramp"]:
            reasons["ramp text" if r["ramp"] else "no cross street"] += 1
            continue
        named += 1
        pl = None
        for i, p in enumerate(forms(r["primary"])):
            for j, q in enumerate(forms(r["secondary"])):
                pl = locate.place(net, {"primary_road": p, "secondary_road": q,
                                        "offset_ft": r["offset_ft"], "offset_dir": r["offset_dir"]})
                if pl.lat is not None:
                    retry += bool(i or j)
                    break
            if pl.lat is not None:
                break
        tiers[pl.tier] += 1
        if pl.lat is None:
            reasons[pl.note or pl.tier] += 1
            if len(ex[pl.note or pl.tier]) < 6:
                ex[pl.note or pl.tier].append(f"{r['primary']} & {r['secondary']}")
            continue
        placed += 1
        auto += gate.auto(pl)
        a_t = gate_t.auto(pl)
        auto_t += a_t
        if r["lat"] is None:
            continue
        scored += 1
        close = osm.metres((pl.lat, pl.lon), (r["lat"], r["lon"])) <= FT250_M
        hits += close
        auto_t_hits += close and a_t
        if r.get("dist", 0) <= 250:          # Tempe gives no offset direction, so only near-intersection crashes can score
            near_n += 1
            near_hits += close
    k = len(rows)
    return {
        "area": {"nv": "City of Las Vegas (Clark 32003), 2020", "az": "City of Tempe (Maricopa 04013), 2025"}[st],
        "n": k, "gps_share": round(sum(r["lat"] is not None for r in rows) / k, 4),
        "street_pair_share": round(named / k, 4), "tiers": dict(tiers),
        "name_placed_share": round(placed / k, 4), "name_placed_share_of_pairs": round(placed / named, 4),
        "auto_share": round(auto / k, 4), "auto_share_if_tiger_only_auto": round(auto_t / k, 4),
        "route_form_retry_used": retry, "scored_against_gps": scored,
        "within_250ft_all_placed": round(hits / scored, 4) if scored else "not measured (no GPS in source)",
        "within_250ft_all_placed_low": round(wilson_low(hits, scored), 4) if scored else None,
        "within_250ft_auto_if_tiger_only_auto": round(auto_t_hits / auto_t, 4) if scored and auto_t else None,
        "within_250ft_auto_if_tiger_only_auto_low": round(wilson_low(auto_t_hits, auto_t), 4) if scored else None,
        "within_250ft_offset_le_250ft": round(near_hits / near_n, 4) if near_n else None,
        "within_250ft_offset_le_250ft_low": round(wilson_low(near_hits, near_n), 4) if near_n else None,
        "offset_le_250ft_n": near_n,
        "not_placed": dict(reasons.most_common(10)), "examples": dict(ex),
    }


if __name__ == "__main__":
    st = sys.argv[1]
    out = run(st, Path(sys.argv[2]))
    print(json.dumps(out, indent=1))
    Path(sys.argv[3] if len(sys.argv) > 3 else f"placement_sample_{st}.json").write_text(json.dumps(out, indent=1) + "\n")
