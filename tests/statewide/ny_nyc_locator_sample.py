"""NYC: what CrashIQ's street-name locator adds, measured with the GPS hidden (state/ny, 2026-11-07).

A seeded random 2,000 crashes of one borough and year that have police GPS. The GPS is hidden, the crash goes through
`locate.place` on a Census TIGER/Line 2024 street network of the borough's county (`tiger.elements`), with house
addresses looked up in NYS SAM address points (gisservices / nysgeohub NYS_Address_Points, CountyName = the county).
Accuracy is the distance to the hidden GPS. Then the same run on that borough-year's crashes with no GPS (no truth;
counts only).

Name fixes done here, not in shared code (listed for Engineering): NYPD writes bare numbers ("E 26 ST", "4508 2 AVE"),
TIGER and SAM write ordinals ("E 26th St", "2nd Ave"); multiple spaces inside house addresses are collapsed by
`ny_nyc.crash_record`.

Run: PYTHONPATH=backend python tests/statewide/ny_nyc_locator_sample.py --scratch ~/.hermes/cache/scratch/states/ny
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from crashiq import locate, osm, tiger  # noqa: E402
from crashiq.names import _ordinal  # noqa: E402
from crashiq.sources import ny_nyc  # noqa: E402
from crashiq.sources.ny_dmv import _get  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ny_refmarker_sample import wilson_low  # noqa: E402

SAM = "https://nysgeohub.ny.gov/arcgis/rest/services/Address/NYS_Address_Points/MapServer/0/query"
BOROUGHS = {"BROOKLYN": ("36047", "Kings"), "QUEENS": ("36081", "Queens"), "MANHATTAN": ("36061", "New York"),
            "BRONX": ("36005", "Bronx"), "STATEN ISLAND": ("36085", "Richmond")}
TYPES = r"(?:ST|STREET|AVE|AVENUE|AV|RD|ROAD|PL|PLACE|DR|DRIVE|CT|COURT|TER|TERRACE|LN|LANE|WALK|BLVD)"
_BARE_NUM = re.compile(rf"\b(\d+)\s+(?={TYPES}\b)")
FT = 0.3048


def ordinals(name: str | None) -> str | None:
    """'E 26 ST' -> 'E 26TH ST', '4508 2 AVE' -> '4508 2ND AVE' (only a number written right before a street type)."""
    return _BARE_NUM.sub(lambda m: _ordinal(int(m.group(1))) + " ", name) if name else name


def sam_points(counties: list[str], numbers: set[int], chunk: int = 25) -> list[tuple[str, int, float, float]]:
    rows, nums = [], sorted(numbers)
    for i in range(0, len(nums), chunk):
        names = ",".join(f"'{c}'" for c in counties)
        where = f"CountyName IN ({names}) AND AddressNumber IN ({','.join(map(str, nums[i:i + chunk]))})"
        offset = 0
        while True:
            js = _get(SAM, {"where": where, "outFields": "AddressNumber,CompleteStreetName", "outSR": 4326,
                            "f": "json", "resultOffset": offset, "resultRecordCount": 2000, "orderByFields": "OBJECTID"})
            feats = js.get("features", [])
            rows += [(f["attributes"]["CompleteStreetName"], f["attributes"]["AddressNumber"], f["geometry"]["y"],
                      f["geometry"]["x"]) for f in feats if f.get("geometry") and f["attributes"]["CompleteStreetName"]]
            if not js.get("exceededTransferLimit") and len(feats) < 2000:
                break
            offset += len(feats)
    return rows


def run(net, crashes, addresses, gate) -> tuple[Counter, list[dict]]:
    tiers, out = Counter(), []
    for c in crashes:
        q = dict(c, primary_road=ordinals(c["primary_road"]), secondary_road=ordinals(c["secondary_road"]),
                 lat=None, lon=None)
        pl = locate.place(net, q, addresses=addresses)
        tiers[pl.tier] += 1
        out.append({"c": c, "pl": pl, "auto": gate.auto(pl)})
    return tiers, out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--borough", default="BROOKLYN")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--n", type=int, default=2000)
    a = ap.parse_args()
    # ALL = the whole city on one 5-county network, including crashes NYPD left without a borough
    picked = BOROUGHS if a.borough == "ALL" else {a.borough: BOROUGHS[a.borough]}
    fips, county = "+".join(f for f, _ in picked.values()), "+".join(c for _, c in picked.values())
    crashes, _ = ny_nyc.fetch(f"{a.year}-01-01", f"{a.year}-12-31", a.scratch / "cache", persons=False)
    boro = [c for c in crashes if a.borough == "ALL" or c["borough"] == a.borough]
    with_gps = [c for c in boro if c["lat"] is not None]
    no_gps = [c for c in boro if c["lat"] is None]
    sample = random.Random(20261107).sample(with_gps, a.n)

    t = a.scratch / "tiger"
    els = []
    for i, (f, _) in enumerate(picked.values()):
        # tiger.elements numbers shape points -1, -2 ... per county: shift them so counties don't share fake nodes
        shift = lambda n: n - i * 10 ** 9 if n < 0 else n
        for el in tiger.elements(t / f"tl_2024_{f}_edges.zip", t / f"tl_2024_{f}_featnames.zip")["elements"]:
            if el["type"] == "node":
                el["id"] = shift(el["id"])
            else:
                el["nodes"] = [shift(n) for n in el["nodes"]]
            els.append(el)
    net = osm.Network({"elements": els})
    nums = set()
    for c in sample + no_gps:
        m = re.match(r"\s*(\d+)\s+\D", ordinals(c["secondary_road"]) or "")
        if m and not c["cross_street"]:
            nums.add(int(m.group(1)))
    addresses = locate.AddressIndex(sam_points([c for _, c in picked.values()], nums))
    gate = locate.Gate()

    tiers, res = run(net, sample, addresses, gate)
    placed = [r for r in res if r["pl"].lat is not None]
    auto = [r for r in placed if r["auto"]]
    err = lambda r: osm.metres((r["pl"].lat, r["pl"].lon), (r["c"]["lat"], r["c"]["lon"])) / FT
    ok = lambda rs: sum(1 for r in rs if err(r) <= 250)
    by_tier = {}
    for tier in sorted({r["pl"].tier for r in placed}):
        rs = [r for r in placed if r["pl"].tier == tier]
        by_tier[tier] = {"n": len(rs), "within_250ft": ok(rs), "pct": round(100 * ok(rs) / len(rs), 1),
                         "low": wilson_low(ok(rs), len(rs))}
    named = sum(1 for c in sample if c["cross_street"] or (c["off_street"] and re.match(r"\s*\d", c["off_street"])))
    misses = Counter(r["pl"].note for r in res if r["pl"].lat is None)
    out = {
        "area": f"{a.borough.title()} ({county} County, FIPS {fips}), NYC crashes {a.year}",
        "borough_crashes": len(boro), "borough_gps": len(with_gps),
        "borough_gps_pct": round(100 * len(with_gps) / len(boro), 1),
        "n": len(sample), "with_street_pair_or_address": named, "tiers": dict(tiers), "by_tier": by_tier,
        "placed": len(placed), "placed_pct": round(100 * len(placed) / len(sample), 1),
        "auto": len(auto), "auto_pct": round(100 * len(auto) / len(sample), 1),
        "auto_within_250ft": ok(auto), "auto_within_250ft_pct": round(100 * ok(auto) / max(1, len(auto)), 1),
        "auto_within_250ft_low": wilson_low(ok(auto), len(auto)),
        "placed_within_250ft_pct": round(100 * ok(placed) / max(1, len(placed)), 1),
        "placed_within_250ft_low": wilson_low(ok(placed), len(placed)),
        "address_crashes": sum(1 for c in sample if c["off_street"] and not c["cross_street"]),
        "address_placed": tiers.get("address", 0), "sam_points_fetched": sum(len(v) for v in addresses.by_street.values()),
        "review_reasons": dict(misses.most_common(8)),
        "network": "TIGER/Line 2024 only (no OSM); tiger.elements leaves ways untagged, so Gate() treats them like OSM",
    }
    nt, nres = run(net, no_gps, addresses, gate)
    out["no_gps"] = {"n": len(no_gps), "tiers": dict(nt), "auto": sum(1 for r in nres if r["auto"]),
                     "auto_pct_of_no_gps": round(100 * sum(1 for r in nres if r["auto"]) / max(1, len(no_gps)), 1),
                     "auto_pct_of_all_borough": round(100 * sum(1 for r in nres if r["auto"]) / len(boro), 2)}
    print(json.dumps(out, indent=1))
    (a.scratch / f"nyc_locator_{a.borough.lower().replace(' ', '_')}_{a.year}.json").write_text(json.dumps(out, indent=1))
    bad = sorted((r for r in auto if err(r) > 250), key=err, reverse=True)[:12]
    for r in bad:
        print(round(err(r)), r["pl"].tier, "|", r["c"]["primary_road"], "|", r["c"]["secondary_road"])


if __name__ == "__main__":
    main()
