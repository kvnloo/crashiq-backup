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
import math
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
BIN1 = ("gps_usable", "gps_usable_dms", "placed_exact", "placed_unique_pair", "placed_fars")
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

    MAX_WAYS = 300000     # parsed roads kept in memory (crash points cluster on the same roads)

    def __init__(self, local: osm_local.LocalOSM, county_box: dict[int, tuple]):
        self.local, self.box = local, county_box
        self.ways: dict[int, tuple] = {}

    def _way(self, wid: int, tags: str | None = None, coords: str | None = None):
        w = self.ways.get(wid)
        if w is None:
            if tags is None:
                tags, coords = self.local.db.execute("SELECT tags, coords FROM ways WHERE id = ?", (wid,)).fetchone()
            t = json.loads(tags)
            names = [t.get(k) for k in ("name", "ref") if t.get(k)]
            if names and t.get("highway") in fatal_mod.ROAD_CLASSES:
                cs = json.loads(coords)
                w = (names, list(zip(cs, cs[1:])) or [(cs[0], cs[0])])
            else:
                w = ((), ())
            if len(self.ways) >= self.MAX_WAYS:
                self.ways.clear()
            self.ways[wid] = w
        return w

    def fits(self, lat: float, lon: float, c: dict) -> bool:
        """The same rule as fatal.fits: a road the report names runs within GPS_CHECK_FT + the report's offset of
        the point. Roads come from the extract's spatial index for a box of that size; parsed roads are cached."""
        tol = cw.GPS_CHECK_FT + (c.get("offset_ft") or 0.0)
        roads = [x for x in (c.get("primary_road"), c.get("secondary_road")) if x and
                 fatal_mod.checks.indep_core(x) not in fatal_mod.UNUSABLE]
        if not roads:
            return False
        dlat = tol / 364000.0
        dlon = dlat / max(0.2, math.cos(math.radians(lat)))
        ids = [r[0] for r in self.local.db.execute(
            "SELECT id FROM way_box WHERE maxlat >= ? AND minlat <= ? AND maxlon >= ? AND minlon <= ?",
            (lat - dlat, lat + dlat, lon - dlon, lon + dlon))]
        for wid in ids:
            names, segs = self._way(wid)
            if names and fatal_mod.road_match(roads, names) and any(cw._seg_ft((lat, lon), a, b) <= tol for a, b in segs):
                return True
        return False

    def _names(self, county: int) -> dict[str, list[int]]:
        """Street core -> way ids for one county's box, built once per county."""
        idx = getattr(self, "_idx", None)
        if idx is None:
            idx = self._idx = {}
        if county not in idx:
            box = self.box.get(county)
            m: dict[str, list[int]] = defaultdict(list)
            if box:
                for wid, tags in self.local.db.execute(
                        "SELECT w.id, w.tags FROM way_box b JOIN ways w ON w.id = b.id WHERE b.maxlat >= ? AND "
                        "b.minlat <= ? AND b.maxlon >= ? AND b.minlon <= ?", (box[0], box[2], box[1], box[3])):
                    t = json.loads(tags)
                    for tag in ("name", "ref"):
                        for v in str(t.get(tag) or "").split(";"):
                            k = street_key(v)
                            if k:
                                m[k.core.replace(" ", "")].append(wid)
            idx[county] = m               # every county kept: crashes come in no county order (~150 MB in all)
        return idx[county]

    def network(self, c: dict) -> osm.Network | None:
        """A small network of just the roads the report names, in its county (no county-wide network in memory)."""
        county = int(c.get("county_code") or 0)
        keys = [k for k in (street_key(c.get(f)) for f in ("primary_road", "secondary_road")) if k]
        if county not in self.box or len(keys) < 2:
            return None
        names = self._names(county)
        ids = set()
        for k in keys:
            ids |= set(names.get(k.core.replace(" ", ""), ()))
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


NETWORK, GATE_TIERS = "clipped", []          # set from the command line
AUTO_TIERS = ("exact", "unique_pair")          # the tiers the app auto-places (config/placement.json since #222)

NO_CROSS = "no cross street (blank, NOT STATED, UNKNOWN, PRIVATE PROPERTY)"


