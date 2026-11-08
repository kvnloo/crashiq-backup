"""Virginia placement sample, the California way (brief 2026-11-07).

Input: the DMV 2025 Datathon crash table (data.virginia.gov, 2022-2024), streamed once by dmv_scan.py into
dmv_keep.csv (Richmond City + Fairfax County rows). It is the only open Virginia table with a cross street
(SecondaryLocation); the VDOT Full Crash layer has one street field only.
For 2,000 random 2024 crashes per area: GPS present and plausible; then hide the GPS, place from RouteName +
SecondaryLocation on a TIGER/Line 2024 network with locate.place, and score against the hidden GPS.
B + C (run_vdot): 2,000 VDOT Full Crash 2024 rows per area (vdot_pull.py): the officer's one street field pre-split
into a pair ("ARLINGTON BLVD / JAGUAR TRAIL"), and house-number text placed on VGIN address points (vgin_pull.py).

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/va-2026-11-07/placement_sample.py <scratch dir>
"""

from __future__ import annotations

import collections
import csv
import json
import math
import random
import re
import sys
from pathlib import Path

from crashiq import locate, osm, tiger

AREAS = {"Richmond City": "51760", "Fairfax County": "51059"}
FT250_M = 250 * 0.3048
# "US-60E", "VA-147W", "IS-95N", "SR-7100N": the RoadName route code -> a form street_key reads ("US 60")
ROUTE = re.compile(r"^(US|VA|IS|SR)-(\d+)[NSEW]?\b")


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def plausible(la, lo) -> bool:
    return la is not None and 36.5 <= la <= 39.5 and -83.7 <= lo <= -75.2


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def route_form(road: str) -> str | None:
    m = ROUTE.match(road or "")
    if not m:
        return None
    return {"US": "US HWY", "VA": "STATE RTE", "IS": "I", "SR": "STATE RTE"}[m[1]] + f" {int(m[2])}"


def run(scratch: Path, area: str, fips: str, n: int = 2000) -> dict:
    rows = [r for r in csv.DictReader(open(scratch / "dmv_keep.csv"))
            if r["Jurisdiction"] == area and r["Year"] == "2024"]
    random.Random(2026).shuffle(rows)
    rows = rows[:n]
    net = osm.Network(tiger.elements(scratch / f"tl_2024_{fips}_edges.zip", scratch / f"tl_2024_{fips}_featnames.zip"))
    gate = locate.Gate()
    tiers, auto, hits, auto_hits, reasons, gps = collections.Counter(), 0, 0, 0, collections.Counter(), 0
    route_retry_used, examples = 0, collections.defaultdict(list)
    named = 0
    for r in rows:
        la, lo = num(r["Latitude"]), num(r["Longitude"])
        ok = plausible(la, lo)
        gps += ok
        prim, sec = r["RouteName"].strip() or re.sub(r"\(.*?\)", "", r["RoadName"]).strip(), r["SecondaryLocation"].strip()
        if not (prim and sec):
            reasons["no cross street in source"] += 1
            continue
        named += 1
        crash = {"primary_road": prim, "secondary_road": sec, "offset_ft": None, "offset_dir": None}   # GPS hidden
        pl = locate.place(net, crash)
        if pl.lat is None and route_form(r["RoadName"]):            # wrap: retry with the route number ("US HWY 60")
            alt = locate.place(net, {**crash, "primary_road": route_form(r["RoadName"])})
            if alt.lat is not None:
                pl, route_retry_used = alt, route_retry_used + 1
        tiers[pl.tier] += 1
        if pl.lat is None:
            reasons[pl.note or pl.tier] += 1
            if len(examples[pl.note]) < 6:
                examples[pl.note].append(f"{r['RoadName']} | {prim} & {sec}")
            continue
        close = ok and osm.metres((pl.lat, pl.lon), (la, lo)) <= FT250_M
        hits += close
        if gate.auto(pl):
            auto += 1
            auto_hits += close
        elif len(examples["placed, not auto: " + pl.tier]) < 4:
            examples["placed, not auto: " + pl.tier].append(f"{prim} & {sec}")
        if not close and len(examples["placed >250 ft off"]) < 8:
            examples["placed >250 ft off"].append(f"{prim} & {sec} [{pl.tier}] "
                                                  f"{osm.metres((pl.lat, pl.lon), (la, lo)) / 0.3048:.0f} ft")
    placed = sum(v for k, v in tiers.items() if k != "review")
    return {
        "area": f"{area} ({fips}), 2024", "n": len(rows), "gps_share": round(gps / len(rows), 4),
        "street_pair_share": round(named / len(rows), 4),
        "tiers": dict(tiers), "name_placed_share": round(placed / len(rows), 4),
        "name_placed_share_of_pairs": round(placed / named, 4) if named else None,
        "auto_share": round(auto / len(rows), 4), "auto_share_of_pairs": round(auto / named, 4) if named else None,
        "route_retry_used": route_retry_used,
        "within_250ft_auto": round(auto_hits / auto, 4) if auto else None,
        "within_250ft_auto_low": round(wilson_low(auto_hits, auto), 4),
        "within_250ft_all_placed": round(hits / placed, 4) if placed else None,
        "within_250ft_all_placed_low": round(wilson_low(hits, placed), 4),
        "not_placed": dict(reasons.most_common(10)), "examples": dict(examples),
    }


