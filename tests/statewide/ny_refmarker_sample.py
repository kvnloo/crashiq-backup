"""NY statewide: how many DMV crashes the reference-marker join places, and how close (state/ny, 2026-11-07).

1. Match rate: a seeded random sample of 2024 crashes that carry a reference marker (statewide), joined to NYSDOT's
   marker layer by `ny_dmv.marker_points`. Plausibility: the marker point lies inside the crash's own county
   (Census cartographic county boundaries, cb_2024_us_county_500k).
2. Accuracy: the DMV table has no GPS, so truth comes from NYC open data (h9gi-nx95, police GPS). A DMV crash in NYC is
   linked to the one NYC crash with the same date, minute, severity class and borough (when NYC gives one); only unique
   links count. A wrong link shows up as a large error, so the numbers are a floor for the method.

Run: PYTHONPATH=backend python tests/statewide/ny_refmarker_sample.py --scratch ~/.hermes/cache/scratch/states/ny
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from crashiq.osm import metres  # noqa: E402
from crashiq.sources import ny_dmv, ny_nyc  # noqa: E402

FT = 0.3048
BOROUGH = {"NEW YORK": "MANHATTAN", "KINGS": "BROOKLYN", "QUEENS": "QUEENS", "BRONX": "BRONX", "RICHMOND": "STATEN ISLAND"}


def wilson_low(k: int, n: int, z: float = 1.96) -> float | None:
    if not n:
        return None
    p = k / n
    return round(100 * (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n), 1)


def counties(zip_path: Path) -> list[tuple[str, list]]:
    """NY county name -> polygon rings, from the Census cartographic county file."""
    import io
    import zipfile

    import shapefile
    z = zipfile.ZipFile(zip_path)
    part = lambda ext: io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith(ext))))
    r = shapefile.Reader(shp=part(".shp"), dbf=part(".dbf"), shx=part(".shx"))
    f = [x[0] for x in r.fields[1:]]
    out = []
    for sr in r.iterShapeRecords():
        rec = dict(zip(f, sr.record))
        if rec["STATEFP"] == "36":
            pts, idx = sr.shape.points, list(sr.shape.parts) + [len(sr.shape.points)]
            out.append((rec["NAME"].upper(), [pts[idx[i]:idx[i + 1]] for i in range(len(idx) - 1)]))
    return out


def inside(lat: float, lon: float, rings) -> bool:
    hit = False
    for ring in rings:                          # even-odd over all rings handles holes and islands
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                hit = not hit
    return hit


def county_of(lat, lon, polys) -> str | None:
    return next((name for name, rings in polys if inside(lat, lon, rings)), None)


def minute(t: str | None) -> int | None:
    try:
        h, m = str(t).strip().split(":")[:2]
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def sev_class(dmv_sev: str | None) -> str | None:
    return {"K": "K", "U": "I", "O": "O"}.get(dmv_sev or "")


def nyc_class(c: dict) -> str:
    return "K" if c["killed"] else ("I" if c["injured"] else "O")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--year", type=int, default=2024)
    a = ap.parse_args()
    cache = a.scratch / "cache"
    polys = counties(a.scratch / "county500k.zip")
    rng = random.Random(20261107)

    # 1. statewide random sample
    where = f"year={a.year} AND dot_reference_marker_location IS NOT NULL"
    total = int(ny_dmv._get(ny_dmv.CASES, {"$select": "count(*) AS n", "$where": where})[0]["n"])
    rows, chunk = [], 25
    for off in sorted(rng.sample(range(0, total - chunk), a.n // chunk)):
        rows += ny_dmv._get(ny_dmv.CASES, {"$select": "*,:id", "$where": where, "$order": ":id",
                                           "$limit": chunk, "$offset": off})
    marks = ny_dmv.marker_points(ny_dmv.panel(r.get("dot_reference_marker_location")) for r in rows)
    crashes = [ny_dmv.crash_record(r, marks) for r in rows]
    placed = [c for c in crashes if c["lat"] is not None]
    same_county = sum(1 for c in placed if county_of(c["lat"], c["lon"], polys) == (c["county_code"] or "").upper())
    misses = Counter(c["reference_marker"] for c in crashes if c["lat"] is None)
    sample = {"year": a.year, "rows_with_marker": total, "n": len(crashes), "placed": len(placed),
              "placed_pct": round(100 * len(placed) / len(crashes), 1),
              "placed_low": wilson_low(len(placed), len(crashes)),
              "in_own_county": same_county, "in_own_county_pct": round(100 * same_county / max(1, len(placed)), 1),
              "in_own_county_low": wilson_low(same_county, len(placed)),
              "nyc_share_of_sample": sum(1 for c in crashes if (c["county_code"] or "") in ny_dmv.NYC_COUNTIES),
              "unmatched_examples": [m for m, _ in misses.most_common(10)]}
    print(json.dumps(sample, indent=1))

    # 2. accuracy against NYC police GPS
    nyc_rm = ny_dmv.fetch_cases(f"{where} AND county_name IN ('NEW YORK','KINGS','QUEENS','BRONX','RICHMOND')", cache)
    nmarks = ny_dmv.marker_points(ny_dmv.panel(r.get("dot_reference_marker_location")) for r in nyc_rm)
    nyc, _ = ny_nyc.fetch(f"{a.year}-01-01", f"{a.year}-12-31", cache, persons=False)
    by_key = defaultdict(list)
    for c in nyc:
        by_key[(c["date"], minute(c["time"]), nyc_class(c))].append(c)
    errs, linked, ambiguous = [], 0, 0
    for r in nyc_rm:
        d = ny_dmv.crash_record(r, nmarks)
        if d["lat"] is None:
            continue
        cands = [c for c in by_key.get((d["date"], minute(r.get("time")), sev_class(d["severity"])), [])
                 if not c["borough"] or c["borough"] == BOROUGH[d["county_code"]]]
        if len(cands) != 1:
            ambiguous += len(cands) > 1
            continue
        linked += 1
        t = cands[0]
        if t["lat"] is not None:
            errs.append(metres((d["lat"], d["lon"]), (t["lat"], t["lon"])) / FT)
    errs.sort()
    within = lambda ft: sum(1 for e in errs if e <= ft)
    acc = {"nyc_marker_crashes": len(nyc_rm), "nyc_marker_matched": sum(1 for r in nyc_rm if ny_dmv.panel(
               r.get("dot_reference_marker_location")) in nmarks), "linked_unique": linked, "ambiguous": ambiguous,
           "with_truth_gps": len(errs), "median_ft": round(errs[len(errs) // 2]) if errs else None,
           **{f"within_{ft}ft": within(ft) for ft in (250, 528, 1320)},
           **{f"within_{ft}ft_pct": round(100 * within(ft) / max(1, len(errs)), 1) for ft in (250, 528, 1320)},
           "within_250ft_low": wilson_low(within(250), len(errs)), "within_528ft_low": wilson_low(within(528), len(errs))}
    print(json.dumps(acc, indent=1))
    (a.scratch / "refmarker_sample.json").write_text(json.dumps({"statewide": sample, "nyc_truth": acc}, indent=1))


if __name__ == "__main__":
    main()
