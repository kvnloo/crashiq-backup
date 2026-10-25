"""Citywide geocoding coverage (#199, measure only): for every police agency, of all its non-freeway CCRS crashes
2021-2025, how many end up on the map, how many wait for review, how many can't be placed, and how accurately.

Per agency (local police: its city's own OSM street network; CHP areas: police GPS only, no single city network):
1. Police GPS usable: the report has GPS and a road it names runs within GPS_CHECK_FT (+ the report's offset) of the
   point, on the city's network. For an agency-year CCRS writes in degrees-minutes-seconds (#143), the converted
   point is tried when the written one doesn't fit.
2. CrashIQ placed: the app's own locator (`locate.place`) on the city's network, auto-placed only under the app's
   gate (`locate.Gate()`: exact tier). Fatal crashes it can't place get their FARS point (the app's `fars.link` and
   `fars.point`) when that point fits the named roads.
3. Review: the locator found something the gate holds (relaxed / near / fuzzy), or the streets meet in more than one
   place.
4. Can't place: no cross street (the report names one road or none), or the two named streets never meet on the
   city's network.
5. Accuracy: the hidden-GPS test per agency (#88, accuracy_by_agency.json, exact tier at the intersection) when the
   agency's GPS is usable as truth; otherwise "can't verify".
On the map % = (police GPS usable + CrashIQ placed) / crashes.

Same basis: the frozen CCRS mirror (2026-10-19), the 2026-10-18 OSM extract, the app's code at the checkout's commit.
Each city is run on its own street map with every agency's crashes there (a sheriff or CHP serves many cities), then
totalled per city and per agency.

Run: python tests/statewide/citywide.py [--cities Fremont,Lancaster]   (writes data/statewide/citywide.json)
"""

from __future__ import annotations

import json
import math
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))

import corridors  # noqa: E402
import osm_local  # noqa: E402
from crashiq import fars, locate, osm  # noqa: E402
from crashiq.assign import GPS_CHECK_FT  # noqa: E402
from crashiq.crashes import DMS_SHARE_MIXED, dms_decode  # noqa: E402
from crashiq.db import Database  # noqa: E402
from crashiq.names import street_key  # noqa: E402
from crashiq.sources import ca_ccrs as cc  # noqa: E402

YEARS = (2021, 2022, 2023, 2024, 2025)
FT_PER_DEG = 364000.0


def _edges(net: osm.Network, key) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    out = []
    for n in net.all_nodes_of.get(key, ()):
        for m in net.neighbors.get((n, key), ()):
            if n < m and m in net.coord:
                out.append((net.coord[n], net.coord[m]))
    return out


def _seg_ft(p, a, b) -> float:
    k = math.cos(math.radians(p[0]))
    px, py = p[1] * k * FT_PER_DEG, p[0] * FT_PER_DEG
    ax, ay, bx, by = a[1] * k * FT_PER_DEG, a[0] * FT_PER_DEG, b[1] * k * FT_PER_DEG, b[0] * FT_PER_DEG
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


_fuzzy_app = locate._fuzzy
_fuzzy_memo: dict = {}


def _fuzzy_cached(net, k, min_score, margin):
    """The app's own fuzzy street match, remembered per (network, street name): it depends on nothing else, and
    re-scoring every street in the city for each crash is what made a citywide run slow. Results are unchanged."""
    key = (id(net), k, min_score, margin)
    if key not in _fuzzy_memo:
        _fuzzy_memo[key] = _fuzzy_app(net, k, min_score, margin)
    return _fuzzy_memo[key]


locate._fuzzy = _fuzzy_cached


class City:
    """One city's street network, with a cache of each street's segments for the GPS street check."""

    def __init__(self, net: osm.Network):
        self.net, self._edges = net, {}

    def keys(self, raw):
        k = street_key(raw)
        if not k:
            return []
        # every map street the name can be: exact keys AND same-core ones (a stretch mapped "West Foothill Boulevard"
        # next to one mapped "Foothill Boulevard"). Exact-only-when-any-exist missed GPS 6 m from the road (#211 audit)
        return list(dict.fromkeys(locate._keys_matching(self.net, k) + locate._same_core_keys(self.net, k)))

    def fits(self, lat: float, lon: float, c: dict) -> bool:
        tol = GPS_CHECK_FT + (c.get("offset_ft") or 0.0)
        for raw in (c.get("primary_road"), c.get("secondary_road")):
            for key in self.keys(raw):
                if key not in self._edges:
                    self._edges[key] = _edges(self.net, key)
                if any(_seg_ft((lat, lon), a, b) <= tol for a, b in self._edges[key]):
                    return True
        return False


