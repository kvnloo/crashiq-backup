"""CCRS tables that data.ca.gov publishes as a file but hasn't loaded into its datastore (#196; user decision
2026-10-22, docs/03; proposal on #188).

Parties_2025 came out with `datastore_active = False`: the SQL API can't read it, but its CSV (~211 MB) downloads in
about 40 s. The server downloads such a file once, in the background, keeps only the columns CrashIQ reads
(~51 MB of SQLite for Parties 2025), and answers lookups by Collision Id from that copy.

- One `<resource id>.sqlite` per resource in the cache folder (default data/cache/ccrs_files/, never committed), with
  the resource's `last_modified` and the download date inside it.
- CHP re-modifies every file daily, so a copy is kept for REFRESH_DAYS before a newer `last_modified` is downloaded
  again; the old copy keeps answering until the new one is complete (written to a temp file, then renamed).
- Never blocks a pull. While a file isn't ready, or its download failed, that year stays missing and the #189 caveat
  shows; a failed download is retried after RETRY_MINUTES, and the pull picks the copy up once it's there.
"""

from __future__ import annotations

import csv
import os
import shutil
import sqlite3
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import ca_ccrs as cc

REFRESH_DAYS = 7
RETRY_MINUTES = 60
ID_CHUNK = 500
BATCH = 50_000

# opener(url) -> a binary file-like response
Opener = Callable[[str], object]


def http_opener(url: str):
    # data.ca.gov redirects to a signed storage URL that refuses HEAD; a ranged GET of the whole file works (#188)
    req = urllib.request.Request(url, headers={"User-Agent": "CrashIQ/0.1 (+crash safety analysis)",
                                               "Range": "bytes=0-"})
    return urllib.request.urlopen(req, timeout=600)


def inactive_resources(package: dict) -> dict[str, dict[int, dict]]:
    """{'parties': {2025: resource}, 'iwp': {...}}: CSV resources not in the datastore (Crashes are never read
    from a file: the pull's SQL filters need the datastore)."""
    out: dict[str, dict[int, dict]] = {"parties": {}, "iwp": {}}
    for res in package.get("resources", []):
        name = str(res.get("name", "")).lower().replace(" ", "")
        if res.get("datastore_active") or not res.get("url") or str(res.get("format", "")).upper() != "CSV":
            continue
        for table in out:
            prefix = cc.TABLE_PREFIX[table]
            tail = name[len(prefix):][:4] if name.startswith(prefix) else ""
            if tail.isdigit():
                out[table][int(tail)] = res
    return out


def _now_iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


