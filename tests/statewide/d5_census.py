"""#264 source 1: the US Census Geocoder batch service (geocoding.geo.census.gov, benchmark Public_AR_Current;
user-approved 2026-10-25 in the Tester session). Only address strings go out: each distinct "number street", city,
"CA" gets a sequence number made here (1, 2, 3 ...), never a crash's record id; ZIP is left blank. At most 10,000
lines per batch (the service's limit). A "Match" (Exact or Non_Exact) is placed at the returned point; the service's
own interpolation along TIGER ranges, so it can differ from d5_tiger.py's. Unmatched / Tie = not placed.

Run: python tests/statewide/d5_census.py   (writes data/statewide/d5_result_census.csv; raw replies in
data/statewide/census_geocoder/, local only)
"""

from __future__ import annotations

import csv
import io
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
BATCH = 9000


def main() -> None:
    import d5_common as dc
    rows = dc.pools()
    # outside cities the CCRS "city" is the word Unincorporated: sent blank (the service then has street + state only)
    addr = lambda r: (f"{r['number']} {r['street']}", "" if r["city"] in ("Unincorporated", "") else r["city"])  # noqa: E731
    distinct = sorted({addr(r) for r in rows})
    seq = {a: i + 1 for i, a in enumerate(distinct)}
    out_dir = dc.DATA / "census_geocoder"
    out_dir.mkdir(exist_ok=True)
    result = {}
    for start in range(0, len(distinct), BATCH):
        part = distinct[start:start + BATCH]
        reply = out_dir / f"reply_{start // BATCH}.csv"
        if not reply.exists():
            body = io.StringIO()
            w = csv.writer(body)
            for a in part:
                w.writerow([seq[a], a[0], a[1], "CA", ""])
            upload = out_dir / f"upload_{start // BATCH}.csv"
            upload.write_text(body.getvalue())
            for attempt in range(3):
                p = subprocess.run(["curl", "-s", "-m", "1800", "-F", f"addressFile=@{upload}", "-F",
                                    "benchmark=Public_AR_Current", URL], capture_output=True, text=True)
                if p.returncode == 0 and p.stdout.strip():
                    reply.write_text(p.stdout)
                    break
                time.sleep(30 * (attempt + 1))
            else:
                raise SystemExit(f"batch {start // BATCH} failed: {p.stderr[:200]}")
            print(f"batch {start // BATCH}: {len(part)} addresses", flush=True)
        for line in csv.reader(reply.read_text().splitlines()):
            if len(line) >= 6 and line[2] == "Match" and line[5]:
                lon, lat = (float(x) for x in line[5].split(","))
                result[int(line[0])] = (lat, lon, line[3])
    out = []
    for r in rows:
        hit = result.get(seq[addr(r)])
        out.append({"collision_id": r["collision_id"], "pool": r["pool"], "district": r["district"],
                    "placed": int(hit is not None), "lat": f"{hit[0]:.6f}" if hit else "",
                    "lon": f"{hit[1]:.6f}" if hit else "", "note": hit[2] if hit else "no match"})
    dc.write("census", out)
    print(f"{len(distinct)} distinct addresses sent; {len(result)} matched")
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