def mirror_rows(con: sqlite3.Connection, col: str, value: str):
    """Every non-deleted CCRS crash row 2021-2025 with `col` = value, as the app's crash records."""
    for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'"):
        if year not in YEARS:
            continue
        fields = [{"id": r[1], "type": "text"} for r in con.execute(f'PRAGMA table_info("{rid}")')]
        cols, _ = cc.resolve_columns(fields, cc.CRASH_COLS)
        match = f'("{col}" = ? OR "{col}" IS NULL)' if value == "" else f'"{col}" = ?'   # blank = also NULL
        cur = con.execute(f'SELECT * FROM "{rid}" WHERE {match} AND COALESCE("IsDeleted", \'\') <> \'True\'',
                          (value,))
        names = [d[0] for d in cur.description]
        for row in cur:
            rec = dict(zip(names, row))
            c = cc.crash_record(rec, cols)
            c["year"] = year
            if c.get("lat") is None:                 # the raw values, for the lost-minus repair (#251, run 10)
                c["_raw_ll"] = (rec.get("Latitude"), rec.get("Longitude"))
            yield c


def dms_years(con: sqlite3.Connection, ncic: str) -> set[int]:
    """Agency-years whose written GPS carries the degrees-minutes-seconds signature (#143): minutes and seconds
    digits never above 59, on at least DMS_SHARE_MIXED of the points."""
    out = set()
    for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'"):
        if year not in YEARS:
            continue
        pts = con.execute(f'SELECT "Latitude", "Longitude" FROM "{rid}" WHERE "NCIC Code" = ? AND "Latitude" IS NOT NULL '
                          f'AND "Latitude" <> \'\' LIMIT 2000', (ncic,)).fetchall()

        def sig(v):
            try:
                f = abs(float(v))
            except (TypeError, ValueError):
                return False
            frac = f"{f:.6f}".split(".")[1]
            return int(frac[:2]) < 60 and int(frac[2:4]) < 60
        if pts and sum(sig(a) and sig(b) for a, b in pts) / len(pts) >= DMS_SHARE_MIXED:
            out.add(year)
    return out


def outcome(c: dict, city: City | None, dms: set[int], fars_db: Database | None, gate) -> tuple[str, str | None]:
    """(outcome, reason) for one non-freeway crash: gps_usable, gps_usable_dms, placed_exact, placed_fars, review,
    cant_place, or not_run (no city street map: CHP-only and unincorporated areas)."""
    if c.get("lat") is not None and c.get("lon") is not None:
        if city is None or city.fits(c["lat"], c["lon"], c):
            return "gps_usable", None
        if c["year"] in dms:
            la, lo = dms_decode(c["lat"]), dms_decode(c["lon"])
            if la is not None and lo is not None and city.fits(la, lo, c):
                return "gps_usable_dms", None
    if city is None:
        return "not_run", None
    pl = locate.place(city.net, c)
    if gate.auto(pl):
        return "placed_exact", None
    if (c.get("killed") or 0) > 0 and fars_db is not None:
        status, row = fars.link(fars_db, c)
        p = fars.point(fars_db, row) if status == "linked" else None
        if p is not None and city.fits(p[0], p[1], c):
            return "placed_fars", None
    if not street_key(c.get("secondary_road")) or not street_key(c.get("primary_road")):
        return "cant_place", "no cross street"
    if pl.tier in ("relaxed", "near", "fuzzy"):
        return "review", f"{pl.tier} match held by the gate"
    if "more than one place" in (pl.note or ""):
        return "review", "streets meet in more than one place"
    return "cant_place", "named streets don't meet on the city's map"


class Tally:
    def __init__(self):
        self.n, self.ctr, self.review, self.cant, self.fatal = 0, Counter(), Counter(), Counter(), Counter()

    def add(self, c: dict, out: str, why: str | None) -> None:
        self.n += 1
        self.ctr[out] += 1
        if out == "review":
            self.review[why] += 1
        elif out == "cant_place":
            self.cant[why] += 1
        if (c.get("killed") or 0) > 0:
            self.fatal["crashes"] += 1
            if out in ON_MAP:
                self.fatal["on_map"] += 1
                self.fatal["fars"] += out == "placed_fars"

    def row(self) -> dict:
        n, k = self.n, self.ctr
        pct = lambda v: round(100 * v / n, 1) if n else None        # noqa: E731
        return {"crashes": n, "police_gps_pct": pct(k["gps_usable"] + k["gps_usable_dms"]),
                "crashiq_placed_pct": pct(k["placed_exact"] + k["placed_fars"]),
                "on_map_pct": pct(sum(k[x] for x in ON_MAP)), "review_pct": pct(k["review"]),
                "cant_place_pct": pct(k["cant_place"]), "not_run_pct": pct(k["not_run"]), "counts": dict(k),
                "review_by_reason": dict(self.review), "cant_place_by_reason": dict(self.cant), "fatal": dict(self.fatal)}


