"""DC placement sample (2026-11-07): 2,000 random 2025 'Crashes in DC' rows, police GPS hidden, placed the CrashIQ way.

Inputs (scratch, not committed; see dc-import.md for how each was pulled):
  sample_2000.json      2,000 rows of MapServer/24, REPORTDATE in 2025, random.seed(2025)
  mar_points.json       MAR Address Points (Location_WebMercator/FeatureServer/0), all 144,451
  tl_2024_11001_{edges,featnames}.zip   Census TIGER/Line 2024, DC (FIPS 11001)
Truth = MPD's own GPS (MPDLATITUDE/MPDLONGITUDE), not DDOT's snapped point.

Shared code is used unchanged; DC formats are pre-processed here (fixes the shared code would need: dc-import.md).
Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/dc-2026-11-07/dc_placement_sample.py <scratch dir>
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

from crashiq import locate, tiger
from crashiq.names import street_key
from crashiq.osm import Network

S = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / ".hermes/cache/scratch/states/dc")
QUAD = {"NW", "NE", "SW", "SE"}
DC_LAT, DC_LON = (38.79, 39.00), (-77.12, -76.90)


def dc_name(s: str | None) -> str | None:
    """'U STREET NW' -> 'U NW STREET': street_key reads a trailing NW as part of the name and then misses the suffix,
    so the quadrant moves in front of the suffix word (K St NW and K St SE stay two streets)."""
    if not s:
        return s
    t = s.upper().replace(".", "").split()
    if len(t) >= 3 and t[-1] in QUAD:
        return " ".join(t[:-2] + [t[-1], t[-2]])
    return " ".join(t)


def plausible(lat, lon) -> bool:
    return lat is not None and lon is not None and DC_LAT[0] <= lat <= DC_LAT[1] and DC_LON[0] <= lon <= DC_LON[1]


def ft(a, b) -> float:
    dy = (a[0] - b[0]) * 364000
    dx = (a[1] - b[1]) * 364000 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def wilson_low(k: int, n: int, z: float = 1.96) -> float | None:
    if n == 0:
        return None
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


HOUSE = re.compile(r"^(\d+)(?:\s*1/2)?\s+(.+)$")


def parse_address(a: str | None) -> tuple[str, dict]:
    """MPD ADDRESS -> (form, parts). Forms: intersection 'A & B', house '1201 U STREET NW', street only, coords, none."""
    a = (a or "").split("\n")[0].strip().rstrip(",")
    if not a:
        return "none", {}
    if re.fullmatch(r"-?\d+\.\d+,\s*-?\d+\.\d+", a):
        return "coords", {}
    if "&" in a:
        p, s = (x.strip() for x in a.split("&", 1))
        return "intersection", {"primary": p, "secondary": s}
    m = HOUSE.match(a)
    if m:
        return "house", {"number": int(m[1]), "street": m[2]}
    return "street_only", {"primary": a}


def main() -> None:
    sample = json.load(open(S / "sample_2000.json"))
    els = tiger.elements(S / "tl_2024_11001_edges.zip", S / "tl_2024_11001_featnames.zip")
    for e in els["elements"]:
        if e["type"] == "way":
            e["tags"] = {k: ";".join(dc_name(v) for v in val.split(";")) for k, val in e["tags"].items()}
    net = Network(els)
    mar = json.load(open(S / "mar_points.json"))
    addr = locate.AddressIndex([(dc_name(f"{r['STREET_NAME']} {r['STREET_TYPE'] or ''} {r['QUADRANT'] or ''}"),
                                 r["ADDRESS_NUMBER"], r["LATITUDE"], r["LONGITUDE"])
                                for r in mar if r["ADDRESS_NUMBER"] and r["LATITUDE"] and r["STATUS"] == "ACTIVE"])
    gate = locate.Gate()
    n = len(sample)
    forms, tiers, auto_tiers = Counter(), Counter(), Counter()
    gps_mpd = gps_ddot = 0
    dist_by_tier: dict[str, list[float]] = {}
    house_via_place_refused = 0
    examples = []
    nearest_test = Counter()   # not independent: DDOT derives the nearest intersection from its own point
    nearest_dist = []
    for r in sample:
        mpd = (r["MPDLATITUDE"], r["MPDLONGITUDE"])
        has_mpd = plausible(*mpd)
        gps_mpd += has_mpd
        gps_ddot += plausible(r["LATITUDE"], r["LONGITUDE"])
        form, p = parse_address(r["ADDRESS"])
        forms[form] += 1
        pl = None
        if form == "intersection":
            pl = locate.place(net, {"primary_road": dc_name(p["primary"]), "secondary_road": dc_name(p["secondary"])})
        elif form == "house":
            k = street_key(dc_name(p["street"]))
            pt = addr.lookup(k, p["number"]) if k else None
            pl = locate.Placement("address", *pt) if pt else locate.Placement("review", note="address not found")
            # what the shared place() would do with the same text (its house reader refuses numbered streets)
            via = locate.place(net, {"primary_road": f"{p['number']} {dc_name(p['street'])}", "secondary_road": None},
                               addresses=addr)
            house_via_place_refused += via.tier != "address"
        elif form == "street_only":
            pl = locate.Placement("review", note="no cross street")
        else:
            pl = locate.Placement("review", note=form)
        tiers[pl.tier] += 1
        if gate.auto(pl):
            auto_tiers[pl.tier] += 1
        if pl.lat is not None and has_mpd:
            d = ft((pl.lat, pl.lon), mpd)
            dist_by_tier.setdefault(pl.tier, []).append(d)
            if len(examples) < 6 and d > 250:
                examples.append({"address": r["ADDRESS"], "tier": pl.tier, "ft_off": round(d)})
        # secondary, not independent: street of ADDRESS x DDOT's NEARESTINTSTREETNAME
        ni = r["NEARESTINTSTREETNAME"]
        street = p.get("primary") or p.get("street")
        if street and ni and ni != "Route not found" and form != "intersection":
            q = locate.place(net, {"primary_road": dc_name(street), "secondary_road": dc_name(ni)})
            nearest_test[q.tier] += 1
            if q.lat is not None and has_mpd:
                nearest_dist.append(ft((q.lat, q.lon), mpd))

    def acc(ds):
        k = sum(d <= 250 for d in ds)
        return {"n": len(ds), "within_250ft": round(k / len(ds), 4) if ds else None,
                "within_250ft_low": round(wilson_low(k, len(ds)), 4) if ds else None,
                "median_ft": round(sorted(ds)[len(ds) // 2]) if ds else None}

    placed = [d for t, ds in dist_by_tier.items() for d in ds]
    auto = [d for t, ds in dist_by_tier.items() if t in gate.auto_tiers for d in ds]
    out = {
        "area": "Washington DC (FIPS 11001), crashes reported in 2025", "n": n,
        "gps_mpd_plausible": gps_mpd, "gps_ddot_plausible": gps_ddot,
        "address_forms": dict(forms),
        "tiers": dict(tiers), "auto_by_tier": dict(auto_tiers),
        "name_placed_share": round(sum(v for t, v in tiers.items() if t != "review") / n, 4),
        "auto_share": round(sum(auto_tiers.values()) / n, 4),
        "address_tier_share": round(tiers["address"] / n, 4),
        "accuracy_by_tier": {t: acc(ds) for t, ds in dist_by_tier.items()},
        "accuracy_all_placed": acc(placed), "accuracy_auto": acc(auto),
        "house_address_refused_by_shared_place": house_via_place_refused,
        "network": {"streets": len(net.streets), "intersections": len(net.intersections)},
        "mar_points_used": sum(len(v) for v in addr.by_street.values()),
        "examples_over_250ft": examples,
        "nearest_int_test_not_independent": {"tiers": dict(nearest_test), "accuracy": acc(nearest_dist)},
    }
    (S / "placement_sample.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    assert dc_name("U STREET NW") == "U NW STREET" and dc_name("I-295") == "I-295"
    assert parse_address("FLORIDA AVENUE NE & NEW YORK AVENUE NE\nWASHINGTON,")[0] == "intersection"
    assert parse_address("16461/2 NEW JERSEY AVENUE NW") == ("house", {"number": 1646, "street": "NEW JERSEY AVENUE NW"})
    assert abs(wilson_low(98, 100) - 0.9299) < 1e-3
    main()
