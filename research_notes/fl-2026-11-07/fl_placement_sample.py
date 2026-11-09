"""Florida placement sample (2026-11-07): 2,000 Palm Beach County 2024 crashes from the Palm Beach MPO's open copy of
Signal Four Analytics (S4) crash events, placed by CrashIQ's locator from the report's street names with S4's mapped
point hidden, on a Census TIGER/Line 2024 street network for the county (12099).

Shared code is used as is. FL report names are pre-split here (fl_variants) and the would-be shared fixes are listed
in research_notes/fl-2026-11-07/fl-import.md. House-address crashes use Palm Beach County's Situs Addresses
(public domain per OpenAddresses us/fl/palm_beach.json), fetched only for the sample's streets.

Run (from the worktree):  PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python research_notes/fl-2026-11-07/fl_placement_sample.py
Writes research_notes/fl-2026-11-07/fl_placement_sample.json (`--summarize` re-reads the saved per-crash rows). Downloads go to ~/.hermes/cache/scratch/states/fl/.
"""

from __future__ import annotations

import itertools
import json
import math
import random
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from crashiq import locate, tiger
from crashiq.names import drop_directional, street_key
from crashiq.osm import Network, metres
from crashiq.sources import fl_s4

HERE = Path(__file__).resolve().parent
SCRATCH = Path.home() / ".hermes/cache/scratch/states/fl"
LAYER = "https://services5.arcgis.com/79IoFXBn9ZeqmVlC/arcgis/rest/services/pal_crash_event/FeatureServer/0"
SITUS = "https://services1.arcgis.com/ZWOoUZbtaYePLlPw/arcgis/rest/services/Situs%20Addresses/FeatureServer/0"
TIGER = "https://www2.census.gov/geo/tiger/TIGER2024/{k}/tl_2024_12099_{f}.zip"
SEED, N, YEAR = 20261107, 2000, 2024
UA = {"User-Agent": "CrashIQ/0.1"}


