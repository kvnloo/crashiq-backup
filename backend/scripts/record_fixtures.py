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

from crashiq import crashes, network  # noqa: E402
from crashiq.db import Database  # noqa: E402
from crashiq.sources import ca_ccrs as cc  # noqa: E402
from crashiq.sources.ckan import Ckan  # noqa: E402

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

    # CCRS: which real columns each logical field resolves to (the adapter's candidate lists are a guess
    # for fields the earlier spike didn't use), then one year's pull for the corridor.
    ckan = Ckan()
    res = cc.table_resources(ckan.get("package_show", id=cc.PACKAGE))
    report = {"resources": {t: {str(y): r for y, r in v.items()} for t, v in res.items()}, "columns": {}}
    for table, wanted in (("crashes", cc.CRASH_COLS), ("parties", cc.PARTY_COLS), ("iwp", cc.IWP_COLS)):
        year = max(res[table])
        fields = ckan.fields(res[table][year])
        got, missing = cc.resolve_columns(fields, wanted)
        report["columns"][table] = {"year": year, "fields": fields,
                                    "resolved": {k: v["id"] for k, v in got.items()}, "missing": missing}
        print(f"CCRS {table} {year}: {len(fields)} columns; missing logical fields: {missing or 'none'}")
    (OUT / "ccrs_columns.json").write_text(json.dumps(report, indent=1))
    out = crashes.pull({"from_year": 2023, "to_year": 2023, "radius_ft": 250, "buffer_ft": 100},
                       {"line": LINE, "corridor_name": found["corridor_name"]}, ckan)
    (OUT / "ccrs_crenshaw_2023.json").write_text(json.dumps(out, indent=1))
    print(f"CCRS Crenshaw 2023: {len(out['crashes'])} crashes; cleaning: {json.dumps(out['cleaning'])}")


if __name__ == "__main__":
    main()
