"""Crash data adapters, one per state (CA = CCRS). All return the shared crash shape."""

from datetime import datetime, timedelta, timezone, tzinfo


def from_epoch(seconds: float, tz: tzinfo) -> datetime:
    """datetime.fromtimestamp(seconds, tz), also before 1970: on Windows fromtimestamp raises OSError there."""
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).astimezone(tz)
