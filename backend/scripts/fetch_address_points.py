"""Download county address points that fill the gaps in USDOT NAD (#393) into data/cache/nad/addr_<name>.csv, in
NAD's own columns, so nad.NadIndex reads them next to nad_ca_r24.csv. Sources and field mappings:
data/reference/address_points.json. ArcGIS REST layers only, paged by object id. Never committed (like NAD).

Run:  python backend/scripts/fetch_address_points.py ca_orange [ca_los_angeles ...]   (or --all)
      --measure   also fetch sources whose licence isn't cleared yet, for measuring only: never upload those files
      --out DIR   write somewhere else than the app's NAD directory
Then rebuild the index: python backend/scripts/build_nad.py
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data" / "reference" / "address_points.json"
COLUMNS = ["County", "Add_Number", "StNam_Full", "Inc_Muni", "Post_City", "Latitude", "Longitude", "Source"]
UA = {"User-Agent": "CrashIQ/0.1 (address points for crash locations)"}


def _get(url: str, params: dict, opener=urllib.request.urlopen, tries: int = 4) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    for k in range(tries):
        try:
            d = json.loads(opener(urllib.request.Request(full, headers=UA), timeout=120).read())
            if "error" in d:
                raise ValueError(d["error"])
            return d
        except Exception:                     # network blips and ArcGIS 'error' bodies: back off and retry
            if k == tries - 1:
                raise
            time.sleep(5 * 2 ** k)
    raise AssertionError


def _xy(geom: dict) -> tuple[float, float] | None:
    """lon, lat of a point, or the mean vertex of a polygon's outer ring (parcels with a situs address)."""
    if not geom:
        return None
    if "x" in geom:
        return geom["x"], geom["y"]
    ring = (geom.get("rings") or [[]])[0]
    return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)) if ring else None


def rows(src: dict, attrs: dict, geom: dict) -> list | None:
    """One NAD-column row, or None when there's no whole house number, no street or no location."""
    num = str(attrs.get(src["number"]) or "").strip()
    street = " ".join(str(attrs.get(f) or "").strip() for f in src["street"]).split()
    xy = _xy(geom)
    if not num.isdigit() or not street or xy is None:
        return None
    city = lambda f: (str(attrs.get(f) or "").strip() if f else "")  # noqa: E731
    return [src["county"], int(num), " ".join(street), city(src.get("inc")), city(src.get("post")),
            round(xy[1], 7), round(xy[0], 7), f"{src['county']} County address points"]


def fetch(src: dict, out_dir: Path, opener=urllib.request.urlopen, page: int | None = None) -> int:
    info = _get(src["url"], {"f": "json"}, opener)
    oid = info.get("objectIdField") or next(f["name"] for f in info["fields"] if f["type"] == "esriFieldTypeOID")
    page = page or int(info.get("maxRecordCount") or 1000)
    fields = sorted({oid, src["number"], *src["street"], *(f for f in (src.get("inc"), src.get("post")) if f)})
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"addr_{src['name']}.csv"
    tmp = dest.with_suffix(".part")
    last, n = -1, 0
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        while True:
            d = _get(src["url"] + "/query", {"where": f"({src.get('where') or '1=1'}) AND {oid} > {last}",
                                  "outFields": ",".join(fields), "orderByFields": oid, "outSR": 4326,
                                  "returnGeometry": "true", "resultRecordCount": page, "f": "json"}, opener)
            feats = d.get("features") or []
            if not feats:
                break
            for ft in feats:
                r = rows(src, ft.get("attributes") or {}, ft.get("geometry") or {})
                if r:
                    w.writerow(r)
                    n += 1
            last = max(ft["attributes"][oid] for ft in feats)
    os.replace(tmp, dest)                     # a half-finished download never reaches the index
    return n


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT / "backend"))
    from crashiq.settings import Settings
    out = a.out or Settings().nad_dir
    sources = json.loads(REGISTRY.read_text())["sources"]
    for s in sources:
        if not (a.all or s["name"] in a.names):
            continue
        if not s.get("licence_ok") and not a.measure:
            print(f"skip {s['name']}: licence not cleared ({s.get('licence')}); --measure fetches it for measuring only")
            continue
        t = time.time()
        print(f"{s['name']}: {fetch(s, out):,} address points in {time.time() - t:.0f} s -> {out}", flush=True)


if __name__ == "__main__":
    main()
