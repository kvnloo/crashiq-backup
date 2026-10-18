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
