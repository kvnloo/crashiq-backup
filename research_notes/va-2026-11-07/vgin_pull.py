# VGIN statewide address points (CC0) for one county FIPS, paged by OBJECTID -> csv street,num,lat,lon
import csv, json, sys, urllib.parse, urllib.request
A = "https://vginmaps.vdem.virginia.gov/arcgis/rest/services/VA_Base_Layers/VA_Address_Points/FeatureServer/0/query"
fips = sys.argv[1]; w = csv.writer(open(f"vgin_{fips}.csv", "w", newline="")); last = n = 0
while True:
    q = {"where": f"FIPS='{fips}' AND OBJECTID>{last}", "outFields": "OBJECTID,FULLNAME,ADDRNUM,LAT,LONG",
         "orderByFields": "OBJECTID", "resultRecordCount": 2000, "returnGeometry": "false", "f": "json"}
    req = urllib.request.Request(A + "?" + urllib.parse.urlencode(q), headers={"User-Agent": "CrashIQ/0.1"})
    f = json.load(urllib.request.urlopen(req, timeout=120))["features"]
    if not f: break
    for x in f:
        a = x["attributes"]; w.writerow([a["FULLNAME"], a["ADDRNUM"], a["LAT"], a["LONG"]])
    n += len(f); last = f[-1]["attributes"]["OBJECTID"]
print(fips, n)
