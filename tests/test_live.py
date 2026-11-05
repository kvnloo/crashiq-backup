"""Live smoke tests against the real services. Skipped unless CRASHIQ_LIVE=1 (needs internet):

    CRASHIQ_LIVE=1 make test-backend
"""
import os

import pytest

from crashiq import crashes, network
from crashiq.db import Database
from crashiq.sources.ckan import Ckan

pytestmark = pytest.mark.skipif(os.getenv("CRASHIQ_LIVE") != "1", reason="live network test; set CRASHIQ_LIVE=1")
LINE = [(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.32662)]


def test_live_crenshaw_one_year():
    osm = network.fetch_overpass(Database(":memory:"), network.overpass_query(LINE))
    net = network.detect(osm, LINE)
    assert net["intersections"], "Overpass returned no intersections for Crenshaw"
    out = crashes.pull({"from_year": 2023, "to_year": 2023, "radius_ft": 250, "buffer_ft": 100},
                       {"line": LINE, "corridor_name": net["corridor_name"]}, Ckan())
    assert out["crashes"], "CCRS returned no crashes for Crenshaw 2023"
    assert not out["cleaning"]["missing_fields"], out["cleaning"]["missing_fields"]


KNOWN_TYPES = {"HEAD-ON", "SIDE SWIPE", "REAR END", "BROADSIDE", "HIT OBJECT", "OVERTURNED", "VEHICLE/PEDESTRIAN", "OTHER"}


def test_live_ccrs_contract(capsys):
    """The checks the 2026-10-18 review asked for on the first live run. Prints the column types it saw and
    writes them to tests/fixtures/live/ so the fixture can be compared with the real layout."""
    import json
    import time
    from pathlib import Path
    from crashiq.sources import ca_ccrs as cc

    ckan = Ckan()
    t0 = time.time()
    osm = network.fetch_overpass(Database(":memory:"), network.overpass_query(LINE))
    net = network.detect(osm, LINE)
    out = crashes.pull({"from_year": 2023, "to_year": 2023, "radius_ft": 250, "buffer_ft": 100},
                       {**net, "line": LINE}, ckan)
    cs, log = out["crashes"], out["cleaning"]
    res = cc.table_resources(ckan.get("package_show", id=cc.PACKAGE))
    types = {t: {f["id"]: f.get("type") for f in ckan.fields(res[t][2023])} for t in ("crashes", "parties", "iwp")}
    live = Path(__file__).parent / "fixtures" / "live"
    live.mkdir(parents=True, exist_ok=True)
    (live / "ccrs_fields_2023.json").write_text(json.dumps(types, indent=1))
    with capsys.disabled():
        print(f"\n[live] {len(cs)} crashes, {ckan.calls} CKAN calls, {time.time() - t0:.0f}s; cleaning: {log}")

    assert cs, "no crashes"
    assert all(c["year"] == 2023 and c["date"] for c in cs), "dates not parsed"
    assert log["bad_dates_dropped"] == 0
    assert not log["unknown_injury_values"], f"ExtentOfInjury values not mapped: {log['unknown_injury_values']}"
    kept = [c for c in cs if not c.get("exclude_rule")]      # excluded reports get no party lookups (#54)
    assert kept and sum(bool(c["parties"]) for c in kept) >= 0.9 * len(kept), \
        "Parties join rate under 90%: check Collision Id type"
    unknown = {c["collision_type"] for c in cs if c["collision_type"]} - KNOWN_TYPES
    assert not unknown, f"collision types not normalized: {unknown}"
    lit = [c["lighting"] for c in cs if c["lighting"]]
    assert len(lit) >= 0.9 * len(cs) and any("DARK" in v.upper() for v in lit), "lighting missing or not recognized"
    assert not any(v[:2].strip().endswith("-") for v in lit), "a code prefix survived cleaning"
    assert log["implausible_coords"] <= 0.02 * len(cs)
