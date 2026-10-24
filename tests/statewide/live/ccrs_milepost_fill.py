"""Fill rates of CCRS crash fields the mirror doesn't keep (live datastore, aggregate SQL only)."""
import json, sqlite3, time, urllib.parse, urllib.request
MIRROR = "/Users/Ak47/Desktop/Crash-tester/data/statewide/ccrs_mirror.sqlite"
FIELDS = ["MilepostMarker", "MilepostDistance", "MilepostDirection", "MilepostUnitOfMeasure", "IsLocationReferToNarrative"]
def sql(q):
    url = "https://data.ca.gov/api/3/action/datastore_search_sql?" + urllib.parse.urlencode({"sql": q})
    req = urllib.request.Request(url, headers={"User-Agent": "CrashIQ-Tester/0.1"})
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)["result"]["records"]
        except Exception as e:
            time.sleep(5 * (a + 1)); err = e
    raise err
con = sqlite3.connect(MIRROR)
out = {}
for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl='crashes' ORDER BY year"):
    nb = ", ".join(f"SUM(CASE WHEN COALESCE(CAST(\"{f}\" AS text),'') NOT IN ('', 'false', 'False') THEN 1 ELSE 0 END) AS \"{f}\"" for f in FIELDS)
    q = (f"SELECT CASE WHEN \"NCIC Code\" LIKE '9%' THEN 'CHP' ELSE 'other' END AS ag, "
         f"COALESCE(CAST(\"IsFreeway\" AS text),'') AS fwy, COUNT(*) AS n, {nb} FROM \"{rid}\" "
         f"WHERE COALESCE(CAST(\"IsDeleted\" AS text),'') <> 'True' GROUP BY 1, 2")
    out[year] = sql(q)
    print(year, json.dumps(out[year]), flush=True)
json.dump(out, open("/Users/Ak47/Desktop/Crash-tester/data/statewide/ccrs_milepost_fill.json", "w"), indent=1)
