"""How often is each location clue on a crash report right? (the user's weighted-clue method, 2026-10-18)

Answer key: the report's own GPS (hidden-GPS design), Long Beach PD 2023-25. Street-name clues are scored on all
records with GPS inside the city; every other clue on "clean-GPS" records (GPS on its own primary street and near
its cross street), so the location is trustworthy. Output feeds the clue weights in the locator.

    python backend/scripts/clue_reliability.py --city lb
"""
import argparse, hashlib, json, math, sys, urllib.parse, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_geocode as V
from crashiq import locate, osm
from crashiq.names import street_key
from crashiq.sources import ca_ccrs

PARTIES = "Parties_"
FT = 0.3048


def resource_ids(prefix):
    pkg = ca_ccrs._get("package_show", id=ca_ccrs.PACKAGE)
    return {int(r["name"].split("_")[1]): r["id"] for r in pkg["resources"] if r["name"].startswith(prefix) and r.get("datastore_active")}


def fetch_parties(year, collision_ids):
    cache = V.CACHE / f"parties_{year}_{len(collision_ids)}_{min(collision_ids)}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rid, out, ids = resource_ids(PARTIES)[year], [], sorted(collision_ids)
    for i in range(0, len(ids), 150):
        chunk = ",".join(str(x) for x in ids[i:i + 150])
        sql = (f'SELECT "CollisionId","PartyNumber","PartyType","StreetOrHighwayName","DirectionOfTravel",'
               f'"MovementPrecCollDescription" FROM "{rid}" WHERE "CollisionId" IN ({chunk})')
        out += ca_ccrs._get("datastore_search_sql", sql=sql)["records"]
    cache.write_text(json.dumps(out))
    return out


def extra_fields(year, where):
    """Beat, reporting district and traffic control, not in the shared crash shape."""
    cache = V.CACHE / f"ccrs_extra_{year}_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rid = ca_ccrs.crash_resource_ids()[year]
    rows, off = [], 0
    while True:
        sql = (f'SELECT "Collision Id","Beat","ReportingDistrict","TrafficControlDeviceCode" FROM "{rid}" '
               f'WHERE {where} ORDER BY "Collision Id" LIMIT 5000 OFFSET {off}')
        b = ca_ccrs._get("datastore_search_sql", sql=sql)["records"]
        rows += b
        if len(b) < 5000:
            break
        off += 5000
    cache.write_text(json.dumps(rows))
    return rows


def signals(wikidata):
    cache = V.CACHE / f"osm_controls_{wikidata}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    q = (f'[out:json][timeout:300];rel["wikidata"="{wikidata}"]["boundary"="administrative"];map_to_area->.a;'
         'node["highway"~"^(traffic_signals|stop)$"](area.a);out;')
    req = urllib.request.Request(osm.OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": "CrashIQ/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=400) as r:
        out = [(e["lat"], e["lon"], e["tags"]["highway"]) for e in json.load(r)["elements"]]
    cache.write_text(json.dumps(out))
    return out


def seg_dist(p, a, b):
    k = 111320 * math.cos(math.radians(p[0]))
    ax, ay, bx, by = (a[1]-p[1])*k, (a[0]-p[0])*110540, (b[1]-p[1])*k, (b[0]-p[0])*110540
    dx, dy = bx-ax, by-ay
    L = dx*dx + dy*dy
    t = 0 if L == 0 else max(0, min(1, -(ax*dx + ay*dy) / L))
    return math.hypot(ax + t*dx, ay + t*dy)


def street_segments(net, name):
    k = street_key(name)
    if not k:
        return []
    return [(net.coord[n], net.coord[m]) for s in locate._same_core_keys(net, k)
            for n in net.all_nodes_of.get(s, ()) for m in net.neighbors.get((n, s), ()) if m in net.coord]


def dist_to(segs, p):
    return min((seg_dist(p, a, b) for a, b in segs), default=None)


