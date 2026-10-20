"""C11 review list (#97): the crashes the app couldn't place, grouped by street pair, for the engineer to place or exclude.

The engineer only chooses: a location (the locator's suggestion, a study intersection, or a point on the map) or
"exclude" with a reason. Code still does every count: a placed crash gets provenance `user` and is assigned by the
normal rules (intersection radius / segment buffer). Decisions are stored per study and laid over the pulled crashes
every time the study is read, so they survive a re-pull. They're matched by Collision Id and kept only while the
report version is the same; a changed report comes back for review (`report_changed`). Nothing is learned across
studies: a placement never feeds an alias table (CLAUDE.md).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import study as study_mod
from .db import Database
from .names import street_key

ACTIONS = ("place", "exclude")
METHODS = ("suggestion", "intersection", "map")


def decisions(db: Database, sid: str) -> dict[str, dict]:
    return {r["crash_id"]: r for r in db.query("SELECT * FROM crash_decision WHERE study_id = ?", (sid,))}


def signature(decs: dict[str, dict]) -> str:
    """Changes whenever a decision does: part of the assignment memo key."""
    raw = json.dumps(sorted((k, v["action"], v["lat"], v["lon"], v["reason"], v["report_version"])
                            for k, v in decs.items()), default=str)
    return hashlib.sha1(raw.encode()).hexdigest()


def overlay(crashes: list[dict], decs: dict[str, dict]) -> list[dict]:
    """The pulled crashes with the engineer's decisions applied (new dicts; the cached pull is never changed).
    A decision applies to a crash the app left unplaced. If CHP has since revised the report, it waits for re-review;
    if the crash now has GPS, the GPS wins."""
    if not decs:
        return crashes
    out = []
    for c in crashes:
        d = decs.get(c["crash_id"])
        if d is None or c.get("location_source") == "gps":
            out.append(c)
        elif d["report_version"] is not None and d["report_version"] != c.get("report_version"):
            out.append({**c, "review_reason": "report_changed", "stale_decision": d["action"]})
        elif d["action"] == "place":
            out.append({**c, "lat": d["lat"], "lon": d["lon"], "location_source": "user", "review_reason": None,
                        "user_method": d["method"]})
        else:
            out.append({**c, "exclude_rule": "user_excluded", "user_reason": d["reason"]})
    return out


def _pair(c: dict, corridor: str, corridor_keys) -> tuple[str, str]:
    """Street pair a crash is listed under. Any spelling of the corridor (SOUTH CRENSHAW BLVD, 'CRENSHAW BLVD;
    MCDONALDS', an address on it) is listed under the corridor's name; each crash still shows the report's text."""
    from .crashes import _names_street

    def norm(raw):
        if raw and corridor_keys and _names_street(raw, corridor_keys):
            return corridor
        k = street_key(raw)
        return f"{k.core} {k.suffix or ''}".strip() if k else (str(raw or "").strip().upper() or "NOT STATED")
    return norm(c.get("primary_road")), norm(c.get("secondary_road"))


def _item(c: dict, a: dict | None, d: dict | None) -> dict:
    return {"crash_id": c["crash_id"], "primary_road": c.get("primary_road"), "secondary_road": c.get("secondary_road"),
            "offset_ft": c.get("offset_ft"), "offset_dir": c.get("offset_dir"), "date": c.get("date"),
            "hour": c.get("hour"), "severity": c.get("severity"), "collision_type": c.get("collision_type"),
            "report_version": c.get("report_version"),
            "reason": c.get("review_reason") or (a or {}).get("rule") or "no_coordinates",
            "suggestion": c.get("suggestion"),
            "decision": None if d is None else {k: d[k] for k in ("action", "method", "lat", "lon", "location_id",
                                                                   "reason", "decided_at")}}


def review_list(db: Database, sid: str) -> dict:
    """Open items (unplaced after decisions) grouped by street pair, plus what was already decided (for undo/edit)."""
    from .assign import for_study
    study, net, pull, a = for_study(db, sid)
    decs = decisions(db, sid)
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    rows = {x["crash_id"]: x for x in a["assignments"]}
    from . import grade
    corridor = str(net.get("corridor_name") or "").upper()
    ck = grade.corridor_keys(net)
    groups: dict[tuple, list] = {}
    for x in a["assignments"]:
        if x["kind"] == "unmatched":
            c = by_id[x["crash_id"]]
            groups.setdefault(_pair(c, corridor, ck), []).append(_item(c, x, decs.get(c["crash_id"])))
    out = []
    for (p, s), items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        items.sort(key=lambda i: (i["date"] or "", i["crash_id"]))
        out.append({"key": f"{p} / {s}", "primary": p, "secondary": s, "count": len(items),
                    "reasons": dict(Counter(i["reason"] for i in items)),
                    "with_suggestion": sum(1 for i in items if i["suggestion"]), "crashes": items})
    names = {i["id"]: i["name"] for i in net["intersections"]} | {g["id"]: g.get("name", g["id"]) for g in net["segments"]}

    def outcome(k):                    # where the code put the crash after the decision (the engineer sees it)
        x = rows.get(k) or {}
        return {"kind": x.get("kind"), "rule": x.get("rule"), "location": names.get(x.get("location_id"))}
    decided = [_item(by_id[k], rows.get(k), d) | {"outcome": outcome(k)} for k, d in decs.items() if k in by_id]
    decided.sort(key=lambda i: i["decision"]["decided_at"] or "", reverse=True)
    return {"open": sum(g["count"] for g in out), "groups": out, "decided": decided,
            "can_undo": bool(db.one("SELECT 1 FROM decision_batch WHERE study_id = ? AND undone = 0", (sid,))),
            "intersections": [{"id": i["id"], "name": i["name"], "lat": i["lat"], "lon": i["lon"]}
                              for i in net["intersections"] if i["is_study"]]}


class DecisionIn(BaseModel):
    crash_ids: list[str] = Field(min_length=1, max_length=5000)
    action: str
    method: str | None = None            # place: suggestion | intersection | map
    location_id: str | None = None       # method=intersection
    lat: float | None = Field(default=None, ge=32.4, le=42.1)      # method=map (inside California)
    lon: float | None = Field(default=None, ge=-124.6, le=-114.0)
    reason: str | None = Field(default=None, max_length=200)       # action=exclude


def decide(db: Database, sid: str, body: DecisionIn) -> dict:
    """One batch of decisions (one crash or a whole group), undoable as a unit."""
    from .assign import for_study
    if body.action not in ACTIONS:
        raise HTTPException(422, f"action must be one of {ACTIONS}")
    study, net, pull, a = for_study(db, sid)
    by_id = {c["crash_id"]: c for c in pull["crashes"]}
    unknown = [i for i in body.crash_ids if i not in by_id]
    if unknown:
        raise HTTPException(404, f"Not crashes of this study: {', '.join(unknown[:5])}")
    rows = []
    for cid in body.crash_ids:
        c = by_id[cid]
        lat = lon = loc = None
        if body.action == "place":
            if body.method == "suggestion":
                sug = c.get("suggestion")
                if not sug:
                    continue                      # a group action places only the crashes that have a suggestion
                lat, lon = sug["lat"], sug["lon"]
            elif body.method == "intersection":
                it = next((i for i in net["intersections"] if i["id"] == body.location_id and i["is_study"]), None)
                if it is None:
                    raise HTTPException(422, "Pick one of the study intersections.")
                lat, lon, loc = it["lat"], it["lon"], it["id"]
            elif body.method == "map":
                if body.lat is None or body.lon is None:
                    raise HTTPException(422, "A map placement needs the point (lat, lon).")
                lat, lon = body.lat, body.lon
            else:
                raise HTTPException(422, f"method must be one of {METHODS}")
        elif not (body.reason or "").strip():
            raise HTTPException(422, "Say why the crash is excluded.")
        rows.append((cid, body.action, body.method if body.action == "place" else None, lat, lon, loc,
                     (body.reason or "").strip() or None, c.get("report_version")))
    if not rows:
        raise HTTPException(422, "None of these crashes has a suggestion to place it at.")
    before = decisions(db, sid)
    with db.transaction() as conn:
        cur = conn.execute("INSERT INTO decision_batch (study_id, before_json) VALUES (?, ?)",
                           (sid, json.dumps({cid: before.get(cid) for cid, *_ in rows}, default=str)))
        bid = cur.lastrowid
        for r in rows:
            conn.execute("INSERT OR REPLACE INTO crash_decision (study_id, crash_id, action, method, lat, lon, "
                         "location_id, reason, report_version, batch_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (sid, *r, bid))
    return {"batch_id": bid, "decided": len(rows), "skipped": len(body.crash_ids) - len(rows)}


def undo(db: Database, sid: str) -> dict:
    """Revert the most recent batch that isn't undone yet."""
    b = db.one("SELECT * FROM decision_batch WHERE study_id = ? AND undone = 0 ORDER BY id DESC LIMIT 1", (sid,))
    if b is None:
        raise HTTPException(409, "Nothing to undo.")
    before = json.loads(b["before_json"])
    cols = ("crash_id", "action", "method", "lat", "lon", "location_id", "reason", "report_version", "batch_id",
            "decided_at")
    with db.transaction() as conn:
        for cid, prev in before.items():
            conn.execute("DELETE FROM crash_decision WHERE study_id = ? AND crash_id = ?", (sid, cid))
            if prev:
                conn.execute(f"INSERT INTO crash_decision (study_id, {', '.join(cols)}) VALUES (?{', ?' * len(cols)})",
                             (sid, *[prev[k] for k in cols]))
        conn.execute("UPDATE decision_batch SET undone = 1 WHERE id = ?", (b["id"],))
    return {"undone": b["id"], "crashes": len(before)}


router = APIRouter()


def _db(request: Request) -> Database:
    return request.app.state.db


@router.get("/studies/{sid}/review")
def get_review(sid: str, request: Request) -> dict:
    return review_list(_db(request), sid)


@router.post("/studies/{sid}/review/decisions")
def post_decision(sid: str, body: DecisionIn, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return {**decide(_db(request), sid, body), "review": review_list(_db(request), sid)}


@router.post("/studies/{sid}/review/undo")
def post_undo(sid: str, request: Request) -> dict:
    study_mod.require(_db(request), sid)
    return {**undo(_db(request), sid), "review": review_list(_db(request), sid)}
