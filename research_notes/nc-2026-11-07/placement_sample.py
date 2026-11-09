"""NC placement sample (2026-11-07): 2,000 Raleigh 2025 crashes, GPS hidden, placed by CrashIQ's own locator on a
Census TIGER/Line 2024 network of Wake County (37183); house-address crashes on Wake County MAR address points.

Measure only. Shared code is untouched: NC name formats are pre-split here and the fixes listed in nc-import.md.
Run (from the repo root):  PYTHONPATH=backend python research_notes/nc-2026-11-07/placement_sample.py
Inputs/outputs live in ~/.hermes/cache/scratch/states/nc/ (never committed); the summary prints as JSON.
"""

from __future__ import annotations

import json
import math
import random
import re
from collections import Counter
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.sources.nc_arcgis import query

S = Path.home() / ".hermes/cache/scratch/states/nc"
MAR = "https://services1.arcgis.com/a7CWfuGP5ZnLYE7I/arcgis/rest/services/Wake_County_MAR_Address_Data_Public/FeatureServer/0"
N, SEED, FT = 2000, 20261107, 0.3048
INTERSTATES = {"40", "440", "540", "85", "87", "95", "885"}   # Raleigh writes I-440 as a bare "440"


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def fix_name(s: str | None) -> str | None:
    """The pre-splits the shared names.py would need for NC (listed in nc-import.md)."""
    if not s:
        return s
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(?:SR|NC|US)\s*\d+\s*\((.+)\)$", s)          # 'SR 1152 (HOLLY SPRINGS RD)' -> the name
    if m:
        s = m.group(1)
    m = re.match(r"^(?:I\s*-?\s*)?(\d{2,3})\b(.*)$", s)          # '440', 'I440 WB', 'I-40 EB' -> 'I-440'
    if m and m.group(1) in INTERSTATES:
        s = f"I-{m.group(1)}"
    return s


def main() -> None:
    rows = json.loads((S / "raleigh_2025.json").read_text())
    gps = [r for r in rows if r["lat"] is not None]
    named = [r for r in gps if r["primary_road"] and r["secondary_road"]]
    sample = random.Random(SEED).sample(named, N)

    net = osm.Network(tiger.elements(S / "tl_2024_37183_edges.zip", S / "tl_2024_37183_featnames.zip"))
    gate = locate.Gate()

    house = [c for c in sample if locate._house_address(c)]
    streets = sorted({locate._house_address(c)[0].core for c in house})
    pts = []
    for i in range(0, len(streets), 40):                          # MAR points for just the sample's streets
        names = ",".join("'" + s.replace("'", "''") + "'" for s in streets[i:i + 40])
        pts += [(r["COMPLETE_STREET_NAME"], r["ADDRNUM"], r["_y"], r["_x"])
                for r in query(MAR, f"UPPER(STNAME) IN ({names})", "OBJECTID,COMPLETE_STREET_NAME,ADDRNUM")]
    addresses = locate.AddressIndex(pts)

    out = {}
    for variant in ("raw", "nc_fixes"):
        tiers, auto, auto_ok, ok_by_tier, misses = Counter(), 0, 0, Counter(), []
        for c in sample:
            crash = dict(c, lat=None, lon=None)
            if variant == "nc_fixes":
                crash["primary_road"], crash["secondary_road"] = fix_name(c["primary_road"]), fix_name(c["secondary_road"])
            pl = locate.place(net, crash, addresses=addresses if locate._house_address(crash) else None)
            tiers[pl.tier] += 1
            if pl.lat is None:
                continue
            d_ft = osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"])) / FT
            ok = d_ft <= 250
            ok_by_tier[pl.tier] += ok
            if gate.auto(pl) or pl.tier == "address":
                auto += 1
                auto_ok += ok
                if not ok and len(misses) < 15:
                    misses.append((c["primary_road"], c["secondary_road"], pl.tier, round(d_ft)))
        placed = sum(v for k, v in tiers.items() if k != "review")
        out[variant] = {
            "n": N, "tiers": dict(tiers), "placed_share": round(placed / N, 4),
            "auto_share": round(auto / N, 4), "auto_within_250ft": round(auto_ok / auto, 4) if auto else None,
            "auto_within_250ft_low": round(wilson_low(auto_ok, auto), 4),
            "within_250ft_by_tier": {t: f"{ok_by_tier[t]}/{tiers[t]}" for t in tiers if t != "review"},
            "auto_misses_sample": misses,
        }
    out["context"] = {
        "rows_2025": len(rows), "gps_plausible": len(gps), "gps_share": round(len(gps) / len(rows), 4),
        "both_names_share": round(sum(bool(r["primary_road"] and r["secondary_road"]) for r in rows) / len(rows), 4),
        "house_address_in_sample": len(house), "house_address_share": round(len(house) / N, 4),
        "mar_points_fetched": len(pts), "network_streets": len(net.streets),
        "auto_tiers": sorted(gate.auto_tiers), "address_counted_as_auto": True,
    }
    (S / "placement_summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
