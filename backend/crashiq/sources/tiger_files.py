"""Census TIGER/Line roads per California county, for the OSM + TIGER street network (#229; user decision and download
approval 2026-10-22, docs/03). US Census Bureau, public domain.

- Source: TIGER/Line EDGES (road segments: geometry, MTFCC, FULLNAME, TLID, topology node ids) and FEATNAMES
  (alternate names per segment) for one county: https://www2.census.gov/geo/tiger/TIGER<vintage>/{EDGES,FEATNAMES}/
  tl_<vintage>_06<county>_{edges,featnames}.zip. Los Angeles is ~50 MB + ~9 MB; most counties are a few MB.
- Kept: named roads only (MTFCC S...), as `data/cache/tiger/<vintage>/<county fips>.sqlite` (never committed):
  one row per segment with its bounding box and points, and its names. Nothing else from the files is kept.
- Refresh: by vintage (config/tiger.json): a new vintage is a new folder, downloaded when first needed.
- Never blocks a pull: a county not yet downloaded starts in the background, the network is OSM only meanwhile and
  the pull log says so; the pull after the download uses it. A failed download is retried after an hour.
- Which counties: the padded county boxes in data/reference/ca_county_boxes.json that contain a point of the line.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import threading
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Callable

from ..settings import ROOT

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config" / "tiger.json").read_text())
BOXES = ROOT / "data" / "reference" / "ca_county_boxes.json"
RETRY_MINUTES = 60
URL = "https://www2.census.gov/geo/tiger/TIGER{v}/{kind}/tl_{v}_06{fips}_{low}.zip"


def http_opener(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "CrashIQ/0.1 (+crash safety analysis)"})
    return urllib.request.urlopen(req, timeout=600)


@lru_cache(maxsize=1)
def _boxes() -> dict[str, list[float]]:
    return {f: c["box"] for f, c in json.loads(BOXES.read_text())["counties"].items()}


def counties_for(points) -> list[str]:
    """County FIPS (3 digits) whose padded box holds any of these (lat, lon) points."""
    out = set()
    for la, lo in points:
        out |= {f for f, (s, w, n, e) in _boxes().items() if s <= la <= n and w <= lo <= e}
    return sorted(out)


class TigerCache:
    def __init__(self, folder: Path | str, vintage: int | None = None, opener: Callable | None = None,
                 now: Callable[[], float] = time.time, background: bool = True):
        self.vintage = int(vintage or CONFIG["vintage"])
        self.folder = Path(folder) / str(self.vintage)
        self.opener = opener or http_opener
        self.now, self.background = now, background
        self._lock = threading.Lock()
        self._running: set[str] = set()
        self._failed: dict[str, tuple[float, str]] = {}

    def path(self, fips: str) -> Path:
        return self.folder / f"{fips}.sqlite"

    def error(self, fips: str) -> str | None:
        hit = self._failed.get(fips)
        return hit[1] if hit else None

    def ready(self, fips: str) -> bool:
        """The county's copy is there; if not, its download is started (in the background) and False returned."""
        if self.path(fips).exists():
            return True
        self._start(fips)
        return self.path(fips).exists()

    def edges_in(self, fips: str, bbox: tuple[float, float, float, float]) -> list[dict]:
        """Named road segments whose box meets bbox (s, w, n, e): {tlid, mtfcc, names, pts, tnidf, tnidt}."""
        s, w, n, e = bbox
        with sqlite3.connect(f"file:{self.path(fips)}?mode=ro", uri=True) as con:
            rows = con.execute("SELECT tlid, mtfcc, names, pts, tnidf, tnidt FROM edge WHERE maxlat >= ? AND minlat <= ? "
                               "AND maxlon >= ? AND minlon <= ?", (s, n, w, e)).fetchall()
        return [{"tlid": r[0], "mtfcc": r[1], "names": json.loads(r[2]), "pts": json.loads(r[3]), "tnidf": r[4],
                 "tnidt": r[5], "county": fips} for r in rows]

    # -- download -----------------------------------------------------------------------------------------------
    def _start(self, fips: str) -> None:
        with self._lock:
            if fips in self._running:
                return
            failed = self._failed.get(fips)
            if failed and self.now() - failed[0] < RETRY_MINUTES * 60:
                return
            self._running.add(fips)
        if self.background:
            threading.Thread(target=self._run, args=(fips,), daemon=True).start()
        else:
            self._run(fips)

    def _run(self, fips: str) -> None:
        try:
            self._download(fips)
            self._failed.pop(fips, None)
        except Exception as e:  # noqa: BLE001 - the network stays OSM only; the pull never fails because of it
            self._failed[fips] = (self.now(), f"{type(e).__name__}: {e}"[:300])
        finally:
            with self._lock:
                self._running.discard(fips)

    def _fetch(self, kind: str, fips: str) -> bytes:
        url = URL.format(v=self.vintage, kind=kind, fips=fips, low=kind.lower())
        buf = io.BytesIO()
        with self.opener(url) as r:
            shutil.copyfileobj(r, buf, 1 << 20)
        return buf.getvalue()

    def _download(self, fips: str) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        edges, feat = self._fetch("EDGES", fips), self._fetch("FEATNAMES", fips)
        tmp = self.folder / f"{fips}.sqlite.tmp"
        if tmp.exists():
            tmp.unlink()
        try:
            n = build(edges, feat, tmp, {"vintage": str(self.vintage), "county": fips,
                                          "downloaded_at": datetime.fromtimestamp(self.now(), timezone.utc)
                                          .isoformat(timespec="seconds")})
            if n == 0:
                raise ValueError(f"county {fips}: no named roads in the TIGER file")
            os.replace(tmp, self.path(fips))
        finally:
            if tmp.exists():
                tmp.unlink()


