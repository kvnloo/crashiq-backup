"""#219: police GPS quality per agency (CCRS 2021-2025, the Tester's mirror 2026-10-19), and pile / default points.

Every crash with police GPS (latest report version, not deleted, coordinates inside California) gets ONE class, first
match wins:
  dms        the #199 coverage placed it from GPS converted from degrees-minutes-seconds (wrong format)
  pile       its exact point (5 decimals, ~1 m) is a pile point of its agency (see PILE_*) and the GPS doesn't fit
             the report's roads: a default / dispatch point, not the crash
  snapped    the GPS fits the report's roads, lies within SNAP_FT of where the two named roads meet, and the report
             states an offset over SNAP_FT: the officer's GPS is at the intersection, the crash isn't (#218 rule 1)
  fits       the GPS fits the report's roads (#199 corrected check)
  far_off    the GPS doesn't fit and is more than a mile from every road the report names
  off_other  the GPS doesn't fit, within a mile of a named road (or the names aren't on the map)
Fit / not fit comes from the corrected #199 per-crash file (coverage_crashes.csv): gps_usable = fits.

Pile point (#218): one exact point shared by at least PILE_MIN_CRASHES crashes of any agencies (pooled: the big ones
are statewide CHP defaults), naming at
least PILE_MIN_PAIRS different street pairs, of which less than PILE_MAX_FIT_SHARE fit the point. A real intersection
that police GPS snaps to has many crashes too, but they name that one intersection and they fit.

Run: python tests/statewide/gps_profile.py --piles   (writes data/statewide/gps_piles.json, fast)
     python tests/statewide/gps_profile.py --profile --shard 0/3 --part p0 ; then --merge p0 p1 p2
"""

from __future__ import annotations

import argparse
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
PILE_MIN_CRASHES, PILE_MIN_PAIRS, PILE_MAX_FIT_SHARE = 10, 5, 0.5
SNAP_FT, MILE_FT = 50.0, 5280.0
COLS = ["Collision Id", "Report Version", "NCIC Code", "Latitude", "Longitude", "PrimaryRoad", "SecondaryRoad",
        "SecondaryDistance", "SecondaryDirection", "SecondaryUnitOfMeasure", "IsDeleted", "City Name", "County Code"]


def gps_crashes() -> dict[str, dict]:
    """collision_id -> latest non-deleted version with coordinates inside California, 2021-2025."""
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    best: dict[str, dict] = {}
    for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'").fetchall():
        q = f'SELECT {", ".join(chr(34) + c + chr(34) for c in COLS)} FROM "{rid}"'
        for row in con.execute(q):
            r = dict(zip(COLS, row))
            if r["Collision Id"] is None:
                continue
            cid = str(int(r["Collision Id"]))
            v = r["Report Version"] or 0
            if cid in best and (best[cid]["Report Version"] or 0) >= v:
                continue
            r["year"] = year
            best[cid] = r
    out = {}
    for cid, r in best.items():
        la, lo = r["Latitude"], r["Longitude"]
        if str(r["IsDeleted"]) == "True" or not isinstance(la, (int, float)) or not isinstance(lo, (int, float)):
            continue
        if not (32 <= la <= 42.1 and -124.5 <= lo <= -114):
            continue
        out[cid] = r
    return out


def outcomes() -> dict[str, str]:
    with open(DATA / "coverage_crashes.csv") as f:
        return {r["collision_id"]: r["outcome"] for r in csv.DictReader(f)}


def pair(r: dict) -> str:
    from crashiq.names import street_key
    ks = sorted(k.core for k in (street_key(r["PrimaryRoad"]), street_key(r["SecondaryRoad"])) if k)
    return " & ".join(ks)


def offset_ft(r: dict) -> float:
    d = r["SecondaryDistance"]
    try:
        d = float(d)
    except (TypeError, ValueError):
        return 0.0
    unit = str(r["SecondaryUnitOfMeasure"] or "").upper()
    return d * 5280 if unit.startswith("M") and d < 50 else d


