"""Exposure for state-highway crash rates (#287; user decision 2026-10-26, docs/03): the Caltrans Traffic Census AADT
on each study segment of a corridor that carries a state route.

- The corridor's route numbers come from its OSM names (refs such as "I 405", "SR 1"); a corridor without one isn't
  on the State Highway System and gets no Caltrans exposure (local traffic counts are needed there).
- Each study segment is sampled every SAMPLE_MI along the corridor line. Each sample gets its postmile from the
  Caltrans postmile layer (#248) and, for each count year, the AADT of the leg that applies there (aadt.py).
- A calendar year (CCRS crashes) is 9 months of its own count year (October to September) and 3 months of the next:
  AADT(year) = 0.75 x AADT(count year) + 0.25 x AADT(count year + 1). A count year after the newest file uses the
  newest, and the row says so.
- A segment-year has an AADT only when every sample has one (coverage 1.0); otherwise none, never a partial guess.
- Trucks: the 3+ axle truck AADT (aadt.truck_segment, the truck point behind) by the same sampling, blend and coverage
  rules, for truck-involved crash rates.
"""

from __future__ import annotations

import math

from .geo import Polyline
from .names import route_numbers

SAMPLE_MI = 0.05
FT_PER_MI = 5280.0


def corridor_routes(net: dict) -> set[str]:
    return route_numbers(" ".join(net.get("corridor_names") or [net.get("corridor_name") or ""]))


def segment_volumes(net: dict, postmiles, aadt_cache, years: list[int]) -> dict | None:
    """{segment id: {"by_year": {year: AADT or None}, "coverage", "latest_used", "count_years", "routes", "source",
    "end_tolerance", "pm_coverage" (share of samples with a postmile), "trucks_by_year" (3+ axle truck AADT,
    same rules), "truck_count_years"}} for a state-highway corridor; None when it isn't one or a source is missing."""
    routes = corridor_routes(net)
    if not routes or postmiles is None or aadt_cache is None or not net.get("line") or aadt_cache.db() is None:
        return None
    line = Polyline([tuple(p) for p in net["line"]])
    have = [y for (y,) in aadt_cache.db().execute("SELECT DISTINCT year FROM point ORDER BY year")]
    have_t = [y for (y,) in aadt_cache.db().execute("SELECT DISTINCT year FROM truck ORDER BY year")]
    out = {}
    for s in net.get("segments", []):
        a, b = s["from_station_ft"], s["to_station_ft"]
        n = max(1, math.ceil((b - a) / (SAMPLE_MI * FT_PER_MI)))
        pms = [postmiles.lookup(*line.point_at(a + (i + 0.5) * (b - a) / n), routes) for i in range(n)]
        pm_cov = sum(pm is not None for pm in pms) / n
        by_year, covered, latest, end, trucks, latest_t = {}, [], False, False, {}, False
        for y in years:
            tv = [[aadt_cache.truck_segment(pm["route"], pm["county"], pm["pm"], cy, pm.get("route_suffix") or "",
                                            pm.get("suffix") or "") if pm else None for cy in (y, y + 1)] for pm in pms]
            ok_t = [0.75 * a["trucks_3plus"] + 0.25 * b["trucks_3plus"] for a, b in tv
                    if a and b and a["trucks_3plus"] is not None and b["trucks_3plus"] is not None]
            trucks[y] = round(sum(ok_t) / n, 1) if len(ok_t) == n else None
            latest_t = latest_t or any(g["latest_used"] for leg in tv for g in leg if g)
            vals = []
            for pm in pms:
                legs = [aadt_cache.segment(pm["route"], pm["county"], pm["pm"], cy, pm.get("route_suffix") or "",
                                           pm.get("suffix") or "", pm.get("prefix") or "") if pm else None
                        for cy in (y, y + 1)]
                if None in legs:
                    vals.append(None)
                    continue
                latest = latest or any(g["latest_used"] for g in legs)
                end = end or any(g["aadt_end_tolerance"] for g in legs)
                vals.append(0.75 * legs[0]["aadt"] + 0.25 * legs[1]["aadt"])
            ok = [v for v in vals if v is not None]
            covered.append(len(ok) / n)
            by_year[y] = round(sum(ok) / n, 1) if len(ok) == n else None
        out[s["id"]] = {"by_year": by_year, "coverage": round(min(covered), 3) if covered else 0.0,
                        "pm_coverage": round(pm_cov, 3),
                        "latest_used": latest, "end_tolerance": end, "routes": sorted(routes),
                        "count_years": _years_label(have, years, latest),
                        "trucks_by_year": trucks, "truck_count_years": _years_label(have_t, years, latest_t),
                        "source": "Caltrans Traffic Census Program" if have else ""}
    return out


def _years_label(have: list[int], years: list[int], latest: bool) -> str:
    if not have:
        return ""
    label = f"{have[0]}–{have[-1]}" if len(have) > 1 else str(have[0])
    return label + (f"; later count years use {have[-1]}" if latest else "")
