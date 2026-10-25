"""Download Caltrans SHN Postmiles Tenth (public ArcGIS feature service) to a CSV, with a source note."""
import csv
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
SRC = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/SHN_Postmiles_Tenth/FeatureServer/0"
OUT = Path("/Users/Ak47/Desktop/Crash-tester/data/cache/postmiles")
F = ["OBJECTID", "Route", "RteSuffix", "County", "District", "PMPrefix", "PM", "PMSuffix", "PMc", "Odometer",
     "AlignCode", "RouteType", "Direction", "PMoffset"]
rows, off = [], 0
while True:
    q = urllib.parse.urlencode({"where": "1=1", "outFields": ",".join(F), "outSR": 4326, "orderByFields": "OBJECTID",
                                "resultOffset": off, "resultRecordCount": 2000, "f": "json"})
    for t in range(4):
        try:
            d = json.load(urllib.request.urlopen(f"{SRC}/query?{q}", timeout=120))
            break
        except Exception:
            time.sleep(5 * (t + 1))
    feats = d["features"]
    for f in feats:
        a = f["attributes"]
        g = f.get("geometry") or {}
        rows.append([a.get(k) for k in F] + [g.get("y"), g.get("x")])
    off += len(feats)
    if not feats or not d.get("exceededTransferLimit", len(feats) == 2000):
        break
with open(OUT / "shn_postmiles_tenth_2026-10-24.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(F + ["lat", "lon"])
    w.writerows(rows)
(OUT / "SOURCE.md").write_text(f"Caltrans SHN Postmiles Tenth (public)\nSource: {SRC}\nDownloaded: 2026-10-24 by Tester "
                               f"(user-approved)\nRows: {len(rows)}\nFields: {', '.join(F)}, lat, lon (WGS84)\n")
print(len(rows))
