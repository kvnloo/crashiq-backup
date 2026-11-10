"""sources.from_epoch: the same answer as datetime.fromtimestamp, and pre-1970 values don't raise (Windows: OSError)."""

import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from crashiq.sources import from_epoch


def test_matches_fromtimestamp_after_1970():
    rnd = random.Random(7)
    for tz in (timezone.utc, ZoneInfo("America/Los_Angeles"), ZoneInfo("America/Chicago")):
        for _ in range(2000):
            ms = rnd.randrange(0, 4_102_444_800_000)          # 1970 .. 2100, epoch milliseconds as ArcGIS sends
            assert from_epoch(ms / 1000, tz) == datetime.fromtimestamp(ms / 1000, tz)


def test_pre_1970_value_reads_instead_of_raising():
    t = from_epoch(-4_575_744_000, timezone.utc)                # an 1825 date, as some state layers hold
    assert (t.year, t.month, t.day) == (1825, 1, 1)
