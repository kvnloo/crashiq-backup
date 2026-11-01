"""Caltrans postmile for a placed state-highway crash (#248; user decision 2026-10-23, docs/03). Looked up by code from
the public "SHN Postmiles Tenth" layer, the same layer, download method and vintage as the Tester's measurement:
https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/SHN_Postmiles_Tenth/FeatureServer/0 (Caltrans,
public). It doesn't change placement: the postmile is derived from where CrashIQ placed the crash, and says so.

- The layer: a point every 0.1 mile along every state route, each side of a divided road on its own (AlignCode Left /
  Right, Direction NB / SB / EB / WB). Postmiles restart at county lines and carry a prefix (R, M, ... realignments)
  and a suffix (independent alignments).
- Lookup: the crash's route (from its road names) and point; the segment between two consecutive points of one line
  (route, county, prefix, suffix, alignment) nearest the crash, within MAX_M; the postmile interpolated along it. A
  stated travel direction picks that side's points. Gaps wider than MAX_GAP_MI between points are never bridged.
- Cache: data/cache/postmiles/shn_postmiles_tenth_<download date>.sqlite (never committed), downloaded in the
  background the first time it's needed and refreshed after REFRESH_DAYS. The layer reports no edit date, so the
  download date is the vintage.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .geo import LocalProjection
from .names import route_numbers

URL = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/SHN_Postmiles_Tenth/FeatureServer/0/query"
FIELDS = ("OBJECTID", "Route", "RteSuffix", "County", "PMPrefix", "PM", "PMSuffix", "Odometer", "AlignCode",
          "Direction")
PAGE = 2000
MAX_M = 100.0
MAX_GAP_MI = 0.15
REFRESH_DAYS = 365
RETRY_MINUTES = 60
TRAVEL = {"N": "NB", "S": "SB", "E": "EB", "W": "WB"}
ONE_PLACE_FT = 528.0          # matches of one postmile within 0.1 mi (the two sides of a divided road) are one place
# Caltrans county abbreviations by CCRS county code (alphabetical, 1-58); the layer's County values
COUNTY = dict(enumerate("ALA ALP AMA BUT CAL COL CC DN ED FRE GLE HUM IMP INY KER KIN LAK LAS LA MAD MRN MPA MEN MER "
                        "MOD MNO MON NAP NEV ORA PLA PLU RIV SAC SBT SBD SD SF SJ SLO SM SB SCL SCR SHA SIE SIS SOL "
                        "SON STA SUT TEH TRI TUL TUO VEN YOL YUB".split(), start=1))


def http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "CrashIQ/0.1 (+crash safety analysis)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def label(p: dict) -> str:
    """Caltrans style: LA-405 PM R12.345."""
    return f"{p['county']}-{p['route']}{p['route_suffix'] or ''} PM {p['prefix'] or ''}{p['pm']:.3f}{p['suffix'] or ''}"


class PostmileCache:
    def __init__(self, folder: Path | str, get: Callable[[str], dict] | None = None, now: Callable[[], float] = time.time,
                 background: bool = True):
        self.folder = Path(folder)
        self.get = get or http_get
        self.now, self.background = now, background
        self._lock = threading.Lock()
        self._running = False
        self._failed: tuple[float, str] | None = None
        self._con: tuple[Path, sqlite3.Connection] | None = None

    # -- the copy ------------------------------------------------------------------------------------------------
    def newest(self) -> Path | None:
        files = sorted(self.folder.glob("shn_postmiles_tenth_*.sqlite"))
        return files[-1] if files else None

    def ready(self) -> Path | None:
        """The newest copy (a refresh starts when it's a year old); without one, the download starts and None."""
        p = self.newest()
        if p is None or (self.now() - p.stat().st_mtime) / 86400 >= REFRESH_DAYS:
            self._start()
            p = self.newest()
        return p

    def error(self) -> str | None:
        return self._failed[1] if self._failed else None

    def _start(self) -> None:
        with self._lock:
            if self._running or (self._failed and self.now() - self._failed[0] < RETRY_MINUTES * 60):
                return
            self._running = True
        if self.background:
            threading.Thread(target=self._run, daemon=True).start()
        else:
            self._run()

    def _run(self) -> None:
        try:
            self._download()
            self._failed = None
        except Exception as e:  # noqa: BLE001 - no postmile is shown meanwhile; nothing else depends on it
            self._failed = (self.now(), f"{type(e).__name__}: {e}"[:300])
        finally:
            with self._lock:
                self._running = False

    def _download(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        day = datetime.fromtimestamp(self.now(), timezone.utc).strftime("%Y-%m-%d")
        out = self.folder / f"shn_postmiles_tenth_{day}.sqlite"
        tmp = out.with_suffix(".tmp")
        if tmp.exists():
            tmp.unlink()
        con = sqlite3.connect(tmp)
        con.execute("CREATE TABLE pm (id INTEGER PRIMARY KEY, route TEXT, route_suffix TEXT, county TEXT, prefix TEXT, "
                    "pm REAL, suffix TEXT, odometer REAL, align TEXT, direction TEXT, lat REAL, lon REAL)")
        offset, n = 0, 0
        try:
            while True:
                q = urllib.parse.urlencode({"where": "1=1", "outFields": ",".join(FIELDS), "outSR": 4326, "f": "json",
                                            "orderByFields": "OBJECTID", "resultOffset": offset,
                                            "resultRecordCount": PAGE})
                page = self.get(f"{URL}?{q}")
                if "error" in page:
                    raise RuntimeError(str(page["error"])[:200])
                feats = page.get("features") or []
                rows = []
                for f in feats:
                    a, g = f.get("attributes") or {}, f.get("geometry") or {}
                    if g.get("x") is None or a.get("PM") is None:
                        continue
                    rows.append((a["OBJECTID"], str(a.get("Route") or "").strip(), (a.get("RteSuffix") or "").strip(),
                                 (a.get("County") or "").strip(), (a.get("PMPrefix") or "").strip(), float(a["PM"]),
                                 (a.get("PMSuffix") or "").strip(), a.get("Odometer"), (a.get("AlignCode") or "").strip(),
                                 (a.get("Direction") or "").strip(), g["y"], g["x"]))
                con.executemany("INSERT OR REPLACE INTO pm VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
                n += len(rows)
                offset += len(feats)
                if not feats or not page.get("exceededTransferLimit"):
                    break
            if n == 0:
                raise RuntimeError("the postmile layer returned no points")
            con.execute("CREATE INDEX pm_lat ON pm (lat)")
            con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
            con.executemany("INSERT INTO meta VALUES (?, ?)", [("source", URL), ("downloaded", day), ("rows", str(n))])
            con.commit()
        finally:
            con.close()
        os.replace(tmp, out)

    # -- lookup ----------------------------------------------------------------------------------------------------
    def _db(self) -> sqlite3.Connection | None:
        p = self.ready()
        if p is None:
            return None
        if self._con is None or self._con[0] != p:
            self._con = (p, sqlite3.connect(f"file:{p}?mode=ro", uri=True, check_same_thread=False))
        return self._con[1]

    def lookup(self, lat: float, lon: float, routes: set[str], travel: str | None = None) -> dict | None:
        con = self._db()
        if con is None or not routes:
            return None
        return nearest(con, lat, lon, routes, travel)

    def places(self, route: str, county: str, pm: float, prefix: str | None = None) -> list[dict]:
        """The distinct places of one postmile on a route in a county (#319): interpolated between the layer's tenth
        points on every line (alignment, prefix, suffix) that spans it, the lines within ONE_PLACE_FT averaged. A
        prefix (R, M...) the report gives keeps only those lines; without one, a realignment can make two places."""
        con = self._db()
        if con is None:
            return []
        return places(con, route, county, pm, prefix)

    def at(self, route: str, county: str, pm: float, prefix: str | None = None) -> dict | None:
        """{"lat", "lon"} of a postmile when it is exactly one place, else None."""
        found = self.places(route, county, pm, prefix)
        return found[0] if len(found) == 1 else None

    def for_crash(self, c: dict) -> dict | None:
        """The derived postmile of a placed crash on a state route, or None."""
        if c.get("lat") is None or c.get("lon") is None:
            return None
        roads = " ".join(str(c.get(f) or "") for f in ("primary_road", "secondary_road"))
        routes = route_numbers(roads)
        if not routes:
            return None
        from .freeway import _travel
        p = self.lookup(c["lat"], c["lon"], routes, _travel(str(c.get("primary_road") or "")))
        return {**p, "label": label(p), "derived": True} if p else None


def nearest(con: sqlite3.Connection, lat: float, lon: float, routes: set[str], travel: str | None) -> dict | None:
    d = MAX_M / 111_000 * 3
    marks = ",".join("?" * len(routes))
    rows = con.execute(f"SELECT route, route_suffix, county, prefix, pm, suffix, odometer, align, direction, lat, lon "
                       f"FROM pm WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? AND route IN ({marks})",
                       (lat - d, lat + d, lon - d * 1.3, lon + d * 1.3, *sorted(routes))).fetchall()
    if not rows:
        return None
    proj = LocalProjection.around([(lat, lon)])
    p = proj.to_xy(lat, lon)
    lines: dict[tuple, list] = {}
    for r in rows:
        lines.setdefault(r[:4] + (r[5], r[7]), []).append(r)
    best = None
    for key, pts in lines.items():
        pts.sort(key=lambda r: (r[6] if r[6] is not None else r[4]))
        for a, b in zip(pts, pts[1:]):
            if abs(b[4] - a[4]) > MAX_GAP_MI:
                continue
            ax, bx = proj.to_xy(a[9], a[10]), proj.to_xy(b[9], b[10])
            dist, t = _seg(p, ax, bx)
            dist_m = dist / 3.28084
            if dist_m > MAX_M:
                continue
            side = 0 if not travel or TRAVEL.get(travel) == a[8] else 1     # the stated side first
            cand = (side, dist_m, key, a, b, t)
            if best is None or cand[:2] < best[:2]:
                best = cand
    if best is None:
        return None
    _, dist_m, key, a, b, t = best
    return {"route": key[0], "route_suffix": key[1], "county": key[2], "prefix": key[3], "suffix": key[4],
            "align": key[5], "direction": a[8], "pm": round(a[4] + t * (b[4] - a[4]), 3), "distance_m": round(dist_m, 1)}


def places(con: sqlite3.Connection, route: str, county: str, pm: float, prefix: str | None) -> list[dict]:
    rows = con.execute("SELECT route_suffix, prefix, suffix, align, pm, lat, lon FROM pm WHERE route = ? AND county = ? "
                       "AND pm BETWEEN ? AND ?", (str(route).lstrip("0"), county, pm - 0.2, pm + 0.2)).fetchall()
    lines: dict[tuple, list] = {}
    for r in rows:
        if prefix is None or r[1] == prefix:
            lines.setdefault(r[:4], []).append(r)
    hits = []
    for pts in lines.values():
        pts.sort(key=lambda r: r[4])
        for a, b in zip(pts, pts[1:]):
            if a[4] - 1e-4 <= pm <= b[4] + 1e-4 and b[4] - a[4] <= MAX_GAP_MI:
                t = 0.0 if b[4] == a[4] else min(1.0, max(0.0, (pm - a[4]) / (b[4] - a[4])))
                hits.append((a[5] + t * (b[5] - a[5]), a[6] + t * (b[6] - a[6])))
                break
    out: list[list] = []
    for h in hits:                                     # group the lines' points into places
        grp = next((g for g in out if _ft(g[0], h) <= ONE_PLACE_FT), None)
        if grp is None:
            out.append([h])
        else:
            grp.append(h)
    return [{"lat": sum(p[0] for p in g) / len(g), "lon": sum(p[1] for p in g) / len(g)} for g in out]


def _ft(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 364000, (a[1] - b[1]) * 364000 * math.cos(math.radians(a[0])))


def _seg(p, a, b) -> tuple[float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy)), t
