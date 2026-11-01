"""C14 spine: read and write the Oracle project context object (oracle-spine skill, v0), so DemandIQ and other
tiles can share a project with CrashIQ.

Read  (prefill, user can still edit): project.name, corridor.termini, corridor.geometry_ref, corridor.intersections[],
      corridor.functional_class, context.setting.
Write (additive, never overwriting another tile's value; provenance on every field):
      corridor.intersections[] (only if absent; from OSM, method auto), corridor.name/termini/length_mi (if absent),
      analysis.flags[] (data_gap), analysis.completed += "crashiq_profile", data_holdings += CCRS,
      and the `safety` block (docs/04-design.md §3; spine extension proposed in the PR, not yet in the skill).
Unknown fields from other tiles are carried through untouched.
"""

from __future__ import annotations

import copy
import json
from datetime import date

from fastapi import APIRouter, HTTPException, Request

from . import network as network_mod
from . import study as study_mod
from .assign import for_study
from .profile import build as build_profile
from .profile import cell

TILE = "crashiq_profile"
CONTROL_OUT = {"signal": "signal", "stop": "stop"}           # unknown → null, never guessed


def blank() -> dict:
    return {"project": {"name": "", "agency": "", "scope_refs": [], "created": "", "version": 1},
            "corridor": {"name": "", "termini": {"from": "", "to": ""}, "orientation": "", "length_mi": None,
                         "functional_class": "", "geometry_ref": "", "lane_profile": [], "drops_merges": [],
                         "intersections": [], "feeds": [], "grade_separations": []},
            "context": {"setting": "", "generators": []},
            "analysis": {"governing_period_rec": "", "count_program_rec": [], "flags": [], "completed": []},
            "data_holdings": [], "provenance": {}}


def _empty(v) -> bool:
    return v in (None, "", [], {}) or (isinstance(v, dict) and all(_empty(x) for x in v.values()))


def parse_geometry(ref) -> list[list[float]] | None:
    """geometry_ref → [[lat, lon], ...] when it holds a line: GeoJSON LineString/Feature or a coordinate list."""
    if isinstance(ref, str):
        try:
            ref = json.loads(ref)
        except (ValueError, TypeError):
            return None
    if isinstance(ref, dict):
        g = ref.get("geometry", ref)
        if g.get("type") == "LineString" and len(g.get("coordinates", [])) >= 2:
            return [[c[1], c[0]] for c in g["coordinates"]]          # GeoJSON is lon, lat
        return None
    if isinstance(ref, list) and len(ref) >= 2 and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in ref):
        return [list(map(float, p)) for p in ref]
    return None


def prefill(ctx: dict) -> dict:
    c = ctx.get("corridor", {}) or {}
    return {"name": (ctx.get("project", {}) or {}).get("name") or c.get("name") or None,
            "termini": c.get("termini") or None,
            "line": parse_geometry(c.get("geometry_ref")),
            "intersections": [i for i in c.get("intersections", []) if i.get("name")],
            "functional_class": c.get("functional_class") or None,
            "setting": (ctx.get("context", {}) or {}).get("setting") or None}


def merge(base: dict, crash: dict, today: str | None = None) -> dict:
    """Write CrashIQ results into a context object. `crash` = what CrashIQ knows (see `crashiq_view`)."""
    today = today or date.today().isoformat()
    ctx = copy.deepcopy(base) if base else blank()
    for k, v in blank().items():
        ctx.setdefault(k, copy.deepcopy(v))
    prov = ctx.setdefault("provenance", {})
    changed = False

    def put(path: str, value, source: str, method: str = "auto"):
        nonlocal changed
        target = ctx
        keys = path.split(".")
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        if not _empty(target.get(keys[-1])):
            return                                  # another tile's value: never overwrite
        target[keys[-1]] = value
        prov[path] = {"source": source, "method": method, "date": today}
        changed = True

    net = crash.get("network") or {}
    if net.get("line"):
        put("corridor.name", net.get("corridor_name") or "", "OSM")
        ints = net.get("intersections", [])
        study_ints = [i for i in ints if i["is_study"]]
        if study_ints:
            put("corridor.termini", {"from": study_ints[0]["name"], "to": study_ints[-1]["name"]}, "OSM")
        put("corridor.length_mi", round(net["length_mi"], 3), "OSM")
        put("corridor.intersections", [
            {"name": i["name"], "legs": None, "control": CONTROL_OUT.get(i["control"]),
             # the spine's control is signal|stop|uncontrolled; a roundabout or yield goes alongside, additively (#337)
             **({"control_detail": i["control"]} if i["control"] in ("roundabout", "yield") else {}),
             "spacing_ft_to_next": (round(b["station_ft"] - i["station_ft"], 1) if b else None),
             "source_id": i["id"], "method": "auto" if i["provenance"] == "auto" else "manual"}
            for i, b in zip(study_ints, study_ints[1:] + [None])], "OSM")
        gs = net.get("grade_separations") or []
        if gs:
            put("corridor.grade_separations", [
                {"name": g["name"], "relation": g["relation"], "station_ft": g["station_ft"], "source_id": g["id"],
                 "method": "auto"} for g in gs], "OSM")
        put("corridor.geometry_ref", {"type": "LineString", "coordinates": [[p[1], p[0]] for p in net["line"]]},
            "CrashIQ (user-drawn corridor)", "manual")

    an = ctx.setdefault("analysis", {})
    safety = crash.get("safety")
    if safety:
        flags = an.setdefault("flags", [])
        for f in crash.get("flags", []):
            if not any(x.get("type") == f["type"] and x.get("detail") == f["detail"] for x in flags):
                flags.append(f)
                changed = True
        if TILE not in an.setdefault("completed", []):
            an["completed"].append(TILE)
            changed = True
        prov["analysis.completed"] = {"source": "CrashIQ", "method": "auto", "date": today}
        holding = crash["holding"]
        dh = ctx.setdefault("data_holdings", [])
        dh[:] = [h for h in dh if not (h.get("kind") == "CCRS" and h.get("path_or_ref") == holding["path_or_ref"])]
        dh.append(holding)
        prov["data_holdings.CCRS"] = {"source": "CCRS (CHP)", "method": "auto", "date": today}
        if ctx.get("safety") != safety:
            changed = True
        ctx["safety"] = safety                      # CrashIQ owns this block
        prov["safety"] = {"source": "CCRS (CHP) + OSM", "method": "auto", "date": today}
    if changed:
        ctx["project"]["version"] = int(ctx["project"].get("version") or 1) + 1
    return ctx


