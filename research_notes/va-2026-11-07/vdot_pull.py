# Pull VDOT Full Crash (layer 0) for Richmond City (127) and Fairfax County (29), 2024, paging by OBJECTID.
import json, urllib.parse, urllib.request
B = "https://services.arcgis.com/p5v98VHDX9Atv3l7/arcgis/rest/services/Full_Crash/FeatureServer/0/query"
out, last = [], 0
while True:
    q = {"where": f"CRASH_YEAR='2024' AND PHYSICAL_JURIS IN ('127','29') AND OBJECTID>{last}", "outFields": "*",
         "orderByFields": "OBJECTID", "resultRecordCount": 2000, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(B + "?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    feats = json.load(urllib.request.urlopen(req, timeout=120))["features"]
    if not feats: break
    out += [f["attributes"] for f in feats]; last = out[-1]["OBJECTID"]
json.dump(out, open("vdot_2024_127_29.json", "w"))
print(len(out))
