"""Scan one MS DPS eCrash yearly workbook: column values, shares and timings (Hermes, 2026-11-08).
Run: ~/Desktop/Crash/.venv/bin/python scan.py ms2024.xlsx > scan2024.json"""
import json
import sys
import time
from collections import Counter

import openpyxl

t0 = time.time()
wb = openpyxl.load_workbook(sys.argv[1], read_only=True)
out = {}
ws = wb["Crashes"]
it = ws.iter_rows(values_only=True)
h = next(it)
ix = {k: i for i, k in enumerate(h)}
cnt = {k: Counter() for k in ("County", "Road Classification", "Light Condition", "Weather", "Is Intersection?",
                              "Junction Location", "Intersection Traffic Control", "City")}
n = gps = st = cross = addr = mp = road = 0
for r in it:
    n += 1
    la, lo = r[ix["Latitude"]], r[ix["Longitude"]]
    gps += isinstance(la, (int, float)) and isinstance(lo, (int, float)) and 30.0 <= la <= 35.1 and -91.8 <= lo <= -88.0
    s = (r[ix["Street Name"]] or "").strip()
    st += bool(s)
    cross += bool(s and (r[ix["Intersecting Street Name"]] or "").strip())
    addr += bool((r[ix["Address Number"]] or "").strip())
    mp += r[ix["Milepost Number"]] not in (None, "")
    road += bool((r[ix["Road Number"]] or "").strip())
    for k, c in cnt.items():
        c[r[ix[k]]] += 1
out["crashes"] = {"n": n, "gps": gps, "street": st, "street_and_cross": cross, "address_number": addr, "milepost": mp,
                  "road_number": road, "seconds": round(time.time() - t0)}
out["crash_values"] = {k: c.most_common(40) for k, c in cnt.items()}
for sheet, col in (("Drivers", "Injury Status"), ("Passengers", "Injury Status"), ("Non-Motorists", "Injury Status"),
                   ("Non-Motorists", "Non-Motorist Type")):
    t1 = time.time()
    it = wb[sheet].iter_rows(values_only=True)
    h = next(it)
    c = Counter(r[h.index(col)] for r in it)
    out[f"{sheet}:{col}"] = {"values": c.most_common(20), "rows": sum(c.values()), "seconds": round(time.time() - t1)}
print(json.dumps(out, indent=1, default=str))
