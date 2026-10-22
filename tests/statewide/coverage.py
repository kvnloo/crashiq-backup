"""Statewide coverage (#199, user direction 2026-10-22): every CCRS crash 2021-2025, all road types, in exactly one of
two bins, rolled up statewide -> Caltrans district -> county -> city / agency -> road type. Measure only.

BIN 1 "on the map":
  - police GPS that fits the report: a road the report names runs within GPS_CHECK_FT (+ the report's offset) of the
    point (degrees-minutes-seconds GPS converted first for the agency-years that write it, #143);
  - CrashIQ placed: the app's own locator (`locate.place`) under its gate (`locate.Gate()`: exact tier only);
  - FARS (fatal crashes): the app's own link (`fars.link` / `fars.point`), kept when the point fits the named roads.
BIN 2 "difficult", with the reason per crash: a likely match the gate holds (relaxed / near / fuzzy), streets that
  meet in more than one place, no cross street, named streets that don't meet on the map.

Street maps: inside a city with an OSM boundary, the city's own network (`citywide.City`, also used for the GPS
check); elsewhere (unincorporated land, freeways outside cities, campuses, parks), the GPS check reads the OSM roads
around the point, and the few crashes there without GPS get a small network of just the roads they name.
Road type per crash: freeway (CCRS IsFreeway) / state highway off the freeway (a route number in a road name) /
city street (inside a city) / county road (outside cities). Severity: fatal = NumberKilled > 0; KSI = fatal or an
injured person with a suspected serious injury (IWP SuspectSerious / SevereInactive).

Writes data/statewide/coverage.json (all roll-ups) and data/statewide/coverage_crashes.csv (one row per crash: bin,
outcome, reason and its place in every roll-up, for the next step's exploration; gitignored).
Run: python tests/statewide/coverage.py [--counties 1,38]
"""

from __future__ import annotations

import csv
import json
import sqlite3
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import citywide as cw
import corridors
import fatal as fatal_mod
import osm_local
from citywide import City, dms_decode, fars, locate, osm, street_key
from crashiq.db import Database
from crashiq.names import route_numbers

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
YEARS = cw.YEARS
BIN1 = ("gps_usable", "gps_usable_dms", "placed_exact", "placed_fars")
GROUPS = ("statewide", "district", "county", "city", "agency", "road_type", "district_road_type")


def districts() -> tuple[dict[int, int], dict[int, str]]:
    rows = list(csv.DictReader(open(ROOT / "data" / "reference" / "caltrans_districts.csv")))
    return ({int(r["ccrs_county_code"]): int(r["caltrans_district"]) for r in rows},
            {int(r["ccrs_county_code"]): r["county"] for r in rows})


def ksi_ids(con: sqlite3.Connection) -> set[str]:
    out = set()
    for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'iwp'"):
        if year in YEARS:
            out |= {str(r[0]) for r in con.execute(
                f'SELECT DISTINCT "CollisionId" FROM "{rid}" WHERE "ExtentOfInjuryCode" IN '
                f'(\'SuspectSerious\', \'SevereInactive\', \'Fatal\')')}
    return out