class FileCache:
    def __init__(self, folder: Path | str, opener: Opener | None = None, now: Callable[[], float] = time.time,
                 background: bool = True):
        self.folder = Path(folder)
        self.opener = opener or http_opener
        self.now, self.background = now, background
        self._lock = threading.Lock()
        self._running: set[str] = set()
        self._failed: dict[str, tuple[float, str]] = {}      # resource id -> (when, why)

    def path(self, rid: str) -> Path:
        return self.folder / f"{rid}.sqlite"

    def meta(self, rid: str) -> dict | None:
        p = self.path(rid)
        if not p.exists():
            return None
        try:
            with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as con:
                m = dict(con.execute("SELECT key, value FROM meta").fetchall())
        except sqlite3.Error:
            return None
        m["columns"] = m.get("columns", "").split(",") if m.get("columns") else []
        m["missing"] = m.get("missing", "").split(",") if m.get("missing") else []
        return m

    def error(self, rid: str) -> str | None:
        hit = self._failed.get(rid)
        return hit[1] if hit else None

    def ready(self, res: dict, wanted: dict[str, list[str]]) -> dict | None:
        """The copy's metadata when one is there (and a refresh started if it's due), else None with the download
        started in the background. Never raises: a failed download is recorded and retried later."""
        rid = res["id"]
        m = self.meta(rid)
        if m is None:
            self._start(res, wanted)
            return self.meta(rid)             # there already when the download ran in this thread
        try:
            age_days = (self.now() - datetime.fromisoformat(m["downloaded_at"]).timestamp()) / 86400
        except (KeyError, ValueError):
            age_days = REFRESH_DAYS
        if age_days >= REFRESH_DAYS and str(res.get("last_modified") or "") != m.get("last_modified", ""):
            self._start(res, wanted)          # the current copy keeps answering until the new one is in place
        return m

    def columns(self, m: dict) -> dict[str, dict]:
        return {c: {"id": c, "type": "text"} for c in m["columns"]}

    def lookup(self, rid: str, ids: list[str]) -> list[dict]:
        rows: list[dict] = []
        with sqlite3.connect(f"file:{self.path(rid)}?mode=ro", uri=True) as con:
            con.row_factory = sqlite3.Row
            for i in range(0, len(ids), ID_CHUNK):
                chunk = [str(x) for x in ids[i:i + ID_CHUNK]]
                rows += [dict(r) for r in con.execute(
                    f"SELECT * FROM rows WHERE collision_id IN ({','.join('?' * len(chunk))})", chunk)]
        return rows

    # -- download ----------------------------------------------------------------------------------------------
    def _start(self, res: dict, wanted: dict[str, list[str]]) -> None:
        rid = res["id"]
        with self._lock:
            if rid in self._running:
                return
            failed = self._failed.get(rid)
            if failed and self.now() - failed[0] < RETRY_MINUTES * 60:
                return
            self._running.add(rid)
        if self.background:
            threading.Thread(target=self._run, args=(res, wanted), daemon=True).start()
        else:
            self._run(res, wanted)

    def _run(self, res: dict, wanted: dict[str, list[str]]) -> None:
        rid = res["id"]
        try:
            self._download(res, wanted)
            self._failed.pop(rid, None)
        except Exception as e:  # noqa: BLE001 - a failed download only keeps the caveat; the pull never fails
            self._failed[rid] = (self.now(), f"{type(e).__name__}: {e}"[:300])
        finally:
            with self._lock:
                self._running.discard(rid)

    def _download(self, res: dict, wanted: dict[str, list[str]]) -> None:
        rid = res["id"]
        self.folder.mkdir(parents=True, exist_ok=True)
        part, tmp = self.folder / f"{rid}.csv.part", self.folder / f"{rid}.sqlite.tmp"
        try:
            with self.opener(res["url"]) as r, open(part, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if tmp.exists():
                tmp.unlink()
            with open(part, newline="", encoding="utf-8-sig", errors="replace") as f:
                rd = csv.reader(f)
                header = [h.strip() for h in next(rd)]
                cols, missing = cc.resolve_columns([{"id": h} for h in header], wanted)
                if "collision_id" in missing:
                    raise ValueError(f"{res.get('name')}: no Collision Id column")
                names = list(cols)
                at = [header.index(cols[n]["id"]) for n in names]
                con = sqlite3.connect(tmp)
                con.execute(f"CREATE TABLE rows ({', '.join(f'{n} TEXT' for n in names)})")
                ins = f"INSERT INTO rows VALUES ({','.join('?' * len(names))})"
                n_rows, batch = 0, []
                for row in rd:
                    if not row:
                        continue
                    batch.append([(row[i].strip() or None) if i < len(row) else None for i in at])
                    if len(batch) >= BATCH:
                        con.executemany(ins, batch)
                        n_rows += len(batch)
                        batch = []
                con.executemany(ins, batch)
                n_rows += len(batch)
                con.execute("CREATE INDEX rows_collision ON rows (collision_id)")
                con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
                con.executemany("INSERT INTO meta VALUES (?, ?)", [
                    ("resource_id", rid), ("name", str(res.get("name") or "")), ("url", res["url"]),
                    ("last_modified", str(res.get("last_modified") or "")), ("downloaded_at", _now_iso(self.now())),
                    ("rows", str(n_rows)), ("columns", ",".join(names)), ("missing", ",".join(missing))])
                con.commit()
                con.close()
            os.replace(tmp, self.path(rid))
        finally:
            for p in (part, tmp):
                if p.exists():
                    p.unlink()
