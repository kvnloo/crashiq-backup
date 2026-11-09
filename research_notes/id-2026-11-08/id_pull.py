"""Idaho: placement sample (Ada County 2022, every row) and the offline test fixture, from ITD's live layers.
Run: PYTHONPATH=backend python research_notes/id-2026-11-08/id_pull.py   (2026-11-08)"""
import json
import urllib.request
from collections import Counter
from pathlib import Path

from crashiq.sources import id_itd

HERE = Path(__file__).parent
FIX = HERE.parents[1] / "tests/fixtures/id_itd_crashes.json"
op = urllib.request.urlopen
UF = "OBJECTID,Serial_Number,Unit_Number,Vehicle_Type,Most_Harmful_Event,Contrib_Circ_1"
none = {}

ada = id_itd._rows(id_itd.CRASH, "Accident_Year='2022' AND County='Ada'", none, "*", op)
units = id_itd._rows(id_itd.UNIT, "Accident_Year='2022' AND County='Ada'", none, UF, op)
by = {}
for u in units:
    by.setdefault(u["Serial_Number"], []).append(u)
recs = [id_itd.contract_record(a, by.get(a["Serial_Number"], [])) for a in ada]
box = json.loads((id_itd.REF / "county_boxes_id.json").read_text())["counties"]["16001"]["box"]
gps = [c for c in recs if c["lat"] is not None]
sample = {"area": "Ada County (Boise), 2022, every row", "n": len(recs),
          "gps_share": round(len(gps) / len(recs), 4),
          "gps_inside_ada_box": round(sum(box[0] <= c["lat"] <= box[2] and box[1] <= c["lon"] <= box[3]
                                          for c in gps) / len(recs), 4),
          "serial_unique": len({c["crash_id"] for c in recs}) == len(recs),
          "county_fips_16001": sum(c["county_fips"] == "16001" for c in recs),
          "severity": Counter(c["severity"] for c in recs), "route_system": Counter((a["RouteID"] or "")[6:8] for a in ada),
          "intersection_related_share": round(sum(c["intersection_related"] for c in recs) / len(recs), 4),
          "crashes_with_units": sum(a["Serial_Number"] in by for a in ada),
          "ped": sum(c["ped"] for c in recs), "bike": sum(c["bike"] for c in recs),
          "collision_type_top": Counter(c["collision_type"] for c in recs).most_common(8),
          "street_text": "none in the layer (no locator test possible)"}
(HERE / "placement_sample.json").write_text(json.dumps(sample, indent=1))
print(json.dumps(sample, indent=1))

# fixture: a spread of Ada 2022 rows, 2008 rows with no point, and 2023 (part-loaded) rows
pick, seen = [], set()
def take(rows, n):
    for a in rows[:n]:
        if a["Serial_Number"] not in seen:
            seen.add(a["Serial_Number"]); pick.append(a)
for sev in id_itd.SEVERITY:
    take([a for a in ada if a["Severity"] == sev], 8)
for flag in ("ped", "bike", "motorcycle", "heavy_truck", "is_freeway"):
    take([a for a, c in zip(ada, recs) if c[flag]], 4)
take([a for a, c in zip(ada, recs) if c["collision_type"] == "REAR END"], 3)
take(id_itd._rows(id_itd.CRASH, "Accident_Year='2008' AND Latitude IS NULL", none, "*", op), 3)
y23 = id_itd._get(id_itd.CRASH, {"where": "Accident_Year='2023' AND County='Ada'", "outFields": "*",
                                 "resultRecordCount": 3, "returnGeometry": "false"}, op)["features"]
take([f["attributes"] for f in y23], 3)
ser = ", ".join(f"'{a['Serial_Number']}'" for a in pick)
fu = id_itd._rows(id_itd.UNIT, f"Serial_Number IN ({ser})", none, UF, op)
hi = id_itd._get(id_itd.CRASH, {"where": "1=1", "outStatistics": json.dumps([{"statisticType": "max",
                 "onStatisticField": "Accident_Date_Time", "outStatisticFieldName": "hi"}])}, op)
FIX.write_text(json.dumps({"recorded": "2026-11-08", "max": hi, "crashes": pick, "units": fu}))
print(len(pick), "crashes", len(fu), "units", FIX.stat().st_size, "bytes")
