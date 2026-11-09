"""GA placement sample, the California way (2026-11-08).

Input: 2,000 random Fulton County 2024 crashes from the Atlanta Regional Commission's open layer "Crashes 2020-2024"
(GDOT AASHTOWare Safety extract; pulled by OBJECTID with seed 2026 into <scratch>/arc_fulton_2024.json).
Hide the GPS, place from "Roadway (From Crash Report)" + "Intersecting Roadway" on a TIGER/Line 2024 network,
score against the hidden GPS. Pre-clean here, not in shared code: "Ga120" -> "GA 120", "I- 285 W" -> "I 285".
Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/ga-2026-11-08/placement_sample.py <scratch>
"""
import collections, json, math, re, sys
from pathlib import Path
from crashiq import locate, osm, tiger

FT250_M = 250 * 0.3048


def wilson_low(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def clean(s):
    s = (s or "").strip()
    if s.lower() in ("", "(none)", "none", "unknown"):
        return ""
    s = re.sub(r"^(Ga|Sr|Us|I)\s*-?\s*(\d+)\b(\s+[NSEW])?$", lambda m: f"{m[1].upper()} {m[2]}", s, flags=re.I)
    return s


def main(scratch: Path):
    rows = json.load(open(scratch / "arc_fulton_2024.json"))
    net = osm.Network(tiger.elements(scratch.parent / "tl_2024_13121_edges.zip", scratch.parent / "tl_2024_13121_featnames.zip"))
    gate = locate.Gate()
    tiers, reasons, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    tier_ok, tier_hit = collections.Counter(), collections.Counter()
    gps = named = hits = auto = auto_hits = tg = tg_hits = 0
    for r in rows:
        la, lo = r["Latitude"], r["Longitude"]
        ok = la is not None and 30.3 <= la <= 35.1 and -85.7 <= lo <= -80.8
        gps += ok
        p, s = clean(r["Roadway__From_Crash_Report_"]), clean(r["Intersecting_Roadway"])
        if not (p and s):
            reasons["no cross street in source"] += 1
            continue
        named += 1
        pl = locate.place(net, {"primary_road": p, "secondary_road": s, "offset_ft": None, "offset_dir": None})
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
    out = {"area": "Fulton County (13121), 2024 (ARC layer)", "n": n, "gps_share": round(gps / n, 4),
           "street_pair_share": round(named / n, 4), "tiers": dict(tiers),
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
