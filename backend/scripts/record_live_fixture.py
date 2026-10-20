"""Record a LIVE crash pull as an offline fixture (#53): every CKAN response the real pull gets, replayable by
FakeCkan with the same SQL. Run on a machine with internet:

    .venv/bin/python backend/scripts/record_live_fixture.py crenshaw
    .venv/bin/python backend/scripts/record_live_fixture.py unioncity

Writes tests/fixtures/live/ckan_<name>.json (CKAN tables: real resource ids, real column lists, the rows the pull
read) and overpass_<name>.json. The rows are public CCRS records (data.ca.gov, CHP, public domain).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from crashiq import crashes, network  # noqa: E402
from crashiq.db import Database  # noqa: E402
from crashiq.sources.ckan import Ckan, http_transport  # noqa: E402

CORRIDORS = {   # the hand fixture's corridor (Crenshaw, Marine Ave -> 132nd St) and a 0%-GPS city (#35)
    "crenshaw": [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)],
    "unioncity": [(37.577737, -122.080690), (37.572678, -122.078362), (37.570229, -122.076430),   # the user's
                  (37.567032, -122.070723), (37.564174, -122.065744), (37.562133, -122.064457),  # study: Union City
                  (37.560092, -122.063770)],                                                     # Blvd, Dyer->Paseo Padre
}
ROW_KEYS = ("Collision Id", "CollisionId", "InjuredWitPassId", "PartyNumber")
OUT = ROOT / "tests" / "fixtures" / "live"


class Recorder:
    def __init__(self):
        self.package, self.fields, self.rows = None, {}, {}

    def __call__(self, action: str, params: dict, timeout: float = 120) -> dict:
        res = http_transport(action, params, timeout)
        if action == "package_show":
            self.package = res
        elif action == "datastore_search":
            self.fields[params["resource_id"]] = [f for f in res["fields"] if f["id"] != "_id"]
        elif action == "datastore_search_sql":
            recs = res.get("records", [])
            sql = params["sql"]
            rid = sql.split(' FROM "', 1)[1].split('"', 1)[0] if ' FROM "' in sql else None
            for r in recs:
                if rid and any(k in r for k in ROW_KEYS):           # table rows, not aggregates
                    key = json.dumps(sorted(r.items()), default=str)
                    self.rows.setdefault(rid, {})[key] = r
        return res

    def fixture(self) -> dict:
        pkg = self.package
        used = set(self.fields)
        pkg = {**pkg, "resources": [r for r in pkg["resources"] if r["id"] in used]}
        return {"package": pkg, "tables": {rid: {"fields": self.fields[rid], "rows": list(self.rows.get(rid, {}).values())}
                                           for rid in self.fields}}


def main(name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    line = CORRIDORS[name]
    db = Database(":memory:")
    osm = network.fetch_overpass(db, network.overpass_query(line))
    (OUT / f"overpass_{name}.json").write_text(json.dumps(osm))
    found = network.detect(osm, line)
    net = {"line": line, **found, "intersections": [{**i, "is_study": True} for i in found["intersections"]]}
    rec = Recorder()
    out = crashes.pull({"from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100}, net, Ckan(rec))
    (OUT / f"ckan_{name}.json").write_text(json.dumps(rec.fixture(), separators=(",", ":"), default=str))
    (OUT / f"line_{name}.json").write_text(json.dumps(line))
    print(f"{name}: {len(out['crashes'])} crashes kept; tables: "
          + ", ".join(f"{rid[:8]}={len(t['rows'])}" for rid, t in rec.fixture()["tables"].items()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "crenshaw")
