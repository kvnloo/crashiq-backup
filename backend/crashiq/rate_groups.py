"""Caltrans rate groups and the statewide expected crash rate (#287 part 1; user decision 2026-10-29, docs/03 #294).

The engineer enters each state-highway segment's, intersection's and ramp's rate group from Caltrans' "2024 Basic
Average Crash Rate Table" (data/reference/caltrans_rate_groups.csv and .md). Expected rate = base rate + ADT factor
("/" divides the factor by ADT in thousands, "*" multiplies); the expected fatal + injury and fatal rates are that
times the group's F+I and fatal percentages. No rate group, no statewide comparison: nothing is guessed.
"""

from __future__ import annotations

import csv
from functools import lru_cache

from fastapi import APIRouter

KINDS = {"segment": "H", "intersection": "I", "ramp": "R"}
SOURCE = "Caltrans, 2024 Crash Data on California State Highways, Basic Average Crash Rate Table"
NUMS = ("base_rate", "adt_factor", "pct_fatal", "pct_injury", "pct_fi")


@lru_cache(maxsize=1)
def table() -> dict[str, dict]:
    from .settings import ROOT
    with (ROOT / "data" / "reference" / "caltrans_rate_groups.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["group"]: {**r, **{k: float(r[k]) for k in NUMS}, "printed_page": int(r["printed_page"]),
                         "label": _label(r)} for r in rows}


def _label(r: dict) -> str:
    """'Conventional 2 lanes or less, flat, design speed <=55, rural': the group's description, as the table gives it."""
    t = r["type"].capitalize() if r["kind"] == "highway" else \
        f"Intersection {r['type']}" if r["kind"] == "intersection" else f"Ramp {r['type'].lower()}"
    parts = [t, r["terrain_or_adt"].lower() if r["terrain_or_adt"].isalpha() or "/" in r["terrain_or_adt"]
             else (f"ADT {r['terrain_or_adt']}" if r["terrain_or_adt"] else ""),
             f"design speed {r['design_speed']}" if r["design_speed"] else "", r["control"].lower(),
             f"{r['ramp_areas']} areas" if r["ramp_areas"] else "",
             r["on_off"].lower() if r["on_off"] not in ("", "N/A") else "", r["area"].lower().rstrip("*")]
    return ", ".join(p for p in parts if p)


def normalize(kind: str, group: str) -> str:
    """'h 07' -> 'H07'; ValueError when it isn't a published group of that location kind."""
    g = (group or "").upper().replace(" ", "")
    if kind not in KINDS or g not in table() or g[0] != KINDS[kind]:
        raise ValueError(f"{group!r} isn't a Caltrans {kind} rate group ({KINDS.get(kind, '?')}01–…).")
    return g


def adt_add(factor: float, op: str, adt: float | None) -> float | None:
    """What the ADT factor adds to the base rate (the table's note: "0.60/" with 5,000 ADT adds 0.12)."""
    if not factor:
        return 0.0
    if not adt:
        return None
    return factor / (adt / 1000) if op == "/" else factor * (adt / 1000)


def expected(group: str, adt: float | None) -> dict | None:
    """{"expected_all", "expected_fi", "expected_fatal", "base_rate", "adt_add"} for a rate group at an ADT, or None."""
    g = table().get(group)
    if g is None:
        return None
    add = adt_add(g["adt_factor"], g["adt_op"], adt)
    if add is None:
        return None
    e = g["base_rate"] + add
    return {"expected_all": e, "expected_fi": e * g["pct_fi"] / 100, "expected_fatal": e * g["pct_fatal"] / 100,
            "base_rate": g["base_rate"], "adt_add": add}


router = APIRouter()


@router.get("/reference/rate-groups")
def get_rate_groups() -> dict:
    """The published groups, for the engineer's picker."""
    keys = ("group", "kind", "label", "base_rate", "adt_factor", "adt_op", "pct_fatal", "pct_fi", "printed_page")
    return {"source": SOURCE, "groups": [{k: g[k] for k in keys} for g in table().values()]}
