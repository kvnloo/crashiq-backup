"""Texas placement sample (Hermes, 2026-11-07): CrashIQ's street-name locator on Dallas County 2025 CRIS crashes.

Source: Dallas County GIS "2025 traffic accidents_no duplicates" (a CRIS Query copy, one row per crash), downloaded by
object-id paging to $SCRATCH/dallas2025.csv. Street network: Census TIGER/Line 2024 for Dallas County (48113) via
`crashiq.tiger.elements`. GPS is hidden on every sampled crash; the locator sees only the two street names.
Shared code is untouched: TxDOT highway codes (IH0035E, SL0012, ...) are rewritten here to TIGER's spellings first.
Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/tx-2026-11-07/tx_placement_sample.py
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

from crashiq import locate, osm, tiger

SCRATCH = Path.home() / ".hermes/cache/scratch/states/tx"
BAD = {"", "N/A", "NO DATA", "NOT REPORTED", "UNKNOWN", "NONE"}
TX_LAT, TX_LON = (25.8, 36.6), (-106.7, -93.5)
N, SEED, FT = 2000, 20261107, 0.3048

# TxDOT locator highway code (system + 4-digit number + suffix) -> the spelling TIGER/Line uses in Dallas County
TIGER_ROUTE = {"IH": "I- {n}", "US": "US Hwy {n}", "SH": "State Hwy {n}", "SL": "State Loop {n}",
               "SS": "State Spur {n}", "FM": "Farm-to-Market Rd {n}", "CR": "Co Rd {n}"}
HWY = re.compile(r"^([A-Z]{2})0*(\d{1,4})([A-Z]?)$")


def tx_name(raw: str | None) -> str | None:
    s = (raw or "").strip().upper()
    if s in BAD:
        return None
    m = HWY.match(s)
    if m and m.group(1) in TIGER_ROUTE:
        return TIGER_ROUTE[m.group(1)].format(n=m.group(2)) + (f" {m.group(3)}" if m.group(3) else "")
    return re.sub(r"\bTLWY\b", "TOLLWAY", s)          # Dallas North Tollway: TLWY isn't a suffix names.py knows


def gps(r) -> tuple[float, float] | None:
    try:
        lat, lon = float(r["Latitude"]), float(r["Longitude"])
    except (TypeError, ValueError):
        return None
    return (lat, lon) if TX_LAT[0] <= lat <= TX_LAT[1] and TX_LON[0] <= lon <= TX_LON[1] else None


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def run(net, rows, gate) -> dict:
    tiers, auto, auto_ok, placed_ok, placed, notes = Counter(), 0, 0, 0, 0, Counter()
    for r in rows:
        truth = gps(r)
        crash = {"primary_road": tx_name(r["Street_Name"]), "secondary_road": tx_name(r["Intersecting_Street_Name"]),
                 "offset_ft": None, "offset_dir": None, "lat": None, "lon": None}      # GPS hidden
        pl = locate.place(net, crash)
        tiers[pl.tier] += 1
        if pl.lat is None:
            notes[pl.note.split(":")[0]] += 1
            continue
        placed += 1
        near = truth is not None and osm.metres((pl.lat, pl.lon), truth) <= 250 * FT
        placed_ok += near
        if gate.auto(pl):
            auto += 1
            auto_ok += near
    n = len(rows)
    return {"n": n, "tiers": dict(tiers), "placed": placed, "placed_share": placed / n if n else 0,
            "auto": auto, "auto_share": auto / n if n else 0,
            "auto_within_250ft": auto_ok, "auto_within_250ft_share": auto_ok / auto if auto else None,
            "auto_within_250ft_wilson_low": wilson_low(auto_ok, auto),
            "placed_within_250ft_share": placed_ok / placed if placed else None,
            "review_reasons": dict(notes)}


def main() -> None:
    rows = list(csv.DictReader(open(SCRATCH / "dallas2025.csv")))
    has = lambda r, f: (r[f] or "").strip().upper() not in BAD
    pair = [r for r in rows if has(r, "Street_Name") and has(r, "Intersecting_Street_Name")]
    nogps = [r for r in rows if gps(r) is None]
    out = {"source": "https://services3.arcgis.com/zqe2kwz79KUqUvxC/arcgis/rest/services/"
                     "2025_traffic_accidents_no_duplicates/FeatureServer/0",
           "crashes": len(rows), "gps": len(rows) - len(nogps), "gps_share": 1 - len(nogps) / len(rows),
           "street_pair": len(pair), "street_pair_share": len(pair) / len(rows),
           "no_gps": len(nogps), "no_gps_road_class": dict(Counter(r["Road_Class"] for r in nogps).most_common()),
           "no_gps_street_pair": sum(1 for r in nogps if r in pair or (has(r, "Street_Name") and has(r, "Intersecting_Street_Name")))}
    sample = random.Random(SEED).sample([r for r in pair if gps(r)], N)
    print("building TIGER network ...", file=sys.stderr)
    net = osm.Network(tiger.elements(SCRATCH / "tl_2024_48113_edges.zip", SCRATCH / "tl_2024_48113_featnames.zip"))
    gate = locate.Gate()
    out["sample"] = run(net, sample, gate)
    out["sample_by_road_class"] = {}
    for rc in ("CITY STREET", "INTERSTATE", "US & STATE HIGHWAYS", "TOLLWAY"):
        sub = [r for r in sample if r["Road_Class"] == rc]
        if sub:
            out["sample_by_road_class"][rc] = {k: v for k, v in run(net, sub, gate).items() if k != "review_reasons"}
    nog_pair = [r for r in nogps if has(r, "Street_Name") and has(r, "Intersecting_Street_Name")]
    out["no_gps_pair_run"] = {k: v for k, v in run(net, nog_pair, gate).items()
                              if k in ("n", "tiers", "placed", "auto")}
    out["no_gps_added_share_of_all"] = out["no_gps_pair_run"]["auto"] / len(rows)
    print(json.dumps(out, indent=1))
    (SCRATCH / "placement_result.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