class Outside:
    """Roads outside any city street map: the GPS check from the OSM roads around the point (fatal.fits), and a small
    network of just the roads a report names for the few crashes there without GPS."""

    CELL = 0.005          # ~500 m; roads cached per cell, read with a margin wider than any tolerance used
    MARGIN = 0.007        # ~700 m: GPS_CHECK_FT (400 ft) + offsets up to ~1,800 ft
    MAX_CELLS = 20000

    def __init__(self, local: osm_local.LocalOSM, county_box: dict[int, tuple]):
        self.local, self.box = local, county_box
        self.cells: dict[tuple[int, int], list] = {}

    def _roads(self, lat: float, lon: float) -> list:
        """(names, segments) of every road way near a point, cached per cell (crash points cluster on roads)."""
        key = (int(lat // self.CELL), int(lon // self.CELL))
        hit = self.cells.get(key)
        if hit is None:
            la0, lo0, m = key[0] * self.CELL, key[1] * self.CELL, self.MARGIN
            hit = []
            for tags, coords in self.local.db.execute(
                    "SELECT w.tags, w.coords FROM way_box b JOIN ways w ON w.id = b.id WHERE b.maxlat >= ? AND "
                    "b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ?",
                    (la0 - m, la0 + self.CELL + m, lo0 - m, lo0 + self.CELL + m)):
                t = json.loads(tags)
                names = [t.get(k) for k in ("name", "ref") if t.get(k)]
                if names and t.get("highway") in fatal_mod.ROAD_CLASSES:
                    cs = json.loads(coords)
                    hit.append((names, list(zip(cs, cs[1:])) or [(cs[0], cs[0])]))
            if len(self.cells) >= self.MAX_CELLS:
                self.cells.clear()
            self.cells[key] = hit
        return hit

    def fits(self, lat: float, lon: float, c: dict) -> bool:
        """The same rule as fatal.fits: a road the report names runs within GPS_CHECK_FT + the report's offset of
        the point; only the road lookup is cached."""
        tol = cw.GPS_CHECK_FT + (c.get("offset_ft") or 0.0)
        roads = [x for x in (c.get("primary_road"), c.get("secondary_road")) if x and
                 fatal_mod.checks.indep_core(x) not in fatal_mod.UNUSABLE]
        for names, segs in self._roads(lat, lon):
            if fatal_mod.road_match(roads, names) and any(cw._seg_ft((lat, lon), a, b) <= tol for a, b in segs):
                return True
        return False

    def network(self, c: dict) -> osm.Network | None:
        box = self.box.get(int(c.get("county_code") or 0))
        words = [w for w in (street_key(c.get(f)) for f in ("primary_road", "secondary_road")) if w]
        if not box or len(words) < 2:
            return None
        ids = set()
        for k in words:
            core = k.core.split()[-1] if k.core.split() else k.core
            ids |= {r[0] for r in self.local.db.execute(
                "SELECT w.id FROM way_box b JOIN ways w ON w.id = b.id WHERE b.maxlat >= ? AND b.minlat <= ? "
                "AND b.maxlon >= ? AND b.minlon <= ? AND (w.name LIKE ? OR w.tags LIKE ?)",
                (box[0], box[2], box[1], box[3], f"%{core}%", f"%{core}%"))}
        if not ids:
            return None
        ways, nodes = [], {}
        for wid, tags, nids, coords in self.local.db.execute(
                f"SELECT id, tags, nodes, coords FROM ways WHERE id IN ({','.join('?' * len(ids))})", list(ids)):
            nl, cl = json.loads(nids), json.loads(coords)
            ways.append({"type": "way", "id": wid, "nodes": nl, "tags": json.loads(tags)})
            for n, (la, lo) in zip(nl, cl):
                nodes[n] = {"type": "node", "id": n, "lat": la, "lon": lo}
        return osm.Network({"elements": ways + list(nodes.values())})


def outcome(c: dict, city: City | None, outside: Outside, dms: set[int], fars_db, gate) -> tuple[str, str | None]:
    fits = city.fits if city else outside.fits
    gps_note = None
    if c.get("lat") is not None and c.get("lon") is not None:
        if fits(c["lat"], c["lon"], c):
            return "gps_usable", None
        if c["year"] in dms:
            la, lo = dms_decode(c["lat"]), dms_decode(c["lon"])
            if la is not None and lo is not None and fits(la, lo, c):
                return "gps_usable_dms", None
        gps_note = "police GPS off the report's roads; "
    net = city.net if city else outside.network(c)
    pl = locate.place(net, c) if net is not None else locate.Placement("review", note="no street map")
    if gate.auto(pl):
        return "placed_exact", None
    if (c.get("killed") or 0) > 0 and fars_db is not None:
        status, row = fars.link(fars_db, c)
        p = fars.point(fars_db, row) if status == "linked" else None
        if p is not None and fits(p[0], p[1], c):
            return "placed_fars", None
    pre = gps_note or ""
    if not street_key(c.get("secondary_road")) or not street_key(c.get("primary_road")):
        return "cant_place", pre + "no cross street"
    if pl.tier in ("relaxed", "near", "fuzzy"):
        return "review", pre + f"{pl.tier} match held by the gate"
    if "more than one place" in (pl.note or ""):
        return "review", pre + "streets meet in more than one place"
    if pl.note == "no street map":
        return "cant_place", pre + "no street map for this place"
    return "cant_place", pre + "named streets don't meet on the map"


def road_type(c: dict, in_city: bool) -> str:
    if c.get("is_freeway"):
        return "freeway"
    if route_numbers(c.get("primary_road")) or route_numbers(c.get("secondary_road")):
        return "state highway (off freeway)"
    return "city street" if in_city else "county road (outside cities)"


class Agg:
    def __init__(self):
        self.t = defaultdict(lambda: {"all": Counter(), "fatal": Counter(), "ksi": Counter(), "reasons": Counter()})

    def add(self, keys: list[tuple[str, str]], out: str, why: str | None, fatal: bool, ksi: bool) -> None:
        b = "bin1" if out in BIN1 else "bin2"
        for k in keys:
            d = self.t[k]
            d["all"][b] += 1
            d["all"][out] += 1
            if fatal:
                d["fatal"][b] += 1
                d["fatal"][out] += 1
            if ksi:
                d["ksi"][b] += 1
            if why:
                d["reasons"][why] += 1

    def rows(self, group: str) -> list[dict]:
        out = []
        for (g, name), d in self.t.items():
            if g != group:
                continue
            a, f, k = d["all"], d["fatal"], d["ksi"]
            n, nf, nk = a["bin1"] + a["bin2"], f["bin1"] + f["bin2"], k["bin1"] + k["bin2"]
            pct = lambda x, y: round(100 * x / y, 1) if y else None     # noqa: E731
            out.append({"name": name, "crashes": n, "on_map_pct": pct(a["bin1"], n), "difficult_pct": pct(a["bin2"], n),
                        "police_gps_pct": pct(a["gps_usable"] + a["gps_usable_dms"], n),
                        "crashiq_placed_pct": pct(a["placed_exact"], n), "fars_pct": pct(a["placed_fars"], n),
                        "review_pct": pct(a["review"], n), "cant_place_pct": pct(a["cant_place"], n),
                        "fatal": nf, "fatal_on_map_pct": pct(f["bin1"], nf), "ksi": nk, "ksi_on_map_pct": pct(k["bin1"], nk),
                        "counts": dict(a), "difficult_by_reason": dict(d["reasons"].most_common())})
        return sorted(out, key=lambda r: -r["crashes"])


def main(only_counties: set[int] | None = None) -> None:
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    dist, cname = districts()
    county_box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            county_box[code] = r
    outside = Outside(local, county_box)
    agencies = {a["ncic"]: a for a in json.loads((DATA / "agencies.json").read_text())}
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    ksi = ksi_ids(con)
    fars_db = Database(ROOT / "data" / "tester.sqlite")
    gate, agg, dms_cache = locate.Gate(), Agg(), {}
    names = Counter()
    for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'").fetchall():
        if year in YEARS:
            q = f'SELECT "City Name", "County Code", COUNT(*) FROM "{rid}" GROUP BY 1, 2'
            for nm, cty, k in con.execute(q):
                if not only_counties or int(cty or 0) in only_counties:
                    names[nm or ""] += k
    t0 = time.time()
    out_csv = open(DATA / "coverage_crashes.csv", "w", newline="")
    w = csv.writer(out_csv)
    w.writerow(["collision_id", "year", "county_code", "district", "city", "agency", "road_type", "killed", "ksi", "bin",
                "outcome", "reason"])
    for i, (nm, n) in enumerate(names.most_common(), 1):
        b = bounds.get(corridors.norm_city(nm)) if nm else None
        cw._fuzzy_memo.clear()
        city = City(osm.Network(osm_local.network_in_area(local, b["rel"]))) if b else None
        for c in cw.mirror_rows(con, "City Name", nm):
            county = int(c.get("county_code") or 0)
            if only_counties and county not in only_counties:
                continue
            ag = str(c.get("agency") or "")
            if ag not in dms_cache:
                dms_cache[ag] = cw.dms_years(con, ag)
            out, why = outcome(c, city, outside, dms_cache[ag], fars_db, gate)
            rt = road_type(c, city is not None)
            killed = (c.get("killed") or 0) > 0
            is_ksi = killed or str(c["crash_id"]) in ksi
            d = dist.get(county)
            keys = [("statewide", "California"), ("district", f"District {d}" if d else "unknown"),
                    ("county", cname.get(county, "unknown")), ("city", nm or "(blank)"),
                    ("agency", ag), ("road_type", rt), ("district_road_type", f"District {d} · {rt}")]
            agg.add(keys, out, why, killed, is_ksi)
            w.writerow([c["crash_id"], c["year"], county, d, nm, ag, rt, int(killed), int(is_ksi),
                        1 if out in BIN1 else 2, out, why or ""])
        print(f"[{i}/{len(names)} {time.time() - t0:.0f}s] {nm or '(blank)'}: {n} crashes "
              f"({'city map' if city else 'outside cities'})", flush=True)
        if i % 25 == 0:
            _save(agg, agencies, local, done=False)
    out_csv.close()
    _save(agg, agencies, local, done=True)


def _save(agg: Agg, agencies: dict, local, done: bool) -> None:
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    res = {"basis": {"commit": commit, "mirror": "2026-10-19", "osm": local.meta.get("timestamp"), "years": "2021-2025",
                     "gate": "exact tier only (locate.Gate default)", "gps_check_ft": cw.GPS_CHECK_FT},
           "complete": done, **{g: agg.rows(g) for g in GROUPS}}
    for r in res["agency"]:
        a = agencies.get(r["name"]) or {}
        r["agency_name"], r["agency_type"] = a.get("city"), a.get("type")
    (DATA / "coverage.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--counties", help="comma-separated CCRS county codes (a sample)")
    a = ap.parse_args()
    main({int(x) for x in a.counties.split(",")} if a.counties else None)
