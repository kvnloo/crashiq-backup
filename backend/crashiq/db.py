"""SQLite storage: one module owns the connection and the schema.

Migrations are an ordered list of SQL scripts. Each runs once; `schema_version` records how far
a database has got, so an existing file upgrades in place and a new file builds from scratch.
Later issues append to MIGRATIONS; never edit a migration that has shipped.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

MIGRATIONS: list[str] = [
    # 1 — #5 scaffold: generic HTTP cache for Overpass / CKAN responses
    """
    CREATE TABLE http_cache (
        key        TEXT PRIMARY KEY,
        source     TEXT NOT NULL,
        body       TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    # 2 — #6 study: project, mode, crash-history window
    """
    CREATE TABLE study (
        id                    TEXT PRIMARY KEY,
        name                  TEXT NOT NULL,
        mode                  TEXT NOT NULL,
        from_year             INTEGER NOT NULL,
        to_year               INTEGER NOT NULL,
        covid_years_in_window INTEGER NOT NULL,
        created_at            TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    # 3 — #7 network: drawn corridor, detected/edited intersections, segment AADT; study assignment settings
    """
    ALTER TABLE study ADD COLUMN radius_ft REAL NOT NULL DEFAULT 250;
    ALTER TABLE study ADD COLUMN buffer_ft REAL NOT NULL DEFAULT 100;
    CREATE TABLE corridor (
        study_id      TEXT PRIMARY KEY REFERENCES study(id) ON DELETE CASCADE,
        line_json     TEXT NOT NULL,
        length_ft     REAL NOT NULL,
        corridor_name TEXT,
        detected_at   TEXT NOT NULL
    );
    CREATE TABLE intersection (
        study_id     TEXT NOT NULL REFERENCES study(id) ON DELETE CASCADE,
        id           TEXT NOT NULL,
        name         TEXT NOT NULL,
        station_ft   REAL NOT NULL,
        lat          REAL NOT NULL,
        lon          REAL NOT NULL,
        osm_node_ids TEXT NOT NULL,
        control      TEXT NOT NULL,
        is_study     INTEGER NOT NULL DEFAULT 1,
        provenance   TEXT NOT NULL,
        name_source  TEXT NOT NULL,
        major_aadt   REAL,
        minor_aadt   REAL,
        PRIMARY KEY (study_id, id)
    );
    CREATE TABLE segment_aadt (
        study_id   TEXT NOT NULL REFERENCES study(id) ON DELETE CASCADE,
        segment_id TEXT NOT NULL,
        aadt       REAL NOT NULL,
        PRIMARY KEY (study_id, segment_id)
    );
    """,
    # 4 — #9 crash pull cache, one per study (re-pulled when the window or corridor changes)
    """
    CREATE TABLE crash_pull (
        study_id  TEXT PRIMARY KEY REFERENCES study(id) ON DELETE CASCADE,
        cache_key TEXT,
        pulled_at TEXT NOT NULL,
        payload   TEXT NOT NULL
    );
    """,
]


class Database:
    """Thread-safe wrapper around one SQLite file. FastAPI runs sync routes in a thread pool."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._lock = threading.RLock()
        self.migrate()

    # -- schema -------------------------------------------------------------------------------
    def migrate(self) -> int:
        with self._lock:
            self._conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
            row = self._conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
            current = row["v"] or 0
            for i, sql in enumerate(MIGRATIONS[current:], start=current + 1):
                self._conn.execute("BEGIN")
                try:
                    # executescript() would commit mid-way, so run statements one by one inside the tx
                    for stmt in _split(sql):
                        self._conn.execute(stmt)
                    self._conn.execute("INSERT INTO schema_version (version) VALUES (?)", (i,))
                    self._conn.execute("COMMIT")
                except Exception:
                    self._conn.execute("ROLLBACK")
                    raise
            return len(MIGRATIONS)

    # -- queries ------------------------------------------------------------------------------
    def query(self, sql: str, params: tuple | dict = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | dict = ()) -> dict | None:
        with self._lock:
            r = self._conn.execute(sql, params).fetchone()
            return dict(r) if r else None

    def execute(self, sql: str, params: tuple | dict = ()) -> int:
        """Run one write; returns rows affected."""
        with self._lock:
            return self._conn.execute(sql, params).rowcount

    def transaction(self):
        return _Tx(self)

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class _Tx:
    """`with db.transaction() as conn:` — all-or-nothing block of writes."""

    def __init__(self, db: Database):
        self.db = db

    def __enter__(self) -> sqlite3.Connection:
        self.db._lock.acquire()
        self.db._conn.execute("BEGIN")
        return self.db._conn

    def __exit__(self, exc_type, exc, tb):
        try:
            self.db._conn.execute("ROLLBACK" if exc_type else "COMMIT")
        finally:
            self.db._lock.release()
        return False


def _split(sql: str) -> list[str]:
    """Split a migration script into statements (no semicolons inside our DDL strings)."""
    return [s.strip() for s in sql.split(";") if s.strip()]
