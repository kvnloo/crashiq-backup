"""Massachusetts placement sample (research only, not the app): 2,000 random MassDOT IMPACT 2025 crashes in
Middlesex County (25017), read by crashiq.sources.ma_impact, placed by the app's locator with the GPS hidden.

  street pairs  -> locate.place on a Census TIGER/Line 2024 network, one network per town (same street pairs
                   repeat across Middlesex's 54 towns, so a county-wide network would send them to review)
  house address -> locate.AddressIndex on MassGIS Master Address Data points (the crash's town and street only)
Scored against the hidden IMPACT GPS: within 250 ft, Wilson 95% lower bound, split by MassDOT's geocoding method
("Operator Designated" = the officer's map click, the only truth not produced from the same street names).

  PYTHONPATH=backend:tests/statewide python tests/statewide/ma_placement.py <scratch dir>   # writes ma_placement.json
The scratch dir holds sample_middlesex_2025.json (+ _persons) from research_notes/ma-2026-11-07/fetch_sample.py, tl_2024_25017_{edges,featnames}.zip
and tl_2024_25_cousub.zip; MAD points are fetched once into mad_points.json.
"""
from __future__ import annotations

import json
import math
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from crashiq import locate, osm, tiger
from crashiq.names import drop_directional, street_key
from crashiq.sources import ma_impact as m

MAD = "https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/MassGIS_Master_Address_Points/FeatureServer/0/query"
FT = 0.3048


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def towns(cousub_zip: Path) -> dict[str, list[list[tuple[float, float]]]]:
    r = tiger._reader(cousub_zip)
    names = [f[0] for f in r.fields[1:]]
    out = {}
    for sr in r.iterShapeRecords():
        rec = dict(zip(names, sr.record))
        if rec["COUNTYFP"] == "017":
            pts, parts = sr.shape.points, list(sr.shape.parts) + [len(sr.shape.points)]
            out[rec["NAME"].upper()] = [[(y, x) for x, y in pts[a:b]] for a, b in zip(parts, parts[1:])]
    return out