def usable(road) -> bool:
    """A road name the locator can use: not blank and not a placeholder (the app's street_key keeps 'NOT STATED')."""
    core = fatal_mod.checks.indep_core(road)
    return bool(street_key(road)) and core not in fatal_mod.UNUSABLE and len(core) > 2


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
    c["_tier"], c["_note"] = pl.tier, pl.note or ""          # recorded per crash (run 8: effects derived from tiers)
    if gate.auto(pl):
        return ("placed_unique_pair" if pl.tier == "unique_pair" else "placed_exact"), None
    if (c.get("killed") or 0) > 0 and fars_db is not None:
        status, row = fars.link(fars_db, c)
        p = fars.point(fars_db, row) if status == "linked" else None
        if p is not None and fits(p[0], p[1], c):
            return "placed_fars", None
    pre = gps_note or ""
    if not usable(c.get("secondary_road")) or not usable(c.get("primary_road")):
        return "cant_place", pre + NO_CROSS
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
                        "crashiq_placed_pct": pct(a["placed_exact"] + a["placed_unique_pair"], n),
                        "unique_pair_pct": pct(a["placed_unique_pair"], n), "fars_pct": pct(a["placed_fars"], n),
                        "review_pct": pct(a["review"], n), "cant_place_pct": pct(a["cant_place"], n),
                        "fatal": nf, "fatal_on_map_pct": pct(f["bin1"], nf), "ksi": nk, "ksi_on_map_pct": pct(k["bin1"], nk),
                        "counts": dict(a), "difficult_by_reason": dict(d["reasons"].most_common())})
        return sorted(out, key=lambda r: -r["crashes"])


def main(only_counties: set[int] | None = None, shard: tuple[int, int] = (0, 1), skip: int = 0,
         part: str | None = None, exclude: set[str] = frozenset(), only_city: str | None = None,
         split: tuple[int, int] = (0, 1)) -> None:
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
    gate, agg, dms_cache = (locate.Gate(auto_tiers=frozenset(GATE_TIERS)) if GATE_TIERS else locate.Gate()), Agg(), {}
    names = Counter()
    for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'").fetchall():
        if year in YEARS:
            q = f'SELECT "City Name", "County Code", COUNT(*) FROM "{rid}" GROUP BY 1, 2'
            for nm, cty, k in con.execute(q):
                if not only_counties or int(cty or 0) in only_counties:
                    names[nm or ""] += k
    t0 = time.time()
    out_csv = open(DATA / (f"coverage_crashes_{part}.csv" if part else "coverage_crashes.csv"), "w", newline="")
    w = csv.writer(out_csv)
    w.writerow(["collision_id", "year", "county_code", "district", "city", "agency", "road_type", "killed", "ksi", "bin",
                "outcome", "reason", "tier", "note"])
    for i, (nm, n) in enumerate(names.most_common(), 1):
        if only_city is not None:
            if nm != only_city:
                continue
        elif i <= skip or (i - skip - 1) % shard[1] != shard[0] or nm in exclude:
            continue                          # another shard's city (a shard writes only its part file)
        b = bounds.get(corridors.norm_city(nm)) if nm else None
        cw._fuzzy_memo.clear()
        if b:
            raw = (osm_local.network_in_box(local, b["rel"]) if NETWORK == "box1km" else
                   osm_local.network_in_area(local, b["rel"]))
            city = City(osm.Network(raw))
        else:
            city = None
        for c in cw.mirror_rows(con, "City Name", nm):
            county = int(c.get("county_code") or 0)
            if split[1] > 1 and int(c["crash_id"]) % split[1] != split[0]:
                continue                      # one city split across processes by Collision Id
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
                        1 if out in BIN1 else 2, out, why or "", c.get("_tier", ""), c.get("_note", "")])
        print(f"[{i}/{len(names)} {time.time() - t0:.0f}s] {nm or '(blank)'}: {n} crashes "
              f"({'city map' if city else 'outside cities'})", flush=True)
        if i % 25 == 0 and not part:
            _save(agg, agencies, local, done=False)
    out_csv.close()
    if not part:
        _save(agg, agencies, local, done=True)
    print("EXIT: finished", flush=True)


