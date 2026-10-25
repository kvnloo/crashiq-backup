"""Run 9 (#229; TIGER download approved by the user in the Tester session 2026-10-22): fetch every California
county's TIGER/Line roads into data/cache/tiger/<vintage>/ with the app's own TigerCache (one county at a time, in the
foreground), so the statewide coverage can build the OSM + TIGER network for any city. Counties already there are
skipped. Prints one line per county and an EXIT line.

Run: python tests/statewide/tiger_fetch.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from crashiq.sources import tiger_files  # noqa: E402


def main() -> None:
    fips = sorted(json.loads(tiger_files.BOXES.read_text())["counties"])
    tc = tiger_files.TigerCache(ROOT / "data" / "cache" / "tiger", background=False)
    t0 = time.time()
    for i, f in enumerate(fips, 1):
        had = tc.path(f).exists()
        ok = tc.ready(f)
        size = tc.path(f).stat().st_size // 1_000_000 if ok else 0
        print(f"[{i}/{len(fips)} {time.time() - t0:.0f}s] {f}: {'cached' if had else 'downloaded' if ok else 'FAILED'}"
              f" {size} MB {tc.error(f) or ''}", flush=True)
    missing = [f for f in fips if not tc.path(f).exists()]
    print(f"EXIT: {len(fips) - len(missing)} of {len(fips)} counties ready; missing {missing}", flush=True)


if __name__ == "__main__":
    main()
