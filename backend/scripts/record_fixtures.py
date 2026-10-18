"""Record LIVE responses as test fixtures. Run on a machine that can reach the internet (the build
sandbox can't):

    .venv/bin/python backend/scripts/record_fixtures.py

Writes tests/fixtures/live/*.json. Compare them with the hand-built fixtures (same corridor:
Crenshaw Blvd, Marine Ave → 132nd St) and replace the hand-built ones once they agree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from crashiq import network  # noqa: E402
from crashiq.db import Database  # noqa: E402

LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]
OUT = ROOT / "tests" / "fixtures" / "live"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = Database(":memory:")
    osm = network.fetch_overpass(db, network.overpass_query(LINE))
    (OUT / "overpass_crenshaw.json").write_text(json.dumps(osm, indent=1))
    found = network.detect(osm, LINE)
    print(f"Overpass: {len(osm['elements'])} elements; corridor = {found['corridor_name']}")
    for i in found["intersections"]:
        print(f"  {i['station_ft']:8.0f} ft  {i['control']:8s} {i['name']}")


if __name__ == "__main__":
    main()
