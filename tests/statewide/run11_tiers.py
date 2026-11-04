"""Run 11 (#387; measure only): the two switched-off tiers that run outside the street locator, statewide.

  postmile (#319)                 a report giving a mile marker: mile_marker.place on the Caltrans postmile layer
  crossing_rail / crossing_path   a report naming a railway or a named trail / path: crossings.place where the
  (#318)                          named street crosses it (features from crossing_features.py)

The app runs them on a corridor; statewide there is none, so the "corridor" is the report's other road:
  - postmile: the route the other field names by number (mile_marker.routes with no corridor route). A road named
    without its route number ("ANGELES CREST HWY") gets no spot here, where the app would use the corridor's route;
  - crossing: every OSM way named like the other field (FwyRaw's name index: name, alt_name, ref, with and without a
    leading direction word) in the crash's city box + 1 km, else its county. Each way is a line for crossings.place;
    crossings of all of them within ONE_CROSSING_FT are one. Two or more = review, as in the app. A city-wide street
    crosses more often than a drawn study stretch, so this is stricter than the app (fewer spots, never a guess).
For every crash whose road fields give a mile marker / a crossing feature (aliases applied, as coverage.py):
  gained    run 11 has it in bin 2 (coverage_crashes_r11_*.csv) and the tier finds a spot; split by no usable GPS (what
            the app's tier reaches: crashes.pull routes only no-GPS reports to it) and GPS off its roads
  accuracy  run 11 has its police GPS as fitting the report (gps_usable): hide it, place, distance to the GPS;
            within 250 ft (the exact tier's point bound), 400 ft (GPS-check distance), 0.5 mi (approximate tier).
            Self-consistent truth only, as the exact tier's: for a crossing the GPS also lies within 400 ft of a
            railway / the named path (fitting GPS is only near the named street, anywhere along it); for postmile,
            fitting GPS is on the named route already
Writes data/statewide/run11_tiers.json and run11_tiers_rows.csv.

Run: python tests/statewide/run11_tiers.py [--base r10d] [--sf38]
"""

from __future__ import annotations

import csv
import json
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
BANDS = (250, 400, 2640)
LIKE = ("MILE", "MM", "M/M", "PM", "P/M", "MP", "RAIL", "RR", "R/R", "BNSF", "AMTRAK", "METROLINK", "TRACK", "TRAIL",
        "TRL", "PATH", "BIKE", "GREENWAY", "CYCLE")


def ft(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 364000, (a[1] - b[1]) * 364000 * math.cos(math.radians(a[0])))


def wilson_low(k: int, n: int, z: float = 1.96) -> float | None:
    if not n:
        return None
    p = k / n
    return round(100 * (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n), 1)


SAMPLE = "--sf38" in sys.argv          # the San Francisco sample run (coverage.py --counties 38 --part r11sample_sf38)
BASE = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "r11sample" if SAMPLE else "r11"   # r10d: run 10's bins