def wilson(k, n):
    return f"{k/n:6.1%} (n={n}, W95 low {V.wilson_low(k, n):.1%})" if n else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="lb", choices=[c for c, v in V.CITIES.items() if v[4] == "gps"])
    a = ap.parse_args()
    cname, ncic, wikidata, years, _ = V.CITIES[a.city]
    net = osm.Network(osm.fetch(wikidata, V.CACHE))
    where = f"\"NCIC Code\"='{ncic}'"
    crashes = [c for y in years for c in ca_ccrs.fetch(y, where, V.CACHE) if c["lat"] and c["lon"]]
    extra = {r["Collision Id"]: r for y in years for r in extra_fields(y, where)}
    by_year = defaultdict(set)
    for c in crashes:
        by_year[int(c["datetime"][:4])].add(c["crash_id"])
    parties = defaultdict(list)
    party_years = resource_ids(PARTIES)  # Parties_2025 is a download only, not in the datastore API (2026-10-18)
    for y, ids in by_year.items():
        if y not in party_years:
            print(f"  no queryable Parties table for {y}; driver clues use the other years")
            continue
        for p in fetch_parties(y, ids):
            parties[p["CollisionId"]].append(p)
    print(f"{cname}: {len(crashes)} crashes with GPS · parties for {len(parties)}")

    res, clean = Counter(), []
    for c in crashes:
        g = c["lat"], c["lon"]
        sp, ss = street_segments(net, c["primary_road"]), street_segments(net, c["secondary_road"])
        dp, ds = dist_to(sp, g), dist_to(ss, g)
        if dp is not None:
            res["primary_n"] += 1; res["primary_ok"] += dp <= 30
        if ds is not None:
            res["secondary_n"] += 1; res["secondary_ok"] += ds <= 76.2 + (c["offset_ft"] or 0) * FT
        if dp is not None and ds is not None and dp <= 30 and ds <= 76.2 + (c["offset_ft"] or 0) * FT:
            clean.append(c)

    # Parties: each driver's street and direction of travel, on clean-GPS crashes.
    for c in clean:
        g = c["lat"], c["lon"]
        for p in parties.get(c["crash_id"], []):
            if p.get("PartyType") != "Driver" or not p.get("StreetOrHighwayName"):
                continue
            segs = street_segments(net, p["StreetOrHighwayName"])
            if not segs:
                res["party_street_unmapped"] += 1
                continue
            d = dist_to(segs, g)
            res["party_street_n"] += 1; res["party_street_ok"] += d <= 76.2
            dirn = (p.get("DirectionOfTravel") or "").strip()[:1].upper()
            if dirn in locate.CARDINAL and d <= 30:
                a_, b_ = min(segs, key=lambda s: seg_dist(g, *s))
                brg = osm.bearing(a_, b_) % 180
                want = locate.CARDINAL[dirn] % 180
                res["party_dir_n"] += 1; res["party_dir_ok"] += min(abs(brg - want), 180 - abs(brg - want)) <= 45

    # Driver direction on mid-block crashes (>=100 ft from the cross street): drivers are on the primary street,
    # so their direction of travel should run along it. (Works even where the driver's street field is empty.)
    for c in clean:
        if (c["offset_ft"] or 0) < 100:
            continue
        g = c["lat"], c["lon"]
        sp = street_segments(net, c["primary_road"])
        if not sp:
            continue
        a_, b_ = min(sp, key=lambda s: seg_dist(g, *s))
        brg = osm.bearing(a_, b_) % 180
        for p in parties.get(c["crash_id"], []):
            dirn = (p.get("DirectionOfTravel") or "").strip()[:1].upper()
            if p.get("PartyType") == "Driver" and dirn in locate.CARDINAL:
                want = locate.CARDINAL[dirn] % 180
                res["party_dir_n"] += 1; res["party_dir_ok"] += min(abs(brg - want), 180 - abs(brg - want)) <= 45

    # Distance and direction of the offset, against the cross street on clean-GPS crashes.
    for c in clean:
        if not c["offset_ft"] or not c["offset_dir"] or c["offset_dir"][:1] not in locate.CARDINAL:
            continue
        g = c["lat"], c["lon"]
        k = street_key(c["secondary_road"])
        nodes = [n for s in locate._same_core_keys(net, k) for n in net.all_nodes_of.get(s, ())] if k else []
        kp = street_key(c["primary_road"])
        pn = {n for s in locate._same_core_keys(net, kp) for n in net.all_nodes_of.get(s, ())} if kp else set()
        meet = [n for n in nodes if n in pn]
        if not meet:
            continue
        x = min(meet, key=lambda n: osm.metres(net.coord[n], g))
        actual, stated = osm.metres(net.coord[x], g), c["offset_ft"] * FT
        res["distance_n"] += 1; res["distance_ok"] += abs(actual - stated) <= max(15, 0.5 * stated)
        if actual >= 15:
            brg = osm.bearing(net.coord[x], g)
            want = locate.CARDINAL[c["offset_dir"][:1]]
            res["direction_n"] += 1; res["direction_ok"] += abs((brg - want + 180) % 360 - 180) <= 60

    # Beat: does the crash's beat match the most common beat among its 15 nearest clean-GPS neighbours?
    pts = [(c["lat"], c["lon"], (extra.get(c["crash_id"]) or {}).get("Beat")) for c in clean]
    pts = [p for p in pts if p[2]]
    grid = defaultdict(list)
    for i, p in enumerate(pts):
        grid[(round(p[0] / .005), round(p[1] / .005))].append(i)
    for i, p in enumerate(pts):
        cx, cy = round(p[0] / .005), round(p[1] / .005)
        near = [j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in grid.get((cx + dx, cy + dy), ()) if j != i]
        near = sorted(near, key=lambda j: osm.metres(p[:2], pts[j][:2]))[:15]
        if len(near) >= 5:
            top = Counter(pts[j][2] for j in near).most_common(1)[0][0]
            res["beat_n"] += 1; res["beat_ok"] += top == p[2]

    # Traffic control: code A (controls functioning) vs a mapped signal/stop within 40 m; D (none) vs nothing mapped.
    ctrl = signals(wikidata)
    cgrid = defaultdict(list)
    for s in ctrl:
        cgrid[(round(s[0] / .002), round(s[1] / .002))].append(s)
    for c in clean:
        code = ((extra.get(c["crash_id"]) or {}).get("TrafficControlDeviceCode") or "").strip()
        if code not in ("A", "D") or (c["offset_ft"] or 0) > 50:
            continue
        g = c["lat"], c["lon"]
        cx, cy = round(g[0] / .002), round(g[1] / .002)
        mapped = any(osm.metres(g, s[:2]) <= 40 for dx in (-1, 0, 1) for dy in (-1, 0, 1) for s in cgrid.get((cx + dx, cy + dy), ()))
        res["control_n"] += 1; res["control_ok"] += (code == "A") == mapped

    print(f"clean-GPS crashes: {len(clean)} of {len(crashes)}\n")
    rows = [("Primary street (GPS on it, <=30 m)", "primary"), ("Cross street (within 250 ft + stated distance)", "secondary"),
            ("Each driver's street (Parties)", "party_street"), ("Beat (matches nearest neighbours)", "beat"),
            ("Traffic control (signal/stop vs map)", "control"), ("Distance (within 50% or 15 m)", "distance"),
            ("Direction of offset (N/S/E/W, within 60°)", "direction"), ("Driver direction (along primary, mid-block)", "party_dir")]
    print(f"{'Clue':48s} right how often")
    summary = {}
    for label, key in rows:
        n, k = res[f"{key}_n"], res[f"{key}_ok"]
        summary[key] = {"n": n, "right": k, "rate": k / n if n else None, "wilson_low": V.wilson_low(k, n) if n else None}
        print(f"{label:48s} {wilson(k, n)}")
    print(f"\n(driver streets not found on the map: {res['party_street_unmapped']})")
    out = V.ROOT / "data" / "results" / f"clue_reliability_{a.city}.json"
    out.write_text(json.dumps(summary, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