def piles(crashes: dict[str, dict], out: dict[str, str]) -> dict:
    by = defaultdict(lambda: defaultdict(list))            # "all agencies" -> point -> crash ids (pooled, #218)
    for cid, r in crashes.items():
        by["all"][(round(r["Latitude"], 5), round(r["Longitude"], 5))].append(cid)
    found, dist = [], Counter()
    for _, pts in by.items():
        for p, ids in pts.items():
            if len(ids) < 3:
                continue
            pairs = {pair(crashes[c]) for c in ids}
            fit = sum(out.get(c) in ("gps_usable", "gps_usable_dms") for c in ids) / len(ids)
            dist[(min(len(ids), 50) // 5 * 5, min(len(pairs), 20) // 5 * 5, round(fit, 1))] += 1
            if len(ids) >= PILE_MIN_CRASHES and len(pairs) >= PILE_MIN_PAIRS and fit < PILE_MAX_FIT_SHARE:
                yrs = Counter(crashes[c]["year"] for c in ids)
                found.append({"agencies": dict(Counter(str(crashes[c]["NCIC Code"]) for c in ids).most_common(5)),
                              "n_agencies": len({crashes[c]["NCIC Code"] for c in ids}), "lat": p[0], "lon": p[1], "crashes": len(ids), "street_pairs": len(pairs),
                              "fit_share": round(fit, 3), "by_year": dict(sorted(yrs.items())),
                              "city_names": dict(Counter(crashes[c]["City Name"] for c in ids).most_common(3)),
                              "examples": sorted(pairs)[:5]})
    found.sort(key=lambda x: -x["crashes"])
    return {"thresholds": {"min_crashes": PILE_MIN_CRASHES, "min_street_pairs": PILE_MIN_PAIRS,
                           "max_fit_share": PILE_MAX_FIT_SHARE, "point": "exact to 5 decimals (~1 m)"},
            "piles": found, "pile_crashes": sum(x["crashes"] for x in found),
            "shared_points_distribution": {f"{a}+ crashes, {b}+ pairs, fit {c}": n for (a, b, c), n in
                                           sorted(dist.items())}}


def describe(piles_: list[dict]) -> None:
    """Where each pile sits: the nearest named streets, and the distance to its city's centre (OSM city outline)."""
    db = sqlite3.connect(ROOT / "data" / "osm" / "ca_osm.sqlite")
    cities = [(n, (a + c) / 2, (b + d) / 2) for n, a, b, c, d in
              db.execute("SELECT name, minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '8'")]
    for p in piles_:
        d = 0.0015
        near = []
        for name, coords in db.execute(
                "SELECT w.name, w.coords FROM way_box b JOIN ways w ON w.id = b.id WHERE b.minlat <= ? AND b.maxlat >= ? "
                "AND b.minlon <= ? AND b.maxlon >= ?", (p["lat"] + d, p["lat"] - d, p["lon"] + d, p["lon"] - d)):
            if not name:
                continue
            m = min(math.hypot((la - p["lat"]) * 364000, (lo - p["lon"]) * 364000 * math.cos(math.radians(p["lat"])))
                    for la, lo in json.loads(coords))
            near.append((m, name))
        near.sort()
        seen, names = set(), []
        for m, n in near:
            if n not in seen:
                seen.add(n)
                names.append(f"{n} ({m:.0f} ft)")
            if len(names) == 3:
                break
        p["nearest_streets"] = names
        c = min(cities, key=lambda x: (x[1] - p["lat"]) ** 2 + (x[2] - p["lon"]) ** 2)
        p["nearest_city_centre"] = c[0]
        p["miles_from_city_centre"] = round(math.hypot((c[1] - p["lat"]) * 69, (c[2] - p["lon"]) * 69 *
                                                       math.cos(math.radians(p["lat"]))), 2)


def decimals(x: float) -> int:
    t = repr(float(x))
    return len(t.split(".")[1].rstrip("0")) if "." in t else 0


class Roads:
    """Named roads around a point, from the OSM extract's spatial index; road-name keys cached."""

    def __init__(self):
        from crashiq import names
        self.names = names
        self.db = sqlite3.connect(ROOT / "data" / "osm" / "ca_osm.sqlite")
        self.kc: dict[str, object] = {}

    def core(self, raw):
        if raw not in self.kc:
            k = self.names.street_key(raw)
            self.kc[raw] = self.names.drop_directional(k).core.replace(" ", "") if k else None
        return self.kc[raw]

    def around(self, lat, lon, ft):
        d = ft / 364000.0
        dl = d / max(0.2, math.cos(math.radians(lat)))
        return self.db.execute(
            "SELECT w.name, w.tags, w.nodes, w.coords FROM way_box b JOIN ways w ON w.id = b.id WHERE b.maxlat >= ? AND "
            "b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ?", (lat - d, lat + d, lon - dl, lon + dl))

    def way_cores(self, name, tags):
        t = json.loads(tags)
        vals = [v for k in ("name", "alt_name", "old_name", "ref") for v in str(t.get(k) or "").split(";") if v.strip()]
        return {c for c in (self.core(v) for v in vals) if c}

    def snapped(self, r) -> bool:
        """GPS within SNAP_FT of a node shared by a road named like the primary and one named like the secondary."""
        cp, cs = self.core(r["PrimaryRoad"]), self.core(r["SecondaryRoad"])
        if not cp or not cs or cp == cs:
            return False
        on_p, on_s = set(), set()
        for name, tags, nids, coords in self.around(r["Latitude"], r["Longitude"], SNAP_FT * 2):
            cores = self.way_cores(name, tags)
            if cp not in cores and cs not in cores:
                continue
            close = {n for n, (la, lo) in zip(json.loads(nids), json.loads(coords))
                     if _ft((la, lo), (r["Latitude"], r["Longitude"])) <= SNAP_FT}
            if cp in cores:
                on_p |= close
            if cs in cores:
                on_s |= close
        return bool(on_p & on_s)

    def nearest_named_ft(self, r, limit_ft=MILE_FT) -> float | None:
        cores = {c for c in (self.core(r["PrimaryRoad"]), self.core(r["SecondaryRoad"])) if c}
        if not cores:
            return None
        best = None
        for name, tags, nids, coords in self.around(r["Latitude"], r["Longitude"], limit_ft):
            if not (self.way_cores(name, tags) & cores):
                continue
            m = min(_ft((la, lo), (r["Latitude"], r["Longitude"])) for la, lo in json.loads(coords))
            best = m if best is None or m < best else best
        return best


def _ft(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 364000, (a[1] - b[1]) * 364000 * math.cos(math.radians(a[0])))


CLASSES = ["fits", "snapped", "dms", "pile", "low_precision", "far_off", "off_other"]


def profile(shard: tuple[int, int], part: str) -> None:
    cr, out = gps_crashes(), outcomes()
    pts = {(p["lat"], p["lon"]) for p in json.loads((DATA / "gps_piles.json").read_text())["piles"]}
    roads = Roads()
    f = open(DATA / f"gps_profile_{part}.csv", "w", newline="")
    w = csv.writer(f)
    w.writerow(["collision_id", "agency", "year", "cls", "offset_ft", "nearest_named_ft"])
    for i, (cid, r) in enumerate(sorted(cr.items(), key=lambda kv: int(kv[0]))):
        if int(cid) % shard[1] != shard[0]:
            continue
        o = out.get(cid)
        fit = o in ("gps_usable",)
        off = offset_ft(r)
        near = ""
        if o == "gps_usable_dms":
            cls = "dms"
        elif not fit and (round(r["Latitude"], 5), round(r["Longitude"], 5)) in pts:
            cls = "pile"
        elif not fit and min(decimals(r["Latitude"]), decimals(r["Longitude"])) <= 2:
            cls = "low_precision"
        elif fit:
            cls = "snapped" if off > SNAP_FT and roads.snapped(r) else "fits"
        else:
            nn = roads.nearest_named_ft(r)
            near = "" if nn is None else round(nn)
            cls = "far_off" if nn is None and roads.core(r["PrimaryRoad"]) else "off_other"
            if nn is None and not roads.core(r["PrimaryRoad"]):
                cls = "off_other"
        w.writerow([cid, r["NCIC Code"], r["year"], cls, round(off), near])
        if i % 50000 == 0:
            f.flush()
            print(f"{i}", flush=True)
    f.close()
    print("EXIT: finished", flush=True)


def merge(parts: list[str]) -> None:
    """Per agency and statewide: share of GPS crashes in each class, overall and by year; agency names; the guard
    that every crash with GPS was classified exactly once."""
    agencies = {a["ncic"]: a for a in json.loads((DATA / "agencies.json").read_text())}
    tot, by_ag, by_year, by_ag_year = Counter(), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    seen = set()
    for p in parts:
        with open(DATA / f"gps_profile_{p}.csv") as f:
            for r in csv.DictReader(f):
                if r["collision_id"] in seen:
                    raise SystemExit(f"{r['collision_id']} twice")
                seen.add(r["collision_id"])
                tot[r["cls"]] += 1
                by_ag[r["agency"]][r["cls"]] += 1
                by_year[r["year"]][r["cls"]] += 1
                by_ag_year[(r["agency"], r["year"])][r["cls"]] += 1
    n_all = len(gps_crashes())
    if len(seen) != n_all:
        raise SystemExit(f"classified {len(seen)} of {n_all} crashes with GPS (completeness guard)")

    def shares(c: Counter) -> dict:
        n = sum(c.values())
        return {"gps_crashes": n, **{f"{k}_pct": round(100 * c[k] / n, 1) if n else None for k in CLASSES},
                **{k: c[k] for k in CLASSES}}
    ag_rows = []
    for ag, c in sorted(by_ag.items(), key=lambda kv: -sum(kv[1].values())):
        a = agencies.get(ag) or {}
        trend = {y: round(100 * (1 - by_ag_year[(ag, y)]["fits"] / max(1, sum(by_ag_year[(ag, y)].values()))), 1)
                 for y in sorted({y for (g, y) in by_ag_year if g == ag})}
        ag_rows.append({"ncic": ag, "agency": a.get("city"), "type": a.get("type"), "crashes": a.get("crashes"),
                        "gps_share_pct": a.get("gps_pct"), **shares(c), "not_fits_pct_by_year": trend})
    res = {"basis": "CCRS mirror 2026-10-19, 2021-2025, latest version, not deleted, GPS inside California; fit = "
                    "corrected #199 check; pile = gps_piles.json (pooled, #218 thresholds); OSM 2026-10-18",
           "classes": CLASSES, "statewide": shares(tot), "by_year": {y: shares(c) for y, c in sorted(by_year.items())},
           "agencies": ag_rows}
    (DATA / "gps_profile.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["statewide"]))
    for y, v in res["by_year"].items():
        print(y, {k: v[f"{k}_pct"] for k in CLASSES})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--piles", action="store_true")
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--part", default="all")
    ap.add_argument("--merge", nargs="*")
    a = ap.parse_args()
    if a.merge:
        merge(a.merge)
        return
    if a.profile:
        profile(tuple(int(x) for x in a.shard.split("/")), a.part)
        return
    if a.piles:
        cr, out = gps_crashes(), outcomes()
        res = piles(cr, out)
        describe(res["piles"])
        res["gps_crashes"] = len(cr)
        (DATA / "gps_piles.json").write_text(json.dumps(res, indent=1))
        print(f"{len(cr)} crashes with GPS; {len(res['piles'])} pile points holding {res['pile_crashes']} crashes")
        for p in res["piles"][:15]:
            print(p["n_agencies"], p["crashes"], p["street_pairs"], p["fit_share"], p["city_names"], p["nearest_streets"][:2],
                  p["miles_from_city_centre"])


if __name__ == "__main__":
    main()
