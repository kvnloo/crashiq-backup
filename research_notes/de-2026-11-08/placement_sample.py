"""DE placement sample (2026-11-08): every New Castle County (Wilmington) 2025 crash on DSHS Public Crash Data, read
through the reader. The data has no street names or addresses, so the California-way locator test doesn't apply:
this counts GPS present and plausible, inside the county box, and how many crashes share a point.

Run: PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/de-2026-11-08/placement_sample.py
"""
import json
import urllib.request
from collections import Counter
from pathlib import Path

from crashiq.sources import de_dshs

rows = de_dshs.fetch("county='N' AND year='2025'")
recs = [c for c in map(de_dshs.crash_record, rows) if c]
s, w, n, e = json.loads((Path(__file__).parents[2] / "data/reference/county_boxes_de.json").read_text())[
    "counties"]["10003"]["box"]
ok = [c for c in recs if c["lat"] is not None]
pts = Counter((round(c["lat"], 5), round(c["lon"], 5)) for c in ok)
stats = de_dshs._get({"$select": "year,count(*) AS n,count(latitude) AS gps", "$group": "year", "$order": "year"},
                     urllib.request.urlopen)
out = {"area": "New Castle County (Wilmington), 2025", "rows": len(rows), "reportable": len(recs),
       "non_reportable": sum(r["crash_class"] == "01" for r in rows),
       "gps_plausible": len(ok), "gps_share": round(len(ok) / len(recs), 4),
       "in_county_box": sum(s <= c["lat"] <= n and w <= c["lon"] <= e for c in ok),
       "distinct_points": len(pts), "sharing_a_point": sum(v for v in pts.values() if v > 1),
       "severity": Counter(c["severity"] for c in recs), "collision_type": Counter(c["collision_type"] for c in recs),
       "statewide_rows_and_gps_by_year": {r.get("year"): [int(r["n"]), int(r["gps"])] for r in stats}}
print(json.dumps(out, indent=1))
(Path(__file__).parent / "placement_sample.json").write_text(json.dumps(out, indent=1) + "\n")
