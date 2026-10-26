"""#264 shared pieces: the pools (d5_pools.csv), city boxes, street-name matching and the one-place rule, the same for
every local address source (TIGER ADDRFEAT, NAD), so the sources differ only in their data.

Matching: a source street is the crash's street when the app's names.same_core says so (a leading direction word
dropped either way), and, when both carry a street type (ST / AVE ...), the types agree. Place: candidates inside the
crash's city box + 1 km when the crash is in a city with an OSM boundary, else its county; the candidates must lie
within ONE_PLACE_FT of each other (one place), and the spot is their mean. More than one place = not placed (ambiguous).
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "statewide"
ONE_PLACE_FT = 1000.0


def ft(a, b) -> float:
    dy = (a[0] - b[0]) * 364000
    dx = (a[1] - b[1]) * 364000 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def pools() -> list[dict]:
    with open(DATA / "d5_pools.csv") as f:
        return list(csv.DictReader(f))


def city_boxes(cities) -> dict[str, tuple]:
    import corridors
    import osm_local
    local = osm_local.LocalOSM(ROOT / "data" / "osm" / "ca_osm.sqlite")
    bounds = corridors.local_boundaries(local)
    out = {}
    for city in cities:
        b = bounds.get(corridors.norm_city(city)) if city else None
        if not b:
            continue
        row = local.db.execute("SELECT minlat, minlon, maxlat, maxlon FROM areas WHERE id = ? "
                               "ORDER BY CAST(admin_level AS INT) DESC LIMIT 1", (b["rel"],)).fetchone()
        if row:
            dlat = 1.0 / 111.32
            dlon = dlat / max(0.2, math.cos(math.radians((row[0] + row[2]) / 2)))
            out[city] = (row[0] - dlat, row[1] - dlon, row[2] + dlat, row[3] + dlon)
    return out


def keys(name: str) -> set[str]:
    """Index keys of a street name: its core and its core without a leading direction word, spaces removed."""
    from crashiq.names import drop_directional, street_key
    k = street_key(name)
    if not k:
        return set()
    return {k.core.replace(" ", ""), drop_directional(k).core.replace(" ", "")}


def same_street(crash_street: str, source_name: str) -> bool:
    from crashiq.names import same_core, street_key
    a, b = street_key(crash_street), street_key(source_name)
    if not a or not b or not same_core(a, b):
        return False
    return not (a.suffix and b.suffix and a.suffix != b.suffix)


def one_place(points: list[tuple[float, float]], box: tuple | None):
    """(spot, note): the mean of the candidates when they're one place, else (None, why)."""
    if box:
        points = [p for p in points if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]]
    if not points:
        return None, "no match"
    if max(ft(a, b) for a in points for b in points) > ONE_PLACE_FT:
        return None, "more than one place"
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)), ""


def write(source: str, rows: list[dict]) -> None:
    with open(DATA / f"d5_result_{source}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["collision_id", "pool", "district", "placed", "lat", "lon", "note"])
        w.writeheader()
        w.writerows(rows)
