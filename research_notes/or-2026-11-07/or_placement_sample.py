"""Oregon placement sample (states brief 2026-11-07): 2,000 Multnomah County 2024 crashes from ODOT's decode DB.

Hides ODOT's GPS, places each crash from its two street names on a Census TIGER/Line 2024 network of Multnomah
(41051) with the app's own locator (`locate.place`), and scores the point against the hidden GPS. Measure only; no
shared code changed. ODOT's street names are pre-cleaned here (see `pre_split`) and the run is reported both raw and
pre-split, so the shared-code fixes needed are visible.

Run: PYTHONPATH=backend python research_notes/or-2026-11-07/or_placement_sample.py <scratch dir>
  <scratch dir> holds mdb2024/CRASH.csv + PARTIC.csv (decode DB export) and tl_2024_41051_{edges,featnames}.zip.
Writes <scratch dir>/or_placement_sample.json.
"""

from __future__ import annotations

import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources import or_odot

N, SEED, TOL_FT = 2000, 20261107, 250.0
# ODOT's 20-character street abbreviations that names.street_key doesn't know (seen in the 2024 Multnomah rows)
ODOT_WORDS = {"FY": "FWY", "AV": "AVE", "BEAV-HILLSDALE": "BEAVERTON-HILLSDALE", "MLK": "MARTIN LUTHER KING JR",
              "FAIRVW": "FAIRVIEW", "PTLD": "PORTLAND"}


def pre_split(name: str | None) -> str | None:
    """'NE 207TH AV/FAIRVW PKWY' -> 'NE 207TH AVE' (first name of a slash pair), ODOT abbreviations spelled out."""
    if not name:
        return name
    first = name.split("/")[0].strip()
    return " ".join(ODOT_WORDS.get(w, w) for w in first.split())


def wilson_low(k: int, n: int, z: float = 1.96) -> float | None:
    if not n:
        return None
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def run(net, crashes, clean: bool) -> dict:
    gate, tiers, rows = locate.Gate(), Counter(), []
    for i, c in enumerate(crashes):
        if i % 250 == 0:
            print(f"  {i}/{len(crashes)}", file=sys.stderr, flush=True)
        h = dict(c, lat=None, lon=None)
        if clean:
            h["primary_road"], h["secondary_road"] = pre_split(c["primary_road"]), pre_split(c["secondary_road"])
        pl = locate.place(net, h)
        tiers[pl.tier] += 1
        err = osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"])) / 0.3048 if pl.lat is not None else None
        rows.append({"tier": pl.tier, "auto": gate.auto(pl), "tier_auto": pl.lat is not None and gate.allows(pl.tier),
                     "ok": err is not None and err <= TOL_FT, "err_ft": err, "note": pl.note,
                     "road": "freeway" if c["is_freeway"] else "non_freeway"})
    n = len(rows)
    placed = [r for r in rows if r["err_ft"] is not None]
    auto = [r for r in rows if r["auto"]]
    tier_auto = [r for r in rows if r["tier_auto"]]
    k = lambda rs: sum(r["ok"] for r in rs)                                                       # noqa: E731
    return {"n": n, "tiers": dict(tiers), "placed": len(placed), "placed_share": len(placed) / n,
            "placed_within_250ft": k(placed), "placed_within_250ft_low": wilson_low(k(placed), len(placed)),
            "auto_gate": len(auto), "auto_gate_share": len(auto) / n,
            "auto_tiers_ignoring_tiger_rule": len(tier_auto), "auto_tiers_share": len(tier_auto) / n,
            "auto_tiers_within_250ft": k(tier_auto), "auto_tiers_within_250ft_share": k(tier_auto) / max(len(tier_auto), 1),
            "auto_tiers_within_250ft_low": wilson_low(k(tier_auto), len(tier_auto)),
            "by_tier": {t: {"n": len(rs), "within_250ft": k(rs), "low": wilson_low(k(rs), len(rs))}
                        for t in tiers for rs in [[r for r in placed if r["tier"] == t]] if rs},
            "by_road": {rd: {"n": len(rs), "placed": sum(r["err_ft"] is not None for r in rs),
                             "auto": sum(r["auto"] for r in rs), "auto_within_250ft": k([r for r in rs if r["auto"]]),
                             "auto_low": wilson_low(k([r for r in rs if r["auto"]]), sum(r["auto"] for r in rs))}
                        for rd in ("freeway", "non_freeway") for rs in [[r for r in rows if r["road"] == rd]]},
            "review_notes": Counter(r["note"].split(":")[0] for r in rows if r["err_ft"] is None).most_common(8)}


def main(scratch: Path) -> None:
    allc = [c for c in or_odot.read_decode(scratch / "mdb2024/CRASH.csv", scratch / "mdb2024/PARTIC.csv")
            if c["county"] == "Multnomah"]
    sample = random.Random(SEED).sample(allc, N)
    net = osm.Network(tiger.elements(scratch / "tl_2024_41051_edges.zip", scratch / "tl_2024_41051_featnames.zip"))
    gps = [c for c in sample if c["lat"] is not None]
    both = lambda c: bool(c["primary_road"] and c["secondary_road"])                              # noqa: E731
    named = [c for c in gps if both(c)]
    no_gps = [c for c in allc if c["lat"] is None]              # every unlocated Multnomah 2024 crash, not a sample
    out = {
        "area": "Multnomah County (Portland), 2024, ODOT decode DB", "n": N, "seed": SEED,
        "county_crashes": len(allc),
        "gps_plausible": len(gps), "gps_share": len(gps) / N,
        "both_street_names": sum(both(c) for c in sample), "street_names_share": sum(both(c) for c in sample) / N,
        "house_address": sum(bool(re.match(r"^\d+\s", c["primary_road"] or "")) for c in sample),
        "freeway": sum(c["is_freeway"] for c in sample),
        "hidden_gps_raw": run(net, named, clean=False),
        "hidden_gps_pre_split": run(net, named, clean=True),
        "no_gps_all_county": {"n": len(no_gps), "both_names": sum(both(c) for c in no_gps),
                              "pre_split": run(net, [dict(c, lat=0.0, lon=0.0) for c in no_gps], clean=True)},
    }
    out["no_gps_all_county"]["pre_split"] = {k: v for k, v in out["no_gps_all_county"]["pre_split"].items()
                                             if "250" not in k and k != "by_tier"}   # no truth for these
    (scratch / "or_placement_sample.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
