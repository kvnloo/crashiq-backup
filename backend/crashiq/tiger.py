"""Census TIGER/Line roads as a street network for the locator (public domain, every US county).

Converts TIGER EDGES (road segments with topology node ids TNIDF/TNIDT and FULLNAME) plus FEATNAMES (alternate
names per segment) into the same element shape `osm.Network` reads, so the locator runs unchanged on TIGER.
Download: https://www2.census.gov/geo/tiger/TIGER2024/{EDGES,FEATNAMES}/tl_2024_<county fips>_{edges,featnames}.zip
"""

from __future__ import annotations

import io
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Callable


def _reader(zpath: Path, ext_wanted=(".shp", ".dbf", ".shx")):
    import shapefile
    z = zipfile.ZipFile(zpath)
    parts = {Path(n).suffix: io.BytesIO(z.read(n)) for n in z.namelist() if Path(n).suffix in ext_wanted}
    return shapefile.Reader(shp=parts.get(".shp"), dbf=parts[".dbf"], shx=parts.get(".shx"))


def elements(edges_zip: Path, featnames_zip: Path, keep: Callable[[float, float], bool] | None = None) -> dict:
    alt = defaultdict(set)
    fr = _reader(featnames_zip, (".dbf",))
    fields = [f[0] for f in fr.fields[1:]]
    for rec in fr.iterRecords():
        r = dict(zip(fields, rec))
        if r.get("FULLNAME"):
            alt[r["TLID"]].add(r["FULLNAME"].strip())
    er = _reader(edges_zip)
    efields = [f[0] for f in er.fields[1:]]
    els, coords, next_id = [], {}, [-1]

    def node_for(key, lat, lon):
        if key not in coords:
            coords[key] = (lat, lon)
            els.append({"type": "node", "id": key, "lat": lat, "lon": lon})
        return key

    for sr in er.iterShapeRecords():
        r = dict(zip(efields, sr.record))
        if not str(r.get("MTFCC", "")).startswith("S") or not (r.get("FULLNAME") or alt.get(r["TLID"])):
            continue                                       # roads only (S1100–S1780), named
        pts = [(y, x) for x, y in sr.shape.points]
        if len(pts) < 2:
            continue
        mid = pts[len(pts) // 2]
        if keep and not keep(*mid):
            continue
        ids = [node_for(int(r["TNIDF"]), *pts[0])]
        for p in pts[1:-1]:                                # shape points get private ids (never intersections)
            next_id[0] -= 1
            ids.append(node_for(next_id[0], *p))
        ids.append(node_for(int(r["TNIDT"]), *pts[-1]))
        names = {r["FULLNAME"].strip()} if r.get("FULLNAME") else set()
        names |= alt.get(r["TLID"], set())
        name = sorted(names)[0]
        others = sorted(names - {name})
        els.append({"type": "way", "id": int(r["TLID"]), "nodes": ids,
                    "tags": {"name": name, **({"alt_name": ";".join(others)} if others else {})}})
    return {"elements": els}
