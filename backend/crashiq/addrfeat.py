"""Census TIGER/Line ADDRFEAT address ranges: the review suggestion for a house-address crash NAD doesn't cover (D5;
user decision 2026-10-25, docs/03, #283). A suggestion only, never an automatic placement (65% within 400 ft of police
GPS in #264).

The number is interpolated along the address-range feature whose range on the matching side (odd or even) holds it.
Local files only (data/cache/tiger_addrfeat/<year>/tl_<year>_<county fips>_addrfeat.zip, downloaded once,
user-approved 2026-10-25), so there are no runtime network calls.
"""

from __future__ import annotations

import csv
import io
import math
import threading
import zipfile
from pathlib import Path

from .names import StreetKey, drop_directional, same_core, street_key

SOURCE = "Census TIGER/Line ADDRFEAT address ranges"


def _fips() -> dict[int, str]:
    from .settings import ROOT
    with (ROOT / "data" / "reference" / "caltrans_districts.csv").open(newline="") as f:
        return {int(r["ccrs_county_code"]): r["fips"] for r in csv.DictReader(f)}


def _num(v) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _along(pts: list[tuple[float, float]], f: float) -> tuple[float, float]:
    """The point a fraction f of the way along a polyline of (lat, lon)."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    goal, run = f * sum(seg), 0.0
    for (a, b), d in zip(zip(pts, pts[1:]), seg):
        if d and run + d >= goal:
            t = (goal - run) / d
            return a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
        run += d
    return pts[-1]


class Addrfeat:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self._county: dict[str, dict[str, list]] = {}
        self._lock = threading.Lock()

    def _file(self, fips: str) -> Path | None:
        hits = sorted(self.folder.glob(f"**/tl_*_{fips}_addrfeat.zip")) if self.folder.exists() else []
        return hits[-1] if hits else None

    def _load(self, fips: str) -> dict[str, list]:
        with self._lock:
            if fips in self._county:
                return self._county[fips]
            idx: dict[str, list] = {}
            path = self._file(fips)
            if path is not None:
                import shapefile
                z = zipfile.ZipFile(path)
                parts = {Path(n).suffix: io.BytesIO(z.read(n)) for n in z.namelist()}
                r = shapefile.Reader(shp=parts[".shp"], shx=parts[".shx"], dbf=parts[".dbf"])
                fields = [f[0] for f in r.fields[1:]]
                for sr in r.iterShapeRecords():
                    rec = dict(zip(fields, sr.record))
                    k = street_key(rec.get("FULLNAME"))
                    if k is None or len(sr.shape.points) < 2:
                        continue
                    pts = [(y, x) for x, y in sr.shape.points]
                    feat = (rec["FULLNAME"], pts, *(_num(rec.get(c)) for c in ("LFROMHN", "LTOHN", "RFROMHN", "RTOHN")))
                    for key in {k.core.replace(" ", ""), drop_directional(k).core.replace(" ", "")}:
                        idx.setdefault(key, []).append(feat)
            self._county[fips] = idx
            return idx

    def lookup(self, county: int | None, number: int, k: StreetKey | None) -> dict | None:
        """{"lat", "lon"} interpolated on the one range that holds the number, or None."""
        fips = _fips().get(int(county)) if county is not None else None
        if k is None or fips is None:
            return None
        idx = self._load(fips)
        hits = []
        for name, pts, l0, l1, r0, r1 in {id(f): f for key in {k.core.replace(" ", ""),
                                                               drop_directional(k).core.replace(" ", "")}
                                          for f in idx.get(key, ())}.values():
            nk = street_key(name)
            if nk is None or not same_core(k, nk) or (k.suffix and nk.suffix and k.suffix != nk.suffix):
                continue
            for a, b in ((l0, l1), (r0, r1)):
                if a is None or b is None or a % 2 != number % 2 or not min(a, b) <= number <= max(a, b):
                    continue
                f = 0.5 if a == b else (number - a) / (b - a)
                hits.append(_along(pts, f))
        if len(hits) != 1:
            return None
        return {"lat": hits[0][0], "lon": hits[0][1]}
