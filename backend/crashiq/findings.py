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
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import assign as assign_mod
from . import profile as profile_mod

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


router = APIRouter()


@router.get("/findings/schema")
def schema() -> dict:
    return Finding.model_json_schema()


@router.post("/studies/{sid}/findings")
def post_findings(sid: str, body: list[Finding], request: Request) -> dict:
    return submit(request.app.state.db, sid, body)


def generate(db, sid: str) -> dict:
    from . import patterns
    prof, _, _ = context(db, sid)
    t12 = next(t for t in prof["tables"] if t["id"] == "T12")
    kept = {r["id"]: r["status"] for r in db.query("SELECT id, status FROM finding WHERE study_id = ?", (sid,))}
    fresh = [Finding(**f, status=kept.get(f["id"], "proposed")) for f in patterns.findings_from(t12)]
    ids = {f.id for f in fresh}
    for old, status in kept.items():          # patterns that no longer apply disappear unless the user decided on them
        if old.startswith("auto-") and old not in ids and status == "proposed":
            db.execute("DELETE FROM finding WHERE study_id = ? AND id = ?", (sid, old))
    res = submit(db, sid, fresh)
    return {**res, "method": t12["method"], "flagged": len(t12["rows"])}


@router.post("/studies/{sid}/findings/generate")
def post_generate(sid: str, request: Request) -> dict:
    return generate(request.app.state.db, sid)


@router.get("/studies/{sid}/findings")
def get_findings(sid: str, request: Request) -> dict:
    db = request.app.state.db
    rows = db.query("SELECT body FROM finding WHERE study_id = ? ORDER BY rowid", (sid,))
    rej = db.one("SELECT COUNT(*) AS n FROM finding_rejected WHERE study_id = ?", (sid,))["n"]
    return {"findings": [json.loads(r["body"]) for r in rows], "rejected_count": rej}


@router.patch("/studies/{sid}/findings/{fid}")
def set_status(sid: str, fid: str, request: Request, status: Literal["accepted", "rejected", "proposed"]) -> dict:
    db = request.app.state.db
    r = db.one("SELECT body FROM finding WHERE study_id = ? AND id = ?", (sid, fid))
    if not r:
        raise HTTPException(404, "Finding not found.")
    body = {**json.loads(r["body"]), "status": status}
    db.execute("UPDATE finding SET body = ?, status = ? WHERE study_id = ? AND id = ?", (json.dumps(body), status, sid, fid))
    return body
