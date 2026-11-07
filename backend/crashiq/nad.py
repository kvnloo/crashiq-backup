"""USDOT National Address Database (NAD) address points for house-address crashes (D5; user decision 2026-10-25,
docs/03, #264, #283).

A crash whose report gives a house number and street (locate._house_address) is placed at the NAD address point with
that number on that street in its city (its county when the crash is unincorporated): the points that match must be
one place (within ONE_PLACE_FT of each other, as the #264 measurement), and the spot is their mean. Approximate
("usually within 400 ft"; 86% within 400 ft of police GPS in #264), so it counts on segments, never at an intersection.

Source: NAD release r24, public domain, California rows filtered from the national text file
(knowledge/sources/us-nad.md). The CSV sits in data/cache/nad/ (downloaded once, user-approved 2026-10-25, never
committed); the index is built from it into SQLite on first use, with no network.
"""

from __future__ import annotations

import csv
import math
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from .names import StreetKey, drop_directional, same_core, street_key

RELEASE = "r24"
SCHEMA = 1
ONE_PLACE_FT = 1000.0
PLUS_MINUS_FT = 400
SOURCE = f"USDOT National Address Database ({RELEASE})"


def _keys(k: StreetKey) -> set[str]:
    return {k.core.replace(" ", ""), drop_directional(k).core.replace(" ", "")}


def _county_codes() -> dict[str, int]:
    from .settings import ROOT
    with (ROOT / "data" / "reference" / "caltrans_districts.csv").open(newline="") as f:
        return {r["county"].upper(): int(r["ccrs_county_code"]) for r in csv.DictReader(f)}


def ft(a: tuple[float, float], b: tuple[float, float]) -> float:
    dy = (a[0] - b[0]) * 364000
    dx = (a[1] - b[1]) * 364000 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


class NadIndex:
    def __init__(self, db_path: Path, csv_path: Path):
        self.db_path, self.csv_path = Path(db_path), Path(csv_path)
        self._ready = False
        self._lock = threading.Lock()            # one build at a time
        self._local = threading.local()          # per-thread read-only connections (#323)

    def ready(self) -> bool:
        """The index exists, or is built now from the CSV. False when there is no CSV (D5 then goes to review)."""
        with self._lock:
            if self._ready:
                return True
            if not self._built():
                if not self.csv_path.exists():
                    return False
                self._build()
            self._ready = True
            return True

    def _conn(self) -> sqlite3.Connection:
        """A read-only connection for this thread: one shared between server threads gives errors and wrong rows."""
        con = getattr(self._local, "con", None)
        if con is None:
            con = self._local.con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        return con

    def _built(self) -> bool:
        if not self.db_path.exists():
            return False
        with sqlite3.connect(self.db_path) as con:
            try:
                return int(con.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone()[0]) >= SCHEMA
            except (sqlite3.Error, TypeError):
                return False

    def _build(self) -> None:
        codes = _county_codes()
        tmp = self.db_path.with_suffix(".building")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.unlink(missing_ok=True)
        con = sqlite3.connect(tmp)
        con.execute("CREATE TABLE point (county INTEGER, number INTEGER, key TEXT, name TEXT, inc TEXT, post TEXT, "
                    "lat REAL, lon REAL)")
        con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        from .crashes import city_key
        batch, n = [], 0
        with self.csv_path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                cty = codes.get((r.get("County") or "").upper().replace(" COUNTY", "").strip())
                k = street_key(r.get("StNam_Full"))
                try:
                    num, lat, lon = int(r["Add_Number"]), float(r["Latitude"]), float(r["Longitude"])
                except (TypeError, ValueError):
                    continue
                if cty is None or k is None:
                    continue
                for key in _keys(k):
                    batch.append((cty, num, key, r["StNam_Full"], city_key(r.get("Inc_Muni")),
                                  city_key(r.get("Post_City")), lat, lon))
                n += 1
                if len(batch) >= 50000:
                    con.executemany("INSERT INTO point VALUES (?,?,?,?,?,?,?,?)", batch)
                    batch = []
        con.executemany("INSERT INTO point VALUES (?,?,?,?,?,?,?,?)", batch)
        con.execute("CREATE INDEX point_key ON point (county, number, key)")
        con.executemany("INSERT INTO meta VALUES (?,?)", [("schema", str(SCHEMA)), ("release", RELEASE),
                                                          ("points", str(n)), ("source", str(self.csv_path.name))])
        con.commit()
        con.close()
        tmp.replace(self.db_path)

    def lookup(self, county: int | None, city: str | None, number: int, k: StreetKey | None) -> dict | None:
        """{"lat", "lon", "points"} for the house number on the street in the crash's city, or None."""
        if k is None or county is None or not self.ready():
            return None
        from .crashes import city_key
        ck = city_key(city)
        rows = {r for key in _keys(k) for r in self._conn().execute(
            "SELECT name, inc, post, lat, lon FROM point WHERE county = ? AND number = ? AND key = ?",
            (int(county), int(number), key))}
        pts = []
        for name, inc, post, lat, lon in rows:
            nk = street_key(name)
            if nk is None or not same_core(k, nk) or (k.suffix and nk.suffix and k.suffix != nk.suffix):
                continue
            if ck and ck != "UNINCORPORATED" and ck not in (inc, post):
                continue
            pts.append((lat, lon))
        if not pts or max(ft(a, b) for a in pts for b in pts) > ONE_PLACE_FT:
            return None
        return {"lat": sum(p[0] for p in pts) / len(pts), "lon": sum(p[1] for p in pts) / len(pts), "points": len(pts)}


@dataclass
class Addresses:
    """The two D5 sources the placement step uses: NAD address points and the TIGER ADDRFEAT suggestion."""
    nad: NadIndex | None
    addrfeat: object | None


def addresses(nad_dir: Path, addrfeat_dir: Path) -> Addresses:
    from .addrfeat import Addrfeat
    from .sources.tiger_files import http_opener
    return Addresses(NadIndex(Path(nad_dir) / "nad_ca.sqlite", Path(nad_dir) / f"nad_ca_{RELEASE}.csv"),
                     Addrfeat(addrfeat_dir, opener=http_opener))
