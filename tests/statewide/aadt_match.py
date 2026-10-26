"""#287 Tester first (measure only): how many State Highway System crashes 2021-2025 get a segment AADT through their
derived postmile (#248), by district and route type, with ramp crashes matched to the district ramp-volume files.

- SHS crash: run 10 (freeway step on main, coverage_crashes_r10c_*) road type freeway or state highway (off freeway).
- Point: the police GPS the coverage used (as written, DMS-read or the restored minus). Crashes CrashIQ placed by
  street names / FARS / approximate have no point in the per-crash files and are counted as "no point in this test".
- Postmile: crashiq.postmile.nearest (#248) on the SHN Postmiles Tenth layer (data/cache/postmiles, 2026-10-24),
  routes from the road names, travel direction from PrimaryRoad.
- Segment AADT (Caltrans Traffic Census xlsx for the crash's year; 2025 uses 2024): on the crash's route + suffix +
  county, the count point at or before its postmile gives its AHEAD leg; when blank, the next point's BACK leg. A
  "BREAK IN RTE" before or after, a route-county with no count points, or a postmile outside the counted range is a gap.
- Ramp crash (a ramp word in the road names): the district ramp file (2024 edition, YR_2015-YR_2024) row on the same
  route and county within RAMP_MI of the postmile, with a value for the crash's year (2025 -> 2024).

Run: python tests/statewide/aadt_match.py   (writes data/statewide/aadt_match.json, aadt_match.csv)
"""

from __future__ import annotations

import bisect
import csv
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
TC = ROOT / "data" / "cache" / "traffic_census" / "2026-10-26" / "xlsx"
PM_DB = ROOT / "data" / "cache" / "postmiles" / "shn_postmiles_tenth_2026-10-24.sqlite"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
RAMP_MI = 0.3
AADT_FILES = {2021: "2021-traffic-volumes-ca-v2-a11y.xlsx", 2022: "2022-traffic-volumes-ca-v2.xlsx",
              2023: "2023-traffic-volumes-ca-a11y.xlsx", 2024: "2024-traffic-volumes-ca-a11y.xlsx"}
INTERSTATE = {"5", "8", "10", "15", "40", "80", "105", "110", "205", "210", "215", "238", "280", "380", "405", "505",
              "580", "605", "680", "710", "780", "805", "880", "980"}
US = {"6", "50", "95", "97", "101", "199", "395"}
RAMP = re.compile(r"\b(?:ON|OFF)?[\s-]*RAMPS?\b|\bON[\s-]?RAMP\b|\bOFF[\s-]?RAMP\b|\bONR\b|\bOFR\b")


def num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def rte(v) -> str:
    return str(v or "").strip().lstrip("0")


def load_aadt():
    import openpyxl
    out = {}
    for year, fn in AADT_FILES.items():
        wb = openpyxl.load_workbook(TC / fn, read_only=True, data_only=True)
        ws = next(w for w in wb.worksheets if "AADT" in w.title.upper())
        it = ws.iter_rows(values_only=True)
        head = [str(h or "").strip().upper() for h in next(it)]
        ix = {h: i for i, h in enumerate(head)}
        g = lambda row, *names: next((row[ix[n]] for n in names if n in ix), None)       # noqa: E731
        lines = defaultdict(list)
        seen = set()
        for row in it:
            pm = num(g(row, "PM"))
            if pm is None:
                continue
            key = (rte(g(row, "RTE", "ROUTE")), str(g(row, "RTE_SFX", "ROUTE_SFX") or "").strip(),
                   str(g(row, "CNTY", "COUNTY") or "").strip())
            rec = (pm, str(g(row, "PM_PFX") or "").strip(), num(g(row, "BACK_AADT")), num(g(row, "AHEAD_AADT")),
                   str(g(row, "DESCRIPTION", "LOCATION DESCRIPTION") or ""))
            if (key, rec) in seen:
                continue
            seen.add((key, rec))
            lines[key].append(rec)
        for v in lines.values():
            v.sort(key=lambda t: (t[0], t[1]))          # by postmile (AADT legs may be blank)
        out[year] = lines
        print(f"AADT {year}: {sum(len(v) for v in lines.values())} count points on {len(lines)} route-counties",
              flush=True)
    return out


def load_ramps():
    import openpyxl
    out = defaultdict(list)                  # (route, county) -> [(pm, {year: adt}, desc)]
    for fn in sorted(TC.glob("2024-d*-ramp-adt*.xlsx")):
        wb = openpyxl.load_workbook(fn, read_only=True, data_only=True)
        ws = next(w for w in wb.worksheets if "RAMP" in w.title.upper())
        it = ws.iter_rows(values_only=True)
        head = [str(h or "").strip().upper() for h in next(it)]
        ix = {h: i for i, h in enumerate(head)}
        years = {int(h[3:]): i for h, i in ix.items() if h.startswith("YR_")}
        for row in it:
            pm = num(row[ix["POSTMILE"]])
            if pm is None:
                continue
            vals = {y: num(row[i]) for y, i in years.items() if num(row[i])}
            out[(rte(row[ix["RTE"]]), str(row[ix["CNTY"]] or "").strip())].append(
                (pm, vals, str(row[ix["LOCATION_DESC"]] or "")))
    for v in out.values():
        v.sort(key=lambda t: t[0])
    print(f"ramp rows: {sum(len(v) for v in out.values())}", flush=True)
    return out


