# Stream the DMV datathon crash table once: per-year counts, GPS / street-name shares; keep Richmond City + Fairfax County rows.
import csv, io, json, sys, urllib.request, collections
URL = "https://data.virginia.gov/dataset/228bccd9-5212-46fa-8d5e-d5840b80cc9d/resource/af75bb2f-bcc9-48d0-8b51-76af391a2980/download/1-crash_table-5.csv"
st = collections.defaultdict(collections.Counter)
vals = collections.defaultdict(collections.Counter)
keep = open("dmv_keep.csv", "w", newline="")
w = None
if True:
    for row in csv.DictReader(io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig", newline="")):
        y = row["Year"]; s = st[y]; s["n"] += 1
        try:
            la, lo = float(row["Latitude"]), float(row["Longitude"])
            if 36.5 <= la <= 39.5 and -83.7 <= lo <= -75.2: s["gps"] += 1
        except ValueError: pass
        if row["RoadName"].strip() or row["RouteName"].strip(): s["road"] += 1
        if row["SecondaryLocation"].strip(): s["sec"] += 1
        if (row["RoadName"].strip() or row["RouteName"].strip()) and row["SecondaryLocation"].strip(): s["pair"] += 1
        for k in ("CrashType", "AtIntersection", "Jurisdiction", "LocationTypeName"):
            vals[k][row[k]] += 1
        if row["Jurisdiction"] in ("Richmond City", "Fairfax County"):
            if w is None:
                w = csv.DictWriter(keep, fieldnames=list(row)); w.writeheader()
            w.writerow(row)
keep.close()
json.dump({"per_year": st, "values": {k: dict(v.most_common(40)) for k, v in vals.items()}}, open("dmv_scan.json", "w"), indent=1)
print(json.dumps(st, indent=0))
