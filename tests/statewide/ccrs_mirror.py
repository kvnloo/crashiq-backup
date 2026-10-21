"""A local mirror of the CCRS datastore, so the app's own pull runs for every city without hammering data.ca.gov.

`build()` downloads, once, the columns the app reads (resolved with the app's own `resolve_columns`) for every
Crashes / Parties / InjuredWitnessPassengers table in the study years, into one SQLite file with the real column
types. `Mirror` answers the three CKAN actions the app calls (`package_show`, `datastore_search` for fields,
`datastore_search_sql`) from that file, the same way the app's test double `FakeCkan` does: the SQL the app sends
to data.ca.gov is kept to the PostgreSQL/SQLite common subset, so it runs here unchanged.

Limits (stated in the workbook's Method sheet): row caps and server errors of the live API are not reproduced, and
LIKE is case-insensitive in SQLite (the app always compares UPPER() on both sides, so results are the same).
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from crashiq.sources import ca_ccrs as cc  # noqa: E402

DUMP = "https://data.ca.gov/datastore/dump/{rid}?{q}"
WANTED = {"crashes": {**cc.CRASH_COLS, "report_number": ["Report Number"], "city_inc": ["City Is Incorporated"]},
          "parties": cc.PARTY_COLS, "iwp": cc.IWP_COLS}
SQL_TYPE = {"numeric": "NUMERIC", "int": "INTEGER", "int4": "INTEGER", "int8": "INTEGER", "float8": "REAL"}
INDEX = {"crashes": ["Collision Id", "County Code", "City Name", "NCIC Code"], "parties": ["CollisionId"],
         "iwp": ["CollisionId"]}


def _get(action: str, **params) -> dict:
    url = cc.API + action + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)["result"]


def build(db_path: Path, cache_dir: Path, years: list[int], log=print) -> None:
    """Download what's missing and load it. Re-running skips tables already loaded."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    pkg_file = cache_dir / "package.json"
    if not pkg_file.exists():
        pkg_file.write_text(json.dumps(_get("package_show", id=cc.PACKAGE)))
    pkg = json.loads(pkg_file.read_text())
    res = cc.table_resources(pkg)
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE IF NOT EXISTS _meta (rid TEXT PRIMARY KEY, tbl TEXT, year INT, fields TEXT, rows INT)")
    done = {r[0] for r in con.execute("SELECT rid FROM _meta")}
    for tbl in ("crashes", "parties", "iwp"):
        for y in years:
            rid = res[tbl].get(y)
            if not rid or rid in done:
                if not rid:
                    log(f"  {tbl} {y}: not published on data.ca.gov")
                continue
            fields = [f for f in _get("datastore_search", resource_id=rid, limit=0)["fields"] if f["id"] != "_id"]
            got, _ = cc.resolve_columns(fields, WANTED[tbl])
            keep = [f for f in fields if f["id"] in {g["id"] for g in got.values()} | {"IsDeleted"}]
            csv_path = cache_dir / f"{tbl}_{y}_{rid[:8]}.csv"
            if not csv_path.exists():
                q = urllib.parse.urlencode({"fields": ",".join(f["id"] for f in keep)})
                log(f"  downloading {tbl} {y} ({len(keep)} columns)")
                tmp = csv_path.with_suffix(".part")
                urllib.request.urlretrieve(DUMP.format(rid=rid, q=q), tmp)
                tmp.rename(csv_path)
            cols = ", ".join(f'"{f["id"]}" {SQL_TYPE.get(f["type"], "TEXT")}' for f in keep)
            con.execute(f'DROP TABLE IF EXISTS "{rid}"')
            con.execute(f'CREATE TABLE "{rid}" ({cols})')
            n = 0
            with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
                rd = csv.DictReader(f)
                names = [k["id"] for k in keep]
                ins = f'INSERT INTO "{rid}" VALUES ({", ".join("?" * len(names))})'
                batch = []
                for r in rd:
                    batch.append([(r.get(k) if r.get(k) != "" else None) for k in names])
                    if len(batch) == 20000:
                        con.executemany(ins, batch)
                        n += len(batch)
                        batch = []
                con.executemany(ins, batch)
                n += len(batch)
            for c in INDEX[tbl]:
                if c in names:
                    con.execute(f'CREATE INDEX "ix_{rid[:8]}_{c}" ON "{rid}" ("{c}")')
            con.execute("INSERT OR REPLACE INTO _meta VALUES (?,?,?,?,?)", (rid, tbl, y, json.dumps(keep), n))
            con.commit()
            log(f"  loaded {tbl} {y}: {n:,} rows")
    con.close()


class Mirror:
    """CKAN transport for `crashiq.sources.ckan.Ckan`: (action, params) -> result."""

    def __init__(self, db_path: Path, cache_dir: Path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        if hasattr(sqlite3, "SQLITE_DBCONFIG_DQS_DML"):     # PostgreSQL: "x" is an identifier, never a string
            self.db.setconfig(sqlite3.SQLITE_DBCONFIG_DQS_DML, False)
        self.fields = {r["rid"]: json.loads(r["fields"]) for r in self.db.execute("SELECT rid, fields FROM _meta")}
        pkg = json.loads((cache_dir / "package.json").read_text())
        # Only tables in the mirror are "datastore active": a study year outside it reads as not published.
        pkg["resources"] = [{**r, "datastore_active": r["id"] in self.fields} for r in pkg["resources"]]
        self.package = pkg
        self.queries = 0

    def __call__(self, action: str, params: dict) -> dict:
        if action == "package_show":
            return self.package
        if action == "datastore_search":
            return {"fields": [{"id": "_id", "type": "int"}] + self.fields[params["resource_id"]], "records": []}
        if action == "datastore_search_sql":
            self.queries += 1
            return {"records": [dict(r) for r in self.db.execute(params["sql"]).fetchall()]}
        raise ValueError(f"unsupported action {action}")