def merge(parts: list[Path]) -> None:
    """Roll-ups rebuilt from the per-crash part files (shards), exactly as a single run computes them."""
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    dist, cname = districts()
    agencies = {a["ncic"]: a for a in json.loads((DATA / "agencies.json").read_text())}
    agg, seen, total = Agg(), set(), 0
    fix = _placeholder_ids(parts)            # bin-2 crashes whose road names are placeholders (first run's reasons)
    relabelled = 0
    with open(DATA / "coverage_crashes.csv", "w", newline="") as fo:
        w = csv.writer(fo)
        for k, p in enumerate(parts):
            with open(p) as fi:
                r = csv.reader(fi)
                head = next(r)
                if k == 0:
                    w.writerow(head)
                for row in r:
                    rec = dict(zip(head, row))
                    key = (rec["collision_id"], rec["city"])
                    if key in seen:
                        raise SystemExit(f"crash {key} is in two part files")
                    seen.add(key)
                    total += 1
                    if rec["reason"].endswith("no cross street"):           # the first run's shorter label
                        rec["reason"] = rec["reason"][: -len("no cross street")] + NO_CROSS
                        row = [rec[h] for h in head]
                    if rec["bin"] == "2" and rec["collision_id"] in fix and "named streets don't meet" in rec["reason"]:
                        rec["reason"] = rec["reason"].replace("named streets don't meet on the map", NO_CROSS)
                        rec["outcome"] = "cant_place"
                        row = [rec[h] for h in head]
                        relabelled += 1
                    w.writerow(row)
                    county = int(rec["county_code"] or 0)
                    d = rec["district"]
                    rt = rec["road_type"]
                    keys = [("statewide", "California"), ("district", f"District {d}" if d else "unknown"),
                            ("county", cname.get(county, "unknown")), ("city", rec["city"] or "(blank)"),
                            ("agency", rec["agency"]), ("road_type", rt), ("district_road_type", f"District {d} · {rt}")]
                    agg.add(keys, rec["outcome"], rec["reason"] or None, rec["killed"] == "1", rec["ksi"] == "1")
    _save(agg, agencies, local, done=True)
    print(f"merged {total} crashes from {len(parts)} part files; {relabelled} reasons relabelled 'no cross street'",
          flush=True)


def _placeholder_ids(parts: list[Path]) -> set[str]:
    """Collision Ids of bin-2 crashes whose primary or secondary road is a placeholder (read from the mirror)."""
    want = set()
    for p in parts:
        with open(p) as fi:
            for rec in csv.DictReader(fi):
                if rec["bin"] == "2" and "named streets don't meet" in rec["reason"]:
                    want.add(rec["collision_id"])
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    out, ids = set(), sorted(want, key=int)
    for (rid,) in con.execute("SELECT rid FROM _meta WHERE tbl = 'crashes'").fetchall():
        for i in range(0, len(ids), 900):
            chunk = ids[i:i + 900]
            for cid, pr, sr in con.execute(f'SELECT "Collision Id", "PrimaryRoad", "SecondaryRoad" FROM "{rid}" '
                                           f'WHERE "Collision Id" IN ({",".join("?" * len(chunk))})', chunk):
                if not usable(pr) or not usable(sr):
                    out.add(str(int(cid)))
    return out


def _wilson_low(k: int, n: int, z: float = 1.96) -> float | None:
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    return round(100 * (p + z * z / (2 * n) - z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5) / d, 1)


