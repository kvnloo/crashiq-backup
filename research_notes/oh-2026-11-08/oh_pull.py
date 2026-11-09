"""Ohio research pulls (2026-11-08): the placement sample (Franklin County 2024, 2,000 rows from 10 spread pages)
and the offline test fixture (central Columbus, 2024). Run: PYTHONPATH=backend python research_notes/oh-2026-11-08/oh_pull.py"""
import json, random, urllib.parse
from collections import Counter
from pathlib import Path
from crashiq.sources import oh_tims as oh

HERE = Path(__file__).parent
REPO = HERE.parents[1]
url = oh.BASE.format(year=2024) + "?"
cnt = oh._get(url + urllib.parse.urlencode({"where": "COUNTY_CD='FRA'", "returnCountOnly": "true", "f": "json"}))["count"]
random.seed(2026)
rows = []
for off in sorted(random.sample(range(0, cnt - 200), 10)):
    q = {"where": "COUNTY_CD='FRA'", "outFields": ",".join(oh.FIELDS), "returnGeometry": "false",
         "orderByFields": "OBJECTID", "resultOffset": off, "resultRecordCount": 200, "f": "json"}
    rows += [f["attributes"] for f in oh._get(url + urllib.parse.urlencode(q))["features"]]
box = json.loads((REPO / "data/reference/county_boxes_oh.json").read_text())["counties"]["39049"]["box"]
recs = [oh.contract_record(r) for r in rows]
gps = [c for c in recs if c["lat"] is not None]
inside = [c for c in gps if box[0] <= c["lat"] <= box[2] and box[1] <= c["lon"] <= box[3]]
out = {"area": "Franklin County (39049), 2024, 10 pages of 200 at seeded random offsets", "county_rows_2024": cnt,
       "n": len(recs), "gps_plausible": len(gps), "gps_share": round(len(gps) / len(recs), 4),
       "inside_county_box": len(inside),
       "route_named_share": round(sum(1 for c in recs if c["road_number"]) / len(recs), 4),
       "nlfid_route_types": Counter((r.get("NLFID") or "")[4:6] for r in rows).most_common(),
       "location_types": Counter(c["location_type"] for c in recs).most_common(),
       "severity": Counter(c["severity"] for c in recs), "freeway": sum(c["is_freeway"] for c in recs)}
(HERE / "placement_sample.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))

# fixture: central Columbus (N High St, short north to campus), 2024, a spread of severities, types and roads
fx_box = (39.975, -83.020, 40.010, -82.990)
allrows = oh.query_year(fx_box, 2024)
pick, seen = [], Counter()
for r in allrows:
    k = (r["CRASH_SEVERITY_CD"], r["CRASH_TYPE_CD"], r["FUNCTIONAL_CLASS_CD"] in (1, 2), (r.get("NLFID") or "")[4:6])
    if seen[k] < 1 and len(pick) < 45:
        seen[k] += 1
        pick.append(r)
(REPO / "tests/fixtures/oh_tims.json").write_text(json.dumps({"box": fx_box, "year": 2024, "box_rows": len(allrows),
                                                               "rows": pick}, indent=0))
print("fixture", len(pick), "of", len(allrows), Counter(oh.SEVERITY[r["CRASH_SEVERITY_CD"]] for r in pick))
