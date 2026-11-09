"""Stream the FLHSMV CrashFacts zip (3.3 GB CSV, '|' delimited) without extracting; crash-level stats per year."""
import csv, io, json, sys, zipfile
from collections import Counter, defaultdict

z = zipfile.ZipFile(sys.argv[1])
name = z.namelist()[0]
f = io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace", newline="")
r = csv.reader(f, delimiter="|")
hdr = next(r)
ix = {h: i for i, h in enumerate(hdr)}
seen = set()
rows = 0
by_year = defaultdict(Counter)
sev = Counter(); psev = Counter(); form = Counter(); code = Counter(); agency = Counter(); roadsys = Counter()
county_year = Counter(); maxdt = ""
persons = Counter()
for row in r:
    rows += 1
    if len(row) != len(hdr):
        by_year["badrow"]["n"] += 1
        continue
    psev[row[ix["Person's Injury Severity"]].strip()] += 1
    k = row[0]
    if k in seen:
        continue
    seen.add(k)
    dt = row[ix["Crash Date and Time"]]
    y = dt[:4]
    maxdt = max(maxdt, dt)
    c = by_year[y]
    c["crashes"] += 1
    lat, lon = row[ix["Crash Latitude"]].strip(), row[ix["Crash Longitude"]].strip()
    try:
        la, lo = float(lat), float(lon)
        c["gps"] += 1
        if 24.3 <= la <= 31.1 and -87.7 <= lo <= -79.8:
            c["gps_fl"] += 1
    except ValueError:
        pass
    if row[ix["Crash Codeable Flag"]] == "Yes":
        c["codeable"] += 1
    sev[(y, row[ix["Crash Maximum Severity"]].strip())] += 1
    form[row[ix["Crash Form Type"]]] += 1
    agency[row[ix["Crash Investigating Agency"]]] += 1
    roadsys[row[ix["Crash Road System Identifier"]]] += 1
    county_year[(row[ix["Crash County"]], y)] += 1
out = {"rows": rows, "crashes": len(seen), "max_datetime": maxdt, "by_year": by_year,
       "max_severity": {f"{a}|{b}": n for (a, b), n in sorted(sev.items())},
       "person_severity": psev, "form": form, "agency": agency, "road_system": roadsys,
       "county_year": {f"{a}|{b}": n for (a, b), n in sorted(county_year.items())}, "header": hdr}
json.dump(out, open(sys.argv[2], "w"), indent=1, default=dict)
print("done", rows, len(seen))
