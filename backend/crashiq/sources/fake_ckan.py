"""Offline CKAN datastore for tests and the demo mode: loads a fixture into SQLite and runs the *same* SQL the
app sends to data.ca.gov (we keep that SQL to the PostgreSQL/SQLite common subset)."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path


def _affinity(ckan_type: str | None) -> str:
    t = str(ckan_type or "").lower()
    return "NUMERIC" if t.startswith(("int", "numeric", "float", "double")) else "TEXT" if t == "text" else ""


class FakeCkan:
    def __init__(self, fixture: dict | Path, rows_max: int | None = None):
        data = json.loads(Path(fixture).read_text()) if isinstance(fixture, (str, Path)) else fixture
        self.package = data["package"]
        self.tables = data["tables"]
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self._lock = threading.Lock()
        self.db.row_factory = sqlite3.Row
        self.sql_log: list[str] = []
        self.rows_max = rows_max                  # emulates data.ca.gov's per-query row cap
        # PostgreSQL semantics: a double-quoted name is an identifier, never a string literal
        if hasattr(sqlite3, "SQLITE_DBCONFIG_DQS_DML"):
            self.db.setconfig(sqlite3.SQLITE_DBCONFIG_DQS_DML, False)
            self.db.setconfig(sqlite3.SQLITE_DBCONFIG_DQS_DDL, False)
        for rid, t in self.tables.items():
            # Column types from the CKAN field list, so SQLite compares like PostgreSQL does: a numeric column
            # matches the text literal '1' ("County Code" IN ('1'), #53). Untyped columns silently dropped every
            # no-coordinate row of the live fixtures.
            cols = ", ".join(f'"{f["id"]}" {_affinity(f.get("type"))}' for f in t["fields"])
            self.db.execute(f'CREATE TABLE "{rid}" ({cols})')
            names = [f["id"] for f in t["fields"]]
            self.db.executemany(f'INSERT INTO "{rid}" VALUES ({", ".join("?" * len(names))})',
                                [[r.get(n) for n in names] for r in t["rows"]])

    def __call__(self, action: str, params: dict) -> dict:
        if action == "package_show":
            return self.package
        if action == "datastore_search":
            t = self.tables[params["resource_id"]]
            return {"fields": [{"id": "_id", "type": "int"}] + t["fields"], "records": []}
        if action == "datastore_search_sql":
            self.sql_log.append(params["sql"])
            with self._lock:                    # one in-memory connection, many server threads (#323)
                rows = [dict(r) for r in self.db.execute(params["sql"]).fetchall()]
            if self.rows_max is not None and len(rows) > self.rows_max:
                return {"records": rows[:self.rows_max], "records_truncated": True}
            return {"records": rows}
        raise ValueError(f"unsupported action {action}")
