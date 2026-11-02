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
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import assign as assign_mod
from . import profile as profile_mod
from . import pcf as pcf_mod
from . import signals as signals_mod

SPELLED = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())}
SPELLED.update({"thirty": 30, "forty": 40, "fifty": 50})
del SPELLED["one"]   # "one" is mostly a determiner ("one report", "one of the"); counts of one must use digits
# #359: "$4.2M", "3x", "-45%" and "1e3" are figures too; "osm-123" and "2021-2025"'s 2025 are not
_NUM = re.compile(r"(?<![\w.])(?<!\w-)(-?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(e[+-]?\d+)?"
                  r"(?:\s*(%|percent)|([kmb]|x|×))?(?![\w])", re.I)
_SCALE = {"k": 3, "m": 6, "b": 9}
_RATIO_COLS = ("ratio_to_corridor", "rate_to_critical", "ratio_to_statewide")   # what "3x" can stand for
# Ratio and change words are numbers (user, 2026-11-02, docs/03 #359): a word is written at RATIO_WORD_DECIMALS, so
# the ratio behind it must round to the word's value there (1: "doubled" = 1.95 to 2.049, not the word's own precision;
# user, 2026-11-02, "Yes, tight"; #362).
RATIO_WORD_DECIMALS = 1
RATIO_WORDS = {"doubled": 2, "twice": 2, "tripled": 3, "quadrupled": 4, "half": 0.5}
# Always rejected; the finding writes the cited numbers as digits (user, 2026-11-02, #362): count words ("option A"),
# and ratio words not exact at RATIO_WORD_DECIMALS ("a third" would pass for 0.25 in the 0.3 window).
COUNT_WORDS: tuple[str, ...] = ("a dozen", "dozens", "a few dozen", "several dozen", "a hundred", "hundreds",
                                "a few hundred", "several hundred", "a handful", "a third", "two thirds")
_RATIO_WORD = re.compile(r"\b(" + "|".join(RATIO_WORDS) + r")\b", re.I)


def _ratio_written(word: str) -> str:
    """'doubled' -> '2.0' at RATIO_WORD_DECIMALS: what matches() compares the ratio with."""
    return str(round_half_up(RATIO_WORDS[word], RATIO_WORD_DECIMALS))
_ORDINAL = re.compile(r"(?<![\w.])\d+(?:st|nd|rd|th)\b", re.I)
_SPELLED = re.compile(r"\b(" + "|".join(SPELLED) + r")\b", re.I)
_QUOTED = re.compile(r"[\"“]([^\"”]{1,120})[\"”]")
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


class Number(BaseModel):
    value: float
    table_id: str
    cell: str = Field(description="'<row>/<column>' inside table_id")


class RecordFilter(BaseModel):
    crash_id: str | None = None          # one crash record by its Collision Id (a fatal-crash finding, #274)
    location_id: str | None = None
    severity: list[str] | None = None
    collision_type: list[str] | None = None
    lighting_dark: bool | None = None
    ped: bool | None = None
    bike: bool | None = None
    motorcycle: bool | None = None
    surface_wet: bool | None = None
    lighting_unlit: bool | None = None
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
    """The cell, rounded to the written precision, equals the written figure. "4.2M" is 4.2 millions (#359); a
    multiple ("3x") is compared as written."""
    if cell_value is None or isinstance(cell_value, (str, bool)):
        return False
    written = written.replace(",", "").rstrip("xX×")
    if written[-1:].lower() in _SCALE:
        cell_value, written = float(cell_value) / 10 ** _SCALE[written[-1].lower()], written[:-1]
    w = Decimal(written)
    d = max(0, -w.as_tuple().exponent)
    return round_half_up(float(cell_value), d) == w


