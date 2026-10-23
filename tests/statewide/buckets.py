"""Difficult-bin buckets for the user's rule-by-rule review (PM 2026-10-23). Every bin-2 crash of run 9A (main 5ed6783:
cleaner rules + approved aliases, box + 1 km city maps, OSM only) gets ONE bucket, first match wins:

  D2 no cross street            the coverage reason (blank, NOT STATED, UNKNOWN, PRIVATE PROPERTY)
  D9 no street map              the coverage reason (no city map and no named road in the county)
  D1 freeway / ramp reference   road type freeway, a ramp word (RAMP, ON/OFF, CONNECTOR, TRANSITION), or a route
                                number (SR 91, I-5, US 101, RT 1 ...) the map doesn't carry as a named street
  D5 house number as location   a name the map doesn't have that carries a house number (BROADWAY 7346)
  D8 meet in more than one place  the locator's note
  D7 spelling held              a relaxed / verified_typo / fuzzy match the gate holds
  D4 near-miss streets          the near tier, or both names on the map with their closest points within NEAR_GAP_M
  D3 street missing from the map  a name with no street on the map (no exact or same-core street)
  D6 named streets don't cross  both names on the map, farther apart than NEAR_GAP_M
Police GPS off the report's roads is counted inside each bucket (gps_off), not as a bucket.

Run: python tests/statewide/buckets.py --shard 0/3 --part b0 ; then --merge b0 b1 b2
Writes data/statewide/buckets_<part>.csv; --merge writes data/statewide/buckets.csv and buckets.json.
"""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
NEAR_GAP_M = 100.0
RAMP = re.compile(r"\b(RAMP|ONRAMP|OFFRAMP|ON|OFF|CONNECTOR|TRANSITION)\b")
HOUSE_NO = re.compile(r"(^\d{2,6}\s+[A-Z])|([A-Z.]\s*\d{2,6}$)")
NUMBERED = re.compile(r"^(AVENUE|AVE|AV|ROAD|RD|COUNTY ROAD|CR|STREET|ST|LANE|LN|HIGHWAY|HWY|ROUTE|RTE|RT|SR|I|US)[\s-]*"
                      r"\d+[A-Z]?$")
LABEL = {"D1": "freeway / ramp reference", "D2": "no cross street", "D3": "street missing from the map",
         "D4": "near-miss streets", "D5": "house number as location", "D6": "named streets don't cross",
         "D7": "spelling held", "D8": "meet in more than one place", "D9": "no street map"}
GPS_OFF = "police GPS off the report's roads; "


