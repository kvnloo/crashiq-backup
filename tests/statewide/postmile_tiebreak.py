"""CHP postmile as the third, independent source (PM 2026-10-24; measure only). 2021-22 CHP crashes whose CCRS
MilepostMarker is a Caltrans postmile ("80 SAC M7.128": route, county, prefix + postmile; route/county taken from the
crash when the marker gives only a number) are placed on the Caltrans SHN Postmiles Tenth layer (data/cache/postmiles,
downloaded 2026-10-24): linear between the two bracketing tenth points on the carriageway of the travel direction in the
road name (both carriageways averaged when none). Two spots: the postmile alone, and the postmile moved by
MilepostDistance in MilepostDirection (postmiles grow south->north and west->east, so N/E add, S/W subtract).
Then, for crashes with police GPS:
  (a) postmile spot vs police GPS distance, both variants
  (b) our cross-street spot (freeway_report_point, GPS unused) vs GPS vs postmile: where ours and GPS disagree
      (> 400 ft), which one the postmile is nearer (and within 400 ft of); the opposite-side class separately
  (c) by agency (NCIC)

Run: python tests/statewide/postmile_tiebreak.py   (writes data/statewide/postmile_tiebreak.json, postmile_tiebreak.csv)
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
LAYER = ROOT / "data" / "cache" / "postmiles" / "shn_postmiles_tenth_2026-10-24.csv"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
AGREE_FT, MAX_GAP_MI = 400.0, 0.25
CO = ("ALA ALP AMA BUT CAL COL CC DN ED FRE GLE HUM IMP INY KER KIN LAK LAS LA MAD MRN MPA MEN MER MOD MNO MON NAP "
      "NEV ORA PLA PLU RIV SAC SBT SBD SD SF SJ SLO SM SB SCL SCR SHA SIE SIS SOL SON STA SUT TEH TRI TUL TUO VEN YOL "
      "YUB").split()                                      # CCRS county code n -> CO[n - 1] (alphabetical by name)
FULL = (re.compile(r"^\s*0*(\d{1,3})()\s*([A-Z]{2,3})\s*([A-Z]?)\s*(\d+(?:\.\d+)?)\s*([LR]?)\s*$"),
        re.compile(r"^\s*0*(\d{1,3})([A-Z])\s*([A-Z]{2,3})\s*([A-Z]?)\s*(\d+(?:\.\d+)?)\s*([LR]?)\s*$"))
ROUTE_BARE = re.compile(r"^\s*0*(\d{1,3})\s*(?:MILE\s*POST(?:\s*MARKER)?|MPM?|PM)\.?\s*([A-Z]?)\s*(\d+(?:\.\d+)?)\s*$")
BARE = re.compile(r"^\s*(?:MILE\s*POST(?:\s*MARKER)?|MPM?|PM)?\.?\s*([A-Z]?)\s*(\d+(?:\.\d+)?)\s*$")
TRAVEL = re.compile(r"\b(N|S|E|W)\s*/?\s*B\b|\b(NORTH|SOUTH|EAST|WEST)\s*BOUND\b|\b(NORTH|SOUTH|EAST|WEST)BOUND\b")


def parse(marker, county_code, roads):
    """(route, county, prefix, pm, suffix, how) or None."""
    from crashiq import names
    for pat in FULL:
        m = pat.match(marker.upper())
        if m and m.group(3) in CO:
            return m.group(1), m.group(3), m.group(4), float(m.group(5)), m.group(6), "full"
    co = CO[county_code - 1] if 1 <= county_code <= 58 else None
    m = ROUTE_BARE.match(marker.upper())
    if m and co:
        return m.group(1), co, m.group(2), float(m.group(3)), "", "route + number"
    m = BARE.match(marker.upper())
    if m:
        rt = names.ROUTE_ANY.findall(roads.upper())
        co = CO[county_code - 1] if 1 <= county_code <= 58 else None
        if len(set(rt)) == 1 and co:
            r = rt[0] if isinstance(rt[0], str) else next(x for x in rt[0] if x)
            r = re.sub(r"\D", "", r)
            return r, co, m.group(1), float(m.group(2)), "", "number only"
    return None


def travel(text):
    m = TRAVEL.search(text.upper())
    return next(g for g in m.groups() if g)[0] + "B" if m else None


class Layer:
    def __init__(self):
        self.pts = defaultdict(list)                       # (route, county, prefix, suffix, direction) -> [(pm, lat, lon)]
        with open(LAYER) as f:
            for r in csv.DictReader(f):
                if not r["lat"]:
                    continue
                k = (r["Route"].lstrip("0"), r["County"], r["PMPrefix"], r["PMSuffix"], r["Direction"])
                self.pts[k].append((float(r["PM"]), float(r["lat"]), float(r["lon"])))
        for v in self.pts.values():
            v.sort()

    def interp(self, k, pm):
        v = self.pts.get(k)
        if not v:
            return None
        i = bisect.bisect_left(v, (pm, -1e9, -1e9))
        if i < len(v) and abs(v[i][0] - pm) < 1e-6:
            return v[i][1:]
        if i == 0 or i == len(v) or v[i][0] - v[i - 1][0] > MAX_GAP_MI:
            return None
        a, b = v[i - 1], v[i]
        t = (pm - a[0]) / (b[0] - a[0])
        return a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])

    def place(self, route, county, prefix, pm, suffix, trav):
        dirs = sorted({k[4] for k in self.pts if k[:2] == (route, county)})
        prefixes = [prefix] if prefix else [""]
        if not prefix:                                     # a bare number: any prefix that brackets it
            prefixes += sorted({k[2] for k in self.pts if k[:2] == (route, county) and k[2]})
        for pf in prefixes:
            use = [d for d in dirs if d == trav] if trav in dirs else dirs
            got = [p for d in use if (p := self.interp((route, county, pf, suffix, d), pm))]
            if got:
                return (sum(p[0] for p in got) / len(got), sum(p[1] for p in got) / len(got)), pf
        return None, None


def main() -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import names

    import citywide as cw
    from freeway_report_point import DIRS, RAMP, Map, ft, report_point, walk
    layer = Layer()
    pm = {}
    with open(DATA / "ccrs_postmile_chp.csv") as f:
        for r in csv.DictReader(f):
            pm[str(int(float(r["Collision Id"])))] = r
    cov = {}
    for p in sorted(DATA.glob("coverage_crashes_r9a_*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["collision_id"] in pm:
                    cov[r["collision_id"]] = r
    by_city = defaultdict(set)
    for cid, r in cov.items():
        by_city[r["city"]].add(cid)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    m = Map()
    rows, parse_c = [], Counter()
    for city, ids in sorted(by_city.items()):
        batch, seen = [], set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid in ids and cid not in seen:
                seen.add(cid)
                batch.append(aliases_mod.apply(dict(c)))
        for c in sorted(batch, key=lambda x: int(x.get("county_code") or 0)):
            cid = str(c["crash_id"])
            r = pm[cid]
            roads = f"{c.get('primary_road') or ''} {c.get('secondary_road') or ''}"
            p = parse(r["MilepostMarker"] or "", int(c.get("county_code") or 0), roads)
            if not p:
                parse_c["not a postmile"] += 1
                continue
            parse_c[f"parsed ({p[5]})"] += 1
            trav = travel(roads)
            spot, pf = layer.place(p[0], p[1], p[2], p[3], p[4], trav)
            if not spot:
                parse_c["postmile not on the layer"] += 1
                continue
            parse_c["placed"] += 1
            mdist = float(r["MilepostDistance"] or 0) * (5280.0 if r["MilepostUnitOfMeasure"] == "M" else 1.0)
            sign = {"N": 1, "E": 1, "S": -1, "W": -1}.get(r["MilepostDirection"] or "", 0)
            spot2 = layer.place(p[0], p[1], pf, p[3] + sign * mdist / 5280.0, p[4], trav)[0] if sign and mdist else spot
            g = (c["lat"], c["lon"]) if c.get("lat") is not None else None
            row = {"collision_id": cid, "year": r["year"], "agency": c.get("agency"), "how": p[5],
                   "route": p[0], "county": p[1], "pm": f"{p[2]}{p[3]}{p[4]}", "travel": trav or "",
                   "pm_ft": "", "pm_off_ft": "", "ours_ft": "", "ours_pm_ft": "", "ours_pm_off_ft": "", "cls": "",
                   "gps_usable": int(cov[cid]["outcome"] == "gps_usable"), "road_type": cov[cid]["road_type"]}
            if g:
                row["pm_ft"] = round(ft(spot, g))
                row["pm_off_ft"] = round(ft(spot2, g)) if spot2 else ""
            p_, s_ = (c.get("primary_road") or "").upper(), (c.get("secondary_road") or "").upper()
            rp_, rs_ = names.ROUTE_ANY.findall(p_), names.ROUTE_ANY.findall(s_)
            kind = "ramp" if RAMP.search(f"{p_} {s_}") else "f2f" if rp_ and rs_ else "mainline" if rp_ or rs_ else ""
            q = {**c, "lat": None, "lon": None}
            ours = report_point(m, q, kind).get("point") if kind else None
            if ours:
                row["ours_pm_ft"] = round(ft(ours, spot))
                if spot2:
                    row["ours_pm_off_ft"] = round(ft(ours, spot2))
                if g:
                    row["ours_ft"] = round(ft(ours, g))
                    d = str(c.get("offset_dir") or "").strip()[:1].upper()
                    off = c.get("offset_ft") or 0.0
                    if kind == "mainline" and off and d in DIRS and row["ours_ft"] > AGREE_FT:
                        cross = report_point(m, {**q, "offset_ft": 0}, kind).get("point")
                        rw = m.route(int(c.get("county_code") or 0),
                                     frozenset(set(names.ROUTE_ANY.findall(p_)) or set(names.ROUTE_ANY.findall(s_))))
                        if cross and rw:
                            mir = walk(rw, min((z for w in rw for z in w[5]), key=lambda z: ft(z, cross)),
                                           (DIRS[d] + 180) % 360, off)
                            if mir and ft(g, mir) < row["ours_ft"]:
                                row["cls"] = "opposite side"
            rows.append(row)
        print(f"{city or '(blank)'}: {len(batch)}", flush=True)
    with open(DATA / "postmile_tiebreak.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summarize(rows, parse_c, len(pm), len(cov))


def summarize(rows, parse_c, pulled, in_mirror) -> None:
    from bin2_whatif import wilson_low

    def dist(v):
        v = sorted(v)
        if not v:
            return {}
        return {"n": len(v), "median_ft": v[len(v) // 2], "within_250ft": sum(x <= 250 for x in v),
                "within_400ft": sum(x <= 400 for x in v), "pct_within_400ft": round(100 * sum(x <= 400 for x in v) / len(v), 1),
                "low_400ft": wilson_low(sum(x <= 400 for x in v), len(v)), "over_1mi": sum(x > 5280 for x in v)}
    a = {var: {sub: dist([int(r[col]) for r in rows if r[col] != "" and (sub == "all GPS" or r["gps_usable"] == 1)])
               for sub in ("all GPS", "gps_usable")} for var, col in (("postmile alone", "pm_ft"),
                                                                       ("postmile + milepost distance", "pm_off_ft"))}
    best = max(("pm_ft", "pm_off_ft"), key=lambda col: sum(1 for r in rows if r[col] != "" and int(r[col]) <= 400))

    def tie(sel):
        c = Counter()
        for r in sel:
            if r["ours_ft"] == "" or r[best] == "" or int(r["ours_ft"]) <= AGREE_FT:
                continue
            c["disagree"] += 1
            po = int(r["ours_pm_ft"] if best == "pm_ft" else r["ours_pm_off_ft"] or 1e9)
            pg = int(r[best])
            if pg <= AGREE_FT and po > AGREE_FT:
                c["postmile sides with GPS"] += 1
            elif po <= AGREE_FT and pg > AGREE_FT:
                c["postmile sides with ours"] += 1
            elif po <= AGREE_FT and pg <= AGREE_FT:
                c["postmile near both"] += 1
            else:
                c["postmile near neither"] += 1
        return dict(c)
    agree = Counter()
    for r in rows:
        if r["ours_ft"] != "" and r[best] != "" and int(r["ours_ft"]) <= AGREE_FT:
            agree["ours and GPS agree"] += 1
            agree["postmile also within 400 ft of GPS"] += int(r[best]) <= AGREE_FT
    ag = Counter(r["agency"] for r in rows if r["ours_ft"] != "" and int(r["ours_ft"]) > AGREE_FT)
    res = {"source": "CCRS live 2021-22, NCIC 9xxx, MilepostMarker non-blank; Caltrans SHN Postmiles Tenth 2026-10-24",
           "pulled": pulled, "in_run9a": in_mirror, "parse": dict(parse_c), "a_postmile_vs_gps": a,
           "b_basis": best, "b_when_ours_and_gps_agree": dict(agree),
           "b_disagree_all": tie(rows), "b_disagree_opposite_side": tie([r for r in rows if r["cls"] == "opposite side"]),
           "c_by_agency": {k: {"disagree": tie([r for r in rows if r["agency"] == k]),
                               "opposite_side": tie([r for r in rows if r["agency"] == k and r["cls"] == "opposite side"]),
                               "postmile_vs_gps": dist([int(r[best]) for r in rows if r["agency"] == k and r[best] != ""])}
                           for k, _ in ag.most_common(12)}}
    (DATA / "postmile_tiebreak.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
