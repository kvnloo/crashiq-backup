"""MT placement sample (2026-11-08): every Yellowstone County 2025 crash on MDT's public layer, in WGS84; counts the
points inside Montana and inside the county box, and how many crashes share a point (MDT places by route + RP)."""
import json, urllib.parse, urllib.request
from collections import Counter
U = "https://gis.mtmdt.us/server/rest/services/MDTGIS/Public_Crash_Information/MapServer/0/query"
rows, last = [], 0
while True:
    q = {"where": f"COUNTY='Yellowstone' AND CRASH_DATE >= DATE '2025-01-01' AND OBJECTID>{last}", "outFields": "*",
         "outSR": 4326, "orderByFields": "OBJECTID", "resultRecordCount": 2000, "f": "json"}
    b = json.load(urllib.request.urlopen(urllib.request.Request(U + "?" + urllib.parse.urlencode(q),
                                                                headers={"User-Agent": "CrashIQ/0.1"}), timeout=120))
    rows += b["features"]
    if len(b["features"]) < 2000:
        break
    last = b["features"][-1]["attributes"]["OBJECTID"]
g = [r["geometry"] for r in rows if r.get("geometry")]
ok = [p for p in g if 44.3 <= p["y"] <= 49.1 and -116.1 <= p["x"] <= -104.0]
inbox = [p for p in ok if 45.4154 <= p["y"] <= 46.5411 and -108.9707 <= p["x"] <= -107.4176]
pts = Counter((round(p["x"], 6), round(p["y"], 6)) for p in ok)
out = {"area": "Yellowstone County (Billings), 2025", "n": len(rows), "gps_plausible": len(ok), "in_county_box": len(inbox),
       "distinct_points": len(pts), "sharing_a_point": sum(c for c in pts.values() if c > 1),
       "severity": Counter(r["attributes"]["CRASH_SEVERITY"] for r in rows),
       "city": Counter(r["attributes"]["CITY_NAME"] or "(rural)" for r in rows).most_common(4)}
print(json.dumps(out, indent=1))