def extract_numbers(text: str, quoted_ok: set[str], names: set[str] | None = None) -> list[str]:
    """Numbers a reader would take as claims, as written (e.g. '38', '2.5', '1,204'). `names` are the cited
    locations' own names from the tables: digits inside them ("Mercedes Avenue / CA 41", "US 395") are part of a road
    name, not a figure (#179)."""
    masked = text
    for name in sorted(names or (), key=len, reverse=True):          # longest first: "A / CA 41" before "CA 41"
        if any(ch.isdigit() for ch in name):
            masked = masked.replace(name, " " * len(name))
    for m in _QUOTED.finditer(text):
        if m.group(1).strip().lower() in quoted_ok:
            masked = masked.replace(m.group(0), " " * len(m.group(0)))
    for code in quoted_ok:            # "VC 22350": a record's own PCF code, written after VC (#346)
        masked = re.sub(rf"\bVC\s+{re.escape(code)}\b", lambda m: " " * len(m.group(0)), masked, flags=re.I)
    masked = _ORDINAL.sub(lambda m: " " * len(m.group(0)), masked)
    counts = []                          # read and blanked first: "two thirds" is one claim, not the number 2
    if COUNT_WORDS:
        pat = r"\b(" + "|".join(sorted(COUNT_WORDS, key=len, reverse=True)) + r")\b"
        counts = [m.group(1).lower() for m in re.finditer(pat, masked, re.I)]
        masked = re.sub(pat, lambda m: " " * len(m.group(0)), masked, flags=re.I)
    out = [m.group(1) + m.group(2) + (m.group(3) or "") + (m.group(4) or "") + (m.group(6) or "")
           for m in _NUM.finditer(masked)]
    out += [str(SPELLED[m.group(1).lower()]) for m in _SPELLED.finditer(masked)]
    out += [m.group(1).lower() for m in _RATIO_WORD.finditer(masked)]
    out += counts
    return out


def _backs_ratio(written: str, finding: Finding, tables: list[dict], by_id: dict) -> bool:
    """A multiple ("3x", "doubled") is backed by a cited ratio cell, or by two cited cells whose quotient rounds to
    it (docs/03 #359)."""
    vals = []
    for n in finding.numbers:
        if n.table_id not in by_id:
            continue
        try:
            v = profile_mod.cell(tables, f"{n.table_id}/{n.cell}")
        except (StopIteration, KeyError, ValueError):
            continue
        if n.cell.rsplit("/", 1)[-1] in _RATIO_COLS and matches(written, v):
            return True
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(float(v))
    return any(b and matches(written, a / b) for i, a in enumerate(vals) for j, b in enumerate(vals) if i != j)


def select_records(crashes: list[dict], f: RecordFilter) -> list[dict]:
    out = []
    for c in crashes:
        if f.crash_id is not None and str(c.get("crash_id")) != f.crash_id:
            continue
        if f.location_id is not None and c.get("location_id") != f.location_id:
            continue
        if f.severity and c.get("severity") not in f.severity:
            continue
        if f.collision_type and (c.get("collision_type") or "").upper() not in {x.upper() for x in f.collision_type}:
            continue
        if f.lighting_dark is not None and profile_mod.is_dark(c) != f.lighting_dark:
            continue
        if f.lighting_unlit is not None and profile_mod.is_unlit(c) != f.lighting_unlit:
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
    # a date written in the text must be the date of a cited crash record (#274: a fatal crash on its date)
    dates = {str(c.get("date") or "")[:10] for c in evidence}
    for d in _DATE.findall(finding.text):
        if d not in dates:
            reasons.append(f"date {d} in the text is not the date of a cited crash record")
    lo, hi = window
    for w in extract_numbers(finding.text, quoted_ok, _location_names(finding, tables)):
        plain = w.replace(",", "")
        if plain.isdigit() and lo <= int(plain) <= hi:
            continue                                   # a year inside the study window
        if w in COUNT_WORDS:
            ok = False                                 # a count word: write the cited number as digits
        elif w in RATIO_WORDS or w[-1] in "xX×":
            ok = _backs_ratio(_ratio_written(w) if w in RATIO_WORDS else plain, finding, tables, by_id)
        else:
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


def _location_names(finding: Finding, tables: list[dict]) -> set[str]:
    """The names of the locations this finding cites, as the app's own tables write them: the label of each cited row
    (the part before " · "), the T2 label of the finding's location, and each street of a corner ("A / B")."""
    keys = {n.cell.split("/")[0] for n in finding.numbers}
    out = set()
    for t in tables:
        for r in t.get("rows", []):
            if (t["id"] in {n.table_id for n in finding.numbers} and r["key"] in keys) or \
                    (t["id"] == "T2" and r["key"] == finding.location_id):
                name = str(r.get("label") or "").split(" · ")[0].strip()
                if name:
                    out.add(name)
                    out.update(part.strip() for part in name.split(" / ") if part.strip())
    return out


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


