"""Cut a small FLHSMV Crash Facts fixture: every row of ~110 Palm Beach 2025 crashes (incl. fatal and blank-severity)."""
import csv, io, sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
f = io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8", errors="replace", newline="")
r = csv.reader(f, delimiter="|")
hdr = next(r); ix = {h: i for i, h in enumerate(hdr)}
keys, fatal, blank, nogps, rows = set(), set(), set(), set(), []
for row in r:
    if len(row) != len(hdr) or row[ix["Crash County"]] != "PALM BEACH" or not row[ix["Crash Date and Time"]].startswith("2025"):
        continue
    k, sev = row[0], row[ix["Crash Maximum Severity"]].strip()
    if k not in keys:
        if len(keys) < 90 or (sev.startswith("Fatal") and len(fatal) < 6) or (sev == "" and len(blank) < 6) \
                or (not row[ix["Crash Latitude"]].strip() and len(nogps) < 8):
            keys.add(k)
            if sev.startswith("Fatal"): fatal.add(k)
            if sev == "": blank.add(k)
            if not row[ix["Crash Latitude"]].strip(): nogps.add(k)
    if k in keys:
        rows.append(row)
with open(sys.argv[2], "w", newline="") as o:
    w = csv.writer(o, delimiter="|", lineterminator="\r\n")
    w.writerow(hdr); w.writerows(rows)
print(len(keys), len(rows), len(fatal), len(blank), len(nogps))