def _reader(data: bytes, wanted=(".shp", ".dbf", ".shx")):
    import shapefile
    z = zipfile.ZipFile(io.BytesIO(data))
    parts = {Path(n).suffix: io.BytesIO(z.read(n)) for n in z.namelist() if Path(n).suffix in wanted}
    return shapefile.Reader(shp=parts.get(".shp"), dbf=parts[".dbf"], shx=parts.get(".shx"))


def build(edges_zip: bytes, featnames_zip: bytes, out: Path, meta: dict) -> int:
    """TIGER EDGES + FEATNAMES zips -> the trimmed SQLite copy. Returns the number of road segments kept."""
    alt: dict[int, list[str]] = {}
    fr = _reader(featnames_zip, (".dbf",))
    fields = [f[0] for f in fr.fields[1:]]
    for rec in fr.iterRecords():
        r = dict(zip(fields, rec))
        if r.get("FULLNAME"):
            alt.setdefault(int(r["TLID"]), []).append(str(r["FULLNAME"]).strip())
    er = _reader(edges_zip)
    efields = [f[0] for f in er.fields[1:]]
    con = sqlite3.connect(out)
    con.execute("CREATE TABLE edge (tlid INTEGER PRIMARY KEY, mtfcc TEXT, names TEXT, pts TEXT, tnidf INTEGER, "
                "tnidt INTEGER, minlat REAL, maxlat REAL, minlon REAL, maxlon REAL)")
    rows, n = [], 0
    for sr in er.iterShapeRecords():
        r = dict(zip(efields, sr.record))
        if not str(r.get("MTFCC", "")).startswith("S"):
            continue                                   # roads only (S1100-S1780)
        tlid = int(r["TLID"])
        names = list(dict.fromkeys(([str(r["FULLNAME"]).strip()] if r.get("FULLNAME") else []) + alt.get(tlid, [])))
        pts = [(round(y, 6), round(x, 6)) for x, y in sr.shape.points]
        if not names or len(pts) < 2:
            continue
        las, los = [p[0] for p in pts], [p[1] for p in pts]
        rows.append((tlid, r.get("MTFCC"), json.dumps(names), json.dumps(pts), int(r["TNIDF"]), int(r["TNIDT"]),
                     min(las), max(las), min(los), max(los)))
        if len(rows) >= 20_000:
            con.executemany("INSERT OR REPLACE INTO edge VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
            n += len(rows)
            rows = []
    con.executemany("INSERT OR REPLACE INTO edge VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    n += len(rows)
    con.execute("CREATE INDEX edge_lat ON edge (minlat)")
    con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    con.executemany("INSERT INTO meta VALUES (?, ?)", [*meta.items(), ("segments", str(n))])
    con.commit()
    con.close()
    return n