def prof_total(prof: dict):
    return profile_mod.cell(prof["tables"], "T1/crashes/value")


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
                f"{_num(v['reference_share_pct'])}% across the {v['reference']}.")
        if sg["location_id"] in (prof.get("approximate_locations") or []):     # #255, no number: nothing to cite
            text += " Some crashes here are freeway crashes placed approximately from the report (no usable GPS)."
        if sg["location_id"] in (prof.get("address_nad_locations") or []):    # #283, likewise
            text += " Some crashes here are placed approximately at the house address the report gives (no usable GPS)."
        cells = ("target_crashes", "location_crashes", "share_pct", "reference_share_pct")
        out.append(Finding(
            id="c7-" + signals_mod.slug(sg["row"]), location_id=sg["location_id"], text=text,
            title=f"{sg['noun']} over-represented at {sg['location']}",
            numbers=[Number(value=v[k], table_id="T12", cell=f"{sg['row']}/{k}") for k in cells],
            pattern_ref=entry["ref"] if entry else None,
            evidence_refs=Evidence(tables=["T12"], records=RecordFilter(**sg["filter"])), source="screen",
            meta={"strength": v["strength"], "probability": v["probability"], "method": v["method"],
                  "excess_pct": v["excess_pct"], "reference": v["reference"],
                  "reference_crashes": v["reference_crashes"], "corridor_crashes": prof_total(prof), "pattern": sg["pattern"], "location": sg["location"],
                  "kind": sg["kind"],
                  "library_status": lib["status"] if entry else None}))
    return out


ROAD_USERS = (("ped", "a pedestrian"), ("bike", "a bicyclist"), ("ebike", "an e-bike rider"),
              ("escooter", "an e-scooter rider"), ("motorcycle", "a motorcyclist"))
APPROX = ("approximate", "address_nad")


def _reported_elsewhere(c: dict, row: dict) -> str | None:
    """The report's own location, quoted as written (title case), when neither road it names is a street of the
    intersection its GPS placed it at (#346: "RT 82 / CARMELITA AV" placed by GPS at Broadway). None otherwise."""
    if row["values"].get("kind") != "intersection" or c.get("location_source") in APPROX:
        return None
    from .names import same_core, street_key
    roads = [r for r in (c.get("primary_road"), c.get("secondary_road")) if r and str(r).strip()]
    keys = [k for k in (street_key(p) for p in str(row["label"]).split(" / ")) if k]
    if not roads or not keys or any(street_key(r) and same_core(street_key(r), k) for r in roads for k in keys):
        return None
    return " / ".join(f'"{str(r).strip().title()}"' for r in roads)


def fatal_findings(prof: dict, tables: list[dict], placed: list[dict]) -> list[Finding]:
    """#274 (user decision 2026-10-25, docs/03): every fatal crash placed at a study location is its own finding,
    written by code from the crash record, with no statistical test. It cites the record (Collision Id) and the
    location's T2 row; an approximate placement says so (and never reaches a collision diagram, #255)."""
    t2 = {r["key"]: r for t in tables if t["id"] == "T2" for r in t["rows"]}
    out = []
    for c in sorted((c for c in placed if c.get("severity") == "K" and c.get("location_id") in t2),
                    key=lambda c: (str(c.get("date") or ""), str(c["crash_id"]))):
        row = t2[c["location_id"]]
        what = [(c.get("collision_type") or "collision type not stated").lower()]
        if c.get("pcf"):                  # the category label, as tab 3's chart shows it, and the code (#346)
            label = pcf_mod.labels().get(c.get("pcf_class") or "")
            what.append(f"primary collision factor {label.lower()} (VC {c['pcf']})" if label
                        else f'primary collision factor "{c["pcf"]}"')
        users = [w for k, w in ROAD_USERS if c.get(k)]
        what.append("involving " + " and ".join(users) if users else "vehicles only")
        approx = c.get("location_source") in APPROX
        reported = _reported_elsewhere(c, row)
        text = (f"Fatal crash at {row['label']} on {str(c.get('date'))[:10]}: {', '.join(what)}."
                + (" Approximate location: no usable GPS, placed from the report." if approx else "")
                + (f" Reported at {reported}; the officer's GPS places it at {row['label']}." if reported else ""))
        out.append(Finding(
            id=f"fatal-{c['crash_id']}", location_id=c["location_id"], text=text,
            title=f"Fatal crash at {row['label']}",
            numbers=[Number(value=row["values"]["fatal_crashes"], table_id="T2", cell=f"{c['location_id']}/fatal_crashes")],
            evidence_refs=Evidence(tables=["T2"], records=RecordFilter(crash_id=str(c["crash_id"]),
                                                                          location_id=c["location_id"])),
            source="screen",
            meta={"kind_of_finding": "fatal", "pattern": "fatal", "location": row["label"], "crash_id": str(c["crash_id"]),
                  "kind": row["values"].get("kind"), "approximate": approx, "corridor_crashes": prof_total(prof)}))
    return out


