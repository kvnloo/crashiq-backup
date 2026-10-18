"""C1 study: project name, study mode and crash-history window. One source of truth for later steps.

Window rules (docs/03-requirements.md R6):
- default = the 5 most recent *complete* calendar years (today 2026-10-18 → 2021–2025; on 1 Jan 2026 also 2021–2025)
- selectable 1–10 years, never before 2016 (first CCRS year), never past the current year
- a window that touches 2020 carries `covid_years_in_window`; the caveat text is written later (profile/export)
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Callable

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .db import Database

CCRS_FIRST_YEAR = 2016
MIN_YEARS, MAX_YEARS, DEFAULT_YEARS = 1, 10, 5
COVID_YEAR = 2020
RADIUS_RANGE = (50.0, 1000.0)   # intersection influence radius, ft (default 250, R2.4)
BUFFER_RANGE = (10.0, 500.0)    # corridor buffer each side of the line, ft

# v1 modes only (R1). Unavailable modes are hidden, not listed as "coming soon" (principle 3).
MODES: dict[str, str] = {
    "profile": "Crash profile / corridor screening",
    "tis": "Traffic-study safety section",
}

# Injectable clock so window tests can pin "today".
today: Callable[[], date] = date.today


def last_complete_year(on: date | None = None) -> int:
    return (on or today()).year - 1


def default_window(on: date | None = None) -> tuple[int, int]:
    to = last_complete_year(on)
    return to - DEFAULT_YEARS + 1, to


def validate_window(from_year: int, to_year: int, on: date | None = None) -> None:
    """Raise ValueError with a plain message if the window breaks a rule."""
    now = (on or today()).year
    n = to_year - from_year + 1
    if from_year > to_year:
        raise ValueError("The start year must not be after the end year.")
    if from_year < CCRS_FIRST_YEAR:
        raise ValueError(f"CCRS crash data starts in {CCRS_FIRST_YEAR}. Pick {CCRS_FIRST_YEAR} or later.")
    if to_year > now:
        raise ValueError(f"The window can't end after {now}.")
    if not MIN_YEARS <= n <= MAX_YEARS:
        raise ValueError(f"Pick between {MIN_YEARS} and {MAX_YEARS} years of crash history (this is {n}).")


def covid_in_window(from_year: int, to_year: int) -> bool:
    return from_year <= COVID_YEAR <= to_year


def window_options(on: date | None = None) -> list[dict]:
    """The dropdown choices: last N complete years for N = 1..10 (stopping at 2016)."""
    to = last_complete_year(on)
    out = []
    for n in range(MIN_YEARS, MAX_YEARS + 1):
        fy = to - n + 1
        if fy < CCRS_FIRST_YEAR:
            break
        span = f"{fy}–{to}" if n > 1 else f"{to}"
        out.append({"years": n, "from_year": fy, "to_year": to, "covid": covid_in_window(fy, to),
                    "label": f"Last {n} complete year{'s' if n > 1 else ''} ({span})"})
    return out


# -- storage --------------------------------------------------------------------------------------
def _row(r: dict | None) -> dict | None:
    if r is None:
        return None
    r = dict(r)
    r["covid_years_in_window"] = bool(r["covid_years_in_window"])
    r["mode_label"] = MODES.get(r["mode"], r["mode"])
    r["years"] = r["to_year"] - r["from_year"] + 1
    return r


def create(db: Database, name: str, mode: str, from_year: int | None = None, to_year: int | None = None) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("Give the project a name.")
    if mode not in MODES:
        raise ValueError(f"Unknown study mode '{mode}'.")
    if from_year is None and to_year is None:
        from_year, to_year = default_window()
    elif from_year is None or to_year is None:
        raise ValueError("Give both the start and end year, or neither for the default window.")
    validate_window(from_year, to_year)
    sid = uuid.uuid4().hex[:12]
    db.execute("INSERT INTO study (id, name, mode, from_year, to_year, covid_years_in_window) VALUES (?,?,?,?,?,?)",
               (sid, name, mode, from_year, to_year, int(covid_in_window(from_year, to_year))))
    return get(db, sid)


def get(db: Database, sid: str) -> dict | None:
    return _row(db.one("SELECT * FROM study WHERE id = ?", (sid,)))


def update(db: Database, sid: str, **changes) -> dict:
    cur = get(db, sid)
    if cur is None:
        raise KeyError(sid)
    name = changes.get("name", cur["name"])
    mode = changes.get("mode", cur["mode"])
    fy = changes.get("from_year", cur["from_year"])
    ty = changes.get("to_year", cur["to_year"])
    radius = changes.get("radius_ft", cur["radius_ft"])
    buffer = changes.get("buffer_ft", cur["buffer_ft"])
    if not (name or "").strip():
        raise ValueError("Give the project a name.")
    if mode not in MODES:
        raise ValueError(f"Unknown study mode '{mode}'.")
    validate_window(fy, ty)
    if not RADIUS_RANGE[0] <= radius <= RADIUS_RANGE[1]:
        raise ValueError(f"Influence radius must be {RADIUS_RANGE[0]:.0f}–{RADIUS_RANGE[1]:.0f} ft.")
    if not BUFFER_RANGE[0] <= buffer <= BUFFER_RANGE[1]:
        raise ValueError(f"Corridor buffer must be {BUFFER_RANGE[0]:.0f}–{BUFFER_RANGE[1]:.0f} ft.")
    db.execute("UPDATE study SET name=?, mode=?, from_year=?, to_year=?, covid_years_in_window=?, radius_ft=?, "
               "buffer_ft=?, updated_at=datetime('now') WHERE id=?",
               (name.strip(), mode, fy, ty, int(covid_in_window(fy, ty)), radius, buffer, sid))
    return get(db, sid)


def require(db: Database, sid: str) -> dict:
    s = get(db, sid)
    if s is None:
        raise HTTPException(404, "Study not found.")
    return s


# -- API ------------------------------------------------------------------------------------------
class StudyIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mode: str
    from_year: int | None = None
    to_year: int | None = None


class StudyPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    mode: str | None = None
    from_year: int | None = None
    to_year: int | None = None
    radius_ft: float | None = None
    buffer_ft: float | None = None


router = APIRouter()


@router.get("/studies/meta")
def meta() -> dict:
    fy, ty = default_window()
    return {
        "modes": [{"id": k, "label": v} for k, v in MODES.items()],
        "default_mode": "profile",
        "default_window": {"from_year": fy, "to_year": ty},
        "window_options": window_options(),
        "first_year": CCRS_FIRST_YEAR,
        "last_year": today().year,
        "min_years": MIN_YEARS,
        "max_years": MAX_YEARS,
    }


@router.post("/studies", status_code=201)
def create_study(body: StudyIn, request: Request) -> dict:
    return create(request.app.state.db, body.name, body.mode, body.from_year, body.to_year)


@router.get("/studies/{sid}")
def get_study(sid: str, request: Request) -> dict:
    return require(request.app.state.db, sid)


@router.patch("/studies/{sid}")
def patch_study(sid: str, body: StudyPatch, request: Request) -> dict:
    db = request.app.state.db
    require(db, sid)
    return update(db, sid, **body.model_dump(exclude_none=True))
