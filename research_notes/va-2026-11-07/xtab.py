# Code -> text for VDOT coded fields, by joining VDOT 2024 rows to the DMV datathon rows (same TREDS crashes) on
# date + time + jurisdiction + rounded lat/lon. Code computes the map; a code is kept only when one text dominates.
import csv, json, collections, datetime
J = {"127": "Richmond City", "29": "Fairfax County"}
v = json.load(open("vdot_2024_127_29.json"))
def key(d, t, la, lo, j): return (d, int(t), round(la, 3), round(lo, 3), j)
idx = collections.defaultdict(list)
for a in v:
    if a["LAT"] is None: continue
    d = datetime.datetime.fromtimestamp(a["CRASH_DT"] / 1000, datetime.UTC).strftime("%m/%d/%Y")
    idx[key(d, a["CRASH_MILITARY_TM"] or 0, a["LAT"], a["LON"], J[a["PHYSICAL_JURIS"]])].append(a)
pairs = {"COLLISION_TYPE": "TypeOfCollision", "WEATHER_CONDITION": "WeatherCondition", "LIGHT_CONDITION": "LightCondition_Value",
         "ROADWAY_SURFACE_COND": "RoadwaySurfaceCondition", "INTERSECTION_TYPE": "IntersectionType",
         "RELATION_TO_ROADWAY": "RelationToRoadway_Value", "TRAFFIC_CONTROL_TYPE": "TrafficControlType", "FUN": "FunctionalClassCode"}
xt = {k: collections.defaultdict(collections.Counter) for k in pairs}
n = m = 0
for r in csv.DictReader(open("dmv_keep.csv")):
    if r["Year"] != "2024": continue
    n += 1
    t = r["CrashTime"].split(":"); 
    hits = idx.get(key(r["CrashDate"], int(t[0]) * 100 + int(t[1]), float(r["Latitude"]), float(r["Longitude"]), r["Jurisdiction"]))
    if not hits or len(hits) != 1: continue
    m += 1
    for c, tcol in pairs.items(): xt[c][str(hits[0][c])][r[tcol]] += 1
res = {"datathon_rows": n, "joined": m, "maps": {}}
for c, d in xt.items():
    res["maps"][c] = {code: [cnt.most_common(1)[0][0], round(cnt.most_common(1)[0][1] / sum(cnt.values()), 3), sum(cnt.values())]
                      for code, cnt in sorted(d.items(), key=lambda kv: (len(kv[0]), kv[0]))}
json.dump(res, open("code_maps.json", "w"), indent=1)
print(n, m)
for c, mp in res["maps"].items(): print(c, mp)
