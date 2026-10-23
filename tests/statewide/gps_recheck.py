"""#219: re-check the difficult crashes where police GPS is off the report's roads but within a mile of them, the cases
that could be read as "the GPS is right and the street names are wrong" (the #211 audit's "near one named road only"
and "near neither road, within 1 mile"). The user doubts the pattern; this looks for evidence either way.

Sample: every such case in the #211 audit sample that is still difficult after the #199 correction, plus a seeded
random sample of SAMPLE_N more from the bin-2 re-run (bin2.py gain rows with police GPS within a mile of a named road).
For each crash, evidence from the OSM extract around the GPS point (the streets that meet there, within NEAR_FT) and
from the report (its two names, its stated offset), then ONE class, first match wins:
  default_point      the GPS is a pile point or has <= 2 decimals (gps_profile.py): the GPS is wrong
  gps_at_named_intersection  the streets meeting at the GPS ARE the report's two streets (similarity >= 0.95): both are
                     right; the harness's GPS check missed it (the city network is clipped to the city boundary, and
                     this intersection lies just outside it, or outside cities the name matcher missed a variant)
  names_misspelled   the streets meeting at the GPS resemble BOTH report names (similarity >= SIM) though not exactly:
                     the GPS is right, the names are misspelled (the only class that supports "names wrong, GPS right")
  offset_consistent  the GPS lies on a named road at about the stated offset from where the named roads meet
                     (within 50% or 150 ft): both are right; the 400 ft check was too tight for this crash
  freeway            a freeway / route / ramp crash with the GPS away from any intersection: the crash is on the
                     freeway at a distance from the named cross street; nothing says the names are wrong
  cross_disagrees    the GPS is at an intersection of ONE report street and another street: report and GPS disagree
                     on the cross street; nothing says which is right
  elsewhere          the GPS is at an intersection of two streets that resemble neither report name
  mid_block          no intersection within NEAR_FT of the GPS (mid-block, parking lot, off the street network)

Run: python tests/statewide/gps_recheck.py   (writes data/statewide/gps_recheck.csv and gps_recheck.json)
"""

from __future__ import annotations

import csv
import glob
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
from crashiq import names  # noqa: E402
from gps_profile import Roads, _ft, decimals, gps_crashes, offset_ft  # noqa: E402

SAMPLE_N, SEED, NEAR_FT, SIM, MILE_M = 200, 219, 150.0, 0.80, 1609.0
FREEWAY = re.compile(r"\b(I|SR|US|RT|RTE|HWY|ROUTE|INTERSTATE|STATE ROUTE|SH)[\s-]*\d+|\bFREEWAY\b|\bFWY\b|\bRAMP\b|"
                     r"[NSEW]/?B\b|BOUND\b")


def candidates() -> list[tuple[str, str]]:
    with open(DATA / "coverage_crashes.csv") as f:
        still = {r["collision_id"] for r in csv.DictReader(f) if r["bin"] == "2"}
    out = []
    with open(DATA / "bin2_audit.csv") as f:
        for r in csv.DictReader(f):
            if r["sample"] == "gps_off" and r["collision_id"] in still and r["gps_side"] in (
                    "near one named road only", "near neither road, within 1 mile"):
                out.append((r["collision_id"], "audit"))
    pool = []
    for p in sorted(glob.glob(str(DATA / "bin2_p*.csv"))) + [str(DATA / "bin2_sd.csv")]:
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["set"] != "gain" or r["collision_id"] not in still or not r["gps_lat"]:
                    continue
                if not r["reason_199"].startswith("police GPS off"):
                    continue
                ds = [float(x) for x in (r["gps_d_primary_m"], r["gps_d_secondary_m"]) if x]
                if ds and min(ds) <= MILE_M:
                    pool.append(r["collision_id"])
    have = {c for c, _ in out}
    pool = sorted(set(pool) - have, key=int)
    out += [(c, "random") for c in random.Random(SEED).sample(pool, min(SAMPLE_N, len(pool)))]
    return out


def main() -> None:
    cand = candidates()
    cr = gps_crashes()
    piles = {(p["lat"], p["lon"]) for p in json.loads((DATA / "gps_piles.json").read_text())["piles"]}
    roads = Roads()
    rows = []
    for cid, src in cand:
        r = cr.get(cid)
        if r is None:
            continue
        g = (r["Latitude"], r["Longitude"])
        pr, sr = r["PrimaryRoad"] or "", r["SecondaryRoad"] or ""
        kp, ks = names.street_key(pr), names.street_key(sr)
        # streets meeting near the GPS: node -> set of street names through it
        at = defaultdict(set)
        for name, tags, nids, coords in roads.around(g[0], g[1], NEAR_FT * 2):
            t = json.loads(tags)
            nm = t.get("name") or t.get("ref")
            if not nm:
                continue
            for n, (la, lo) in zip(json.loads(nids), json.loads(coords)):
                if _ft((la, lo), g) <= NEAR_FT:
                    at[n].add(nm)
        inter = sorted({tuple(sorted(v)[:2]) for v in at.values() if len(v) >= 2})
        sim = lambda k, nm: names.similarity(k, names.street_key(nm)) if k and names.street_key(nm) else 0.0  # noqa: E731
        best = None
        for a, b in inter:
            sp, ss = max(sim(kp, a), sim(kp, b)), max(sim(ks, a), sim(ks, b))
            if best is None or sp + ss > best[0] + best[1]:
                best = (sp, ss, f"{a} & {b}")
        dp = roads.nearest_named_ft({**r, "SecondaryRoad": None})
        ds = roads.nearest_named_ft({**r, "PrimaryRoad": r["SecondaryRoad"], "SecondaryRoad": None})
        off = offset_ft(r)
        if (round(g[0], 5), round(g[1], 5)) in piles or min(decimals(g[0]), decimals(g[1])) <= 2:
            cls = "default_point"
        elif best and best[0] >= 0.95 and best[1] >= 0.95:
            cls = "gps_at_named_intersection"
        elif best and best[0] >= SIM and best[1] >= SIM:
            cls = "names_misspelled"
        elif off > 0 and dp is not None and ds is not None and min(dp, ds) <= 100 and \
                abs(max(dp, ds) - off) <= max(150.0, 0.5 * off):
            cls = "offset_consistent"
        elif FREEWAY.search(f"{pr} {sr}".upper()):
            cls = "freeway"
        elif best and max(best[0], best[1]) >= 0.9:
            cls = "cross_disagrees"
        elif inter:
            cls = "elsewhere"
        else:
            cls = "mid_block"
        rows.append({"collision_id": cid, "source": src, "agency": r["NCIC Code"], "city": r["City Name"],
                     "year": r["year"], "primary": pr, "secondary": sr, "offset_ft": round(off),
                     "offset_dir": r["SecondaryDirection"], "gps": f"{g[0]},{g[1]}",
                     "gps_to_primary_ft": None if dp is None else round(dp),
                     "gps_to_secondary_ft": None if ds is None else round(ds),
                     "streets_at_gps": best[2] if best else "", "sim_primary": round(best[0], 2) if best else "",
                     "sim_secondary": round(best[1], 2) if best else "", "cls": cls})
    with open(DATA / "gps_recheck.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    res = {"cases": len(rows), "by_source": dict(Counter(r["source"] for r in rows)),
           "classes": dict(Counter(r["cls"] for r in rows).most_common()),
           "classes_random_sample": dict(Counter(r["cls"] for r in rows if r["source"] == "random").most_common())}
    (DATA / "gps_recheck.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
