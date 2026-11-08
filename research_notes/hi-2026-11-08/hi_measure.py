"""Measure HDOT's open crash layers (2026-11-08): rows per year, usable points, jurisdiction, severity fields.

Layers (ArcGIS Online org HQ0xoN0EzDPBOEci = Hawaii DOT, owners dot_zwu / dot_mmekuria; no login):
  HDOT_Crash/FeatureServer/0            "HDOT_Crash_Layer"       2015-2023 (also Socrata kktn-udgf)
  HDOT_Crash_Layer_2014/FeatureServer/0 "HDOT_Crash_Layer_2024"  2024 only
  FatalCrash/FeatureServer/0            "FatalCrash_2012-2025"   fatal crashes, with date

Run: python3 research_notes/hi-2026-11-08/hi_measure.py <scratch/hi>   (writes hi_measure.json next to this file)
"""

import collections
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

B = "https://services.arcgis.com/HQ0xoN0EzDPBOEci/arcgis/rest/services"
UA = {"User-Agent": "CrashIQ/0.1"}
HI = (18.8, 22.3, -160.3, -154.7)
# the layer's own description (Socrata kktn-udgf): "(0, 0) coordinates will be defaulted to corresponded countries"
DEFAULT = {"HON": (21.480852, -157.92313)}


def pull(layer: str, fields: str, page: int = 1000) -> list[dict]:
    out, off = [], 0
    while True:
        q = urllib.parse.urlencode({"where": "1=1", "outFields": fields, "returnGeometry": "false", "f": "json",
                                    "resultOffset": off, "resultRecordCount": page, "orderByFields": "ObjectId"
                                    if "ObjectId" in fields else "FID"})
        with urllib.request.urlopen(urllib.request.Request(f"{B}/{layer}/query?{q}", headers=UA), timeout=120) as r:
            d = json.load(r)
        out += [f["attributes"] for f in d["features"]]
        off += len(d["features"])
        if not d["features"] or not d.get("exceededTransferLimit"):
            return out


def ok(lat, lon) -> bool:
    return bool(lat and lon) and HI[0] <= lat <= HI[1] and HI[2] <= lon <= HI[3]


def main(scratch: Path) -> dict:
    cache = scratch / "hi_layers.json"
    if not cache.exists():
        cache.write_text(json.dumps({
            "all": pull("HDOT_Crash/FeatureServer/0", "ObjectId,crash_year,county,gps_latitude,gps_longitude,"
                        "crashseveritymajorinjury,prim_jurisdict,pedinvolved,bcinvolved"),
            "y2024": pull("HDOT_Crash_Layer_2014/FeatureServer/0", "FID,Crash_Year,County,GPS_Latitude,GPS_Longitude,"
                          "Crashseveritymajorinjury,Prim_Jurisdict"),
            "fatal": pull("FatalCrash/FeatureServer/0", "ObjectId,CrashId,Crash_Year,Crash_Date,x,y,Total_Fatalities")}))
    d = json.loads(cache.read_text())
    rows = [{"year": r["crash_year"], "county": r["county"], "lat": r["gps_latitude"], "lon": r["gps_longitude"],
             "major": r["crashseveritymajorinjury"], "jur": r["prim_jurisdict"] or ""} for r in d["all"]]
    rows += [{"year": r["Crash_Year"], "county": r["County"], "lat": r["GPS_Latitude"], "lon": r["GPS_Longitude"],
              "major": r["Crashseveritymajorinjury"], "jur": r["Prim_Jurisdict"] or ""} for r in d["y2024"]]
    per = collections.defaultdict(collections.Counter)
    shared = collections.Counter((round(r["lat"] or 0, 5), round(r["lon"] or 0, 5)) for r in rows)
    for r in rows:
        c = per[r["year"]]
        c["rows"] += 1
        c["point_in_hawaii"] += ok(r["lat"], r["lon"])
        c["on_a_point_shared_by_10+"] += shared[(round(r["lat"] or 0, 5), round(r["lon"] or 0, 5))] >= 10
        c["state_jurisdiction"] += r["jur"].startswith("S")
        c["county_jurisdiction"] += r["jur"].startswith("C")
        c["major_injury_flag_1"] += r["major"] == 1
        c["major_injury_flag_null"] += r["major"] is None
    fat_y = collections.Counter(f["Crash_Year"] for f in d["fatal"])   # one row per crash; CrashId is blank before 2019
    top = [(k, v) for k, v in shared.most_common(5)]
    return {"per_year": {y: dict(per[y]) for y in sorted(per)}, "rows": len(rows),
            "point_in_hawaii_share": round(sum(ok(r["lat"], r["lon"]) for r in rows) / len(rows), 4),
            "most_shared_points": [{"point": list(k), "rows": v} for k, v in top],
            "fatal_crashes_per_year": dict(sorted(fat_y.items())), "fatal_rows": len(d["fatal"]),
            "fatal_rows_with_crash_id": sum(bool(f["CrashId"]) for f in d["fatal"])}


if __name__ == "__main__":
    out = main(Path(sys.argv[1]))
    print(json.dumps(out, indent=1))
    (Path(__file__).parent / "hi_measure.json").write_text(json.dumps(out, indent=1) + "\n")
