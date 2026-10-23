"""Build data/reference/ca_county_boxes.json: a padded bounding box per California county, from where its CCRS crashes
with police GPS are (0.5-99.5 percentile of latitude and longitude, plus 5 km; the Tester's county box, agency_scan.py).
Used to pick which TIGER/Line county files a corridor needs (#229): over-inclusive near county lines, which is fine.

Run:  python backend/scripts/build_county_boxes.py <path to a CCRS mirror SQLite>   (the Tester's ccrs_mirror.sqlite)
"""
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "reference" / "ca_county_boxes.json"


def main(mirror: str) -> None:
    con = sqlite3.connect(f"file:{mirror}?mode=ro", uri=True)
    pts = defaultdict(lambda: ([], []))
    for rid in [r[0] for r in con.execute("SELECT * FROM _meta") if r[1] == "crashes"]:
        for code, la, lo in con.execute(f'SELECT "County Code", CAST("Latitude" AS REAL), CAST("Longitude" AS REAL) '
                                        f'FROM "{rid}" WHERE "Latitude" IS NOT NULL AND "Latitude" != \'\''):
            if code and la and lo and 32.4 <= la <= 42.1 and -124.6 <= lo <= -114.0:
                pts[str(code).strip()][0].append(la)
                pts[str(code).strip()][1].append(lo)
    out, m = {}, 5 / 111.0
    for code, (las, los) in sorted(pts.items(), key=lambda t: int(t[0])):
        las.sort()
        los.sort()
        q = lambda v, f: v[min(len(v) - 1, int(f * len(v)))]  # noqa: E731
        fips = f"{2 * int(code) - 1:03d}"
        out[fips] = {"ccrs_county": int(code), "crashes_with_gps": len(las),
                     "box": [round(q(las, .005) - m, 4), round(q(los, .005) - m * 1.25, 4),
                             round(q(las, .995) + m, 4), round(q(los, .995) + m * 1.25, 4)]}
    OUT.write_text(json.dumps({"source": f"CCRS crashes with GPS in {Path(mirror).name}, 0.5-99.5 percentile + 5 km",
                               "box": "[min lat, min lon, max lat, max lon]", "counties": out}, indent=1) + "\n")
    print(len(out), "counties ->", OUT)


if __name__ == "__main__":
    main(sys.argv[1])
