"""Step 2 (#211) Part B: root causes in the two big difficult reasons, on seeded stratified samples.

Samples (from the #199 per-crash file, stratified by Caltrans district, proportional with at least MIN_PER per district):
  dont_meet - "named streets don't meet on the map" (with or without police GPS)
  gps_off   - any difficult crash whose police GPS lies more than 400 ft (+ the stated offset) from both named roads

Each crash is re-examined on the app's own network for its city (or the named roads in its county outside cities) on
the --backend code, and given ONE root cause by fixed rules, first match wins, with its evidence:
  freeway or ramp                 road type freeway, or a name with RAMP / ON / OFF
  route number vs street name     a name is a route (SR 1, RT 63, I-5, US 101 ...) that the map doesn't carry as named
  private road or parking lot     PARKING / LOT / DRIVEWAY / PRIVATE / ALLEY / ENTRANCE in a name
  leading abbreviation (#212)     a name not on the map that starts AVE / AV / ST / MT / FT / BL (AVE M = Avenue M)
  house number in the name        a name not on the map that carries a house number (BROADWAY 7346: an address)
  travel direction in the name    a name not on the map that carries N/B, S/B, EASTBOUND ... (normalizer gap)
  two streets in one field        a name not on the map with AND / & / AT / "/" between two names
  street outside the city's map   a name not on the city's map but on a road in the same county
  misspelling or abbreviation     a name not on the map, but a map street scores >= FUZZY_EVIDENCE
  street missing from the map     a name not on the map and nothing close (OSM gap or a different name: TIGER check);
                                  outside cities only the county's exact names are searched, so spelling isn't checked
  streets nearly meet             both names on the map, closest points within NEAR_GAP_M (divided road, offset node)
  streets don't intersect         both names on the map, closest points farther apart (parallel or far apart)
For gps_off the GPS side is classified too: within 400 ft of one named road only / of both roads but far from where
they meet / of neither but within 1 mile / far off (> 1 mile: wrong coordinates).

Run: python tests/statewide/bin2_audit.py --backend <main checkout>/backend   (writes data/statewide/bin2_audit.csv)
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
N_PER, MIN_PER, SEED = 300, 10, 2110
FUZZY_EVIDENCE, NEAR_GAP_M, ONE_MILE_M, CHECK_M = 0.85, 100.0, 1609.0, 400 * 0.3048
GPS_OFF = "police GPS off the report's roads; "
PRIVATE = re.compile(r"\b(PARKING|LOT|DRIVEWAY|PRIVATE|ALLEY|ENTRANCE|DRIVE ?THRU|DRIVE THROUGH)\b")
RAMP = re.compile(r"\b(RAMP|ONRAMP|OFFRAMP|ON|OFF|CONNECTOR|TRANSITION)\b")
HOUSE_NO = re.compile(r"(^\d{2,6}\s+[A-Z])|([A-Z.]\s*\d{2,6}$)")           # 7346 BROADWAY, BROADWAY 7346, ST40
NUMBERED = re.compile(r"^(AVENUE|AVE|AV|ROAD|RD|COUNTY ROAD|CR|STREET|ST|LANE|LN|HIGHWAY|HWY|ROUTE|RTE|RT|SR|I|US)[\s-]*"
                      r"\d+[A-Z]?$")                                          # AVENUE 12, ROAD 140: street names
TRAVEL = re.compile(r"(^|\s)([NSEW]/?B|NORTHBOUND|SOUTHBOUND|EASTBOUND|WESTBOUND)(\s|$)")
LEADING = re.compile(r"^(AVE|AV|ST|MT|FT|BL|BLVD)\s+(?!OF\b)[A-Z0-9]")
TWO_IN_ONE = re.compile(r"\s(AND|&|/|@|AT)\s")


def sample() -> list[dict]:
    pools: dict[str, dict[str, list[dict]]] = {"dont_meet": defaultdict(list), "gps_off": defaultdict(list)}
    with open(DATA / "coverage_crashes.csv") as f:
        for r in csv.DictReader(f):
            if r["bin"] != "2":
                continue
            base = r["reason"].removeprefix(GPS_OFF)
            if base.startswith("named streets don't meet"):
                pools["dont_meet"][r["district"]].append(r)
            if r["reason"].startswith(GPS_OFF):
                pools["gps_off"][r["district"]].append(r)
    rng, out = random.Random(SEED), []
    for which, by in pools.items():
        tot = sum(len(v) for v in by.values())
        for d in sorted(by):
            rows = sorted(by[d], key=lambda r: int(r["collision_id"]))
            k = min(len(rows), max(MIN_PER, round(N_PER * len(rows) / tot)))
            for r in rng.sample(rows, k):
                out.append({**r, "sample": which, "weight": len(rows) / k})
    return out


def main(backend: Path) -> None:
    sys.path.insert(0, str(backend.resolve()))
    from crashiq import locate, names, osm
    sys.path.insert(1, str(HERE))
    import sqlite3

    import citywide as cw
    import corridors
    import osm_local
    from coverage import Outside, districts

    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    _, cname = districts()
    box = {}
    for code, name in cname.items():
        r = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if r:
            box[code] = r
    outside = Outside(local, box)
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    rows = sample()
    by_city = defaultdict(dict)
    for r in rows:
        by_city[r["city"]].setdefault(r["collision_id"], []).append(r)

    def found(net, k):
        if not k:
            return []
        return locate._same_core_keys(net, k)

    def best_fuzzy(net, k):
        sc = sorted(((names.similarity(k, s), s) for s in locate._similar_pool(net, k)), key=lambda t: -t[0])
        return (round(sc[0][0], 2), net.name(sc[0][1])) if sc else (0.0, "")

    def gap(net, a, b):
        pb = [net.coord[n] for k in b for n in net.all_nodes_of.get(k, ())]
        best = None
        for k in a:
            for n in net.all_nodes_of.get(k, ()):
                p = net.coord[n]
                for q in pb:
                    d = osm.metres(p, q)
                    if best is None or d < best:
                        best = d
        return best

    def dist(net, ks, p):
        return min((osm.metres(net.coord[n], p) for k in ks for n in net.all_nodes_of.get(k, ())), default=None)

    out = open(DATA / "bin2_audit.csv", "w", newline="")
    cols = ["sample", "weight", "collision_id", "city", "district", "road_type", "reason", "primary", "secondary",
            "offset_ft", "offset_dir", "cause", "evidence", "gps_side", "gps_evidence"]
    w = csv.DictWriter(out, cols)
    w.writeheader()
    for city, want in sorted(by_city.items(), key=lambda kv: -len(kv[1])):
        b = bounds.get(corridors.norm_city(city)) if city else None
        net_city = osm.Network(osm_local.network_in_area(local, b["rel"])) if b else None
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in want or cid in seen:
                continue
            seen.add(cid)
            net = net_city if net_city is not None else outside.network(c)
            pr, sr = c.get("primary_road") or "", c.get("secondary_road") or ""
            kp, ks = names.street_key(pr), names.street_key(sr)
            up = f"{pr} {sr}".upper()
            ev, cause = "", None
            a = found(net, kp) if net else []
            bb = [s for s in (found(net, ks) if net else []) if s not in a]
            r0 = want[cid][0]
            if r0["road_type"] == "freeway" or RAMP.search(up):
                cause, ev = "freeway or ramp", r0["road_type"]
            if cause is None:
                for raw, k, hit in ((pr, kp, a), (sr, ks, bb)):
                    if not hit and names.ROUTE.match(re.sub(r"[.,]", " ", raw.upper()).strip()):
                        cause, ev = "route number vs street name", raw
                        break
            if cause is None and PRIVATE.search(up):
                cause, ev = "private road or parking lot", PRIVATE.search(up).group(0)
            if cause is None:
                for raw, k, hit in ((pr, kp, a), (sr, ks, bb)):
                    u = re.sub(r"[.,]", " ", raw.upper()).strip()
                    if hit or not k:
                        continue
                    if LEADING.match(u):
                        cause, ev = "leading abbreviation (#212)", raw
                    elif HOUSE_NO.search(u) and not re.search(r"\d+(ST|ND|RD|TH)$", u) and not NUMBERED.match(u):
                        cause, ev = "house number in the name", raw
                    elif TRAVEL.search(u):
                        cause, ev = "travel direction in the name", raw
                    elif TWO_IN_ONE.search(u):
                        cause, ev = "two streets in one field", raw
                    if cause:
                        break
            if cause is None:
                for raw, k, hit in ((pr, kp, a), (sr, ks, bb)):
                    if hit or not k:
                        continue
                    county = int(c.get("county_code") or 0)
                    if net_city is not None and outside._names(county).get(k.core.replace(" ", "")):
                        cause, ev = "street outside the city's map", raw
                        break
                    fz = best_fuzzy(net, k) if net else (0.0, "")
                    if fz[0] >= FUZZY_EVIDENCE:
                        cause, ev = "misspelling or abbreviation", f"{raw} ~ {fz[1]} ({fz[0]})"
                    else:
                        cause, ev = "street missing from the map", f"{raw} (closest: {fz[1]} {fz[0]})"
                    break
            if cause is None and net and a and bb:
                g = gap(net, a, bb)
                if g is not None and g <= NEAR_GAP_M:
                    cause, ev = "streets nearly meet", f"{g:.0f} m apart"
                else:
                    cause, ev = "streets don't intersect", f"{g:.0f} m apart" if g is not None else "no nodes"
            if cause is None:
                cause, ev = "no street map for this place", ""
            gside, gev = "", ""
            if c.get("lat") is not None and net:
                p = (c["lat"], c["lon"])
                dp, ds = dist(net, a, p), dist(net, bb, p)
                tol = CHECK_M + (c.get("offset_ft") or 0) * 0.3048
                near = [x for x in (dp, ds) if x is not None and x <= tol]
                dmin = min([x for x in (dp, ds) if x is not None], default=None)
                if len(near) == 2:
                    gside = "near both roads, far from where they meet"
                elif len(near) == 1:
                    gside = "near one named road only"
                elif dmin is not None and dmin <= ONE_MILE_M:
                    gside = "near neither road, within 1 mile"
                else:
                    gside = "far off (over 1 mile, or the roads aren't on the map)"
                gev = json.dumps({"to_primary_m": round(dp) if dp is not None else None,
                                  "to_secondary_m": round(ds) if ds is not None else None})
            for r in want[cid]:
                w.writerow({"sample": r["sample"], "weight": round(r["weight"], 2), "collision_id": cid, "city": city,
                            "district": r["district"], "road_type": r["road_type"], "reason": r["reason"],
                            "primary": pr, "secondary": sr, "offset_ft": c.get("offset_ft"),
                            "offset_dir": c.get("offset_dir"), "cause": cause, "evidence": ev,
                            "gps_side": gside if r["sample"] == "gps_off" else "", "gps_evidence": gev})
        out.flush()
        print(f"{city or '(blank)'}: {len(seen)}", flush=True)
    out.close()
    with open(DATA / "bin2_audit.csv") as f:
        res = list(csv.DictReader(f))
    for s in ("dont_meet", "gps_off"):
        sub = [r for r in res if r["sample"] == s]
        tw = sum(float(r["weight"]) for r in sub)
        cnt = Counter()
        for r in sub:
            cnt[r["cause"]] += float(r["weight"])
        print(s, len(sub), {k: f"{100 * v / tw:.0f}%" for k, v in cnt.most_common()})
        if s == "gps_off":
            gs = Counter()
            for r in sub:
                gs[r["gps_side"]] += float(r["weight"])
            print("  gps side", {k: f"{100 * v / tw:.0f}%" for k, v in gs.most_common()})
    print("EXIT: finished", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", type=Path, required=True)
    main(ap.parse_args().backend)