def bin2() -> dict[str, dict[str, dict]]:
    by = defaultdict(dict)
    for p in sorted(DATA.glob("coverage_crashes_r9a_*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                if r["bin"] == "2":
                    by[r["city"]][r["collision_id"]] = r
    return by


def main(shard: tuple[int, int], part: str) -> None:
    from crashiq import aliases as aliases_mod
    from crashiq import locate, names, osm

    import citywide as cw
    import corridors
    import osm_local
    from coverage import Outside, districts

    by = bin2()
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
    order = sorted(by, key=lambda c: -len(by[c]))
    out = open(DATA / f"buckets_{part}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["collision_id", "city", "district", "county_code", "road_type", "killed", "ksi", "gps_off", "bucket",
                "evidence"])

    def norm(x):
        return re.sub(r"\s+", " ", re.sub(r"[.,#'\"]", " ", (x or "").upper())).strip()

    for i, city in enumerate(order):
        if i % shard[1] != shard[0]:
            continue
        want = by[city]
        b = bounds.get(corridors.norm_city(city)) if city else None
        net_city = osm.Network(osm_local.network_in_box(local, b["rel"])) if b else None
        seen = set()
        for c in cw.mirror_rows(con, "City Name", city):
            cid = str(c["crash_id"])
            if cid not in want or cid in seen:
                continue
            seen.add(cid)
            c = aliases_mod.apply(dict(c))
            r = want[cid]
            reason = r["reason"].removeprefix(GPS_OFF)
            pr, sr = norm(c.get("primary_road")), norm(c.get("secondary_road"))
            net = net_city if net_city is not None else outside.network(c)

            def found(raw):
                k = names.street_key(raw)
                return (locate._keys_matching(net, k) or locate._same_core_keys(net, k)) if (k and net) else []
            a, bb = found(pr), found(sr)
            bb = [s for s in bb if s not in a]
            ev = ""
            if reason.startswith("no cross street"):
                bk = "D2"
            elif reason.startswith("no street map") or r["note"] == "no street map":
                bk = "D9"
            elif r["road_type"] == "freeway" or RAMP.search(f"{pr} {sr}") or any(
                    not hit and names.ROUTE.match(raw) for raw, hit in ((pr, a), (sr, bb))):
                bk, ev = "D1", r["road_type"] if r["road_type"] == "freeway" else f"{pr} & {sr}"
            elif any(not hit and HOUSE_NO.search(raw) and not re.search(r"\d+(ST|ND|RD|TH)$", raw)
                     and not NUMBERED.match(raw) for raw, hit in ((pr, a), (sr, bb))):
                bk, ev = "D5", f"{pr} & {sr}"
            elif "more than one place" in (r["note"] or "") or "more than one place" in reason:
                bk = "D8"
            elif r["tier"] in ("relaxed", "verified_typo", "fuzzy"):
                bk, ev = "D7", r["tier"]
            elif r["tier"] == "near":
                bk, ev = "D4", "near tier"
            elif not a or not bb:
                bk, ev = "D3", pr if not a else sr
            else:
                pb = [net.coord[n] for k in bb for n in net.all_nodes_of.get(k, ())]
                gap = None
                for k in a:
                    for n in net.all_nodes_of.get(k, ()):
                        p = net.coord[n]
                        for q in pb:
                            d = osm.metres(p, q)
                            if gap is None or d < gap:
                                gap = d
                bk, ev = ("D4", f"{gap:.0f} m apart") if gap is not None and gap <= NEAR_GAP_M else \
                    ("D6", f"{gap:.0f} m apart" if gap is not None else "")
            w.writerow([cid, city, r["district"], r["county_code"], r["road_type"], r["killed"], r["ksi"],
                        int(r["reason"].startswith(GPS_OFF)), bk, ev])
        out.flush()
        print(f"[{i + 1}/{len(order)}] {city or '(blank)'}: {len(seen)} of {len(want)}", flush=True)
    out.close()
    print("EXIT: finished", flush=True)


def merge(parts: list[str]) -> None:
    rows = []
    for p in parts:
        with open(DATA / f"buckets_{p}.csv") as f:
            rows += list(csv.DictReader(f))
    total = sum(len(v) for v in bin2().values())
    if len(rows) != total or len({r["collision_id"] for r in rows}) != total:
        raise SystemExit(f"classified {len(rows)} of {total} difficult crashes (completeness guard)")
    with open(DATA / "buckets.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    st, dist = Counter(), defaultdict(Counter)
    extra = defaultdict(Counter)
    for r in rows:
        st[r["bucket"]] += 1
        d = f"District {r['district']}" if r["district"] else "unknown"
        dist[d][r["bucket"]] += 1
        extra[r["bucket"]]["fatal"] += r["killed"] == "1"
        extra[r["bucket"]]["ksi"] += r["ksi"] == "1"
        extra[r["bucket"]]["gps_off"] += r["gps_off"] == "1"
    res = {"basis": "run 9A (main 5ed6783), every bin-2 crash", "total": total,
           "buckets": [{"code": k, "label": LABEL[k], "crashes": st[k], "pct": round(100 * st[k] / total, 1),
                        **extra[k]} for k in sorted(LABEL)],
           "districts": {d: dict(v) for d, v in sorted(dist.items(), key=lambda kv: int(kv[0].split()[-1])
                                                      if kv[0].split()[-1].isdigit() else 99)}}
    (DATA / "buckets.json").write_text(json.dumps(res, indent=1))
    for b in res["buckets"]:
        print(b)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--part")
    ap.add_argument("--merge", nargs="*")
    a = ap.parse_args()
    if a.merge:
        merge(a.merge)
    else:
        main(tuple(int(x) for x in a.shard.split("/")), a.part)
