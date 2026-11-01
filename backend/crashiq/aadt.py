"""State-highway traffic volumes for crash rates (#287; user decision 2026-10-26, docs/03). Caltrans Traffic Census
Program, public: the annual traffic-volume and truck AADT workbooks at
https://dot.ca.gov/programs/traffic-operations/census (config/aadt.json lists the files by count year).

- Count points: one row per point (route, county, postmile), with the AADT just behind it (BACK) and just ahead of it
  (AHEAD). A count year runs October to September (Caltrans).
- Segment join: the count points of one line (route + route suffix, county, postmile suffix) in postmile order. Between
  two points the volume changes (on 2024's 6,527 segments the AHEAD of one point and the BACK of the next differ on
  2,662, by 20% or more on 943), so a crash takes the leg of the nearer point that faces it: the AHEAD AADT of the
  point behind it in the first half of the segment, the BACK AADT of the point ahead in the second half (#287: "BACK
  leg before a point, AHEAD leg after it"). The two halves are the pieces rates are computed on. A blank AHEAD ends
  the line there: route breaks ("BREAK IN RTE", "ROUTE BREAK AHEAD") are never bridged. A crash's segment comes from
  its derived postmile (#248).
- Years: each crash uses its own count year; a year after the newest loaded file uses the newest, labelled
  `latest_used`; a year before the first loaded file gets nothing.
- Trucks: the truck workbook has a row per leg (B behind, A ahead) at fewer points; trucks with 3 or more axles are
  TRK_3 + TRK_4 + TRK_5 (docs/03 truck definition).
- Ramps: the district ramp ADT workbooks, one row per ramp (route, county, postmile, description) with ten years of
  counts (YR_<year>); Caltrans counts ramps on rotation. Every listed edition is loaded and, where editions overlap,
  the newest edition's value wins. 1001 and 999 are codes, not counts (runs of 1001 ending in 999 on closed ramps, a
  lone 999 between real counts, in every district), so they count as missing (#287 point 3). A ramp's ADT for a year
  is the latest count at or before it, labelled with its year, never a later one (#287 point 2).
- Cache: data/cache/aadt/caltrans_aadt_<download date>.sqlite (never committed), downloaded in the background the
  first time it's needed, refreshed after REFRESH_DAYS, or at once when it predates SCHEMA (a copy without ramps).
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

CONFIG = json.loads((Path(__file__).parent / "config" / "aadt.json").read_text())
YEARS = {int(y): v for y, v in CONFIG["years"].items()}
END_TOLERANCE_MI = 0.05     # PM decision on #289 (a): at a line's first and last count points only
REFRESH_DAYS = 365
RETRY_MINUTES = 60
SOURCE = "Caltrans Traffic Census Program"
SCHEMA = 2                  # 2: ramp table (#287 ramps)
RAMP_PLACEHOLDERS = (999, 1001)
RAMP_MAX_AGE = 5                    # years; an older ramp count gives no rate (user decision 2026-11-01)

# the workbooks name the same column differently from year to year
ALIASES = {"ROUTE": "RTE", "ROUTE_SFX": "RTE_SFX", "COUNTY": "CNTY", "LOCATION DESCRIPTION": "DESCRIPTION",
           "POSTMILE": "PM", "DIST": "DISTRICT"}


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "CrashIQ/0.1 (+crash safety analysis)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def count_year(when) -> int | None:
    """The Caltrans count year (October to September) of a crash date."""
    try:
        d = datetime.fromisoformat(str(when)[:19])
    except ValueError:
        return None
    return d.year + 1 if d.month >= 10 else d.year


def _txt(v) -> str:
    return "" if v is None else str(v).strip()


def _num(v) -> float | None:
    s = _txt(v).replace(",", "")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _int(v) -> int | None:
    x = _num(v)
    return None if x is None else int(round(x))


def _rows(data: bytes):
    """The data sheet's rows as dicts with one spelling of every column (the first sheet is the preface)."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = next(w for w in wb.worksheets if not w.title.strip().lower().startswith("preface"))
    it = ws.iter_rows(values_only=True)
    head = [ALIASES.get(_txt(h).upper(), _txt(h).upper()) for h in next(it)]
    for r in it:
        if any(v not in (None, "", " ") for v in r):
            yield {h: v for h, v in zip(head, r) if h}


def _key(r: dict) -> tuple:
    return (_txt(r.get("RTE")).lstrip("0"), _txt(r.get("RTE_SFX")), _txt(r.get("CNTY")), _txt(r.get("PM_PFX")),
            _num(r.get("PM")), _txt(r.get("PM_SFX")))


