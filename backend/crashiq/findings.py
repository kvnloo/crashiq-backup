"""C10 findings contract + validator. The analyst (C9, Claude) must emit findings in this shape; code checks
every number against the computed tables before a finding can be shown. AI never produces a number that
reaches the user unchecked (CLAUDE.md, "Code computes every number").

A finding is REJECTED (logged with reasons, never shown) when:
  - it cites no table, or a cited table doesn't exist;
  - a declared number doesn't match the cell it cites;
  - a number written in the text isn't one of its declared, verified numbers;
  - its evidence filter selects zero crash records.
Rounding rule (the only one): a number written with d decimals matches a cell value v when v rounded half-up to
d decimals equals it ("38%" matches 38.46; "38.5%" matches 38.46; "38.4%" doesn't).
Spelled-out counts two..twenty, thirty, forty, fifty are checked like digits ("one" is skipped: it's
usually a determiner, so the analyst is told to write counts as digits).
Allowed without a citation: years inside the study window, ordinals in street names ("135th"), and numbers inside
a quoted span that appears verbatim in an evidence record (CCRS codes/names such as "VC 22350").
CCRS free text is data: the validator only matches strings, it never acts on their content.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import assign as assign_mod
from . import profile as profile_mod
from . import signals as signals_mod

SPELLED = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())}
SPELLED.update({"thirty": 30, "forty": 40, "fifty": 50})
del SPELLED["one"]   # "one" is mostly a determiner ("one report", "one of the"); counts of one must use digits
_NUM = re.compile(r"(?<![\w.$-])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?:\s*(%|percent))?(?![\w])", re.I)
_ORDINAL = re.compile(r"(?<![\w.])\d+(?:st|nd|rd|th)\b", re.I)
_SPELLED = re.compile(r"\b(" + "|".join(SPELLED) + r")\b", re.I)
_QUOTED = re.compile(r"[\"“]([^\"”]{1,120})[\"”]")


class Number(BaseModel):
    value: float
    table_id: str
    cell: str = Field(description="'<row>/<column>' inside table_id")


class RecordFilter(BaseModel):
    location_id: str | None = None
    severity: list[str] | None = None
    collision_type: list[str] | None = None
    lighting_dark: bool | None = None
    ped: bool | None = None
    bike: bool | None = None
    motorcycle: bool | None = None
    surface_wet: bool | None = None
    day_of_week: list[str] | None = None
    hour_from: int | None = Field(default=None, ge=0, le=23)
    hour_to: int | None = Field(default=None, ge=0, le=23)
    year: list[int] | None = None


class Evidence(BaseModel):
    tables: list[str] = []
    records: RecordFilter = RecordFilter()


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: "f-" + uuid.uuid4().hex[:8])
    location_id: str | None = None
    text: str = Field(min_length=1, max_length=2000)
    numbers: list[Number] = []
    pattern_ref: str | None = None
    evidence_refs: Evidence = Evidence()
    status: Literal["proposed", "accepted", "rejected", "edited"] = "proposed"
    title: str | None = Field(default=None, max_length=200)
    source: Literal["analyst", "screen"] = Field(default="analyst",
                                                description="screen = written by code from T12 (C7); analyst = Claude (C9)")
    meta: dict = Field(default_factory=dict, description="screen findings: strength, probability, method, pattern")
    audit: dict = Field(default_factory=dict, description="reserved; fields wait for #3 Q6")


def round_half_up(v: float, d: int) -> Decimal:
    return Decimal(str(v)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)


def matches(written: str, cell_value) -> bool:
    if cell_value is None or isinstance(cell_value, (str, bool)):
        return False
    w = Decimal(written.replace(",", ""))
    d = max(0, -w.as_tuple().exponent)
    return round_half_up(float(cell_value), d) == w


def extract_numbers(text: str, quoted_ok: set[str]) -> list[str]:
    """Numbers a reader would take as claims, as written (e.g. '38', '2.5', '1,204')."""
    masked = text
    for m in _QUOTED.finditer(text):
        if m.group(1).strip().lower() in quoted_ok:
            masked = masked.replace(m.group(0), " " * len(m.group(0)))
    masked = _ORDINAL.sub(lambda m: " " * len(m.group(0)), masked)
    out = [m.group(1) + (m.group(2) or "") for m in _NUM.finditer(masked)]
    out += [str(SPELLED[m.group(1).lower()]) for m in _SPELLED.finditer(masked)]
    return out


def select_records(crashes: list[dict], f: RecordFilter) -> list[dict]:
    out = []
    for c in crashes:
        if f.location_id is not None and c.get("location_id") != f.location_id:
            continue
        if f.severity and c.get("severity") not in f.severity:
            continue
        if f.collision_type and (c.get("collision_type") or "").upper() not in {x.upper() for x in f.collision_type}:
            continue
        if f.lighting_dark is not None and profile_mod.is_dark(c) != f.lighting_dark:
            continue
        if f.ped is not None and bool(c.get("ped")) != f.ped:
            continue
        if f.bike is not None and bool(c.get("bike")) != f.bike:
            continue
        if f.motorcycle is not None and bool(c.get("motorcycle")) != f.motorcycle:
            continue
        if f.surface_wet is not None and (c.get("surface") or "").upper().startswith("WET") != f.surface_wet:
            continue
        if f.day_of_week and c.get("day_of_week") not in f.day_of_week:
            continue
        h = c.get("hour")
        if f.hour_from is not None and (h is None or h < f.hour_from):
            continue
        if f.hour_to is not None and (h is None or h > f.hour_to):
            continue
        if f.year and c.get("year") not in f.year:
            continue
        out.append(c)
    return out


_TEXT_FIELDS = ("pcf", "collision_type", "primary_road", "secondary_road", "lighting", "weather", "surface", "pcf_category")


def validate(finding: Finding, tables: list[dict], crashes: list[dict], window: tuple[int, int]) -> list[str]:
    """Reasons to reject; empty list = valid. `crashes` = placed crashes with location_id."""
    reasons = []
    by_id = {t["id"]: t for t in tables}
    cited = {n.table_id for n in finding.numbers} | set(finding.evidence_refs.tables)
    if not cited:
        reasons.append("no table cited")
    for tid in sorted(cited):
        if tid not in by_id:
            reasons.append(f"cited table {tid} does not exist")
    for n in finding.numbers:
        if n.table_id not in by_id:
            continue
        try:
            val = profile_mod.cell(tables, f"{n.table_id}/{n.cell}")
        except (StopIteration, KeyError, ValueError):
            reasons.append(f"cell {n.table_id}/{n.cell} does not exist")
            continue
        if not matches(_fmt(n.value), val):
            reasons.append(f"declared {_fmt(n.value)} does not match {n.table_id}/{n.cell} = {val}")
    evidence = select_records(crashes, finding.evidence_refs.records)
    if not evidence:
        reasons.append("evidence filter selects zero crash records")
    quoted_ok = {str(c.get(k)).strip().lower() for c in evidence for k in _TEXT_FIELDS if c.get(k)}
    lo, hi = window
    for w in extract_numbers(finding.text, quoted_ok):
        plain = w.replace(",", "")
        if "." not in plain and lo <= int(plain) <= hi:
            continue                                   # a year inside the study window
        ok = False
        for n in finding.numbers:
            if n.table_id in by_id:
                try:
                    if matches(plain, profile_mod.cell(tables, f"{n.table_id}/{n.cell}")):
                        ok = True
                        break
                except (StopIteration, KeyError, ValueError):
                    pass
        if not ok:
            reasons.append(f"number {w} in the text is not backed by a cited table cell")
    return reasons


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else repr(float(v))


# -- storage + API ----------------------------------------------------------------------------------------
def context(db, sid: str) -> tuple[dict, list[dict], list[dict]]:
    """(profile, tables incl. per-location, placed crashes with location ids) for validation."""
    study, net, pull, a = assign_mod.for_study(db, sid)
    prof = profile_mod.build(study, net, pull, a)
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    placed = [{**by_id[x["crash_id"]], "location_id": x["location_id"]} for x in a["assignments"]
              if x["kind"] in ("intersection", "segment")]
    years = prof["window"]["years_with_data"]
    tables = list(prof["tables"])
    for lid in {c["location_id"] for c in placed}:
        tables += profile_mod.tables_for([c for c in placed if c["location_id"] == lid], years, suffix=f"@{lid}")
    return prof, tables, placed


def submit(db, sid: str, findings: list[Finding]) -> dict:
    prof, tables, placed = context(db, sid)
    window = (prof["window"]["from_year"], prof["window"]["to_year"])
    shown, rejected = [], []
    for f in findings:
        reasons = validate(f, tables, placed, window)
        if reasons:
            db.execute("INSERT INTO finding_rejected (study_id, finding_id, body, reasons) VALUES (?,?,?,?)",
                       (sid, f.id, f.model_dump_json(), json.dumps(reasons)))
            rejected.append({"id": f.id, "reasons": reasons})
        else:
            db.execute("INSERT OR REPLACE INTO finding (study_id, id, body, status) VALUES (?,?,?,?)",
                       (sid, f.id, f.model_dump_json(), f.status))
            shown.append(f.model_dump())
    return {"shown": shown, "rejected": rejected}


PATTERNS_FILE = Path(__file__).parent / "config" / "patterns.json"


@lru_cache(maxsize=1)
def patterns() -> dict:
    return json.loads(PATTERNS_FILE.read_text())


def _num(v: float) -> str:
    """How a T12 value is written in a finding: integers bare, everything else with one decimal."""
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def screen_findings(prof: dict, tables: list[dict]) -> list[Finding]:
    """C7 → findings, written by code from T12. Every number cites its T12 cell; the validator still checks them."""
    t12 = next(t for t in tables if t["id"] == "T12")
    rows = {r["key"]: r for r in t12["rows"]}
    lib = patterns()
    out = []
    for sg in prof["signals"]:
        v = rows[sg["row"]]["values"]
        entry = lib["entries"].get(sg["pattern"])
        text = (f"{sg['noun']} are over-represented at {sg['location']}: {v['target_crashes']} of "
                f"{v['location_crashes']} crashes here ({_num(v['share_pct'])}%) vs "
                f"{_num(v['corridor_share_pct'])}% corridor-wide.")
        cells = ("target_crashes", "location_crashes", "share_pct", "corridor_share_pct")
        out.append(Finding(
            id="c7-" + signals_mod.slug(sg["row"]), location_id=sg["location_id"], text=text,
            title=f"{sg['noun']} over-represented at {sg['location']}",
            numbers=[Number(value=v[k], table_id="T12", cell=f"{sg['row']}/{k}") for k in cells],
            pattern_ref=entry["ref"] if entry else None,
            evidence_refs=Evidence(tables=["T12"], records=RecordFilter(**sg["filter"])), source="screen",
            meta={"strength": v["strength"], "probability": v["probability"], "method": v["method"],
                  "excess_pct": v["excess_pct"], "corridor_crashes": v["corridor_crashes"], "pattern": sg["pattern"], "location": sg["location"],
                  "kind": "segment" if sg["location_id"].startswith("seg") else "intersection",
                  "library_status": lib["status"] if entry else None}))
    return out


def run_screen(db, sid: str) -> dict:
    """(Re)write the code findings for a study. A finding keeps its accept/reject status while its text is unchanged;
    findings the data no longer supports are removed."""
    prof, tables, _ = context(db, sid)
    fresh = screen_findings(prof, tables)
    old = {r["id"]: json.loads(r["body"]) for r in db.query(
        "SELECT id, body FROM finding WHERE study_id = ? AND id LIKE 'c7-%'", (sid,))}
    for f in fresh:
        if f.id in old and old[f.id]["text"] == f.text:
            f.status = old[f.id]["status"]
    keep = {f.id for f in fresh}
    for fid in old:
        if fid not in keep:
            db.execute("DELETE FROM finding WHERE study_id = ? AND id = ?", (sid, fid))
    db.execute("DELETE FROM finding_rejected WHERE study_id = ? AND finding_id LIKE 'c7-%'", (sid,))
    return submit(db, sid, fresh)


router = APIRouter()


@router.get("/findings/schema")
def schema() -> dict:
    return Finding.model_json_schema()


@router.post("/studies/{sid}/findings")
def post_findings(sid: str, body: list[Finding], request: Request) -> dict:
    return submit(request.app.state.db, sid, body)


@router.get("/studies/{sid}/findings")
def get_findings(sid: str, request: Request) -> dict:
    db = request.app.state.db
    rows = db.query("SELECT body FROM finding WHERE study_id = ? ORDER BY rowid", (sid,))
    rej = db.one("SELECT COUNT(*) AS n FROM finding_rejected WHERE study_id = ?", (sid,))["n"]
    return {"findings": [json.loads(r["body"]) for r in rows], "rejected_count": rej}


@router.post("/studies/{sid}/findings/screen")
def post_screen(sid: str, request: Request) -> dict:
    return run_screen(request.app.state.db, sid)


@router.get("/studies/{sid}/findings/{fid}/records")
def get_records(sid: str, fid: str, request: Request) -> dict:
    db = request.app.state.db
    r = db.one("SELECT body FROM finding WHERE study_id = ? AND id = ?", (sid, fid))
    if not r:
        raise HTTPException(404, "Finding not found.")
    f = Finding(**json.loads(r["body"]))
    _, _, placed = context(db, sid)
    keys = ("crash_id", "date", "hour", "day_of_week", "collision_type", "severity", "lighting", "surface", "pcf",
            "primary_road", "secondary_road", "lat", "lon", "location_id")
    return {"records": [{k: c.get(k) for k in keys} for c in select_records(placed, f.evidence_refs.records)]}


@router.get("/patterns")
def get_patterns() -> dict:
    return patterns()


@router.patch("/studies/{sid}/findings/{fid}")
def set_status(sid: str, fid: str, request: Request, status: Literal["accepted", "rejected", "proposed"]) -> dict:
    db = request.app.state.db
    r = db.one("SELECT body FROM finding WHERE study_id = ? AND id = ?", (sid, fid))
    if not r:
        raise HTTPException(404, "Finding not found.")
    body = {**json.loads(r["body"]), "status": status}
    db.execute("UPDATE finding SET body = ?, status = ? WHERE study_id = ? AND id = ?", (json.dumps(body), status, sid, fid))
    return body
