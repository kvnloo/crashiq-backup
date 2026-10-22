"""FARS (NHTSA Fatality Analysis Reporting System, public domain) as a location source for fatal crashes (#174).

User decision 2026-10-21 (docs/03): a fatal crash with no usable location gets its linked FARS point when that point
fits the report's streets (the same check as GPS); provenance `fars`. Otherwise it stays on the review list.

- Store: California rows of FARS `accident.csv`, one table per app database (`fars_accident`), with the file and load
  date per year in `fars_source`. Loading and the yearly refresh: data/reference/fars.md, backend/scripts/load_fars.py.
- Link (the Tester's verified rule, #166 / PR #172): same county (CCRS county code -> FIPS) and date, same number
  killed, time within LINK_MINUTES (FARS unknown time matches any); when more than one FARS crash fits, a road the
  report names breaks the tie; still more than one = ambiguous, never used. A FARS case is year + ST_CASE (case numbers
  restart every year).
- A usable point: inside California, not one of FARS's unknown codes, and not shared by 3+ FARS crashes.
"""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from .db import Database
from .names import route_numbers, same_core, street_key

LINK_MINUTES = 60
SHARED_MAX = 2              # a point used by 3+ FARS crashes is a placeholder, not a location
CA_FIPS = 6
CA_LAT, CA_LON = (32.4, 42.1), (-124.6, -114.0)


def fips(ccrs_county) -> int | None:
    """CCRS County Code (California's alphabetical 1-58) -> FIPS county code (1, 3, 5, ... 115)."""
    try:
        return 2 * int(str(ccrs_county).strip()) - 1
    except (TypeError, ValueError):
        return None


def case_key(year, st_case) -> str:
    return f"{int(year)}-{int(st_case)}"


# -- store -------------------------------------------------------------------------------------------
def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_csv(db: Database, path: Path | str, file_name: str | None = None) -> int:
    """Load the California rows of a FARS accident.csv (national, or already filtered), replacing each year it holds.
    Returns the rows loaded. Some years' files start with a byte-order mark (2021, 2022): read as utf-8-sig."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            if _int(r.get("STATE")) != CA_FIPS:
                continue
            rows.append((_int(r["YEAR"]), _int(r["ST_CASE"]), _int(r["COUNTY"]), _int(r.get("CITY")), _int(r["MONTH"]),
                         _int(r["DAY"]), _int(r.get("HOUR")), _int(r.get("MINUTE")), _int(r["FATALS"]) or 0,
                         _float(r.get("LATITUDE")), _float(r.get("LONGITUD")), r.get("TWAY_ID") or None,
                         r.get("TWAY_ID2") or None))
    if not rows:
        raise ValueError(f"{path}: no California (STATE 6) rows")
    with db.transaction() as conn:
        for year in sorted({r[0] for r in rows}):
            these = [r for r in rows if r[0] == year]
            conn.execute("DELETE FROM fars_accident WHERE year = ?", (year,))
            conn.executemany("INSERT INTO fars_accident VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", these)
            conn.execute("INSERT OR REPLACE INTO fars_source (year, file, rows, loaded_at) "
                         "VALUES (?, ?, ?, datetime('now'))", (year, file_name or Path(path).name, len(these)))
    return len(rows)


def years_loaded(db: Database) -> list[int]:
    return [r["year"] for r in db.query("SELECT year FROM fars_source ORDER BY year")]


# -- link ----------------------------------------------------------------------------------------------
def _minutes(r: dict) -> int | None:
    h, m = r.get("hour"), r.get("minute")
    if h is None or h > 23:
        return None                        # FARS 99 = unknown time: matches any
    return h * 60 + (0 if m is None or m > 59 else m)


def _names_road(ccrs_roads, fars_ways) -> bool:
    """A CCRS road and a FARS trafficway (TWAY_ID) name the same road: a shared route number or the same street."""
    for a in ccrs_roads:
        for b in fars_ways:
            if not a or not b:
                continue
            if route_numbers(a) & route_numbers(b):
                return True
            ka, kb = street_key(a), street_key(b)
            if ka and kb and same_core(ka, kb):
                return True
    return False


def link(db: Database, c: dict) -> tuple[str, dict | None]:
    """('linked', FARS row) | ('ambiguous', None) | ('unlinked', None) | ('no_fars_year', None) for one fatal crash."""
    t = _parse(c.get("reported_at"))
    county = fips(c.get("county_code"))
    if t is None or county is None:
        return "unlinked", None
    if not db.one("SELECT 1 FROM fars_source WHERE year = ?", (t.year,)):
        return "no_fars_year", None
    cands = db.query("SELECT * FROM fars_accident WHERE county = ? AND year = ? AND month = ? AND day = ? AND fatals = ?",
                     (county, t.year, t.month, t.day, int(c.get("killed") or 0)))
    cm = t.hour * 60 + t.minute
    cands = [r for r in cands if _minutes(r) is None or abs(_minutes(r) - cm) <= LINK_MINUTES]
    if len(cands) > 1:
        roads = [r for r in cands if _names_road([c.get("primary_road"), c.get("secondary_road")],
                                                 [r["tway_id"], r["tway_id2"]])]
        return ("linked", roads[0]) if len(roads) == 1 else ("ambiguous", None)
    return ("linked", cands[0]) if cands else ("unlinked", None)


def named_roads(c: dict) -> list[str]:
    """The roads the report names: placeholders (NOT STATED, UNKNOWN, blank) aren't roads."""
    from .crashes import _placeholder
    return [r for r in (c.get("primary_road"), c.get("secondary_road")) if r and not _placeholder(r)]


def on_named_roads(road_tags: list[dict], c: dict) -> bool:
    """Every road the report names runs at the point (OSM name or ref): both when it names two, the one when it names
    one (user decision 2026-10-22, docs/03; Palm Desert, #191: one long road matched a point 7.4 mi away)."""
    ways = [t.get(k) for t in road_tags for k in ("name", "ref", "alt_name", "old_ref") if t.get(k)]
    named = named_roads(c)
    return bool(named) and all(_names_road([r], ways) for r in named)


def _parse(s) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(s)[:19])
    except (TypeError, ValueError):
        return None


def point(db: Database, r: dict) -> tuple[float, float] | None:
    """The FARS row's point when usable: inside California (FARS writes 77.7777 / 88.8888 / 99.9999 for unknown) and
    not shared by 3+ FARS crashes (a placeholder)."""
    la, lo = r.get("latitude"), r.get("longitude")
    if la is None or lo is None or not (CA_LAT[0] <= la <= CA_LAT[1] and CA_LON[0] <= lo <= CA_LON[1]):
        return None
    n = db.one("SELECT COUNT(*) AS n FROM fars_accident WHERE ROUND(latitude, 5) = ROUND(?, 5) "
               "AND ROUND(longitude, 5) = ROUND(?, 5)", (la, lo))["n"]
    return (la, lo) if n <= SHARED_MAX else None
