"""North Carolina sources: the bits every NC reader shares (ArcGIS paging, KABCO letters, epoch -> local time).

NC open crash data is published as ArcGIS feature layers (NCDOT, Raleigh, Durham). Standalone; not wired into the app.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Iterator
from zoneinfo import ZoneInfo

from . import from_epoch

UA = {"User-Agent": "CrashIQ/0.1"}
EASTERN = ZoneInfo("America/New_York")
KABCO = "KABCO"


def _get(url: str, params: dict) -> dict:
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=UA)
    for attempt in range(4):              # ArcGIS Online answers 5xx under load now and then
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            time.sleep(2 ** attempt * 3)
    if "error" in body:
        raise RuntimeError(f"ArcGIS error from {url}: {body['error']}")
    return body


def query(layer: str, where: str = "1=1", fields: str = "*", oid: str = "OBJECTID", page: int = 2000) -> Iterator[dict]:
    """Every row of `layer` matching `where`, paged by object id (attributes, plus `_x`/`_y` in WGS84 if a point)."""
    last = -1
    while True:
        body = _get(layer + "/query", {"where": f"({where}) AND {oid} > {last}", "outFields": fields,
                                       "orderByFields": oid, "resultRecordCount": page, "outSR": 4326, "f": "json"})
        feats = body.get("features", [])
        for f in feats:
            row = dict(f["attributes"])
            g = f.get("geometry") or {}
            row["_x"], row["_y"] = g.get("x"), g.get("y")
            yield row
        if not feats:
            return
        last = feats[-1]["attributes"][oid]


def kabco_letter(value) -> str | None:
    """'K', 'A: Suspected Serious Injury', 'C Type Injury (Possible)', 'O No Injury' -> the letter; else None."""
    s = str(value or "").strip().upper()
    return s[0] if s and s[0] in KABCO and (len(s) == 1 or not s[1].isalpha()) else None


def day_time(day, hhmm=None) -> str | None:
    """A crash date (UTC-midnight epoch ms, or 'MM/DD/YYYY.') plus a local 'H:MM' time or an hour -> ISO local.
    NCDOT and Durham publish the date and the time separately; the date carries no time zone shift."""
    if day in (None, ""):
        return None
    if isinstance(day, (int, float)):
        d = from_epoch(day / 1000, timezone.utc).date()
    else:
        d = datetime.strptime(str(day).strip().rstrip("."), "%m/%d/%Y").date()
    m = re.match(r"^\s*(\d{1,2})(?::(\d{2}))?\s*$", str(hhmm if hhmm is not None else ""))
    if not m or int(m.group(1)) > 23:
        return d.isoformat()
    return f"{d.isoformat()}T{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}:00"


def coord(lat, lon) -> tuple[float | None, float | None]:
    """GPS only when plausible for North Carolina (0/0 and out-of-state points become None)."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None
    return (lat, lon) if 33.7 <= lat <= 36.7 and -84.4 <= lon <= -75.3 else (None, None)


def text(v) -> str | None:
    return (str(v).strip() or None) if v is not None else None