def crashiq_view(db, sid: str) -> dict:
    """Everything CrashIQ can write for a study, from its own tables. Profile parts only once crashes are pulled."""
    net = network_mod.network(db, sid)
    out = {"network": net}
    try:
        study, net, pull, a = for_study(db, sid)
    except HTTPException:
        return out
    p = build_profile(study, net, pull, a)
    t2 = next(t for t in p["tables"] if t["id"] == "T2")
    prov = p["location_provenance"]
    out["safety"] = {
        "window": {"from_year": study["from_year"], "to_year": study["to_year"],
                   "preliminary_included": any(c["key"] == "preliminary" for c in p["caveats"])},
        "locate_summary": {"gps": prov.get("gps", 0) + prov.get("gps_dms_corrected", 0) + prov.get("gps_sign_corrected", 0) + prov.get("gps_offset_applied", 0), "exact": prov.get("exact", 0), "fuzzy": prov.get("fuzzy", 0),
                           "jev": sum(v for k, v in prov.items() if k.startswith("jev")), "user": prov.get("user", 0),
                           "unmatched": prov.get("unmatched", 0)},
        "locations": [{"id": r["key"], "name": r["label"], "kind": r["values"]["kind"], "crashes": r["values"]["crashes"],
                       "ksi": r["values"]["ksi_crashes"], "crashes_per_mi_yr": r["values"]["crashes_per_mi_yr"],
                       "rate": r["values"]["rate"]} for r in t2["rows"]],
        "findings": [],
    }
    flags = []
    unplaced = next((c for c in p["caveats"] if c["key"] == "unplaced"), None)
    if unplaced:
        flags.append({"type": "data_gap", "detail": f"{unplaced['share_pct']}% of corridor crashes unplaced (no coordinates)"})
    if pull["cleaning"].get("years_missing"):
        flags.append({"type": "data_gap", "detail": f"CCRS years missing: {pull['cleaning']['years_missing']}"})
    out["flags"] = flags
    out["holding"] = {"kind": "CCRS", "period": f"{study['from_year']}–{study['to_year']}",
                      "location": net.get("corridor_name") or "", "path_or_ref": f"crashiq:study/{sid}/crashes",
                      "crashes": cell(p["tables"], "T1/crashes/value")}
    return out


# -- API -------------------------------------------------------------------------------------------------
router = APIRouter()


def _stored(db, sid):
    r = db.one("SELECT body FROM context_object WHERE study_id = ?", (sid,))
    return json.loads(r["body"]) if r else None


@router.put("/studies/{sid}/context")
def put_context(sid: str, body: dict, request: Request) -> dict:
    """Import a context object from another tile (e.g. DemandIQ). Returns what CrashIQ can prefill."""
    db = request.app.state.db
    study_mod.require(db, sid)
    db.execute("INSERT OR REPLACE INTO context_object (study_id, body) VALUES (?, ?)", (sid, json.dumps(body)))
    return {"prefill": prefill(body)}


@router.get("/studies/{sid}/context/prefill")
def get_prefill(sid: str, request: Request) -> dict:
    db = request.app.state.db
    study_mod.require(db, sid)
    ctx = _stored(db, sid)
    return {"prefill": prefill(ctx) if ctx else None}


@router.get("/studies/{sid}/context")
def get_context(sid: str, request: Request) -> dict:
    """The context object with CrashIQ's results written in (export for other tiles)."""
    db = request.app.state.db
    s = study_mod.require(db, sid)
    base = _stored(db, sid) or blank()
    if _empty(base.get("project", {}).get("name")):
        base.setdefault("project", {})["name"] = s["name"]
        base.setdefault("provenance", {})["project.name"] = {"source": "CrashIQ", "method": "manual", "date": s["created_at"][:10]}
    return merge(base, crashiq_view(db, sid))