def segment(lines, key, pm):
    pts = lines.get(key)
    if not pts:
        return None, "no count points on the route in this county"
    pms = [p[0] for p in pts]
    i = bisect.bisect_right(pms, pm) - 1
    if i < 0:
        return None, "postmile before the first count point"
    if i >= len(pts) - 1 and pm > pts[-1][0] + 0.05:
        return None, "postmile after the last count point"
    prev = pts[i]
    nxt = pts[i + 1] if i + 1 < len(pts) else None
    if "BREAK IN RTE" in prev[4].upper():
        return None, "break in route at the count point before"
    aadt = prev[3] or (nxt[2] if nxt else None)
    if not aadt:
        return None, "count point with no AADT on this leg"
    return {"aadt": aadt, "from_pm": prev[0], "to_pm": nxt[0] if nxt else None, "from": prev[4],
            "to": nxt[4] if nxt else ""}, ""


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import postmile
    from crashiq.freeway import _travel
    from crashiq.names import route_numbers

    import citywide as cw
    from citywide import dms_decode
    from run9_reconcile import parts
    r10 = parts("r10c")
    shs = {cid: r for cid, r in r10.items() if r["road_type"] in ("freeway", "state highway (off freeway)")}
    aadt, ramps = load_aadt(), load_ramps()
    pmcon = sqlite3.connect(f"file:{PM_DB}?mode=ro", uri=True)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    by_city = defaultdict(set)
    for cid, r in shs.items():
        by_city[r["city"]].add(cid)
    t = defaultdict(Counter)
    rows = []
    for city, ids in sorted(by_city.items(), key=lambda kv: -len(kv[1])):
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in ids or cid in seen:
                continue
            seen.add(cid)
            c = aliases_mod.apply(dict(c))
            r = shs[cid]
            roads = f"{c.get('primary_road') or ''} {c.get('secondary_road') or ''}"
            routes = route_numbers(roads)
            rt = ("Interstate" if routes & INTERSTATE else "US route" if routes & US else
                  "State route" if routes else "no route number")
            is_ramp = bool(RAMP.search(roads.upper()))
            keys = ["California", f"District {r['district'] or 'unknown'}", f"type {rt}",
                    f"road {r['road_type']}"] + (["ramps"] if is_ramp else [])
            o, pt = r["outcome"], None
            if o == "gps_usable":
                pt = (c["lat"], c["lon"])
            elif o == "gps_usable_dms":
                pt = (dms_decode(c["lat"]), dms_decode(c["lon"]))
            elif o == "gps_usable_sign" and c.get("_raw_ll"):
                pt = (c["_raw_ll"][0], -c["_raw_ll"][1])
            year = int(r["year"])
            res = {"collision_id": cid, "year": year, "district": r["district"], "route_type": rt,
                   "road_type": r["road_type"], "ramp": int(is_ramp), "outcome": o, "status": "", "route": "",
                   "county": "", "pm": "", "aadt": "", "aadt_year": "", "seg_from": "", "seg_to": "",
                   "ramp_adt": "", "ramp_desc": ""}
            if r["bin"] != "1":
                res["status"] = "not on the map"
            elif pt is None:
                res["status"] = "placed by CrashIQ (no point in this test)"
            elif not routes:
                res["status"] = "no route number in the road names"
            else:
                p = postmile.nearest(pmcon, pt[0], pt[1], routes, _travel(str(c.get("primary_road") or "")))
                if p is None:
                    res["status"] = "no postmile within 100 m"
                else:
                    ay = min(year, 2024)
                    key = (p["route"].lstrip("0"), p["route_suffix"] or "", p["county"])
                    seg, why = segment(aadt[ay], key, p["pm"])
                    res.update(route=p["route"], county=p["county"], pm=p["pm"], aadt_year=ay)
                    if seg is None:
                        res["status"] = why
                    else:
                        res.update(status="segment AADT", aadt=seg["aadt"], seg_from=seg["from_pm"],
                                   seg_to=seg["to_pm"] if seg["to_pm"] is not None else "")
                    if is_ramp:
                        cand = [x for x in ramps.get((key[0], key[2]), ()) if abs(x[0] - p["pm"]) <= RAMP_MI
                                and x[1].get(ay)]
                        if cand:
                            best = min(cand, key=lambda x: abs(x[0] - p["pm"]))
                            res.update(ramp_adt=best[1][ay], ramp_desc=best[2])
            for k in keys:
                s = t[k]
                s["crashes"] += 1
                s[res["status"]] += 1
                if is_ramp and res["pm"] != "":
                    s["ramp with postmile"] += 1
                    s["ramp matched to ramp ADT"] += bool(res["ramp_adt"])
            rows.append(res)
        print(f"{city or '(blank)'}: {len(seen)}", flush=True)
    with open(DATA / "aadt_match.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    out = {}
    for k, s in t.items():
        on = s["crashes"] - s["not on the map"]
        out[k] = {**dict(s), "on_map": on,
                  "segment_aadt_pct_of_on_map": round(100 * s["segment AADT"] / on, 1) if on else None}
    (DATA / "aadt_match.json").write_text(json.dumps(dict(sorted(out.items())), indent=1))
    print(json.dumps(out["California"], indent=1))
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
