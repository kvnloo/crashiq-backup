"""Run backend/scripts/validate_geocode.py offline (#211): CCRS rows from the Tester's local mirror (CCRS mirror
2026-10-19) instead of the live datastore, LAPD truth from the cached 2024 open-data file (data/cache), every network
call blocked (no downloads). Run from a checkout's root with the caches in data/cache:

  CCRS_MIRROR=<Tester worktree>/data/statewide/ccrs_mirror.sqlite python tests/statewide/validate_geocode_la_offline.py [sf|la] [--network both]
"""
import os
import sqlite3
import sys
import urllib.request

MIRROR = os.environ.get("CCRS_MIRROR", "data/statewide/ccrs_mirror.sqlite")
def _no_net(*a, **k):
    raise SystemExit(f"network call blocked: {a[0] if a else k}")
urllib.request.urlopen = _no_net
sys.path.insert(0, "backend")
sys.path.insert(0, "backend/scripts")
from crashiq.sources import ca_ccrs  # noqa: E402
con = sqlite3.connect(MIRROR)
ca_ccrs.crash_resource_ids = lambda: {y: rid for rid, y in con.execute("SELECT rid, year FROM _meta WHERE tbl = 'crashes'")}
def _get(action, **kw):
    assert action == "datastore_search_sql", action
    cur = con.execute(kw["sql"])
    names = [d[0] for d in cur.description]
    return {"records": [{k: (None if v is None else str(v)) for k, v in zip(names, r)} for r in cur]}
ca_ccrs._get = _get
import validate_geocode as vg  # noqa: E402
vg.CITIES["la"] = vg.CITIES["la"][:3] + ((2024,),) + vg.CITIES["la"][4:]
CITY = sys.argv.pop(1) if len(sys.argv) > 1 and sys.argv[1] in ("sf", "la") else "la"
sys.argv = ["validate_geocode.py", "--city", CITY, "--split", "test", "--no-address"] + sys.argv[1:]
vg.main()