def run11_outcomes(want: set[str]) -> tuple[dict[str, dict], int]:
    """The run's rows for these crashes only (2 million full rows don't fit in memory here), and its crash count."""
    out, total = {}, 0
    for p in sorted(DATA.glob(f"coverage_crashes_{BASE}_*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                total += 1
                if r["collision_id"] in want:
                    out[r["collision_id"]] = r
    return out, total


def candidates(con):
    """Mirror rows (as coverage.py reads them) whose road fields may give a mile marker or a crossing feature."""
    import citywide as cw
    from crashiq import crossings, mile_marker
    from crashiq.sources import ca_ccrs as cc
    where = " OR ".join(f'UPPER(COALESCE("{f}", \'\')) LIKE \'%{w}%\'' for f in ("PrimaryRoad", "SecondaryRoad")
                        for w in LIKE)
    for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'").fetchall():
        if year not in cw.YEARS:
            continue
        fields = [{"id": r[1], "type": "text"} for r in con.execute(f'PRAGMA table_info("{rid}")')]
        cols, _ = cc.resolve_columns(fields, cc.CRASH_COLS)
        cur = con.execute(f'SELECT * FROM "{rid}" WHERE ({where}) AND COALESCE("IsDeleted", \'\') <> \'True\'')
        names = [d[0] for d in cur.description]
        for row in cur:
            c = cc.crash_record(dict(zip(names, row)), cols)
            if mile_marker._fields(c) or any(crossings.read(c.get(f)) for f in ("primary_road", "secondary_road")):
                c["year"] = year
                yield c


class Crossing:
    def __init__(self, local, county_box, bounds):
        from coverage import Outside
        from fwy_raw import FwyRaw
        self.local, self.bounds = local, bounds
        self.fr = FwyRaw(local, county_box, Outside(local, county_box))
        self.feat = sqlite3.connect(f"file:{DATA / 'crossing_features.sqlite'}?mode=ro", uri=True)
        self.box_memo = {}

    def city_box(self, city):
        import corridors
        if city not in self.box_memo:
            b = self.bounds.get(corridors.norm_city(city)) if city else None
            row = self.local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE id = ? ORDER BY "
                                        "CAST(admin_level AS INT) DESC LIMIT 1", (b["rel"],)).fetchone() if b else None
            if row:
                d = 1.0 / 111.32
                dl = d / max(0.2, math.cos(math.radians((row[0] + row[2]) / 2)))
                row = (row[0] - d, row[1] - dl, row[2] + d, row[3] + dl)
            self.box_memo[city] = row
        return self.box_memo[city]

    def near_feature(self, c: dict, pt: tuple[float, float], tol_ft: float = 400.0) -> bool:
        """The police GPS lies within tol_ft of a railway / the named path the report gives: self-consistent truth,
        as the exact tier's (GPS near the meeting point of the two named roads)."""
        import citywide as cw
        from crashiq import crossings
        want = next((f for f in (crossings.read(c.get(x)) for x in ("primary_road", "secondary_road")) if f), None)
        d = tol_ft / 364000 * 1.5
        els, nodes = [], {}
        for wid, tags, nids, cs in self.feat.execute(
                "SELECT w.id, w.tags, w.nodes, w.coords FROM way_box b JOIN ways w ON w.id = b.id WHERE b.maxlat >= ? "
                "AND b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ?", (pt[0] - d, pt[0] + d, pt[1] - d, pt[1] + d)):
            nl = json.loads(nids)
            els.append({"type": "way", "id": wid, "nodes": nl, "tags": json.loads(tags)})
            for n, q in zip(nl, json.loads(cs)):
                nodes[n] = {"type": "node", "id": n, "lat": q[0], "lon": q[1]}
        paths = crossings.features({"elements": els + list(nodes.values())}, want) if want and els else []
        return any(cw._seg_ft(pt, a, b) <= tol_ft for q in paths for a, b in zip(q, q[1:]))

    def place(self, c: dict) -> dict:
        from crashiq import crossings
        from crashiq.geo import Polyline
        from crashiq.names import route_numbers, street_key
        fields = [f for f in ("primary_road", "secondary_road") if crossings.read(c.get(f))]
        if len(fields) != 1:
            return {"why": "no railway or path" if not fields else "both fields are features"}
        street = c.get("secondary_road" if fields[0] == "primary_road" else "primary_road")
        county = int(c.get("county_code") or 0)
        keys = self.fr.keys(street or "")
        if not keys or county not in self.fr.box:
            return {"why": "no street named"}
        cty = self.fr._county(county)
        ids = set().union(*(cty["named"].get(k, set()) for k in keys))
        ids |= {w["id"] for rt in route_numbers(street) for w in cty["lanes"].get(rt, ())}   # a freeway: its lanes
        box = self.city_box(c.get("city"))
        lines = []
        if ids:
            for (cs,) in self.local.db.execute(f"SELECT coords FROM ways WHERE id IN ({','.join('?' * len(ids))})",
                                               list(ids)):
                cl = [tuple(p) for p in json.loads(cs)]
                if len(cl) >= 2 and (not box or any(box[0] <= a <= box[2] and box[1] <= b <= box[3] for a, b in cl)):
                    lines.append(cl)
        if not lines:
            return {"why": "street not on the map"}
        fk = street_key(c.get(fields[0]))
        if fk and fk.suffix and self.fr.keys(c.get(fields[0])) & cty["named"].keys():
            return {"why": "the feature is a mapped street (RAILROAD AVE): the locator's, not a crossing"}
        want, pad = crossings.read(c.get(fields[0])), 0.002
        hits = []                                      # (lat, lon, the street way, the features around it)
        for ln in lines:                               # per way: the features in its box only (features() is pairwise)
            la, lo = [p[0] for p in ln], [p[1] for p in ln]
            els, nodes = [], {}
            for wid, tags, nids, cs in self.feat.execute(
                    "SELECT w.id, w.tags, w.nodes, w.coords FROM way_box b JOIN ways w ON w.id = b.id WHERE b.maxlat >= ? "
                    "AND b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ?", (min(la) - pad, max(la) + pad,
                                                                             min(lo) - pad, max(lo) + pad)):
                nl = json.loads(nids)
                els.append({"type": "way", "id": wid, "nodes": nl, "tags": json.loads(tags)})
                for n, q in zip(nl, json.loads(cs)):
                    nodes[n] = {"type": "node", "id": n, "lat": q[0], "lon": q[1]}
            if not els:
                continue
            osm_x = {"elements": els + list(nodes.values())}
            paths = crossings.features(osm_x, want)
            if paths:
                pl = Polyline(ln)
                hits += [(*pl.proj.to_ll(*h["xy"]), ln, osm_x) for h in crossings.crossings(pl, paths)]
        if not hits:
            return {"why": "the street doesn't cross it on the map"}
        # one crossing = every hit within ONE_CROSSING_FT of the first (the street's ways meet at their ends)
        if any(ft(h[:2], hits[0][:2]) > crossings.ONE_CROSSING_FT for h in hits[1:]):
            return {"why": "the street crosses it in more than one place"}
        return crossings.place(c, {"line": hits[0][2]}, hits[0][3])    # the app's own spot, with the stated distance


def main() -> None:
    import citywide as cw  # noqa: F401  (sets up the harness path)
    import corridors
    import osm_local
    from coverage import districts
    from crashiq import aliases as aliases_mod
    from crashiq import crossings, mile_marker
    from crashiq.names import route_numbers
    from crashiq.postmile import PostmileCache
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    _, cname = districts()
    county_box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name IN (?, ?) "
                             "ORDER BY name = ? DESC", (f"{name} County", name, f"{name} County")).fetchone()   # SF: city-county
        if r:
            county_box[code] = r
    xing = Crossing(local, county_box, corridors.local_boundaries(local))
    pm = PostmileCache(ROOT / "data" / "cache" / "postmiles", background=False)
    assert pm.newest() is not None
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    rows, seen = [], set()
    cands = sorted(candidates(con), key=lambda c: int(c.get("county_code") or 0))
    out11, total = run11_outcomes({str(c["crash_id"]) for c in cands})
    assert SAMPLE or total >= 2_057_508, f"{BASE} parts hold {total} crashes"
    print(f"{len(cands)} candidate rows, {len(out11)} in {BASE}", flush=True)
    for i, c in enumerate(cands, 1):
        cid = str(c["crash_id"])
        r11 = out11.get(cid)
        if r11 is None or (cid, r11["city"]) in seen or (c.get("city") or "") != r11["city"]:
            continue                     # a crash once, in the city run 11 counted it in
        seen.add((cid, r11["city"]))
        c = aliases_mod.apply(dict(c))
        tiers = []
        if mile_marker._fields(c):
            tiers.append(("postmile", mile_marker.place(c, pm, set())))
        feat = next((f for f in (crossings.read(c.get(x)) for x in ("primary_road", "secondary_road")) if f), None)
        if feat:
            tiers.append((f"crossing_{feat['kind']}", xing.place(c)))
        for tier, r in tiers:
            truth = (c["lat"], c["lon"]) if r11["outcome"] == "gps_usable" and c.get("lat") is not None else None
            d = ft((r["lat"], r["lon"]), truth) if truth and "lat" in r else None
            # postmile: GPS that fits is on the named route already; crossings: also near the railway / path
            cons = d is not None and (tier == "postmile" or xing.near_feature(c, truth))
            rows.append({"collision_id": cid, "tier": tier, "district": r11["district"], "road_type": r11["road_type"],
                         "killed": r11["killed"], "ksi": r11["ksi"], "outcome": r11["outcome"], "bin": r11["bin"],
                         "gps": "off_roads" if r11["reason"].startswith("police GPS off") else
                                ("fits" if truth else "none"),
                         "spot": int("lat" in r), "why": r.get("why", ""), "dist_ft": round(d) if d is not None else "",
                         "consistent": int(cons),
                         "routes": "/".join(sorted(route_numbers(c.get("primary_road")) | route_numbers(c.get("secondary_road")))),
                         "primary": c.get("primary_road"), "secondary": c.get("secondary_road")})
        if i % 500 == 0:
            print(f"{i}/{len(cands)}", flush=True)
    tag = "" if BASE == "r11" else f"_{BASE}"
    with open(DATA / f"run11_tiers{tag}_rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    res = {}
    for tier in sorted({r["tier"] for r in rows}):
        rs = [r for r in rows if r["tier"] == tier]
        g = Counter()
        for r in rs:
            if r["bin"] == "2" and r["spot"]:
                for k, on in (("all", True), ("fatal", r["killed"] == "1"), ("ksi", r["ksi"] == "1")):
                    g[f"{r['gps']}_{k}"] += on
        acc = [r for r in rs if r["gps"] == "fits"]
        placed = [r for r in acc if r["spot"] and r["consistent"]]     # self-consistent truth only
        res[tier] = {"reports": len(rs), "in_bin2": sum(r["bin"] == "2" for r in rs), "gained": dict(g),
                     "why_no_spot_bin2": dict(Counter(r["why"] for r in rs if r["bin"] == "2" and not r["spot"]).most_common(8)),
                     "truth_gps_fits": len(acc), "truth_placed_any": sum(bool(r["spot"]) for r in acc),
                     "truth_placed": len(placed),
                     "median_ft": sorted(int(r["dist_ft"]) for r in placed)[len(placed) // 2] if placed else None,
                     **{f"within_{b}ft": {"k": sum(int(r["dist_ft"]) <= b for r in placed), "n": len(placed),
                                          "pct": round(100 * sum(int(r["dist_ft"]) <= b for r in placed) / len(placed), 1)
                                          if placed else None,
                                          "low": wilson_low(sum(int(r["dist_ft"]) <= b for r in placed), len(placed))}
                        for b in BANDS},
                     "by_district_gained": dict(Counter(r["district"] for r in rs if r["bin"] == "2" and r["spot"]
                                                        and r["gps"] == "none"))}
    (DATA / f"run11_tiers{tag}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    main()
