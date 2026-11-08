"""Pull the Pulaski County 2025 sample (all rows, paged) from ARDOT's ACAT layer and measure it; record the fixture.
    PYTHONPATH=backend python research_notes/ar-2026-11-08/ar_pull.py <scratch dir>
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LAYER = "https://gis.ardot.gov/referenced/rest/services/TPP_TrafficSafety/NotForOfficialUse/FeatureServer/20"
out = Path(sys.argv[1])


def get(where, last=0, n=2000):
    q = {"where": f"({where}) AND OBJECTID>{last}", "outFields": "*", "orderByFields": "OBJECTID",
         "resultRecordCount": n, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(LAYER + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    return [f["attributes"] for f in json.load(urllib.request.urlopen(req, timeout=120))["features"]]


def all_rows(where):
    rows, last = [], 0
    while True:
        b = get(where, last)
        rows += b
        if len(b) < 2000:
            return rows
        last = b[-1]["OBJECTID"]


cache = out / "pulaski_2025.json"
rows = json.loads(cache.read_text()) if cache.exists() else all_rows("County='Pulaski' AND Year='2025'")
cache.write_text(json.dumps(rows))
tz = ZoneInfo("America/Chicago")
n = len(rows)
gps = sum(r["Latitude"] is not None for r in rows)
inter = sum(bool(r["IntersectingStreetName"]) for r in rows)
spaced = sum(bool(r["IntersectingStreetName"]) and " " in r["IntersectingStreetName"].strip() for r in rows)
rid = Counter(r["AH_RoadID"].split("x")[0] if r["AH_RoadID"] else None for r in rows)


def hhmm(t):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?(?: ?([AP]M))?", (t or "").strip())
    if not m:
        return None
    h = int(m.group(1)) % 12 + (12 if m.group(3) == "PM" else 0) if m.group(3) else int(m.group(1))
    return h, int(m.group(2))


agree = sum(hhmm(r["CrashTime"]) == (lambda d: (d.hour, d.minute))(datetime.fromtimestamp(r["CrashDate"] / 1000, tz))
            for r in rows if r["CrashDate"] and hhmm(r["CrashTime"]))
timed = sum(bool(r["CrashDate"] and hhmm(r["CrashTime"])) for r in rows)
res = {"area": "Pulaski County (Little Rock), 2025, every row", "n": n, "gps_share": round(gps / n, 4),
       "intersecting_street_share": round(inter / n, 4), "intersecting_street_spaced_share": round(spaced / n, 4),
       "road_id_county_prefix": dict(rid.most_common(5)), "crashdate_local_time_equals_crashtime": f"{agree}/{timed}",
       "severity": dict(Counter(r["CrashSeverity"] for r in rows)), "road_system": dict(Counter(r["RoadSystem"] for r in rows)),
       "time_formats": dict(Counter("12h" if "M" in (r["CrashTime"] or "") else "24h" for r in rows)),
       "serinj_vs_A": Counter((r["CrashSeverity"][-2], r["NumSerInj"] > 0, r["NumFatalities"] > 0) for r in rows).most_common(8)}
print(json.dumps(res, indent=1, default=str))
(Path(__file__).parent / "placement_sample.json").write_text(json.dumps(res, indent=1, default=str) + "\n")

# fixture: Little Rock 2025 by severity x manner, 24h times, plus statewide no-GPS and out-of-state-county rows
pick, seen = [], Counter()
for r in rows:
    k = (r["CrashSeverity"], r["CrashManner"], "M" in (r["CrashTime"] or ""))
    if r["City"] == "Little Rock" and seen[k] < 1:
        seen[k] += 1
        pick.append(r)
for r in rows:
    if r["NonMotoristType"] not in ("No Non-Motorist Relation",) and seen[r["NonMotoristType"]] < 1:
        seen[r["NonMotoristType"]] += 1
        pick.append(r)
pick += get("Latitude IS NULL", n=3) + get("County='Bowie County'", n=2)
fx = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "ar_ardot_acat.json"
uniq = list({r["OBJECTID"]: r for r in pick}.values())
fx.write_text(json.dumps({"source": LAYER, "recorded": "2026-11-08", "features": [{"attributes": r} for r in uniq]}, indent=0))
print("fixture rows", len(uniq), fx.stat().st_size, "bytes")
