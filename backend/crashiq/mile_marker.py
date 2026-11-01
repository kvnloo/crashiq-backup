"""'MILE MARKER x' crashes at that Caltrans postmile on the state route (#319; user decision 2026-11-01, docs/03).

A no-GPS report on a state-route corridor that gives a mile marker in one road field ("ANGELES CREST HWY & MILE MARKER
28.86", "STATE HIGHWAY 96 & MM 95.29") is placed at that postmile on the route the other field names (its route
number), else the corridor's own route (OSM ref, shs.corridor_routes), in the crash's county: interpolated between the
layer's tenth points (postmile.places), plus any stated offset along the route in the stated direction. No route, or
the postmile not on it in the county (or in two places), sends it to review with the reason.

Behind a switch (config/placement.json `mile_marker_auto`, off): while off the point is the review list's suggestion;
the Tester measures it on crashes with fitting police GPS, and the user decides. CHP's mile markers may be signed
miles, not Caltrans postmiles; that measurement tells.
"""

from __future__ import annotations

import re

from .names import route_numbers
from .postmile import COUNTY

MARKER = re.compile(r"(?<![A-Z])(?:MILE\s*MARKER|MILEMARKER|MILE\s*POST|MILEPOST|M\s*/\s*M|MM|P\s*/\s*M|PM|MP)\s*#?\s*"
                    r"([A-Z](?=\d))?(\d{1,3}(?:\.\d+)?)(?![\d.])")
FT_PER_MI = 5280.0
MIN_OFFSET_FT = 50.0


def marker(text: str | None) -> tuple[str | None, float] | None:
    """(prefix or None, postmile) the text gives as a mile marker, or None."""
    m = MARKER.search(str(text or "").upper())
    return (m.group(1), float(m.group(2))) if m else None


def _fields(c: dict) -> tuple[tuple[str | None, float], str] | None:
    for f, other in (("secondary_road", "primary_road"), ("primary_road", "secondary_road")):
        mk = marker(c.get(f))
        if mk:
            return mk, str(c.get(other) or "")
    return None


def routes(c: dict, corridor_routes: set[str]) -> set[str]:
    """The route the other field names by number, else the corridor's own route(s)."""
    got = _fields(c)
    return (route_numbers(got[1]) if got else set()) or set(corridor_routes)


def place(c: dict, cache, corridor_routes: set[str]) -> dict:
    """{"lat", "lon", "note"} at the mile marker's postmile, or {"why": ...}."""
    got = _fields(c)
    if got is None:
        return {"why": "no mile marker"}
    (prefix, pm), _ = got
    rts = sorted(routes(c, corridor_routes))
    county = COUNTY.get(int(c["county_code"])) if str(c.get("county_code") or "").strip().isdigit() else None
    if not rts:
        return {"why": "no state route named"}
    if county is None:
        return {"why": "county not stated"}
    found = [(r, p) for r in rts for p in cache.places(r, county, pm, prefix)]
    where = f"route {'/'.join(rts)} in {county}"
    if not found:
        return {"why": f"postmile {pm:.3f} isn't on {where}"}
    if len(found) > 1:
        return {"why": f"postmile {pm:.3f} is in more than one place on {where}"}
    route, base = found[0]
    note = f"{county}-{route} PM {prefix or ''}{pm:.3f}"
    off, d = c.get("offset_ft") or 0.0, str(c.get("offset_dir") or "").upper()[:1]
    if off >= MIN_OFFSET_FT and d in "NSEW":      # a few feet is within the marker's own precision
        step = off / FT_PER_MI
        ends = [p for p in (cache.at(route, county, pm + step, prefix), cache.at(route, county, pm - step, prefix)) if p]
        axis, sign = ("lat" if d in "NS" else "lon"), (1 if d in "NE" else -1)
        moved = [p for p in ends if (p[axis] - base[axis]) * sign > 0]
        if not moved:
            return {"why": f"the stated {off:g} ft {d} runs off {where}"}
        base = moved[0]
        note += f", {off:g} ft {d}"
    return {"lat": base["lat"], "lon": base["lon"], "note": note}