def run_screen(db, sid: str) -> dict:
    """(Re)write the code findings for a study. A finding keeps its accept/reject status while its text is unchanged;
    findings the data no longer supports are removed."""
    prof, tables, placed = context(db, sid)
    fresh = screen_findings(prof, tables) + fatal_findings(prof, tables, placed)
    old = {r["id"]: json.loads(r["body"]) for r in db.query(
        "SELECT id, body FROM finding WHERE study_id = ? AND (id LIKE 'c7-%' OR id LIKE 'fatal-%')", (sid,))}
    for f in fresh:
        if f.id in old and old[f.id]["text"] == f.text:
            f.status = old[f.id]["status"]
    keep = {f.id for f in fresh}
    for fid in old:
        if fid not in keep:
            db.execute("DELETE FROM finding WHERE study_id = ? AND id = ?", (sid, fid))
    db.execute("DELETE FROM finding_rejected WHERE study_id = ? AND (finding_id LIKE 'c7-%' OR finding_id LIKE 'fatal-%')",
               (sid,))
    return submit(db, sid, fresh)


router = APIRouter()


@router.get("/findings/schema")
def schema() -> dict:
    return Finding.model_json_schema()


@router.post("/studies/{sid}/findings")
def post_findings(sid: str, body: list[Finding], request: Request) -> dict:
    """The analyst's entry point. The server owns status, source and id: nothing submitted here can arrive
    accepted, pass as code-written, or overwrite an existing finding. Only the user's PATCH accepts."""
    db = request.app.state.db
    taken = {r["id"] for r in db.query("SELECT id FROM finding WHERE study_id = ?", (sid,))}
    for f in body:
        f.status, f.source = "proposed", "analyst"
        if f.id.startswith("c7-") or f.id in taken:
            f.id = "f-" + uuid.uuid4().hex[:8]
        f.meta = {k: v for k, v in f.meta.items() if k not in ("decided_at", "decided_status")}
    return submit(db, sid, body)


def check_stored(db, sid: str) -> list[dict]:
    """Every stored finding re-validated against the data as it is now. A finding whose numbers no longer match
    (radius, window or corridor changed) is marked stale and is never exported."""
    rows = db.query("SELECT body FROM finding WHERE study_id = ? ORDER BY rowid", (sid,))
    if not rows:
        return []
    try:
        prof, tables, placed = context(db, sid)
        window = (prof["window"]["from_year"], prof["window"]["to_year"])
    except HTTPException:
        return [{**json.loads(r["body"]), "stale": True, "stale_reasons": ["the study's crashes need re-pulling"]}
                for r in rows]
    t2 = {r["key"]: r for t in tables if t["id"] == "T2" for r in t["rows"]}
    out = []
    for r in rows:
        f = json.loads(r["body"])
        model = Finding(**f)
        reasons = validate(model, tables, placed, window)
        recs = select_records(placed, model.evidence_refs.records)
        out.append({**f, "stale": bool(reasons), "stale_reasons": reasons,
                    # #267: the location by its current name (T2), never an id; and what the list is ordered by
                    "location_name": (t2.get(f.get("location_id")) or {}).get("label")
                    or _named((f.get("meta") or {}).get("location")),
                    "rank": {"location_fatal_crashes": ((t2.get(f.get("location_id")) or {}).get("values") or {})
                             .get("sev_k", 0),
                             "fatal_crashes": sum(c.get("severity") == "K" for c in recs),
                             "ksi_crashes": sum(c.get("severity") in ("K", "A") for c in recs), "crashes": len(recs)}})
    return sorted(out, key=_order)


def _named(label) -> str | None:
    """A stored label that is a name, or None when it is an id (SEG:OSM-1029:OSM-1035, osm-1029)."""
    s = str(label or "").strip()
    return None if not s or re.match(r"^(SEG|INT|LOC)?:?\s*OSM-?\d", s.upper()) or re.match(r"^(SEG|INT):", s.upper()) else s


