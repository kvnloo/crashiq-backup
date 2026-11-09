"""Placement sample, the California way (brief 2026-11-07), for VT or IA: about 2,000 newest-full-year crashes from one
county, read through the state's reader; GPS present and plausible; then hide the GPS, place street pairs on a
TIGER/Line 2024 network with locate.place, and score against the hidden GPS (within 250 ft, Wilson 95% low).

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/<st>-2026-11-08/placement_sample.py <st> <scratch>
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
ROUTE_PREFIX = re.compile(r"^(?:US|VT|I|IA)-?\s?\d+[A-Z]?\s+(?=[A-Z])", re.I)   # "US-7 Shelburne Rd" -> "Shelburne Rd"


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def vt_rows(scratch: Path) -> tuple[str, str, list[dict]]:
    from crashiq.sources import vt_vtrans
    raw = vt_vtrans.fetch_raw("CITYORTOWNid LIKE '04%' AND ACCIDENTDATE >= TIMESTAMP '2025-01-01 00:00:00' "
                              "AND ACCIDENTDATE < TIMESTAMP '2026-01-01 00:00:00'", scratch)
    good = [a for a in raw if (a.get("InjuryType") or "").strip() in vt_vtrans.SEVERITY]
    return "Chittenden County (50007), 2025", "50007", [vt_vtrans.contract_record(a) for a in good]


def ia_rows(scratch: Path) -> tuple[str, str, list[dict]]:
    from crashiq.sources import ia_dot
    raw = json.loads((scratch / "sample_2000.json").read_text())       # Polk County 2024, random 2,000 (seed 2026)
    feats = [{"attributes": a, "geometry": {"x": a["_lon"], "y": a["_lat"]}} for a in raw]
    return "Polk County (19153), 2024", "19153", [ia_dot.crash_record(f) for f in feats]


def run(st: str, scratch: Path, n: int = 2000) -> dict:
    area, fips, recs = (vt_rows if st == "vt" else ia_rows)(scratch)
    random.Random(2026).shuffle(recs)
    recs = recs[:n]
    net = osm.Network(tiger.elements(scratch / f"tl_2024_{fips}_edges.zip", scratch / f"tl_2024_{fips}_featnames.zip"))
    # the sample's network is TIGER only, so Gate() (tiger_only_auto off) auto-places nothing; score its tiers instead
    gate = locate.Gate(tiger_only_auto=True)
    tiers, reasons, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    gps = pairs = house = placed = auto = hits = auto_hits = retry_used = 0
    for c in recs:
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
        crash = {"primary_road": prim, "secondary_road": sec, "offset_ft": c["offset_ft"], "offset_dir": c["offset_dir"]}
        pl = locate.place(net, crash)                                     # GPS hidden
        if pl.lat is None and (ROUTE_PREFIX.match(prim) or ROUTE_PREFIX.match(sec)):   # wrap: drop "US-7 "
            alt = locate.place(net, {**crash, "primary_road": ROUTE_PREFIX.sub("", prim),
                                     "secondary_road": ROUTE_PREFIX.sub("", sec)})
            if alt.lat is not None:
                pl, retry_used = alt, retry_used + 1
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
            "house_address_share": round(house / k, 4), "tiers": dict(tiers),
            "name_placed_share": round(placed / k, 4), "name_placed_share_of_pairs": round(placed / pairs, 4),
            "auto_share": round(auto / k, 4), "auto_share_of_pairs": round(auto / pairs, 4),
            "route_prefix_retry_used": retry_used,
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