ON_MAP = ("gps_usable", "gps_usable_dms", "placed_exact", "placed_fars")


def _accuracy(acc: dict | None) -> str:
    if acc and acc.get("exact_intersection_acc_pct") is not None and (acc.get("gps_self_consistent_pct") or 0) >= 50:
        return (f"{acc['exact_intersection_acc_pct']}% of exact matches at the right intersection "
                f"(hidden police GPS, n={acc.get('exact_n')})")
    return "can't verify (no usable truth for this agency)"


def main(only: set[str] | None = None) -> None:
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    agencies = {a["ncic"]: a for a in json.loads((DATA / "agencies.json").read_text())}
    acc = {x["ncic"]: x for x in json.loads((DATA / "accuracy_by_agency.json").read_text())}
    city_agency = {}                     # each city's own police agency: the local agency with most crashes there
    for a in sorted(agencies.values(), key=lambda a: a["crashes"]):
        if a["type"] == "local":
            city_agency[corridors.norm_city(a["city"] or "")] = a["ncic"]
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    fars_db = Database(ROOT / "data" / "tester.sqlite")
    gate = locate.Gate()
    names = Counter()
    for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'").fetchall():
        if year in YEARS:
            for name, k in con.execute(f'SELECT "City Name", COUNT(*) FROM "{rid}" GROUP BY 1'):
                names[name or ""] += k
    todo = [c for c, _ in names.most_common() if not only or c in only]
    by_city, by_agency, dms_cache, t0 = {}, defaultdict(Tally), {}, time.time()
    for i, cname in enumerate(todo, 1):
        _fuzzy_memo.clear()
        b = bounds.get(corridors.norm_city(cname))
        city = City(osm.Network(osm_local.network_in_area(local, b["rel"]))) if b else None
        t = Tally()
        for c in mirror_rows(con, "City Name", cname):
            if c.get("is_freeway"):
                continue
            ag = str(c.get("agency") or "")
            if ag not in dms_cache:
                dms_cache[ag] = dms_years(con, ag)
            out, why = outcome(c, city, dms_cache[ag], fars_db, gate)
            t.add(c, out, why)
            by_agency[ag].add(c, out, why)
        own = city_agency.get(corridors.norm_city(cname))
        by_city[cname] = {"city": cname, "network": "city OSM network" if city else "none (no OSM city boundary)",
                          "police_agency": own, "accuracy": _accuracy(acc.get(own)), **t.row()}
        print(f"[{i}/{len(todo)} {time.time() - t0:.0f}s] {cname or '(blank)'}: {t.n} crashes, on the map "
              f"{by_city[cname]['on_map_pct']}%, review {by_city[cname]['review_pct']}%, can't place "
              f"{by_city[cname]['cant_place_pct']}%", flush=True)
        if i % 25 == 0 or i == len(todo):
            _save(local, by_city, by_agency, agencies, acc, only, done=i == len(todo))


def _save(local, by_city, by_agency, agencies, acc, only, done: bool) -> None:
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    ag_rows = [{"ncic": k, "agency": (agencies.get(k) or {}).get("city"), "type": (agencies.get(k) or {}).get("type"),
                "county": (agencies.get(k) or {}).get("county"), "accuracy": _accuracy(acc.get(k)), **t.row()}
               for k, t in sorted(by_agency.items(), key=lambda kv: -kv[1].n)]
    res = {"basis": {"commit": commit, "mirror": "2026-10-19", "osm": local.meta.get("timestamp"),
                     "gate": "exact tier only (locate.Gate default)", "gps_check_ft": GPS_CHECK_FT},
           "complete": done, "cities": sorted(by_city.values(), key=lambda r: -r["crashes"]), "agencies": ag_rows}
    (DATA / ("citywide.json" if not only else "citywide_sample.json")).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", help="comma-separated CCRS city names (a sample); default every city")
    a = ap.parse_args()
    main(set(a.cities.split(",")) if a.cities else None)
