"""WA placement sample (state onboarding, 2026-11-07): how CrashIQ's own locator places Washington crashes when GPS
is hidden. Two samples, newest full year (2025):

  seattle  2,000 SDOT collisions (wa_sdot), street network = TIGER/Line 2024 King County (53033)
  tacoma   all Tacoma city-street rows of the WSDOT export layout (wa_wsdot, City of Tacoma republication),
           street network = TIGER/Line 2024 Pierce County (53053)

Shared code is used unchanged. What this script does around it, and what the shared code would need instead, is
listed in research_notes/wa-2026-11-07/wa-import.md. Also compares SDOT's points with WSDOT's on the same report
number (WSDOT Crash Data Portal).

Inputs (scratch, never committed): ~/.hermes/cache/scratch/states/wa/{sdot_2025.json, sdot_persons_2025.json,
tacoma_2025.json, portal_seattle_2025.json, tl_2024_<fips>_{edges,featnames}.zip}
Run: PYTHONPATH=backend python tests/statewide/wa_placement.py   (prints JSON; writes wa_placement.json in scratch)
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from crashiq import tiger  # noqa: E402
from crashiq.locate import Gate, place  # noqa: E402
from crashiq.osm import Network, metres  # noqa: E402
from crashiq.sources import wa_sdot, wa_wsdot  # noqa: E402

S = Path.home() / ".hermes/cache/scratch/states/wa"
FT = 0.3048


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def network(fips: str, box) -> Network:
    keep = lambda lat, lon: box[0] <= lat <= box[2] and box[1] <= lon <= box[3]
    return Network(tiger.elements(S / f"tl_2024_{fips}_edges.zip", S / f"tl_2024_{fips}_featnames.zip", keep))


def run(net: Network, crashes: list[dict], wrap_block: bool) -> dict:
    """Hide GPS, place from names, score against the hidden point. `wrap_block`: for SDOT block crashes (A BETWEEN
    B AND C) also try the middle of A&B and A&C, which is where SDOT draws a block crash."""
    gate, tiers, auto, near, near_auto, mid_near, mid_n, mid_auto, rows = Gate(), Counter(), 0, 0, 0, 0, 0, 0, []
    for c in crashes:
        truth = (c["lat"], c["lon"])
        q = {**c, "lat": None, "lon": None, "offset_ft": c.get("sec_distance"), "offset_dir": c.get("sec_direction")}
        pl = place(net, q)
        tiers[pl.tier] += 1
        ok_auto = gate.auto(pl)
        auto += ok_auto
        d = metres(truth, (pl.lat, pl.lon)) / FT if pl.lat is not None else None
        if d is not None and d <= 250:
            near += 1
            near_auto += ok_auto
        if wrap_block and c.get("block_end_road") and pl.lat is not None:
            p2 = place(net, {**q, "secondary_road": c["block_end_road"]})
            if p2.lat is not None and metres((pl.lat, pl.lon), (p2.lat, p2.lon)) < 1200:   # one block, not a guess
                mid_n += 1
                mid_auto += ok_auto and gate.auto(p2)
                mid = ((pl.lat + p2.lat) / 2, (pl.lon + p2.lon) / 2)
                mid_near += metres(truth, mid) / FT <= 250
        rows.append({"id": c["collision_id"], "p": c["primary_road"], "s": c["secondary_road"], "tier": pl.tier,
                     "auto": ok_auto, "ft": round(d) if d is not None else None, "note": pl.note})
    n = len(crashes)
    placed = sum(v for k, v in tiers.items() if k != "review")
    return {"n": n, "tiers": dict(tiers), "placed": placed, "placed_share": round(placed / n, 4) if n else None,
            "auto": auto, "auto_share": round(auto / n, 4) if n else None,
            "within_250ft_of_placed": round(near / placed, 4) if placed else None,
            "within_250ft_low": round(wilson_low(near, placed), 4),
            "auto_within_250ft": round(near_auto / auto, 4) if auto else None,
            "auto_within_250ft_low": round(wilson_low(near_auto, auto), 4),
            "block_midpoint": {"n": mid_n, "auto_share_of_block_crashes": round(mid_auto / n, 4) if n else None,
                               "within_250ft": round(mid_near / mid_n, 4) if mid_n else None,
                               "low": round(wilson_low(mid_near, mid_n), 4)} if wrap_block else None,
            "_rows": rows}


def seattle(n: int = 2000) -> dict:
    crashes = wa_sdot.build(json.loads((S / "sdot_2025.json").read_text()),
                            json.loads((S / "sdot_persons_2025.json").read_text()))
    sample = random.Random(20261107).sample(crashes, n)
    gps = [c for c in sample if c["lat"] is not None]
    named = [c for c in gps if c["primary_road"] and c["secondary_road"]]
    net = network("53033", (47.47, -122.45, 47.75, -122.22))
    out = {"area": "Seattle (SDOT Collisions 2025)", "n": n, "gps": len(gps), "gps_share": round(len(gps) / n, 4),
           "names": sum(1 for c in sample if c["primary_road"] and c["secondary_road"]),
           "no_gps": n - len(gps),
           "no_gps_with_names": sum(1 for c in sample if c["lat"] is None and c["primary_road"] and c["secondary_road"]),
           "addr_type": dict(Counter(c["addr_type"] for c in sample))}
    out["names_share"] = round(out["names"] / n, 4)
    by_type = {}
    for t in ("I", "B"):
        by_type[t] = run(net, [c for c in named if c["addr_type"] == t], wrap_block=(t == "B"))
    out["by_type"] = by_type
    allr = run(net, named, wrap_block=False)
    out["all_named"] = allr
    # what names add where GPS is missing (no truth to score; tiers only)
    nog = [c for c in sample if c["lat"] is None and c["primary_road"] and c["secondary_road"]]
    gate = Gate()
    pls = [place(net, {**c, "offset_ft": None, "offset_dir": None}) for c in nog]
    out["no_gps_auto_placed"] = sum(gate.auto(p) for p in pls)
    return out


def sdot_vs_wsdot() -> dict:
    """Same report number in SDOT and WSDOT: how far apart are their points (2025)."""
    sd = {c["report_number"]: c for c in wa_sdot.build(json.loads((S / "sdot_2025.json").read_text()), [])}
    ws = [wa_wsdot.portal_record(r) for r in json.loads((S / "portal_seattle_2025.json").read_text())]
    d = sorted(metres((w["lat"], w["lon"]), (sd[w["report_number"]]["lat"], sd[w["report_number"]]["lon"])) / FT
               for w in ws if w["report_number"] in sd and sd[w["report_number"]]["lat"] is not None and w["lat"])
    k = sum(x <= 250 for x in d)
    return {"wsdot_rows": len(ws), "sdot_rows": len(sd), "matched_with_both_points": len(d),
            "within_250ft": round(k / len(d), 4) if d else None, "median_ft": round(d[len(d) // 2]) if d else None,
            "jurisdiction_of_wsdot_rows": dict(Counter(w["jurisdiction"] for w in ws))}


def tacoma() -> dict:
    feats = json.loads((S / "tacoma_2025.json").read_text())
    cols = wa_wsdot.resolve(feats[0]["attributes"])
    crashes = [wa_wsdot.export_record(f["attributes"], cols, f.get("geometry")) for f in feats]
    city = [c for c in crashes if c["jurisdiction"] == "City Street"]
    named = [c for c in city if c["lat"] is not None and c["primary_road"] and c["secondary_road"]]
    net = network("53053", (47.15, -122.57, 47.33, -122.34))
    r = run(net, named, wrap_block=False)
    return {"area": "Tacoma city streets (WSDOT layout, City of Tacoma open data, 2025)", "n_all": len(crashes),
            "city_street": len(city), "gps_share": round(sum(c["lat"] is not None for c in crashes) / len(crashes), 4),
            "names_share_city": round(sum(1 for c in city if c["primary_road"] and c["secondary_road"]) / len(city), 4),
            "with_offset": sum(1 for c in named if c["sec_distance"]), "block_number_share_city":
            round(sum(1 for c in city if c["block_number"]) / len(city), 4), **{"result": r}}


def main() -> None:
    out = {"seattle": seattle(), "sdot_vs_wsdot": sdot_vs_wsdot(), "tacoma": tacoma()}
    (S / "wa_placement.json").write_text(json.dumps(out, indent=1))

    def strip(o):
        return {k: strip(v) for k, v in o.items() if k != "_rows"} if isinstance(o, dict) else o
    print(json.dumps(strip(out), indent=1))


if __name__ == "__main__":
    main()
