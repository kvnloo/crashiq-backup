"""C5 assign: every crash → a study intersection, a segment, excluded, or unmatched. Deterministic; counts add up.

Rules (docs/03-requirements.md R2.3-4):
1. No coordinates yet → `unmatched` (counted, never dropped).
2. Within the influence radius (study setting, default 250 ft) of a study intersection → that intersection.
   Inside more than one radius → the nearest one, which splits at mid-block when intersections are
   closer than twice the radius. (The formal HSIP < 500 ft rule is #3 Q6; it would replace `_pick_intersection` only.)
3. Otherwise within the corridor buffer of the drawn line and between A and B → the segment it projects onto.
4. Otherwise → `excluded`, with the reason. Grade separations (N7, #67, `grade.py`): a crash on a road passing
   over or under the corridor → `grade_separated_crossing`; on a freeway corridor only CHP IsFreeway crashes count. Crashes the pull already ruled out (`exclude_rule`, e.g. a side street
   that isn't one of the corridor's intersections, #39) are `excluded` under that rule: listed, not dropped.
5. Road-name check for GPS crashes (#53, the #39 rule): a crash in an influence area or the buffer whose report
   names neither the corridor nor (at an intersection) that cross street → `excluded`, `not_on_corridor_street`.
   Blank road fields are kept. A GPS point more than 400 ft (plus the reported offset) from the intersection the
   report names is flagged (`gps_check`) and counted, not moved.
Ties: inside two radii at exactly the same distance → the lower station (A side).
Distances are feet in the corridor's projected CRS.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter

from fastapi import APIRouter, HTTPException, Request

from . import crashes as crashes_mod
from . import grade
from . import review as review_mod
from . import network as network_mod
from . import union as union_mod
from . import study as study_mod
from .geo import Polyline

KINDS = ("intersection", "segment", "excluded", "unmatched")
GPS_CHECK_FT = 400.0    # GPS more than this (plus the reported offset) from the intersection the report names: flagged


def _names(c: dict, keys) -> bool | None:
    """Does the report name one of these streets? None when both road fields are blank (nothing to check)."""
    roads = [r for r in (c.get("primary_road"), c.get("secondary_road")) if r and str(r).strip()]
    if not roads or not keys:
        return None
    return any(crashes_mod._names_street(r, keys) or grade.names(r, keys) for r in roads)


def _stated_intersection(c: dict, studies: list[dict], corridor_keys) -> dict | None:
    """The study intersection the report names (corridor street + that cross street), if exactly one."""
    if not _names(c, corridor_keys):
        return None
    hits = [i for i in studies if _names(c, grade.intersection_keys(i))]
    return hits[0] if len(hits) == 1 else None


def _pick_intersection(cands: list[tuple[float, dict]]) -> tuple[float, dict, str]:
    d, it = min(cands, key=lambda t: (t[0], t[1]["station_ft"]))
    return d, it, "influence_radius" if len(cands) == 1 else "nearest_of_overlapping_radii"


def assign(crashes: list[dict], net: dict, radius_ft: float, buffer_ft: float, include_freeway: bool = False,
           carriageways: list | None = None) -> dict:
    line = Polyline([tuple(p) for p in net["line"]])
    # a freeway corridor's buffer is measured from every carriageway of its route, not only the drawn line (#329);
    # station, and so the study limits and the segment, still come from the drawn line
    lanes = [Polyline([tuple(p) for p in cw], line.proj) for cw in (carriageways or [])] if net.get("is_freeway") else []
    off_ft = lambda p, x, y: min([p.offset_ft] + [ln.project_xy(x, y).offset_ft for ln in lanes]) \
        if lanes and p.offset_ft > buffer_ft else p.offset_ft                       # noqa: E731
    studies = [i for i in net["intersections"] if i["is_study"]]
    pts = {i["id"]: line.proj.to_xy(i["lat"], i["lon"]) for i in studies}
    segs = net["segments"]
    freeway = bool(net.get("is_freeway"))
    corridor_keys = grade.corridor_keys(net)
    crossings = grade.crossing_keys(net)
    out = []
    for c in crashes:
        base = {"crash_id": c["crash_id"], "location_provenance": c.get("location_source", "gps")}
        if c.get("exclude_rule"):      # decided at pull time, e.g. a side street off the corridor (#39)
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": None, "rule": c["exclude_rule"]})
            continue
        rule = None
        if not freeway and c.get("is_freeway") and not include_freeway:  # CHP's IsFreeway: mainline/ramp crashes under or beside an arterial study
            rule = "freeway"
        elif grade.on_crossing_road(c, corridor_keys, crossings):        # on a road over/under the corridor (N7, #67)
            rule = "grade_separated_crossing"
        elif freeway:                               # freeway corridor: only IsFreeway crashes, ramps on the switch
            rule = grade.freeway_rule(c, include_freeway)
        if rule:
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": None, "rule": rule})
            continue
        if c.get("lat") is None or c.get("lon") is None:
            out.append({**base, "kind": "unmatched", "location_id": None, "distance_ft": None,
                        "rule": c.get("review_reason") or "no_coordinates"})
            continue
        x, y = line.proj.to_xy(c["lat"], c["lon"])
        cands = [(math.hypot(x - px, y - py), it) for it in studies for px, py in [pts[it["id"]]]
                 if math.hypot(x - px, y - py) <= radius_ft]
        if base["location_provenance"] in ("approximate", "address_nad"):
            cands = []           # an estimate (#255 +-0.5 mi, #283 NAD ~400 ft): never an intersection crash; on a
            #                      segment, or out by the usual rules
        gps = base["location_provenance"] in crashes_mod.GPS_SOURCES     # converted (#143) or offset (#218): still GPS
        if gps:
            # #53: GPS far from the intersection the report itself names -> flagged and counted (not moved)
            st = _stated_intersection(c, studies, corridor_keys)
            if st is not None:
                sx, sy = pts[st["id"]]
                off = c.get("offset_ft") or 0.0
                if math.hypot(x - sx, y - sy) > GPS_CHECK_FT + off:
                    base["gps_check"] = "far_from_stated_intersection"
                    base["stated_location_id"] = st["id"]
        if cands:
            d, it, rule = _pick_intersection(cands)
            if gps and _names(c, corridor_keys + grade.intersection_keys(it)) is False:
                # #53 / #39: GPS in the influence area, but the report names neither the corridor nor this cross
                # street (a parking aisle, alley or parallel street)
                out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": round(d, 1),
                            "rule": "not_on_corridor_street"})
                continue
            out.append({**base, "kind": "intersection", "location_id": it["id"], "distance_ft": round(d, 1), "rule": rule,
                        "station_ft": it["station_ft"]})       # where along A->B (the strip diagram, #102)
            continue
        p = line.project_xy(x, y)
        off_rule = "fars_off_corridor" if base["location_provenance"] == "fars" else None   # elsewhere on its roads (#174)
        if p.station_ext < 0 or p.station_ext > line.length_ft:
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": round(p.offset_ft, 1),
                        "rule": off_rule or "outside_study_limits"})
            continue
        d_ft = off_ft(p, x, y)
        if d_ft > buffer_ft:
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": round(d_ft, 1),
                        "rule": off_rule or "outside_buffer"})
            continue
        seg = next((s for s in segs if s["from_station_ft"] <= p.station_ft <= s["to_station_ft"]), None)
        if seg is None:   # station falls in a stub the network dropped (within 50 ft of a terminus intersection)
            seg = min(segs, key=lambda s: min(abs(p.station_ft - s["from_station_ft"]), abs(p.station_ft - s["to_station_ft"])),
                      default=None)
        if seg is None:
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": round(p.offset_ft, 1),
                        "rule": "no_segment"})
            continue
        if gps and _names(c, corridor_keys) is False:   # #53 / #39: in the buffer, but on another street
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": round(p.offset_ft, 1),
                        "rule": "not_on_corridor_street"})
            continue
        out.append({**base, "kind": "segment", "location_id": seg["id"], "distance_ft": round(d_ft, 1),
                    "station_ft": round(p.station_ft, 1), "rule": "corridor_buffer"})
    counts = Counter(a["kind"] for a in out)
    totals = {k: counts.get(k, 0) for k in KINDS}
    totals["total"] = len(crashes)
    assert sum(totals[k] for k in KINDS) == totals["total"], "assignment lost a crash"
    return {"counts": totals, "by_location": dict(Counter(a["location_id"] for a in out if a["location_id"])),
            "excluded_by_rule": dict(Counter(a["rule"] for a in out if a["kind"] == "excluded")),
            "unmatched_by_rule": dict(Counter(a["rule"] for a in out if a["kind"] == "unmatched")),
            "gps_far_from_stated": sum(1 for a in out if a.get("gps_check") and a["kind"] in ("intersection", "segment")),
            "approximate": sum(1 for a in out if a["location_provenance"] == "approximate"
                               and a["kind"] in ("intersection", "segment")),
            "address_nad": sum(1 for a in out if a["location_provenance"] == "address_nad"
                               and a["kind"] in ("intersection", "segment")),
            "radius_ft": radius_ft, "buffer_ft": buffer_ft, "assignments": out}


_MEMO: dict[tuple, tuple[dict, dict]] = {}      # (study inputs) -> (pull, assignment); newest last
_MEMO_MAX = 16


def forget(sid: str) -> None:
    """Drop a study's memoized assignments: called when a new pull is stored (two pulls can share a timestamp)."""
    for k in [k for k in _MEMO if k[1] == sid]:
        _MEMO.pop(k, None)


