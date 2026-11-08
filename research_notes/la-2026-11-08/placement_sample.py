"""Placement sample, the California way (brief 2026-11-07), for two gated states, on open rows in the state's format.

LA: Orleans Parish 2019, a consultant's public copy of the LADOTD/CARTS crash file (Toole Design's
    `new_orleans_crashes` layer): primary road, intersecting road, offset distance + unit (FT/MI) + direction,
    and DOTD's own latitude/longitude, which is hidden and scored against. Measurement only, not a source.
OK: Tulsa County 2021, OHSO's public `2021_kab_crashes` layer (fatal + serious + minor injury crashes only):
    STREET_HIGHWAY + NEAREST_INTERSECTING_ROAD, no offset; the GPS is hidden and scored against.
Network: TIGER/Line 2024 EDGES + FEATNAMES for the county (Orleans 22071, Tulsa 40143).

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/<st>-2026-11-08/placement_sample.py <la|ok> <scratch>
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
TIGER = {"la": "22071", "ok": "40143"}
FILE = {"la": "la/orleans_2019.json", "ok": "ok/okco_kab_2021.json"}
AREA = {"la": "Orleans Parish (22071), 2019, LADOTD file layout", "ok": "Tulsa County (40143), 2021, OHSO KAB layer"}
PAREN = re.compile(r"^(.*?)\s*\((.+)\)\s*$")     # OK officers write "E 151ST S (ST HWY 67)": street, then the route


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def forms(road: str | None) -> list[str]:
    """Every spelling to try for a road, the reader's first (a parenthesised route is a second name)."""
    road = (road or "").strip()
    m = PAREN.match(road)
    return [m[1], m[2]] if m else [road]


def rows_for(st: str, scratch: Path) -> list[dict]:
    raw = json.load(open(scratch / FILE[st]))
    if st == "la":
        out = []
        for r in raw:
            d = (r["pri_dist"] or "").strip()
            unit = (r["pri_measur"] or "").strip() or "FT"     # blank unit with a distance: DOTD's default is feet
            ft = float(d) * (5280 if unit == "MI" else 1) if re.fullmatch(r"\d+(\.\d+)?", d) else None
            out.append({"primary": (r["r_pri_road"] or "").strip(), "secondary": (r["inter_road"] or "").strip(),
                        "lat": r["DOTD_LATIT"] or None, "lon": r["DOTD_LONGI"] or None,
                        "offset_ft": ft or None, "offset_dir": (r["pri_dir"] or "").strip() or None})
        return out
    return [{"primary": r["STREET_HIGHWAY"], "secondary": r["NEAREST_INTERSECTING_ROAD"],
             "lat": r["LATITIDE"] or None, "lon": r["LONGITUDE"] or None, "offset_ft": None, "offset_dir": None}
            for r in raw]


def run(st: str, scratch: Path, n: int = 2000) -> dict:
    c = TIGER[st]
    net = osm.Network(tiger.elements(scratch / st / f"tl_2024_{c}_edges.zip", scratch / st / f"tl_2024_{c}_featnames.zip"))
    rows = rows_for(st, scratch)
    random.Random(2026).shuffle(rows)
    rows = rows[:n]
    gate, gate_t = locate.Gate(), locate.Gate(tiger_only_auto=True)   # TIGER-only network; the app's is OSM + TIGER
    tiers, reasons, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    named = placed = auto = auto_t = hits = auto_t_hits = scored = near_hits = near_n = retry = 0
    for r in rows:
        if not (r["primary"] and r["secondary"]):
            reasons["no cross street"] += 1
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
        if (r["offset_ft"] or 0) <= 250:
            near_n += 1
            near_hits += close
    k = len(rows)
    return {
        "area": AREA[st], "n": k, "gps_share": round(sum(r["lat"] is not None for r in rows) / k, 4),
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
