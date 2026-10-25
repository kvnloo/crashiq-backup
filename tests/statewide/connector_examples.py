"""Connector examples for the user (PM 2026-10-25; measure only): from d1_compare.csv (run 10's seed-246 sample), the
crashes the app's freeway.place placed as connectors; a seeded 4 misses (> 0.5 mi from police GPS) and 4 hits. For
each: the report fields, both parties' DirectionOfTravel and Lane (live CCRS Parties, public), police GPS, the app's
point, and where the connector meets the second freeway (the join freeway.place walks back from), with Google Maps links.

Run: python tests/statewide/connector_examples.py   (writes data/statewide/connector_examples.md)
"""

from __future__ import annotations

import csv
import json
import math
import random
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))
SEED = 1025


def live(rid: str, cid: str) -> list[dict]:
    q = urllib.parse.urlencode({"resource_id": rid, "filters": json.dumps({"CollisionId": int(cid)}), "limit": 20})
    req = urllib.request.Request(f"https://data.ca.gov/api/3/action/datastore_search?{q}",
                                 headers={"User-Agent": "CrashIQ-Tester/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["result"]["records"]


def joins(raw: dict, c: dict):
    """The connector's join points with the second route, as freeway.place computes them, and which walks it kept."""
    from crashiq import freeway as fw
    r = fw.parse(c)
    net = fw._Net(raw)
    first, second = net.lanes(r["route"], r["travel"]), net.lanes(r["to"], None)
    a, b = fw._linked(net, first), fw._linked(net, second)
    conn = [w for w in net.ways if w["id"] in a and w["id"] in b]
    sn = {n for w in second for n in w["nodes"]}
    js = [net.xy[n] for w in conn for n in (w["nodes"][0], w["nodes"][-1]) if n in sn]
    out = []
    for j in js:
        e = fw._walk(net, conn, j, r["offset_ft"], r["dir"])
        kept = not (r["offset_ft"] and r["dir"]) or math.hypot(e[0] - j[0], e[1] - j[1]) >= 0.5 * r["offset_ft"]
        out.append((net.proj.to_ll(*j), kept))
    return out


def main() -> None:
    import osm_local
    from coverage import Outside, districts
    from fwy_raw import FwyRaw
    rows = [r for r in csv.DictReader(open(DATA / "d1_compare.csv")) if r["app_kind"] == "connector" and r["app_point"]]
    rows.sort(key=lambda r: int(r["collision_id"]))
    rng = random.Random(SEED)
    miss = rng.sample([r for r in rows if int(r["app_ft"]) > 2640], 4)
    hit = rng.sample([r for r in rows if int(r["app_ft"]) <= 2640], 4)
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    _, cname = districts()
    box = {}
    for code, name in cname.items():
        x = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE admin_level = '6' AND name = ?",
                             (f"{name} County",)).fetchone()
        if x:
            box[code] = x
    fr = FwyRaw(local, box, Outside(local, box))
    con = sqlite3.connect(DATA / "ccrs_mirror.sqlite")
    import citywide as cw
    from crashiq import aliases as aliases_mod
    ll = lambda p: f"{p[0]:.6f}, {p[1]:.6f}"                  # noqa: E731
    gm = lambda p: f"https://www.google.com/maps?q={p[0]:.6f},{p[1]:.6f}"   # noqa: E731
    md = ["# Freeway-to-freeway connector crashes: 4 misses, 4 hits (run 10, for the user's review)", "",
          "From run 10's accuracy sample: freeway crashes whose police GPS fits the report, placed by the app's "
          "`freeway.place` with the GPS hidden. A miss is more than 0.5 mi (2,640 ft) from the officer's GPS. "
          "\"Connector start\" is where the connector meets the second freeway; the app walks back from it along the "
          "connector by the stated distance. Coordinates use a plain ASCII minus.", ""]
    for label, sel in (("Miss", miss), ("Hit", hit)):
        for i, r in enumerate(sel, 1):
            rec = None
            for rid, year in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'"):
                cur = con.execute(f'SELECT * FROM "{rid}" WHERE "Collision Id" = ?', (int(r["collision_id"]),))
                row = cur.fetchone()
                if row:
                    rec = dict(zip([d[0] for d in cur.description], row))
                    rec["_year"] = year
            prid = con.execute("SELECT rid FROM _meta WHERE tbl = 'parties' AND year = ?", (rec["_year"],)).fetchone()
            parties = live(prid[0], r["collision_id"]) if prid else []
            c = next(x for x in cw.mirror_rows(con, "City Name", r["city"]) if str(x["crash_id"]) == r["collision_id"])
            c = aliases_mod.apply(dict(c))
            js = joins(fr.raw(c), c)
            g = tuple(map(float, r["gps"].split(",")))
            a = tuple(map(float, r["app_point"].split(",")))
            md += [f"## {label} {i}: record {r['collision_id']}", "",
                   f"- PrimaryRoad: {rec.get('PrimaryRoad')} · SecondaryRoad: {rec.get('SecondaryRoad')}",
                   f"- Distance: {rec.get('SecondaryDistance')} {rec.get('SecondaryUnitOfMeasure') or ''} "
                   f"{rec.get('SecondaryDirection') or ''} · IsFreeway: {rec.get('IsFreeway')} · "
                   f"{r['city'] or 'outside cities'}, agency {r['agency']}"]
            for p in sorted(parties, key=lambda x: int(x.get("PartyNumber") or 0))[:2]:
                md.append(f"- Party {p.get('PartyNumber')}: DirectionOfTravel {p.get('DirectionOfTravel') or '(blank)'}"
                          f" · Lane {p.get('Lane') or '(blank)'}")
            if not parties:
                md.append("- Parties: none found in the live table")
            md += [f"- Officer GPS: {ll(g)} ({gm(g)})", f"- App's point: {ll(a)} ({gm(a)})"]
            for k, (j, kept) in enumerate(js, 1):
                md.append(f"- Connector start {k}{'' if kept else ' (walk dropped: too short)'}: {ll(j)} ({gm(j)})")
            md += [f"- Miss: {int(r['app_ft']):,} ft ({int(r['app_ft']) / 5280:.2f} mi) from the officer's GPS", ""]
    (DATA / "connector_examples.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
