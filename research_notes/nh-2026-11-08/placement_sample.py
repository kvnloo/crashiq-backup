"""Placement sample, the California way (brief 2026-11-07), on the only open copy of NHDOT's crash layout.

Data: UVLSRPC "Crash History" (NHDOT crash data re-hosted by the Upper Valley Lake Sunapee regional planning
commission, 2002 - Jun 2017), Grafton County 2015-2016, 1,773 crashes, every one with a point. Not a source (a
regional re-host, no grant), only evidence of how NHDOT's export writes locations: ACDSTREET + INTERSTREE (often with a
house number in front: "2345 RT 25A"), MILESFTFRO (distance, read as feet) + NSEW_TO_IN (direction, or AT).
The point is hidden, the crash is placed from the two names on a TIGER/Line 2024 network of Grafton (33009), and
scored against it.

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/nh-2026-11-08/placement_sample.py <scratch/nh>
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
HOUSE = re.compile(r"^\d+[A-Z]?\s+(?=\D)(?![NSEW]B?$)")            # "2345 RT 25A" -> "RT 25A"; "89 N" (no letter after) stays
ROUTE = re.compile(r"^(?:RT|RTE|ROUTE|STHY|NH|ST RT|STATE ROUTE|US|US RT|I|I-|INTERSTATE)\s*-?\s*(\d+)-?([A-Z])?"
                   r"(?:\s+[NSEW]B?)?$")
US = {"1", "2", "3", "4", "202", "302"}
INTERSTATE = {"89", "93", "95", "293", "393"}


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def road(street: str | None, route: str | None) -> str | None:
    """The road as written, house number off; a blank street with a route code (00118, 0004A) is that route."""
    s = HOUSE.sub("", (street or "").strip().upper()).strip()
    r = (route or "").strip().lstrip("0").replace("-", "")
    if not s and r and r[0].isdigit():
        s = f"RT {r}"
    if not s and r.startswith("I"):
        s = f"I {r[1:].rstrip('NSEW')}"
    return s or None


def forms(s: str | None) -> list[str]:
    """Every spelling to try, as written first: 'RT 25A' -> 'NH 25A', 'State Hwy 25A'; 'RT 4' -> 'US 4', 'US Hwy 4'."""
    if not s:
        return []
    m = ROUTE.match(s) or (re.match(r"^(\d+)([A-Z])?(?:\s+[NSEW]B?)?$", s) if s.split()[0] in INTERSTATE else None)
    if not m:
        return [s]
    n, suf = m[1], m[2] or ""
    if n in INTERSTATE and not suf:
        return [f"I-{n}", s]
    if n in US and not suf:
        return [f"US {n}", f"US Hwy {n}", s]
    return [f"NH {n}{suf}", f"State Hwy {n}{suf}", f"State Rte {n}{suf}", s]


def run(scratch: Path, n: int = 2000) -> dict:
    rows = json.load(open(scratch / "uvlsrpc_grafton_2015_2016.json"))
    lats, lons = [r["lat"] for r in rows if r["lat"]], [r["lon"] for r in rows if r["lon"]]
    s, nn, w, e = min(lats) - .02, max(lats) + .02, min(lons) - .02, max(lons) + .02
    net = osm.Network(tiger.elements(scratch / "tl_2024_33009_edges.zip", scratch / "tl_2024_33009_featnames.zip",
                                     keep=lambda lat, lon: s <= lat <= nn and w <= lon <= e))
    random.Random(2026).shuffle(rows)
    rows = rows[:n]
    gate, gate_t = locate.Gate(), locate.Gate(tiger_only_auto=True)   # TIGER-only network; the app's is OSM + TIGER
    tiers, reasons, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    named = placed = auto = auto_t = hits = auto_t_hits = scored = near_hits = near_n = retry = house = 0
    for r in rows:
        house += bool(HOUSE.match((r["ACDSTREET"] or "").strip()))
        p, q = road(r["ACDSTREET"], r["ACDROUTE"]), road(r["INTERSTREE"], r["INTERROUTE"])
        if not (p and q):
            reasons["no cross street"] += 1
            continue
        named += 1
        at = (r["NSEW_TO_IN"] or "").strip() in ("AT", "")
        off = None if at else (float(r["MILESFTFRO"] or 0) or None)
        pl = None
        for i, pf in enumerate(forms(p)):
            for j, qf in enumerate(forms(q)):
                pl = locate.place(net, {"primary_road": pf, "secondary_road": qf, "offset_ft": off,
                                        "offset_dir": None if at else r["NSEW_TO_IN"].strip()})
                if pl.lat is not None:
                    retry += bool(i or j)
                    break
            if pl.lat is not None:
                break
        tiers[pl.tier] += 1
        if pl.lat is None:
            reasons[pl.note or pl.tier] += 1
            if len(ex[pl.note or pl.tier]) < 6:
                ex[pl.note or pl.tier].append(f"{p} & {q}")
            continue
        placed += 1
        auto += gate.auto(pl)
        a_t = gate_t.auto(pl)
        auto_t += a_t
        scored += 1
        close = osm.metres((pl.lat, pl.lon), (r["lat"], r["lon"])) <= FT250_M
        hits += close
        auto_t_hits += close and a_t
        if (off or 0) <= 250:
            near_n += 1
            near_hits += close
    k = len(rows)
    return {
        "area": "Grafton County (33009), 2015-2016, UVLSRPC re-host of NHDOT crash data", "n": k,
        "gps_share": round(sum(r["lat"] is not None for r in rows) / k, 4),
        "house_number_in_street_share": round(house / k, 4),
        "street_pair_share": round(named / k, 4), "tiers": dict(tiers),
        "name_placed_share": round(placed / k, 4), "name_placed_share_of_pairs": round(placed / named, 4),
        "auto_share": round(auto / k, 4), "auto_share_if_tiger_only_auto": round(auto_t / k, 4),
        "route_form_retry_used": retry, "scored_against_gps": scored,
        "within_250ft_all_placed": round(hits / scored, 4) if scored else None,
        "within_250ft_all_placed_low": round(wilson_low(hits, scored), 4),
        "within_250ft_auto_if_tiger_only_auto": round(auto_t_hits / auto_t, 4) if auto_t else None,
        "within_250ft_auto_if_tiger_only_auto_low": round(wilson_low(auto_t_hits, auto_t), 4),
        "within_250ft_offset_le_250ft": round(near_hits / near_n, 4) if near_n else None,
        "within_250ft_offset_le_250ft_low": round(wilson_low(near_hits, near_n), 4), "offset_le_250ft_n": near_n,
        "not_placed": dict(reasons.most_common(10)), "examples": dict(ex),
    }


if __name__ == "__main__":
    assert forms("RT 25A")[0] == "NH 25A" and forms("RT 4")[0] == "US 4" and forms("89 N")[0] == "I-89"
    assert road("2345 RT 25A", "00000") == "RT 25A" and road(" ", "00118") == "RT 118" and road("89 N", "00089") == "89 N"
    out = run(Path(sys.argv[1]))
    print(json.dumps(out, indent=1))
    (Path(__file__).parent / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