class AadtCache:
    def __init__(self, folder: Path | str, years: dict | None = None, get: Callable[[str], bytes] | None = None,
                 now: Callable[[], float] = time.time, background: bool = True):
        self.folder = Path(folder)
        self.years = years or YEARS
        self.get = get or http_get
        self.now, self.background = now, background
        self._lock = threading.Lock()
        self._running = False
        self._failed: tuple[float, str] | None = None
        self._local = threading.local()          # per-thread read-only connections (#323)

    # -- the copy ------------------------------------------------------------------------------------------------
    def newest(self) -> Path | None:
        files = sorted(self.folder.glob("caltrans_aadt_*.sqlite"))
        return files[-1] if files else None

    def ready(self) -> Path | None:
        p = self.newest()
        if p is None or (self.now() - p.stat().st_mtime) / 86400 >= REFRESH_DAYS or self._schema(p) < SCHEMA:
            self._start()
            p = self.newest()
        return p

    def _schema(self, p: Path) -> int:
        """The copy's schema; an older copy keeps serving until the new one is in."""
        if getattr(self, "_schema_of", (None,))[0] != p:
            with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as con:
                row = con.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone()
            self._schema_of = (p, int(row[0]) if row else 1)
        return self._schema_of[1]

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
        except Exception as e:  # noqa: BLE001 - no AADT (so no rates) meanwhile; nothing else depends on it
            self._failed = (self.now(), f"{type(e).__name__}: {e}"[:300])
        finally:
            with self._lock:
                self._running = False

    def _download(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        day = datetime.fromtimestamp(self.now(), timezone.utc).strftime("%Y-%m-%d")
        out = self.folder / f"caltrans_aadt_{day}.sqlite"
        tmp = out.with_suffix(".tmp")
        if tmp.exists():
            tmp.unlink()
        con = sqlite3.connect(tmp)
        con.execute("CREATE TABLE point (year INTEGER, route TEXT, route_suffix TEXT, county TEXT, prefix TEXT, pm REAL, "
                    "suffix TEXT, description TEXT, back_aadt INTEGER, ahead_aadt INTEGER, back_peak_hour INTEGER, "
                    "ahead_peak_hour INTEGER)")
        con.execute("CREATE TABLE truck (year INTEGER, route TEXT, route_suffix TEXT, county TEXT, prefix TEXT, pm REAL, "
                    "suffix TEXT, leg TEXT, description TEXT, vehicle_aadt INTEGER, truck_aadt INTEGER, "
                    "trk_2 INTEGER, trk_3 INTEGER, trk_4 INTEGER, trk_5 INTEGER)")
        con.execute("CREATE TABLE ramp (route TEXT, route_suffix TEXT, county TEXT, prefix TEXT, pm REAL, suffix TEXT, "
                    "description TEXT, district TEXT, year INTEGER, adt INTEGER, edition INTEGER)")
        sources, ramps, placeholders = [], {}, 0
        try:
            for year, files in sorted(self.years.items()):
                for kind, url in files.items():
                    if kind == "ramps":
                        for u in url:
                            sources.append((year, kind, u))
                            placeholders += _ramp_rows(self.get(u), year, ramps)
                        continue
                    data = self.get(url)
                    sources.append((year, kind, url))
                    for r in _rows(data):
                        k = _key(r)
                        if not k[0] or k[4] is None:
                            continue
                        if kind == "volumes":
                            con.execute("INSERT INTO point VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                        (year, *k, _txt(r.get("DESCRIPTION")), _int(r.get("BACK_AADT")),
                                         _int(r.get("AHEAD_AADT")), _int(r.get("BACK_PEAK_HOUR")),
                                         _int(r.get("AHEAD_PEAK_HOUR"))))
                        else:
                            con.execute("INSERT INTO truck VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                        (year, *k, _txt(r.get("LEG")).upper(), _txt(r.get("DESCRIPTION")),
                                         _int(r.get("VEHICLE_AADT_TOTAL")), _int(r.get("TOT_TRK_AADT")),
                                         *(_int(r.get(f"TRK_{n}_AXLE")) for n in (2, 3, 4, 5))))
            if not con.execute("SELECT COUNT(*) FROM point").fetchone()[0]:
                raise RuntimeError("the traffic-volume files had no count points")
            con.executemany("INSERT INTO ramp VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            [(*k, dist, y, adt, ed) for (k, y), (adt, ed, dist) in ramps.items()])
            con.execute("CREATE INDEX point_line ON point (route, county, year)")
            con.execute("CREATE INDEX truck_line ON truck (route, county, year)")
            con.execute("CREATE INDEX ramp_line ON ramp (route, county, pm)")
            con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
            con.executemany("INSERT INTO meta VALUES (?, ?)", [("downloaded", day), ("sources", json.dumps(sources)),
                                                               ("schema", str(SCHEMA)),
                                                               ("ramp_placeholders", str(placeholders))])
            con.commit()
        finally:
            con.close()
        os.replace(tmp, out)

    def db(self) -> sqlite3.Connection | None:
        """A read-only connection to the newest copy, one per thread: the server answers requests on several threads
        at once, and a connection shared between them gives errors and wrong rows (#323)."""
        p = self.ready()
        if p is None:
            return None
        con = getattr(self._local, "con", None)
        if con is None or con[0] != p:
            con = self._local.con = (p, sqlite3.connect(f"file:{p}?mode=ro", uri=True))
        return con[1]

    # -- the join ------------------------------------------------------------------------------------------------
    def _year(self, con: sqlite3.Connection, table: str, year: int) -> tuple[int, bool] | None:
        have = [y for (y,) in con.execute(f"SELECT DISTINCT year FROM {table} ORDER BY year")]
        if not have or year < have[0]:
            return None
        if year in have:
            return year, False
        return (max(have), True) if year > max(have) else (max(y for y in have if y < year), True)

    def segment(self, route: str, county: str, pm: float, year: int, route_suffix: str = "",
                suffix: str = "", prefix: str = "") -> dict | None:
        """The count segment a postmile lies on, with its AADT for that count year; None where there is none."""
        con = self.db()
        if con is None or pm is None:
            return None
        y = self._year(con, "point", year)
        if y is None:
            return None
        rows = self._line(con, "point", y[0], route, route_suffix, county, suffix,
                          "pm, prefix, description, back_aadt, ahead_aadt")
        out = self._pick(_around(rows, pm), pm, prefix)
        return {"year": y[0], "wanted_year": year, "latest_used": y[1], **out} if out else None

    @staticmethod
    def _pick(ab: tuple, pm: float, prefix: str = "") -> dict | None:
        """The leg that applies at a postmile between count points a and b (rows: pm, prefix, description, back, ahead).
        - Between two points: the nearer point's leg facing the crash, split at the midpoint.
        - Ends differ in postmile prefix (#287 point 1): never measured across; the crash takes the leg of the end
          whose prefix it shares (else the point ahead's BACK), and the piece has no length.
        - Up to END_TOLERANCE_MI before a line's first point or past its last (PM, #289 a): that point's facing leg,
          labelled `aadt_end_tolerance`. A blank AHEAD is a route break and is never bridged (#289 b)."""
        a, b = ab
        if a is None and b is not None and b[0] - pm <= END_TOLERANCE_MI + 1e-9 and b[3] is not None:
            return _seg(b, b, b[3], {"from_pm": pm, "to_pm": b[0], "leg": f"back of {b[2]}"}, end=True)
        if b is None and a is not None and pm - a[0] <= END_TOLERANCE_MI + 1e-9 and a[4] is not None:
            return _seg(a, a, a[4], {"from_pm": a[0], "to_pm": pm, "leg": f"ahead of {a[2]}"}, end=True)
        if a is None or b is None or a[4] is None:
            return None
        if a[1] != b[1]:
            use_b = prefix != a[1] and b[3] is not None
            leg = {"from_pm": None, "to_pm": None, "leg": f"back of {b[2]}" if use_b else f"ahead of {a[2]}"}
            return _seg(a, b, b[3] if use_b else a[4], leg)
        mid = round((a[0] + b[0]) / 2, 3)
        second = pm >= mid and b[3] is not None           # the second half takes the next point's BACK leg
        piece = {"from_pm": mid if second else a[0], "to_pm": b[0] if second else mid,
                 "leg": f"back of {b[2]}" if second else f"ahead of {a[2]}"}
        return _seg(a, b, b[3] if second else a[4], piece)

    def truck_segment(self, route: str, county: str, pm: float, year: int, route_suffix: str = "",
                      suffix: str = "") -> dict | None:
        """Trucks on the segment between truck count points: the ahead (A) leg of the point behind."""
        con = self.db()
        if con is None or pm is None:
            return None
        y = self._year(con, "truck", year)
        if y is None:
            return None
        rows = self._line(con, "truck", y[0], route, route_suffix, county, suffix,
                          "pm, prefix, description, leg, truck_aadt, trk_3, trk_4, trk_5")
        ahead = [r for r in rows if r[3] == "A"]
        pts = sorted({r[0] for r in rows})
        a = max((r for r in ahead if r[0] <= pm), key=lambda r: r[0], default=None)
        nxt = [p for p in pts if p > pm]
        if a is None or not nxt or a[4] is None:
            return None
        three = None if None in a[5:8] else sum(a[5:8])
        return {"year": y[0], "wanted_year": year, "latest_used": y[1], "truck_aadt": a[4], "trucks_3plus": three,
                "length_mi": round(nxt[0] - a[0], 3), "from": {"pm": a[0], "description": a[2]}, "to": {"pm": nxt[0]}}

    def ramps_near(self, route: str, county: str, pm: float, mi: float, route_suffix: str = "") -> list[dict]:
        """The Caltrans ramps within `mi` of a postmile on one route and county, with their counts by year."""
        con = self.db()
        if con is None or pm is None:
            return []
        out = {}
        q = ("SELECT route, route_suffix, county, prefix, pm, suffix, description, district, year, adt FROM ramp "
             "WHERE route = ? AND route_suffix = ? AND county = ? AND pm BETWEEN ? AND ? ORDER BY pm")
        for *k, dist, y, adt in con.execute(q, (str(route).lstrip("0"), route_suffix or "", county, pm - mi - 1e-9,
                                                pm + mi + 1e-9)):
            r = out.setdefault(tuple(k), {"id": "|".join(map(str, k)), "route": k[0], "route_suffix": k[1],
                                          "county": k[2], "prefix": k[3], "pm": k[4], "suffix": k[5],
                                          "description": k[6], "district": dist, "by_year": {}})
            if adt is not None:
                r["by_year"][y] = adt
        return list(out.values())

    @staticmethod
    def ramp_adt(ramp: dict, year: int) -> dict | None:
        """The latest count at or before the year, with its year; never a later one (#287 point 2). A count more than
        RAMP_MAX_AGE years before the year is too old to use (user decision 2026-11-01): adt None, too_old True."""
        ys = [y for y in ramp["by_year"] if y <= year]
        if not ys:
            return None
        cy = max(ys)
        if year - cy > RAMP_MAX_AGE:
            return {"adt": None, "count_year": cy, "too_old": True}
        return {"adt": ramp["by_year"][cy], "count_year": cy}

    def _line(self, con, table, year, route, route_suffix, county, suffix, cols):
        q = (f"SELECT {cols} FROM {table} WHERE year = ? AND route = ? AND county = ? AND route_suffix = ? "
             "AND suffix = ? ORDER BY pm")
        args = (year, str(route).lstrip("0"), county, route_suffix or "")
        rows = con.execute(q, (*args, suffix or "")).fetchall()
        if not rows and suffix:                       # an independent-alignment postmile with no points of its own
            rows = con.execute(q, (*args, "")).fetchall()
        return rows

    def for_crash(self, c: dict) -> dict | None:
        """The segment of a crash on a state route, by its derived postmile (#248) and its count year."""
        p = c.get("postmile")
        y = count_year(c.get("reported_at") or c.get("date"))
        if not p or y is None:
            return None
        s = self.segment(p["route"], p["county"], p["pm"], y, p.get("route_suffix") or "", p.get("suffix") or "",
                         p.get("prefix") or "")
        if s is None:
            return None
        label = f"{SOURCE}, {s['year']} AADT" + (" (latest available)" if s["latest_used"] else "")
        return {**s, "source": label}


def _ramp_rows(data: bytes, edition: int, out: dict) -> int:
    """A district ramp workbook into out[(ramp key, year)] = (ADT, edition, district), the newest edition winning;
    returns how many placeholder values (1001, 999) were left out."""
    skipped = 0
    for r in _rows(data):
        k = _key(r)
        if not k[0] or k[4] is None:
            continue
        key = (*k, " ".join(_txt(r.get("LOCATION_DESC")).upper().split()))
        for col, v in r.items():
            if not col.startswith("YR_") or not col[3:].isdigit():
                continue
            n = _int(v)
            if n in RAMP_PLACEHOLDERS:
                skipped += 1
                continue
            if n is None:
                continue
            was = out.get((key, int(col[3:])))
            if was is None or was[1] <= edition:
                out[(key, int(col[3:]))] = (n, edition, _txt(r.get("DISTRICT")))
    return skipped


def _seg(a, b, aadt, piece: dict, end: bool = False) -> dict:
    lengths = None not in (piece["from_pm"], piece["to_pm"])
    return {"aadt": aadt, "piece": {**piece, "length_mi": round(piece["to_pm"] - piece["from_pm"], 3) if lengths else None},
            "length_mi": round(b[0] - a[0], 3),
            "from": {"pm": a[0], "prefix": a[1], "description": a[2], "ahead_aadt": a[4]},
            "to": {"pm": b[0], "prefix": b[1], "description": b[2], "back_aadt": b[3]},
            "prefix_change": a[1] != b[1], "aadt_end_tolerance": end}


def _around(rows: list, pm: float):
    """The count point at or behind the postmile, and the next one ahead of it."""
    a = b = None
    for r in rows:
        if r[0] <= pm:
            a = r
        elif b is None:
            b = r
            break
    return a, b
