"""Crash cost per location, for ranking by cost (#273; user decision 2026-10-25, docs/03 "Ranking by crash cost").

Each crash once, at its KABCO level, at Caltrans' published cost (LRSM v1.8, May 2026, Appendix D;
data/reference/crash_costs_ca.csv, its source in crash_costs_ca.md). K and A take the combined KA price of the
location type: roadway (segment), signalized or non-signalized intersection. Two rules the LRSM doesn't give, decided
by the user (2026-11-01, #273): U (injury, level not stated) is priced at C; a KA crash at an intersection whose
control isn't known takes the signalized price (the lower one), and the location says so.
"""

from __future__ import annotations

import csv
from functools import lru_cache

from .settings import ROOT

FILE = ROOT / "data" / "reference" / "crash_costs_ca.csv"
NON_SIGNAL = {"stop", "all_way_stop", "yield", "roundabout"}     # LRSM "Non-Signalized Intersection" (PM, 2026-11-01)
SOURCE = ("Caltrans Local Roadway Safety Manual v1.8 (May 2026), Appendix D, p. 100, 2026 dollars. Fatal and serious "
          "(KA) priced together by location type; injury with level not stated (U) priced as possible injury (C); KA at "
          "an intersection with unknown control at the signalized price.")


@lru_cache(maxsize=1)
def table() -> dict[tuple[str, str], int]:
    with FILE.open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return {(r["severity"], r["location_type"]): int(r["cost_usd"]) for r in rows}


def location_type(kind: str, control: str | None) -> tuple[str, bool]:
    """(LRSM location type, control unknown?) for a T2 location."""
    if kind == "segment":
        return "roadway", False
    if control == "signal":
        return "signalized_intersection", False
    if control in NON_SIGNAL:
        return "non_signalized_intersection", False
    return "signalized_intersection", True                    # unknown control: the lower KA price (user 2026-11-01)


def cost(severity: str, loc_type: str) -> int:
    t = table()
    if severity in ("K", "A"):
        return t[("KA", loc_type)]
    return t[("C" if severity == "U" else severity, "any")]


def location_cost(crashes: list[dict], kind: str, control: str | None) -> dict:
    """{"crash_cost", "cost_control_unknown"} for one location's crashes."""
    lt, unknown = location_type(kind, control)
    total = sum(cost(c["severity"], lt) for c in crashes if c.get("severity") and c["severity"] in "KABCUO")
    return {"crash_cost": total, "cost_control_unknown": bool(unknown and any(c.get("severity") in ("K", "A")
                                                                               for c in crashes))}
