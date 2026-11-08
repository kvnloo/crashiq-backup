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

from . import packs
from .db import Database

CCRS_FIRST_YEAR = 2016
MIN_YEARS, MAX_YEARS, DEFAULT_YEARS = 1, 10, 5
COVID_YEARS = (2020, 2021)    # #34 item 13: both years noted
FINAL_LAG_MONTHS = 18          # #34 item 8: CHP data entry lags 12-18 months (TIMS); a year is treated as final
                               # once 18 months have passed since it ended
K_RANGE = (0.04, 0.25)         # peak-hour share of daily traffic; 10% default (user: "10% is typical")
SHORT_WINDOW_YEARS = 3         # #34 item 15: warn below this (Caltrans LRSM: at least 3, preferably 5)
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
    """Last calendar year that has ended (the latest year an engineer may choose)."""
    return (on or today()).year - 1


def last_final_year(on: date | None = None, lag: int = FINAL_LAG_MONTHS) -> int:
    """Last year whose data should be final: it ended at least `lag` months ago (#34 item 8; the pack's lag)."""
    d = on or today()
    months = d.year * 12 + (d.month - 1) - lag
    return months // 12 - 1


def default_window(on: date | None = None, pack: packs.StatePack | None = None) -> tuple[int, int]:
    to = last_final_year(on, pack.final_lag_months if pack else FINAL_LAG_MONTHS)
    return to - DEFAULT_YEARS + 1, to


def validate_window(from_year: int, to_year: int, on: date | None = None, pack: packs.StatePack | None = None) -> None:
    """Raise ValueError with a plain message if the window breaks a rule."""
    now = (on or today()).year
    n = to_year - from_year + 1
    first, src = (pack.first_year, pack.source_short) if pack else (CCRS_FIRST_YEAR, "CCRS")
    if from_year > to_year:
        raise ValueError("The start year must not be after the end year.")
    if from_year < first:
        raise ValueError(f"{src} crash data starts in {first}. Pick {first} or later.")
    if to_year > now:
        raise ValueError(f"The window can't end after {now}.")
    if not MIN_YEARS <= n <= MAX_YEARS:
        raise ValueError(f"Pick between {MIN_YEARS} and {MAX_YEARS} years of crash history (this is {n}).")


def covid_in_window(from_year: int, to_year: int) -> bool:
    return any(from_year <= y <= to_year for y in COVID_YEARS)


def window_options(on: date | None = None, pack: packs.StatePack | None = None) -> list[dict]:
    """The dropdown choices: last N finalized years for N = 1..10 (stopping at the pack's first year, CA 2016)."""
    to = last_final_year(on, pack.final_lag_months if pack else FINAL_LAG_MONTHS)
    out = []
    for n in range(MIN_YEARS, MAX_YEARS + 1):
        fy = to - n + 1
        if fy < (pack.first_year if pack else CCRS_FIRST_YEAR):
            break
        span = f"{fy}–{to}" if n > 1 else f"{to}"
        out.append({"years": n, "from_year": fy, "to_year": to, "covid": covid_in_window(fy, to),
                    "short": n < SHORT_WINDOW_YEARS,
                    "label": f"Last {n} year{'s' if n > 1 else ''} ({span})"})
    return out


# -- storage --------------------------------------------------------------------------------------
def _row(r: dict | None) -> dict | None:
    if r is None:
        return None
    r = dict(r)
    r["covid_years_in_window"] = bool(r["covid_years_in_window"])
    r["include_freeway"] = bool(r.get("include_freeway", 0))
    r["volume_basis"] = r.get("volume_basis") or "aadt"
    r["k_factor"] = r.get("k_factor") if r.get("k_factor") is not None else 0.10
    r["mode_label"] = MODES.get(r["mode"], r["mode"])
    r["years"] = r["to_year"] - r["from_year"] + 1
    return r


def ready_pack(state: str) -> packs.StatePack:
    """The pack of a state a new study may use; ValueError for one that isn't ready (#19)."""
    pack = packs.PACKS.get(state)
    if pack is None or pack.status != "active":
        name = pack.name if pack else packs.COMING.get(state, state)
        raise ValueError(f"{name} isn't ready yet.")
    return pack


