"""CHP 2021-22 crashes with a non-blank MilepostMarker, from the live CCRS datastore (public)."""
import csv
import json
import sqlite3
import time
import urllib.parse
import urllib.request
MIRROR = "/Users/Ak47/Desktop/Crash-tester/data/statewide/ccrs_mirror.sqlite"
OUT = "/Users/Ak47/Desktop/Crash-tester/data/statewide/ccrs_postmile_chp.csv"
COLS = ["Collision Id", "NCIC Code", "IsFreeway", "PrimaryRoad", "SecondaryRoad", "SecondaryDistance", "SecondaryDirection",
        "SecondaryUnitOfMeasure", "MilepostMarker", "MilepostDistance", "MilepostDirection", "MilepostUnitOfMeasure",
        "Latitude", "Longitude"]
def sql(q):
    url = "https://data.ca.gov/api/3/action/datastore_search_sql?" + urllib.parse.urlencode({"sql": q})
    req = urllib.request.Request(url, headers={"User-Agent": "CrashIQ-Tester/0.1"})
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)["result"]["records"]
        except Exception as e:
            time.sleep(5 * (a + 1))
            err = e
    raise err
con = sqlite3.connect(MIRROR)
w = csv.writer(open(OUT, "w", newline=""))
w.writerow(["year"] + COLS)
for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl='crashes' AND year IN (2021, 2022) ORDER BY year"):
    off = 0
    while True:
        rows = sql("SELECT " + ", ".join(f'"{c}"' for c in COLS) + f' FROM "{rid}" WHERE "NCIC Code" LIKE \'9%\' AND '
                   "COALESCE(CAST(\"MilepostMarker\" AS text),'') <> '' AND COALESCE(CAST(\"IsDeleted\" AS text),'') <> 'True' "
                   f'ORDER BY "_id" LIMIT 10000 OFFSET {off}')
        for r in rows:
            w.writerow([year] + [r.get(c) for c in COLS])
        if len(rows) < 10000:
            break
        off += 10000
    print(year, flush=True)