def for_study(db, sid: str) -> tuple[dict, dict, dict, dict]:
    """(study, network, pull, assignment) — assignment recomputed from the cached pull, so radius/buffer edits apply.
    Memoized on everything it depends on (pull key + time, settings, network), so the profile, map, findings and
    exports don't each reload the pull and re-assign it (#54). Callers must not mutate what they get."""
    study = study_mod.require(db, sid)
    net = network_mod.network(db, sid)
    if not net.get("line"):
        raise HTTPException(409, "Draw the corridor first.")
    head = db.one("SELECT cache_key, pulled_at FROM crash_pull WHERE study_id = ?", (sid,))
    if head is None:
        raise HTTPException(409, "Pull the crashes first.")
    if head["cache_key"] != crashes_mod.cache_key(study, net):
        # the window, corridor or radius changed since this pull: never compute from the old crashes
        raise HTTPException(409, "The study changed since the crashes were pulled. Open Crash profile to pull them again.")
    net_sig = json.dumps({k: net.get(k) for k in ("intersections", "segments", "grade_separations", "corridor_names",
                                                  "corridor_name", "is_freeway", "line")}, sort_keys=True, default=str)
    decs = review_mod.decisions(db, sid)          # the engineer's place/exclude choices (#97), never cached away
    key = (getattr(db, "path", id(db)), sid, head["cache_key"], head["pulled_at"], study["radius_ft"],
           study["buffer_ft"], bool(study.get("include_freeway")), hashlib.sha1(net_sig.encode()).hexdigest(),
           review_mod.signature(decs))
    hit = _MEMO.pop(key, None)
    if hit is None:
        pull = crashes_mod.get_cached(db, sid)
        pull = {**pull, "crashes": review_mod.overlay(pull["crashes"], decs)}
        anet = union_mod.with_alt(net, pull.get("network_alt"))      # the TIGER names the pull used (#229)
        hit = (pull, assign(pull["crashes"], anet, study["radius_ft"], study["buffer_ft"],
                            bool(study.get("include_freeway")), pull.get("carriageways")), anet)
    _MEMO[key] = hit                                  # most recently used last
    while len(_MEMO) > _MEMO_MAX:
        _MEMO.pop(next(iter(_MEMO)))
    return study, hit[2], hit[0], hit[1]


router = APIRouter()


@router.get("/studies/{sid}/assignment")
def get_assignment(sid: str, request: Request) -> dict:
    _, _, _, a = for_study(request.app.state.db, sid)
    return a