def post(url, **params):
    req = urllib.request.Request(url + "/query", data=urllib.parse.urlencode({**params, "f": "json"}).encode(), headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(body["error"])
    return body


def sample_features() -> list[dict]:
    cache = SCRATCH / "pb2024_sample_features.json"
    if not cache.exists():
        ids = post(LAYER, where=f"CRASH_YEAR={YEAR}", returnIdsOnly="true")["objectIds"]
        pick = sorted(random.Random(SEED).sample(ids, N))
        feats = []
        for i in range(0, N, 200):
            feats += post(LAYER, objectIds=",".join(map(str, pick[i:i + 200])), outFields="*", returnGeometry="false")["features"]
        cache.write_text(json.dumps(feats))
    return json.loads(cache.read_text())


def network() -> Network:
    paths = []
    for k, f in (("EDGES", "edges"), ("FEATNAMES", "featnames")):
        p = SCRATCH / "tiger" / f"tl_2024_12099_{f}.zip"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(TIGER.format(k=k, f=f), p)
        paths.append(p)
    return Network(tiger.elements(*paths))


# --- Florida report names -> names the shared key matches (would-be fixes to names.py, listed in fl-import.md) ---
_DIR = re.compile(r"\b(?:[NSEW]/B|[NSEW]B|NORTH ?BOUND|SOUTH ?BOUND|EAST ?BOUND|WEST ?BOUND)\b")
_MM = re.compile(r"\b(?:MM|MILE ?MARKER|MP|EXIT)\s*\d+(?:\.\d+)?\b")
_SUBS = [(re.compile(r"\b(?:STATE ROAD|STATE RD|ST RD|S\.R\.)\s*(?=\w*\d)"), "SR "),
         (re.compile(r"\b(?:COUNTY ROAD|COUNTY RD|CR)[ -]*(?=\w*\d)"), "CO RD "),
         (re.compile(r"\b(?:FLORIDA'?S? )?(?:TURNPIKE|TPKE)\b"), "SR 91"),
         (re.compile(r"\bINTERSTATE[ -]*(?=\d)"), "I-"),
         (re.compile(r"\bSR[ -]+(\d)"), r"SR \1")]


def fl_variants(name: str | None) -> list[str | None]:
    """'SR 806 (E ATLANTIC AVE)' -> ['SR 806', 'E ATLANTIC AVE']; 'S/B INTERSTATE 95 (STATE ROAD 9)' -> ['I-95', 'SR 9']."""
    if not name:
        return [None]
    t = _MM.sub(" ", _DIR.sub(" ", name.upper()))
    parts = [p for p in re.split(r"[()]", t) if p.strip()]
    out = []
    for p in parts:
        for rx, rep in _SUBS:
            p = rx.sub(rep, p)
        p = re.sub(r"\s+", " ", p).strip(" -/,")
        m = re.match(r"^((?:SR|CO RD|US|I)[ -]?\d+[A-Z]?)\s+(.+)$", p)   # 'SR 808 GLADES ROAD': route, then its name
        for q in ([m[1], m[2]] if m else [p]):
            if q and street_key(q) and q not in out:
                out.append(q)
    return out or [None]


def place_fl(net, crash, addresses=None):
    """First placement over the name variants (both streets must still meet at one intersection)."""
    first = None
    prim = fl_variants(crash["primary_road"])
    num = crash.get("house_number")
    sec = ([f"{num} {p}" for p in prim if p] if num and (crash["secondary_road"] or "").startswith(num)
           else fl_variants(crash["secondary_road"]))
    for a, b in itertools.product(prim, sec or [None]):
        pl = locate.place(net, {**crash, "primary_road": a, "secondary_road": b}, addresses=addresses)
        first = first or pl
        if pl.lat is not None:
            return pl
    return first


def situs_rows(streets: set[str]) -> list[tuple]:
    cache = SCRATCH / "pb_situs_sample.json"
    have = json.loads(cache.read_text()) if cache.exists() else {}
    for name in sorted(streets - set(have)):
        rows, off = [], 0
        while True:
            b = post(SITUS, where=f"UPPER(STREET_NAME)='{name.replace(chr(39), chr(39) * 2)}'", outSR=4326,
                     outFields="STREET_NO,STREET_PRE_DIR,STREET_NAME,STREET_SUFFIX,STREET_POST_DIR,ZIP_CITY",
                     resultOffset=off, resultRecordCount=1000)
            for f in b["features"]:
                a, g = f["attributes"], f.get("geometry") or {}
                if g.get("y") and a.get("STREET_NO"):
                    st = " ".join(x for x in (a["STREET_PRE_DIR"], a["STREET_NAME"], a["STREET_SUFFIX"], a["STREET_POST_DIR"]) if x)
                    rows.append((st, a["STREET_NO"], g["y"], g["x"], (a.get("ZIP_CITY") or "").upper()))
            if not b.get("exceededTransferLimit"):
                break
            off += 1000
        have[name] = rows
        cache.write_text(json.dumps(have))
    return [r for n in streets for r in have.get(n, [])]


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


_CTX = None


def _one(i):
    net, crashes, is_house, addr_index, gate = _CTX
    c, house = crashes[i], is_house[i]
    hidden = {**c, "lat": None, "lon": None}
    raw = locate.place(net, hidden)
    pl = place_fl(net, hidden, addresses=addr_index(c["city"]) if house else None)
    r = {"i": i, "road_system": c["road_system"], "freeway": c["is_freeway"], "offset_ft": c["offset_ft"],
         "two_streets": bool(c["primary_road"] and c["secondary_road"] and not house), "house": house,
         "gps": c["lat"] is not None, "tier_raw": raw.tier if raw.lat is not None else "review",
         "tier": pl.tier if pl.lat is not None else "review", "note": pl.note, "auto": False, "ft": None,
         "node_ft": None, "on": c["primary_road"], "from": c["secondary_road"]}
    if pl.lat is not None:
        r["auto"] = gate.auto(pl)
        if c["lat"] is not None:
            r["ft"] = metres((pl.lat, pl.lon), (c["lat"], c["lon"])) / 0.3048
            if pl.node is not None and pl.node in net.coord:
                r["node_ft"] = metres(net.coord[pl.node], (c["lat"], c["lon"])) / 0.3048
    return r


def _share(rs, key="ft", lim=250):
    have = [r for r in rs if r[key] is not None]
    k = sum(r[key] <= lim for r in have)
    return {"n": len(have), "within_250ft": k, "share": round(k / len(have), 4) if have else None,
            "low": round(wilson_low(k, len(have)), 4)}


_FWY = re.compile(r"\b(I-?\s?95|I95|INTERSTATE|TPKE|TURNPIKE|RAMP|SR[- ]?9\b|SR[- ]?91\b|STATE ROAD[- ]?91?\b)")


def summarize(res):
    placed = [r for r in res if r["tier"] != "review"]
    auto = [r for r in placed if r["auto"]]
    off = lambda r: ("none" if not r["offset_ft"] else "<=250" if r["offset_ft"] <= 250 else
                     "250-1000" if r["offset_ft"] <= 1000 else ">1000")
    dists = sorted(r["ft"] for r in placed if r["ft"] is not None)
    return {
        "gps_plausible": sum(r["gps"] for r in res), "two_streets": sum(r["two_streets"] for r in res),
        "house_address": sum(r["house"] for r in res),
        "named_any": sum(r["two_streets"] or r["house"] for r in res),
        "tiers_raw_names": dict(Counter(r["tier_raw"] for r in res)), "tiers": dict(Counter(r["tier"] for r in res)),
        "placed": len(placed), "auto": len(auto), "auto_by_tier": dict(Counter(r["tier"] for r in auto)),
        "accuracy_placed": _share(placed), "accuracy_auto": _share(auto),
        "accuracy_auto_not_freeway": _share([r for r in auto if not r["freeway"]]),
        "accuracy_auto_freeway": _share([r for r in auto if r["freeway"]]),
        # neither street a freeway, interchange or ramp (those need the freeway method, not a street pair)
        "accuracy_auto_no_freeway_names": _share([r for r in auto if not r["freeway"] and not _FWY.search(f"{r['on']} {r['from']}")]),
        "accuracy_auto_by_offset": {b: _share([r for r in auto if off(r) == b]) for b in ("none", "<=250", "250-1000", ">1000")},
        "accuracy_auto_intersection_node": _share(auto, "node_ft"),
        "accuracy_address": _share([r for r in placed if r["tier"] == "address"]),
        "median_ft": round(dists[len(dists) // 2]) if dists else None,
        "review_notes": dict(Counter(r["note"].split(":")[0] for r in res if r["tier"] == "review")),
        "far_auto_examples": [{k: r[k] for k in ("on", "from", "road_system", "offset_ft", "tier")} | {"ft": round(r["ft"])}
                              for r in auto if r["ft"] and r["ft"] > 250][:20],
    }


def main():
    if "--summarize" in sys.argv:            # re-summarize the saved per-crash rows without placing again
        old = json.loads((HERE / "fl_placement_sample.json").read_text())
        res = json.loads((SCRATCH / "fl_placement_rows.json").read_text())
        out = {k: old[k] for k in ("source", "area", "year", "seed", "n")} | summarize(res) | \
            {"situs_points_fetched": old["situs_points_fetched"]}
        (HERE / "fl_placement_sample.json").write_text(json.dumps(out, indent=1))
        print(json.dumps(out, indent=1))
        return
    feats = sample_features()
    crashes = fl_s4.read_features(feats)
    assert len(crashes) == N, len(crashes)
    net = network()
    gate = locate.Gate()
    is_house = [bool(c["house_number"]) and not (f["attributes"].get("FROM_INTERSECTION_OF") or "").strip()
                for c, f in zip(crashes, feats)]
    bare = set()
    for c, h in zip(crashes, is_house):
        for v in fl_variants(c["primary_road"]) if h else []:
            k = street_key(v)
            if k:
                bare.add(drop_directional(k).core)
    rows = situs_rows(bare)
    by_city: dict[str, locate.AddressIndex] = {}

    def addr_index(city):
        key = (city or "").upper()
        if key not in by_city:
            sel = [r[:4] for r in rows if key in ("", "UNINCORPORATED") or r[4] == key]
            by_city[key] = locate.AddressIndex(sel or [r[:4] for r in rows])
        return by_city[key]

    global _CTX
    _CTX = (net, crashes, is_house, addr_index, gate)
    import multiprocessing as mp
    with mp.get_context("fork").Pool(3) as pool:     # shared Mac: 3 workers; the network is shared copy-on-write
        res = pool.map(_one, range(N), chunksize=25)
    # per-crash results (no personal data) for re-analysis without re-placing
    with open(SCRATCH / "fl_placement_rows.json", "w") as fh:
        json.dump(res, fh)
    out = {"source": LAYER, "area": "Palm Beach County, FL (12099)", "year": YEAR, "seed": SEED, "n": N,
           **summarize(res), "situs_points_fetched": len(rows)}
    (HERE / "fl_placement_sample.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    sys.exit(main())
