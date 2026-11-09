"""SC placement sample, the California way (2026-11-08).

Input: every Spartanburg County 2024 row on the county's open layer "Spartanburg County Crash Data Monthly Update"
(SCDPS TR-310 fields, one row per person; <scratch>/sptbg_2024_people.json), one row per crash_number, then 2,000 random
crashes (seed 2026). Hide the GPS, place from on_route + base_route (+ base_distance_offset miles, offset_direction) on a
TIGER/Line 2024 network, score against the hidden GPS. When a street name is blank or doesn't place, retry with the
route number (Interstate 85 -> I 85, US Primary 29 -> US 29, SC Primary 9 -> SC 9). Wraps here, not in shared code.
Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/sc-2026-11-08/placement_sample.py <scratch>
"""
import collections, json, math, random, sys
from pathlib import Path
from crashiq import locate, osm, tiger

FT250_M = 250 * 0.3048
ROUTE = {"Interstate": "I", "US Primary": "US", "SC Primary": "SC"}


def wilson_low(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def route(cat, num):
    return f"{ROUTE[cat]} {num}" if cat in ROUTE and (num or "").isdigit() else ""


def main(scratch: Path):
    crashes = {}
    for r in json.load(open(scratch / "sptbg_2024_people.json")):
        crashes.setdefault(r["crash_number"], r)
    rows = sorted(crashes.values(), key=lambda r: r["crash_number"])
    random.Random(2026).shuffle(rows)
    rows = rows[:2000]
    net = osm.Network(tiger.elements(scratch.parent / "tl_2024_45083_edges.zip", scratch.parent / "tl_2024_45083_featnames.zip"))
    gate = locate.Gate()
    tiers, reasons, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    tier_ok, tier_hit = collections.Counter(), collections.Counter()
    gps = named = hits = auto = auto_hits = tg = tg_hits = retry = 0
    for r in rows:
        la, lo = r["decimal_degrees_latitude"], r["decimal_degrees_longitude"]
        ok = la is not None and lo is not None and 32.0 <= la <= 35.25 and -83.4 <= lo <= -78.5
        gps += ok
        p = (r["on_route_street_name"] or "").strip() or route(r["on_route_category"], r["on_route_number"])
        s = (r["base_route_street_name"] or "").strip() or route(r["base_route_category"], r["base_route_number"])
        if not (p and s):
            reasons["no on/base street in source"] += 1
            continue
        named += 1
        off = r["base_distance_offset"]
        crash = {"primary_road": p, "secondary_road": s, "offset_ft": off * 5280 if off else None,
                 "offset_dir": r["offset_direction"]}
        pl = locate.place(net, crash)
        if pl.lat is None:
            alt = {**crash, "primary_road": route(r["on_route_category"], r["on_route_number"]) or p,
                   "secondary_road": route(r["base_route_category"], r["base_route_number"]) or s}
            if alt != crash and (pl2 := locate.place(net, alt)).lat is not None:
                pl, retry = pl2, retry + 1
        tiers[pl.tier] += 1
        if pl.lat is None:
            reasons[pl.note or pl.tier] += 1
            if len(ex[pl.note]) < 6:
                ex[pl.note].append(f"{p} & {s}")
            continue
        close = ok and osm.metres((pl.lat, pl.lon), (la, lo)) <= FT250_M
        hits += close
        tier_ok[pl.tier] += 1
        tier_hit[pl.tier] += close
        if gate.allows(pl.tier):  # tier gate only; gate.auto() also refuses TIGER-only roads (tiger_only_auto)
            tg, tg_hits = tg + 1, tg_hits + close
        if gate.auto(pl):
            auto, auto_hits = auto + 1, auto_hits + close
    placed = sum(v for k, v in tiers.items() if k != "review")
    n = len(rows)
    out = {"area": "Spartanburg County (45083), 2024 (county layer)", "n": n, "crashes_in_year": len(crashes),
           "gps_share": round(gps / n, 4), "street_pair_share": round(named / n, 4), "tiers": dict(tiers),
           "route_retry_used": retry,
           "name_placed_share": round(placed / n, 4), "name_placed_share_of_pairs": round(placed / named, 4),
           "auto_share": round(auto / n, 4), "auto_share_of_pairs": round(auto / named, 4),
           "within_250ft_auto": round(auto_hits / auto, 4) if auto else None,
           "within_250ft_auto_low": round(wilson_low(auto_hits, auto), 4),
           "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
           "within_250ft_all_placed_low": round(wilson_low(hits, placed), 4),
           "tier_gate_share": round(tg / n, 4), "within_250ft_tier_gate": round(tg_hits / tg, 4) if tg else None,
           "within_250ft_tier_gate_low": round(wilson_low(tg_hits, tg), 4),
           "within_250ft_by_tier": {t: round(tier_hit[t] / c, 4) for t, c in tier_ok.items()},
           "not_placed": dict(reasons.most_common(8)), "examples": dict(ex)}
    print(json.dumps(out, indent=1))
    (Path(__file__).parent / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
