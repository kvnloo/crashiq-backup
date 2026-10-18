"""California crash source: CHP's CCRS open data on data.ca.gov (public domain).

One adapter per state lives in `crashiq.sources`. Each returns crashes in the shared
shape documented on `CRASH_FIELDS`, so the locate/assign/profile engine never sees a
state-specific column name.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://data.ca.gov/api/3/action/"
PACKAGE = "ccrs"

# Shared crash shape (all states map onto this).
CRASH_FIELDS = (
    "crash_id", "report_number", "agency_code", "datetime", "lat", "lon",
    "primary_road", "secondary_road", "offset_ft", "offset_dir", "is_freeway",
    "collision_type", "killed", "injured",
)

_COLUMNS = {
    "crash_id": "Collision Id", "report_number": "Report Number", "agency_code": "NCIC Code",
    "datetime": "Crash Date Time", "lat": "Latitude", "lon": "Longitude",
    "primary_road": "PrimaryRoad", "secondary_road": "SecondaryRoad",
    "_dist": "SecondaryDistance", "offset_dir": "SecondaryDirection", "_unit": "SecondaryUnitOfMeasure",
    "is_freeway": "IsFreeway", "collision_type": "Collision Type Description",
    "killed": "NumberKilled", "injured": "NumberInjured", "_deleted": "IsDeleted",
}
_UNIT_FT = {"F": 1.0, "M": 5280.0, "Y": 3.0}  # feet, miles, yards


def _get(action: str, **params) -> dict:
    url = API + action + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as r:
        body = json.load(r)
    if not body.get("success"):
        raise RuntimeError(f"CCRS API error: {body.get('error')}")
    return body["result"]


def crash_resource_ids() -> dict[int, str]:
    """Year -> datastore resource id, resolved at runtime (ids change when CHP republishes)."""
    pkg = _get("package_show", id=PACKAGE)
    out = {}
    for res in pkg["resources"]:
        name = res.get("name", "")
        if name.startswith("Crashes_") and res.get("datastore_active"):
            out[int(name.split("_")[1])] = res["id"]
    return out


def _normalize(rec: dict) -> dict:
    c = {k: rec.get(v) for k, v in _COLUMNS.items()}
    c.pop("_deleted")
    dist, unit = c.pop("_dist"), (c.pop("_unit") or "F").strip().upper()
    c["offset_ft"] = float(dist) * _UNIT_FT.get(unit, 1.0) if dist not in (None, "") else None
    # Cleaning rule (2026-10-18): a "miles" offset over 2 is feet typed as miles (73 "miles" from 3rd St).
    c["offset_fixed"] = False
    if c["offset_ft"] is not None and unit == "M" and float(dist) > 2:
        c["offset_ft"], c["offset_fixed"] = float(dist), True
    c["is_freeway"] = str(c["is_freeway"]) == "True"
    c["report_number"] = str(c["report_number"] or "").strip()
    c["agency_code"] = str(c["agency_code"] or "").strip()
    for k in ("primary_road", "secondary_road", "offset_dir"):
        c[k] = (c[k] or "").strip() or None
    return c


def fetch(year: int, where: str, cache_dir: Path, page: int = 5000) -> list[dict]:
    """All crashes for `year` matching a SQL `where` clause, cached as JSON."""
    cache = cache_dir / f"ccrs_{year}_{hashlib.sha1(where.encode()).hexdigest()[:10]}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rid = crash_resource_ids()[year]
    cols = ", ".join(f'"{v}"' for v in _COLUMNS.values())
    rows, offset = [], 0
    while True:
        sql = f'SELECT {cols} FROM "{rid}" WHERE {where} ORDER BY "Collision Id" LIMIT {page} OFFSET {offset}'
        batch = _get("datastore_search_sql", sql=sql)["records"]
        rows += [_normalize(r) for r in batch if str(r.get("IsDeleted")) != "True"]  # CHP-deleted reports
        if len(batch) < page:
            break
        offset += page
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows))
    return rows