def create(db: Database, name: str, mode: str, from_year: int | None = None, to_year: int | None = None,
           state: str = "CA") -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("Give the project a name.")
    if mode not in MODES:
        raise ValueError(f"Unknown study mode '{mode}'.")
    pack = ready_pack(state)
    if from_year is None and to_year is None:
        from_year, to_year = default_window(pack=pack)
    elif from_year is None or to_year is None:
        raise ValueError("Give both the start and end year, or neither for the default window.")
    validate_window(from_year, to_year, pack=pack)
    sid = uuid.uuid4().hex[:12]
    db.execute("INSERT INTO study (id, name, mode, from_year, to_year, covid_years_in_window, state) "
               "VALUES (?,?,?,?,?,?,?)", (sid, name, mode, from_year, to_year, int(covid_in_window(from_year, to_year)),
                                          state))
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
    fwy = bool(changes.get("include_freeway", cur["include_freeway"]))
    basis = changes.get("volume_basis", cur["volume_basis"])
    k = changes.get("k_factor", cur["k_factor"])
    if basis not in ("aadt", "peak_hour"):
        raise ValueError("Volumes are entered either as daily AADT or as peak-hour counts.")
    if not K_RANGE[0] <= k <= K_RANGE[1]:
        raise ValueError(f"K factor must be {K_RANGE[0]:.0%}–{K_RANGE[1]:.0%} of daily traffic.")
    if not (name or "").strip():
        raise ValueError("Give the project a name.")
    if mode not in MODES:
        raise ValueError(f"Unknown study mode '{mode}'.")
    validate_window(fy, ty, pack=packs.for_study(cur))
    if not RADIUS_RANGE[0] <= radius <= RADIUS_RANGE[1]:
        raise ValueError(f"Influence radius must be {RADIUS_RANGE[0]:.0f}–{RADIUS_RANGE[1]:.0f} ft.")
    if not BUFFER_RANGE[0] <= buffer <= BUFFER_RANGE[1]:
        raise ValueError(f"Corridor buffer must be {BUFFER_RANGE[0]:.0f}–{BUFFER_RANGE[1]:.0f} ft.")
    db.execute("UPDATE study SET name=?, mode=?, from_year=?, to_year=?, covid_years_in_window=?, radius_ft=?, "
               "buffer_ft=?, include_freeway=?, volume_basis=?, k_factor=?, updated_at=datetime('now') WHERE id=?",
               (name.strip(), mode, fy, ty, int(covid_in_window(fy, ty)), radius, buffer, int(fwy), basis, k, sid))
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
    state: str = "CA"             # fixed once the study exists: StudyPatch has no state (#19)


class StudyPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    mode: str | None = None
    from_year: int | None = None
    to_year: int | None = None
    radius_ft: float | None = None
    buffer_ft: float | None = None
    include_freeway: bool | None = None
    volume_basis: str | None = None
    k_factor: float | None = None


router = APIRouter()


@router.get("/studies/meta")
def meta(state: str | None = None) -> dict:
    """Setup's choices for one state (#19): the first ready state when none is asked for."""
    states = packs.states()
    try:
        pack = ready_pack(state or states[0]["code"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    fy, ty = default_window(pack=pack)
    short = packs.value(pack, "min_years")
    return {
        "states": states,
        "state": pack.code,
        "state_name": pack.name,
        "source_short": pack.source_short,
        # CA keeps its sentence; elsewhere only a cited minimum (methods file) says anything
        "short_window_note": ("Under 3 years of crashes. Caltrans recommends at least 3, preferably 5." if pack.caltrans
                              else f"Under {short['value']} years of crashes. {packs.cite(pack, 'min_years')} asks for "
                                   f"at least {short['value']}." if short else None),
        "severity_note": pack.severity_note,
        "modes": [{"id": k, "label": v} for k, v in MODES.items()],
        "default_mode": "profile",
        "default_window": {"from_year": fy, "to_year": ty},
        "window_options": window_options(pack=pack),
        "first_year": pack.first_year,
        "last_year": today().year,
        "min_years": MIN_YEARS,
        "max_years": MAX_YEARS,
    }


@router.post("/studies", status_code=201)
def create_study(body: StudyIn, request: Request) -> dict:
    return create(request.app.state.db, body.name, body.mode, body.from_year, body.to_year, body.state)


@router.get("/studies/{sid}")
def get_study(sid: str, request: Request) -> dict:
    db = request.app.state.db
    s = require(db, sid)
    has = lambda t: db.one(f"SELECT 1 AS x FROM {t} WHERE study_id = ?", (sid,)) is not None  # noqa: E731
    return {**s, "progress": {"corridor": has("corridor"), "crashes": _pull_current(db, sid, s)}}


def _pull_current(db, sid: str, study: dict) -> bool:
    """True only when a pull exists AND matches the study as it is now (window, corridor, radius)."""
    from . import crashes as crashes_mod, network as network_mod       # local: those modules import this one
    r = db.one("SELECT cache_key FROM crash_pull WHERE study_id = ?", (sid,))
    net = network_mod.network(db, sid)
    return bool(r and net.get("line") and r["cache_key"] == crashes_mod.cache_key(study, net))


@router.patch("/studies/{sid}")
def patch_study(sid: str, body: StudyPatch, request: Request) -> dict:
    db = request.app.state.db
    require(db, sid)
    return update(db, sid, **body.model_dump(exclude_none=True))