def add_accuracy(res: dict, agencies: dict) -> None:
    """Accuracy beside coverage, with its basis (#199): the hidden-GPS test (#88) on CrashIQ's exact tier (the tier the
    gate auto-places), pooled over every tested agency (raw counts, accuracy_by_agency.py). Two measures, side by side:
    - headline: at the right intersection (chosen intersection within 250 ft of the police GPS), on self-consistent
      truth only (GPS within 400 ft of an intersection of the two streets the report names);
    - lower bound: the final point (after the officer's stated distance and direction) within 250 ft of the police GPS,
      on all police GPS, noisy GPS included.
    k of n with the Wilson 95% low bound. It covers city streets (where the test samples); freeways, state highways
    and county roads can't be verified this way. San Francisco's open-data test (claim C1) is cited separately."""
    r8 = DATA / "accuracy_by_agency_r8.json"            # run 8: unique_pair measured too (it auto-places since #222)
    acc = json.loads((r8 if r8.exists() else DATA / "accuracy_by_agency.json").read_text())
    tiers = [t for t in AUTO_TIERS if any(a.get(f"{t}_counts") for a in acc)]
    dist, _ = districts()
    pool: dict[str, Counter] = defaultdict(Counter)
    for a in acc:
        cs = [a.get(f"{t}_counts") for t in tiers if a.get(f"{t}_counts")]
        if not cs:
            continue
        ag = agencies.get(a["ncic"]) or {}
        d = dist.get(int(ag.get("county") or a.get("county") or 0))
        for key in ("California", f"District {d}"):
            pool[key].update({"agencies": 1})
            for c in cs:
                pool[key].update(c)
    head = (f"right intersection (within 250 ft), self-consistent police GPS as truth; CrashIQ {' + '.join(tiers)} "
            "(the tiers that auto-place); hidden-GPS test #88, pooled over tested agencies")
    low = f"final point within 250 ft of police GPS, all police GPS (noisy truth: a lower bound); {' + '.join(tiers)}; #88"

    def fmt(k, n):
        return f"{round(100 * k / n, 1)}% ({k} of {n}; 95% low {_wilson_low(k, n)}%)"

    def note(key):
        p = pool.get(key)
        if not p or not p["n"]:
            return {"accuracy": "can't verify (no tested agency here)", "accuracy_point_all_gps": "can't verify"}
        return {"accuracy": fmt(p["ok_consistent"], p["n_consistent"]), "accuracy_point_all_gps": fmt(p["ok_point"], p["n"]),
                "accuracy_agencies": p["agencies"], "accuracy_basis": head, "accuracy_point_basis": low}
    for r in res["statewide"]:
        r.update(note("California"))
        r["accuracy_open_data"] = "San Francisco: 98.8% exact at the right intersection (claim C1, open data)"
    for r in res["district"]:
        r.update(note(r["name"]))
    for r in res["road_type"]:
        r.update(note("California") if r["name"] == "city street" else
                 {"accuracy": "can't verify (police GPS checked for consistency only; CrashIQ places few here)",
                  "accuracy_point_all_gps": "can't verify"})


def _save(agg: Agg, agencies: dict, local, done: bool) -> None:
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    res = {"basis": {"commit": commit, "mirror": "2026-10-19", "osm": local.meta.get("timestamp"), "years": "2021-2025",
                     "gate": "exact tier only (locate.Gate default)", "gps_check_ft": cw.GPS_CHECK_FT},
           "complete": done, **{g: agg.rows(g) for g in GROUPS}}
    for r in res["agency"]:
        a = agencies.get(r["name"]) or {}
        r["agency_name"], r["agency_type"] = a.get("city"), a.get("type")
    add_accuracy(res, agencies)
    (DATA / "coverage.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--counties", help="comma-separated CCRS county codes (a sample)")
    ap.add_argument("--shard", default="0/1", help="k/n: this process's share of the cities")
    ap.add_argument("--skip", type=int, default=0, help="skip the first N city groups (done in an earlier part)")
    ap.add_argument("--part", help="write coverage_crashes_<part>.csv only (merge later)")
    ap.add_argument("--exclude", default="", help="comma-separated city names to leave out (run on their own)")
    ap.add_argument("--only-city", help="run just this CCRS city name (with --split)")
    ap.add_argument("--split", default="0/1", help="j/m: this process's share of one city's crashes, by Collision Id")
    ap.add_argument("--merge", nargs="*", help="part files to merge into coverage.json and coverage_crashes.csv")
    ap.add_argument("--network", choices=["clipped", "box1km"], default="clipped",
                    help="city street map: clipped to the city outline (#199) or its box + 1 km (run 8)")
    ap.add_argument("--gate-tiers", default="", help="comma-separated auto tiers (default: the app's config)")
    a = ap.parse_args()
    NETWORK = a.network
    GATE_TIERS = [x for x in a.gate_tiers.split(",") if x]
    if a.merge:
        merge([Path(x) for x in a.merge])
    else:
        k, n = (int(x) for x in a.shard.split("/"))
        j, m = (int(x) for x in a.split.split("/"))
        main({int(x) for x in a.counties.split(",")} if a.counties else None, (k, n), a.skip, a.part,
             {x for x in a.exclude.split(",") if x}, a.only_city, (j, m))
