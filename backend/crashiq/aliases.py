"""User-approved street aliases (#235; approvals recorded in docs/03, 2026-10-22).

`data/reference/street_aliases.csv` holds one row per local spelling CHP uses for a map street ("MARTIN LUTHER
KING JR WY" in Oakland = Martin Luther King Junior Way), with its evidence. Only rows with `status = approved` are
used, and only in their own scope (city + CCRS county code). Adding an entry is a data change: a new approved row.

A crash's road field that matches an approved alias in its city is read as the replacement everywhere (the pull's
filters, the GPS street check, the locator, FARS); the field as reported is kept (`roads_as_reported`) and the rows
used are listed on the crash (`aliases_used`).
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache

from .settings import ROOT

FILE = ROOT / "data" / "reference" / "street_aliases.csv"
FIELDS = ("primary_road", "secondary_road")


def norm(raw) -> str:
    """How a road field is compared with an alias: upper case, punctuation as spaces, single spaces (names.py)."""
    return re.sub(r"\s+", " ", re.sub(r"[.,#'\"]", " ", str(raw or "").upper())).strip()


def _county(v) -> str:
    try:
        return str(int(str(v).strip()))
    except (TypeError, ValueError):
        return str(v or "").strip()


@lru_cache(maxsize=1)
def table() -> dict[tuple[str, str], dict[str, tuple[str, str]]]:
    """(city key, county code) -> {normalized raw: (replacement, row id)}, approved rows only."""
    from .crashes import city_key
    out: dict[tuple[str, str], dict[str, tuple[str, str]]] = {}
    if not FILE.exists():
        return out
    with FILE.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("status") or "").strip().lower() != "approved" or (r.get("scope_type") or "") != "city":
                continue
            key = (city_key(r["scope"]), _county(r.get("county_code")))
            row_id = f"{r['scope']}|{norm(r['raw'])}"
            out.setdefault(key, {})[norm(r["raw"])] = (r["replacement"].strip(), row_id)
    return out


def replacements() -> dict[str, set[str]]:
    """Replacement -> the raw spellings approved for it anywhere (for the pull's name search)."""
    out: dict[str, set[str]] = {}
    for rows in table().values():
        for raw, (rep, _) in rows.items():
            out.setdefault(rep, set()).add(raw)
    return out


def apply(c: dict) -> dict:
    """Read the crash's road fields through the approved aliases of its city (in place); returns the crash."""
    from .crashes import city_key
    rows = table().get((city_key(c.get("city")), _county(c.get("county_code"))))
    if not rows:
        return c
    used, before = [], {}
    for f in FIELDS:
        hit = rows.get(norm(c.get(f)))
        if hit:
            before[f] = c.get(f)
            c[f] = hit[0]
            used.append(hit[1])
    if used:
        c["roads_as_reported"] = before
        c["aliases_used"] = used
    return c