# ---- B + C: the VDOT Full Crash layer's one officer-written field, ROUTE_OR_STREET_NM (vdot_pull.py, 2024) ----
# Pre-split here, not in shared code: "ARLINGTON BLVD / JAGUAR TRAIL", "W BROAD ST AND SUMMIT AVE", "NB 95 AT EXIT 78".
SPLIT = re.compile(r"\s*/\s*|\s+&\s+|\s+AND\s+|\s+AT\s+")
BOUND = re.compile(r"\b(?:[NSEW]/?B|NORTH ?BOUND|SOUTH ?BOUND|EAST ?BOUND|WEST ?BOUND|FRFX|EXPRESS|INNER LOOP|OUTER LOOP)\b")
MARKER = re.compile(r"\b(?:EXIT|MM|MILE)\b|\d+\s*MM\b")
BLOCK = re.compile(r"^(\d{1,5})\s+(?:BLK|BLOCK|BLOCK OF)\s+")


def clean(part: str) -> str:
    s = BOUND.sub(" ", part.upper())
    s = re.sub(r"^(I|RT|RTE|ROUTE)\s*(\d+)", r"\1 \2", s.strip())          # RT244, I66 -> RT 244, I 66
    return re.sub(r"\s+", " ", s).strip()


def split_pair(raw: str) -> tuple[str, str] | None:
    parts = [clean(p) for p in SPLIT.split(raw or "") if p.strip()]
    parts = [p for p in parts if p and not MARKER.search(p)]
    if len(parts) == 3 and re.match(r"^(RT|RTE|ROUTE|I)\s\d+$", parts[0]):   # "RT 644 / FRANCONIA RD / JAPONICA ST"
        parts = parts[1:]
    return (parts[0], parts[1]) if len(parts) >= 2 else None


def run_vdot(scratch: Path, juris: str, fips: str, n: int = 2000) -> dict:
    rows = [a for a in json.load(open(scratch / "vdot_2024_127_29.json")) if a["PHYSICAL_JURIS"] == juris]
    random.Random(2026).shuffle(rows)
    rows = rows[:n]
    net = osm.Network(tiger.elements(scratch / f"tl_2024_{fips}_edges.zip", scratch / f"tl_2024_{fips}_featnames.zip"))
    addr = locate.AddressIndex([(s, num_, float(la), float(lo)) for s, num_, la, lo in
                                csv.reader(open(scratch / f"vgin_{fips}.csv")) if s and num_])
    gate = locate.Gate()
    t_pair, t_addr = collections.Counter(), collections.Counter()
    pair_n = pair_hit = pair_auto = pair_auto_hit = 0
    addr_n = addr_placed = addr_250 = addr_400 = 0
    gps = sum(plausible(a["LAT"], a["LON"]) for a in rows)
    for a in rows:
        raw = (a["ROUTE_OR_STREET_NM"] or "").strip()
        house = BLOCK.sub(r"\1 ", raw.upper())
        if re.match(r"^\d{1,5}\s+[A-Z]", house) and not SPLIT.search(house):
            addr_n += 1
            pl = locate.place(net, {"primary_road": clean(house), "secondary_road": None}, addresses=addr)
            t_addr[pl.tier] += 1
            if pl.tier == "address":
                addr_placed += 1
                d = osm.metres((pl.lat, pl.lon), (a["LAT"], a["LON"])) / 0.3048
                addr_250 += d <= 250
                addr_400 += d <= 400
            continue
        pr = split_pair(raw)
        if not pr:
            continue
        pair_n += 1
        pl = locate.place(net, {"primary_road": pr[0], "secondary_road": pr[1], "offset_ft": None, "offset_dir": None})
        t_pair[pl.tier] += 1
        if pl.lat is None:
            continue
        close = osm.metres((pl.lat, pl.lon), (a["LAT"], a["LON"])) <= FT250_M
        pair_hit += close
        if gate.auto(pl):
            pair_auto += 1
            pair_auto_hit += close
    placed = sum(v for k, v in t_pair.items() if k != "review")
    return {
        "area": f"VDOT Full Crash, JURIS {juris} ({fips}), 2024", "n": len(rows), "gps_share": round(gps / len(rows), 4),
        "officer_pair_share": round(pair_n / len(rows), 4), "pair_tiers": dict(t_pair),
        "pair_placed_share_of_pairs": round(placed / pair_n, 4) if pair_n else None,
        "pair_auto_share_of_pairs": round(pair_auto / pair_n, 4) if pair_n else None,
        "pair_within_250ft_auto": round(pair_auto_hit / pair_auto, 4) if pair_auto else None,
        "pair_within_250ft_auto_low": round(wilson_low(pair_auto_hit, pair_auto), 4),
        "house_address_share": round(addr_n / len(rows), 4), "address_tiers": dict(t_addr),
        "address_placed_share_of_house": round(addr_placed / addr_n, 4) if addr_n else None,
        "address_within_250ft": round(addr_250 / addr_placed, 4) if addr_placed else None,
        "address_within_250ft_low": round(wilson_low(addr_250, addr_placed), 4),
        "address_within_400ft": round(addr_400 / addr_placed, 4) if addr_placed else None,
        "address_points_source": "VGIN Virginia Address Points (CC0), FIPS " + fips,
    }


if __name__ == "__main__":
    scratch = Path(sys.argv[1])
    out = {a: run(scratch, a, f) for a, f in AREAS.items()}
    out["vdot_officer_text"] = {j: run_vdot(scratch, j, f) for j, f in (("127", "51760"), ("29", "51059"))}
    print(json.dumps(out, indent=1))
    (Path(__file__).parent / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
