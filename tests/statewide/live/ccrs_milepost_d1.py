import json
import sqlite3
import csv
import sys
sys.path.insert(0, '.')
from ccrs_milepost_fill import sql, MIRROR  # note: importing runs the fill aggregate first
con = sqlite3.connect(MIRROR)
ids, ex = set(), []
for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl='crashes' ORDER BY year"):
    off = 0
    while True:
        rows = sql(f'SELECT "Collision Id", "NCIC Code", "IsFreeway", "PrimaryRoad", "SecondaryRoad", "SecondaryDistance", '
                   f'"SecondaryDirection", "MilepostMarker", "MilepostDistance", "MilepostDirection", "MilepostUnitOfMeasure", '
                   f'"Latitude", "Longitude" FROM "{rid}" WHERE COALESCE(CAST("MilepostMarker" AS text),\'\') <> \'\' '
                   f'ORDER BY "_id" LIMIT 10000 OFFSET {off}')
        for r in rows:
            ids.add(str(int(float(r["Collision Id"]))))
            r["year"] = year
        if len(ex) < 400:
            ex += rows[:80]
        if len(rows) < 10000:
            break
        off += 10000
    print(year, len(ids), flush=True)
d1 = {r["collision_id"] for r in csv.DictReader(open("/Users/Ak47/Desktop/Crash-tester/data/statewide/buckets.csv")) if r["bucket"] == "D1"}
print("D1 crashes:", len(d1), "with a milepost marker:", len(d1 & ids))
json.dump({"crashes_with_marker": len(ids), "d1": len(d1), "d1_with_marker": len(d1 & ids), "examples": ex},
          open("/Users/Ak47/Desktop/Crash-tester/data/statewide/ccrs_milepost_examples.json", "w"), indent=1)