def _order(f: dict):
    """#267: the fatal-crash findings (#274), then findings at locations with a fatal crash (T2), then by KSI crashes in
    the finding's records, then by test strength (probability), then by crash count; stale findings last. Ties keep the
    screen's order."""
    rk = f.get("rank") or {}
    fatal = (f.get("meta") or {}).get("kind_of_finding") == "fatal"                      # every fatal crash first (#274)
    return (bool(f.get("stale")), -fatal, -(rk.get("location_fatal_crashes", 0) > 0), -rk.get("ksi_crashes", 0),
            -float((f.get("meta") or {}).get("probability") or 0), -rk.get("crashes", 0))


@router.get("/studies/{sid}/findings")
def get_findings(sid: str, request: Request) -> dict:
    db = request.app.state.db
    from . import study as study_mod
    study_mod.require(db, sid)
    rej = db.one("SELECT COUNT(*) AS n FROM finding_rejected WHERE study_id = ?", (sid,))["n"]
    return {"findings": check_stored(db, sid), "rejected_count": rej}


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


@router.get("/studies/{sid}/findings/{fid}/diagram")
def get_diagram(sid: str, fid: str, request: Request) -> dict:
    """#268: the N10 collision diagram of a finding's own records at a study intersection, numbered and keyed to a
    T21 list; for a segment finding, where the segment lies along the corridor. Approximate freeway placements are
    never at an intersection, so they never reach a diagram."""
    db = request.app.state.db
    r = db.one("SELECT body FROM finding WHERE study_id = ? AND id = ?", (sid, fid))
    if not r:
        raise HTTPException(404, "Finding not found.")
    f = Finding(**json.loads(r["body"]))
    study, net, pull, a = assign_mod.for_study(db, sid)
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    placed = [{**by_id[x["crash_id"]], "location_id": x["location_id"], "location_provenance": x["location_provenance"],
               "station_ft": x.get("station_ft")} for x in a["assignments"] if x["kind"] in ("intersection", "segment")]
    recs = select_records(placed, f.evidence_refs.records)
    it = next((i for i in net["intersections"] if i["id"] == f.location_id and i.get("is_study")), None)
    if it is not None:
        from . import diagram as diagram_mod
        d = diagram_mod.build(net, it, recs)
        return {"kind": "intersection", "records": len(recs), "diagram": d,
                "table": profile_mod.diagram_table(fid, d, recs)}
    seg = next((g for g in net.get("segments", []) if g["id"] == f.location_id), None)
    length = max([g["to_station_ft"] for g in net.get("segments", [])] + [net.get("length_ft") or 0])
    keys = ("crash_id", "date", "hour", "severity", "collision_type", "location_id", "station_ft", "ped", "bike",
            "ebike", "escooter")
    return {"kind": "segment", "records": len(recs), "diagram": None,
            "strip": {"location_id": f.location_id, "name": seg["name"] if seg else None,
                      "from_ft": seg["from_station_ft"] if seg else None,
                      "to_ft": seg["to_station_ft"] if seg else None, "length_ft": length,
                      # the strip's labels (PM review of #293): the corridor's study intersections, by name
                      "intersections": [{"id": i["id"], "name": i["name"], "station_ft": i["station_ft"]}
                                        for i in net["intersections"] if i.get("is_study")],
                      "crashes": [{k: c.get(k) for k in keys} for c in recs]}}


@router.get("/patterns")
def get_patterns() -> dict:
    return patterns()


@router.patch("/studies/{sid}/findings/{fid}")
def set_status(sid: str, fid: str, request: Request, status: Literal["accepted", "rejected", "proposed"]) -> dict:
    db = request.app.state.db
    r = db.one("SELECT body FROM finding WHERE study_id = ? AND id = ?", (sid, fid))
    if not r:
        raise HTTPException(404, "Finding not found.")
    body = json.loads(r["body"])
    if status == "accepted":
        prof, tables, placed = context(db, sid)
        reasons = validate(Finding(**body), tables, placed, (prof["window"]["from_year"], prof["window"]["to_year"]))
        if reasons:
            raise HTTPException(409, "This finding no longer matches the data (the study changed). Re-run the screen.")
    meta = {**(body.get("meta") or {}), "decided_status": status,
            "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    body = {**body, "status": status, "meta": meta}
    db.execute("UPDATE finding SET body = ?, status = ? WHERE study_id = ? AND id = ?", (json.dumps(body), status, sid, fid))
    return {**body, "stale": False, "stale_reasons": []}