def inside(rings, lat, lon) -> bool:
    hit = False
    for ring in rings:   # even-odd over all rings, so holes work
        for (y1, x1), (y2, x2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def town_networks(d: Path, polys) -> dict[str, osm.Network]:
    els = tiger.elements(d / "tl_2024_25017_edges.zip", d / "tl_2024_25017_featnames.zip")["elements"]
    coord = {e["id"]: (e["lat"], e["lon"]) for e in els if e["type"] == "node"}
    boxes = {t: (min(p[0] for r in rs for p in r), max(p[0] for r in rs for p in r),
                 min(p[1] for r in rs for p in r), max(p[1] for r in rs for p in r)) for t, rs in polys.items()}
    cell_town: dict = {}

    def towns_at(la, lo):   # shortcut: decided per ~200 m cell, so a way within ~150 m of a town line may join both
        key = (round(la / 0.002), round(lo / 0.002))
        if key not in cell_town:
            cla, clo = key[0] * 0.002, key[1] * 0.002
            cell_town[key] = [t for t, (a, b, c, e) in boxes.items() if a <= cla <= b and c <= clo <= e
                              and inside(polys[t], cla, clo)]
        return cell_town[key]

    per = defaultdict(list)
    for w in (e for e in els if e["type"] == "way"):
        ns = w["nodes"]
        for t in {t for n in (ns[0], ns[len(ns) // 2], ns[-1]) for t in towns_at(*coord[n])}:
            per[t].append(w)   # a way belongs to every town one of its ends or middle lies in
    nets = {}
    for t, ways in per.items():
        ids = {n for w in ways for n in w["nodes"]}
        nets[t] = osm.Network({"elements": [{"type": "node", "id": n, "lat": coord[n][0], "lon": coord[n][1]}
                                            for n in ids] + ways})
    return nets


def _base(street: str) -> str | None:
    k = street_key(street)
    return drop_directional(k).core if k else None


def mad_points(d: Path, wanted: dict[str, set[str]]) -> list:
    cache = d / "mad_points.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rows = []
    for town, bases in sorted(wanted.items()):
        bl = sorted(b for b in bases if b and "'" not in b)
        for i in range(0, len(bl), 40):
            where = f"GEOGRAPHIC_TOWN='{town}' AND STR_NAME_BASE IN ({','.join(repr(b) for b in bl[i:i + 40])})"
            off = 0
            while True:   # shortcut: resultOffset paging per (town, streets) slice; fine for a 2,000-crash sample
                q = urllib.parse.urlencode({"where": where, "outFields": "ADDRESS_NUMBER,STREET_NAME,GEOGRAPHIC_TOWN",
                                            "outSR": 4326, "resultOffset": off, "resultRecordCount": 2000,
                                            "orderByFields": "OBJECTID", "f": "json"})
                with urllib.request.urlopen(urllib.request.Request(MAD, data=q.encode(), headers=m.UA), timeout=300) as r:
                    res = json.load(r)
                feats = res.get("features", [])
                rows += [(f["attributes"]["GEOGRAPHIC_TOWN"], f["attributes"]["STREET_NAME"],
                          f["attributes"]["ADDRESS_NUMBER"], f["geometry"]["y"], f["geometry"]["x"])
                         for f in feats if f.get("geometry") and f["attributes"]["ADDRESS_NUMBER"]]
                if not res.get("exceededTransferLimit"):
                    break
                off += len(feats)
    cache.write_text(json.dumps(rows))
    return rows


def main(d: Path) -> dict:
    raw = json.loads((d / "sample_middlesex_2025.json").read_text())
    crashes = [m.crash_record(a) for a in raw]
    n = len(crashes)
    gps = [c for c in crashes if c["lat"] is not None]
    addr = [c for c in crashes if c["house_number"] and c["primary_road"] and not c["secondary_road"]]
    pair = [c for c in crashes if c["primary_road"] and c["secondary_road"]]
    polys = towns(d / "tl_2024_25_cousub.zip")
    nets = town_networks(d, polys)
    wanted = defaultdict(set)
    for c in addr:
        wanted[c["city_name"]].add(_base(c["primary_road"]))
    by_town = defaultdict(list)
    for t, st, num, la, lo in mad_points(d, wanted):
        by_town[t].append((st, num, la, lo))
    aidx = {t: locate.AddressIndex(v) for t, v in by_town.items()}
    gate = locate.Gate()
    out = []
    for c in crashes:
        kind = "pair" if c["primary_road"] and c["secondary_road"] else \
            "address" if c["house_number"] and c["primary_road"] else "none"
        net = nets.get(c["city_name"] or "")
        hidden = {**c, "lat": None, "lon": None}
        if kind == "address":
            hidden = {**hidden, "primary_road": f"{c['house_number']} {c['primary_road']}"}
            pl = locate.place(net, hidden, addresses=aidx.get(c["city_name"])) if aidx.get(c["city_name"]) \
                else locate.Placement("review", note="no address points for the town")
            auto = pl.tier == "address"
        elif kind == "pair" and net is not None:
            pl = locate.place(net, hidden)
            auto = gate.auto(pl)
        else:
            pl, auto = locate.Placement("review", note="no street pair or address" if kind == "none" else "town not in county"), False
        dist = osm.metres((pl.lat, pl.lon), (c["lat"], c["lon"])) / FT if pl.lat is not None and c["lat"] is not None else None
        out.append({"id": c["collision_id"], "kind": kind, "method": c["geocode_method"], "gps": c["lat"] is not None,
                    "tier": pl.tier, "auto": auto, "dist_ft": dist, "note": pl.note,
                    "primary": c["primary_road"], "secondary": c["secondary_road"], "town": c["city_name"]})
    (d / "ma_placement_rows.json").write_text(json.dumps(out))

    def score(rows):
        a = [r for r in rows if r["auto"] and r["dist_ft"] is not None]
        k = sum(r["dist_ft"] <= 250 for r in a)
        return {"n": len(rows), "auto": sum(r["auto"] for r in rows), "auto_share": round(sum(r["auto"] for r in rows) / len(rows), 4) if rows else None,
                "scored": len(a), "within_250ft": round(k / len(a), 4) if a else None, "within_250ft_low": round(wilson_low(k, len(a)), 4) if a else None}
    g = [r for r in out if r["gps"]]
    res = {
        "area": "Middlesex County MA (25017), IMPACT 2025, random 2,000 (seed 20251107)", "n": n,
        "gps": len(gps), "gps_share": round(len(gps) / n, 4),
        "kinds": Counter(r["kind"] for r in out), "name_placeable_share": round((len(pair) + len(addr)) / n, 4),
        "tiers_gps_pairs": Counter(r["tier"] for r in g if r["kind"] == "pair"),
        "pairs_on_gps": score([r for r in g if r["kind"] == "pair"]),
        "address_on_gps": score([r for r in g if r["kind"] == "address"]),
        "all_named_on_gps": score([r for r in g if r["kind"] != "none"]),
        "by_method": {mt: score([r for r in g if r["method"] == mt and r["kind"] != "none"])
                      for mt in sorted({r["method"] or "None" for r in g}) if mt != "None"},
        "no_gps": {"n": n - len(gps), "auto": sum(r["auto"] for r in out if not r["gps"]),
                   "kinds": Counter(r["kind"] for r in out if not r["gps"])},
        "review_notes_pairs": Counter(r["note"] for r in g if r["kind"] == "pair" and r["tier"] == "review").most_common(8),
        "networks": len(nets), "mad_points": sum(len(v) for v in by_town.values()),
    }
    res["name_placed_share"] = round(sum(r["tier"] != "review" for r in out) / n, 4)
    res["auto_share_all"] = round(sum(r["auto"] for r in out) / n, 4)
    res["house_address_share"] = round(len(addr) / n, 4)
    return res


if __name__ == "__main__":
    d = Path(sys.argv[1])
    res = main(d)
    (d / "ma_placement.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
