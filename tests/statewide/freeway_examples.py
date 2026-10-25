"""D1 (freeway / ramp reference) examples for the user's walk-through (PM 2026-10-23): 15 difficult crashes from run
9A, 5 of each kind, seeded and spread over districts:
  mainline   a freeway / route named with a local cross street and a stated offset ("I-5 N/B & MAIN ST, 500 ft N")
  ramp       a ramp named ("SR-91 E/B OFF RAMP TO MAIN ST")
  f2f        two freeways / routes ("I-405 & I-605")
For each: the report's fields (CCRS mirror), what the OSM extract has nearby (the freeway's motorway ways by route
number, where the cross street or the other freeway comes closest to it: the crossing structure / interchange, the
motorway_link ends within RAMP_M of it), where the stated offset would put the crash, any police GPS and its distance
from that point, and an OpenStreetMap link. Nothing here is a placement rule: it shows the evidence a rule would use.

Run: python tests/statewide/freeway_examples.py   (writes data/statewide/freeway_examples.json and .md)
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
RAMP = re.compile(r"\b(RAMP|ONRAMP|OFFRAMP|CONNECTOR|TRANSITION)\b")
FWY = re.compile(r"\b(FREEWAY|FWY|EXPRESSWAY)\b")
SEARCH_KM, RAMP_M, SEED, MAX_GAP_FT = 6.0, 400.0, 2301, 1000.0
DIRS = {"N": 0, "E": 90, "S": 180, "W": 270}


def ft(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 364000, (a[1] - b[1]) * 364000 * math.cos(math.radians(a[0])))


def move(p, bearing_deg, dist_ft):
    d = dist_ft / 364000.0
    return (p[0] + d * math.cos(math.radians(bearing_deg)),
            p[1] + d * math.sin(math.radians(bearing_deg)) / math.cos(math.radians(p[0])))


def main() -> None:
    from crashiq import names
    db = sqlite3.connect(ROOT / "data" / "osm" / "ca_osm.sqlite")
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    with open(DATA / "buckets.csv") as f:
        d1 = {r["collision_id"]: r for r in csv.DictReader(f) if r["bucket"] == "D1"}
    rec = {}
    cols = ["Collision Id", "Report Version", "PrimaryRoad", "SecondaryRoad", "SecondaryDistance", "SecondaryDirection",
            "SecondaryUnitOfMeasure", "Latitude", "Longitude", "City Name", "County Code", "Crash Date Time",
            "NCIC Code", "NumberKilled", "NumberInjured", "IsFreeway"]
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes'").fetchall():
        q = f'SELECT {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{rid}"'
        for row in con.execute(q):
            r = dict(zip(cols, row))
            if r["Collision Id"] is None:
                continue
            cid = str(int(r["Collision Id"]))
            if cid in d1 and (cid not in rec or (r["Report Version"] or 0) > (rec[cid]["Report Version"] or 0)):
                rec[cid] = r
    kinds = defaultdict(list)
    for cid, r in rec.items():
        p, s = (r["PrimaryRoad"] or "").upper(), (r["SecondaryRoad"] or "").upper()
        rp, rs = names.ROUTE_ANY.findall(p) or FWY.search(p), names.ROUTE_ANY.findall(s) or FWY.search(s)
        try:
            off = float(r["SecondaryDistance"] or 0)
        except ValueError:
            off = 0
        if RAMP.search(f"{p} {s}"):
            kinds["ramp"].append(cid)
        elif rp and rs:
            kinds["f2f"].append(cid)
        elif (rp or rs) and off > 0 and str(r["SecondaryDirection"] or "").strip()[:1] in DIRS:
            kinds["mainline"].append(cid)
    rng = random.Random(SEED)
    out = []
    for kind in ("mainline", "ramp", "f2f"):
        pool = sorted(kinds[kind], key=int)
        rng.shuffle(pool)
        picked, used_d = [], set()
        for want_gps in (True, False):                   # prefer crashes with police GPS, then others; spread districts
            for cid in pool:
                if len(picked) >= 5:
                    break
                r = rec[cid]
                has = isinstance(r["Latitude"], (int, float))
                if has != want_gps or cid in picked or d1[cid]["district"] in used_d and len(used_d) < 5:
                    continue
                picked.append(cid)
                used_d.add(d1[cid]["district"])
        for cid in picked:
            out.append(describe(db, names, kind, rec[cid], d1[cid]))
    (DATA / "freeway_examples.json").write_text(json.dumps({"counts": {k: len(v) for k, v in kinds.items()},
                                                             "examples": out}, indent=1, default=str))
    md = ["# Freeway / ramp crashes (D1): 15 examples for the walk-through", "",
          f"D1 in run 9A: {len(d1):,} difficult crashes. Of those with readable names: mainline + cross street + offset "
          f"{len(kinds['mainline']):,}; ramp {len(kinds['ramp']):,}; freeway-to-freeway {len(kinds['f2f']):,}.", ""]
    for i, e in enumerate(out, 1):
        md += [f"## {i}. {e['kind']}: {e['primary']} & {e['secondary']}", "",
               f"- Crash {e['collision_id']}, {e['city']} (district {e['district']}), {e['when']}; killed {e['killed']}, "
               f"injured {e['injured']}; CCRS IsFreeway {e['is_freeway']}",
               f"- Stated: {e['offset']}",
               f"- Map: {e['map']}",
               f"- Police GPS: {e['gps']}",
               f"- Look: {e['link']}", ""]
    (DATA / "freeway_examples.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:8]))


def map_text(mp: dict, f2f: bool, est, off_ft: float) -> str:
    other = "the other freeway" if f2f else "the cross street"
    if not mp:
        return "the freeway by its route number or the cross street wasn't found near this city"
    if mp.get("far"):
        return f"no crossing nearby: the freeway and {other} come no closer than {mp['far']:,} ft near this city"
    t = (f"freeway and {other} come within {mp['gap_ft']} ft at {mp['crossing'][0]}, {mp['crossing'][1]} (the crossing /"
         f" interchange); ramp ends within {RAMP_M:.0f} m: {', '.join(mp['ramp_ends_ft']) or 'none'}")
    if est and off_ft:
        t += f"; the stated offset (compass direction) puts the crash at {est[0]:.6f}, {est[1]:.6f}"
    return t


def typo(gps, est) -> str:
    """A police GPS point that looks mistyped: latitude or longitude off by a whole number of degrees, or a lost minus."""
    if not est:
        return ""
    out = []
    if gps[1] > 0:
        out.append("longitude has no minus sign")
    for i, nm in ((0, "latitude"), (1, "longitude")):
        d = abs(abs(gps[i]) - abs(est[i]))
        if d >= 0.9 and abs(d - round(d)) < 0.02:
            out.append(f"{nm} off by {round(d)} degree{'s' if round(d) > 1 else ''} (a mistyped digit?)")
    return f"; looks mistyped: {', '.join(out)}" if out else ""


def describe(db, names, kind, r, b) -> dict:
    p, s = (r["PrimaryRoad"] or "").upper(), (r["SecondaryRoad"] or "").upper()
    county = int(r["County Code"] or 0)
    city = r["City Name"] or ""
    area = db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '8' AND name = ? "
                      "ORDER BY (maxlat - minlat) LIMIT 1", (city,)).fetchone()
    if not area:
        with open(ROOT / "data" / "reference" / "caltrans_districts.csv") as f:
            cn = {int(x["ccrs_county_code"]): x["county"] for x in csv.DictReader(f)}
        area = db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                          (f"{cn.get(county, '')} County",)).fetchone()
    pad = SEARCH_KM / 111
    bx = (area[0] - pad, area[1] - pad * 1.25, area[2] + pad, area[3] + pad * 1.25) if area else None
    nums_p, nums_s = set(names.ROUTE_ANY.findall(p)), set(names.ROUTE_ANY.findall(s))
    ks = names.street_key(s) if not nums_s else None
    kp = names.street_key(p) if not nums_p else None
    fwy, other, links = [], [], []
    if bx:
        for hw, name, tags, coords in db.execute(
                "SELECT w.highway, w.name, w.tags, w.coords FROM way_box x JOIN ways w ON w.id = x.id WHERE "
                "x.maxlat >= ? AND x.minlat <= ? AND x.maxlon >= ? AND x.minlon <= ?", (bx[0], bx[2], bx[1], bx[3])):
            t = json.loads(tags)
            refs = set(re.findall(r"\d+", str(t.get("ref") or "")))
            cs = json.loads(coords)
            if hw == "motorway_link":
                links.append((t.get("name") or t.get("destination") or t.get("ref") or "ramp", cs[0], cs[-1]))
                continue
            for nums, store in ((nums_p, "p"), (nums_s, "s")):
                if nums and refs & nums and hw in ("motorway", "trunk", "primary"):
                    fwy.append((store, t.get("ref"), cs))
            for k in (kp, ks):
                if k and name and names.street_key(name) and names.same_core(k, names.street_key(name)):
                    other.append((name, cs))
    main_ = [c for st, _, c in fwy if st == ("p" if nums_p else "s")]
    second = [c for st, _, c in fwy if st == ("s" if nums_p else "p")] if nums_p and nums_s else [c for _, c in other]
    best = None
    for a in main_:
        for q in a:
            for bline in second:
                for z in bline:
                    d = ft(q, z)
                    if best is None or d < best[0]:
                        best = (d, q)
    mp = {}
    if best and best[0] > MAX_GAP_FT:
        mp = {"far": round(best[0])}
        best = None
    if best:
        x = best[1]
        ramps = sorted({(round(min(ft(x, e0), ft(x, e1))), n) for n, e0, e1 in links
                        if min(ft(x, e0), ft(x, e1)) <= RAMP_M / 0.3048})[:4]
        mp = {"crossing": [round(x[0], 6), round(x[1], 6)], "gap_ft": round(best[0]),
              "ramp_ends_ft": [f"{n} ({d} ft)" for d, n in ramps]}
    try:
        off = float(r["SecondaryDistance"] or 0)
    except ValueError:
        off = 0.0
    unit = str(r["SecondaryUnitOfMeasure"] or "").upper()
    off_ft = off * 5280 if unit.startswith("M") and off < 50 else off
    dr = str(r["SecondaryDirection"] or "").strip()[:1]
    cx = tuple(mp["crossing"]) if mp.get("crossing") else None
    est = move(cx, DIRS[dr], off_ft) if cx and dr in DIRS and off_ft else cx
    gps = (r["Latitude"], r["Longitude"]) if isinstance(r["Latitude"], (int, float)) else None
    where = est or gps
    return {"kind": kind, "collision_id": str(int(r["Collision Id"])), "primary": r["PrimaryRoad"],
            "secondary": r["SecondaryRoad"], "city": city, "district": b["district"], "when": r["Crash Date Time"],
            "killed": r["NumberKilled"], "injured": r["NumberInjured"], "is_freeway": r["IsFreeway"],
            "offset": f"{r['SecondaryDistance']} {r['SecondaryUnitOfMeasure'] or ''} {r['SecondaryDirection'] or ''}".strip(),
            "map": map_text(mp, nums_p and nums_s, est, off_ft),
            "gps": (f"{gps[0]}, {gps[1]}" + (f" ({ft(gps, est):,.0f} ft from that point)" if est else "")
                    + typo(gps, est)) if gps else "none",
            "link": (f"https://www.openstreetmap.org/?mlat={where[0]:.6f}&mlon={where[1]:.6f}#map=17/{where[0]:.6f}/"
                     f"{where[1]:.6f}") if where else ""}


if __name__ == "__main__":
    main()
