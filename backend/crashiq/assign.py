"""C5 assign: every crash → a study intersection, a segment, excluded, or unmatched. Deterministic; counts add up.

Rules (docs/03-requirements.md R2.3-4):
1. No coordinates yet → `unmatched` (counted, never dropped).
2. Within the influence radius (study setting, default 250 ft) of a study intersection → that intersection.
   Inside more than one radius → the nearest one, which splits at mid-block when intersections are
   closer than twice the radius. (The formal HSIP < 500 ft rule is #3 Q6; it would replace `_pick_intersection` only.)
3. Otherwise within the corridor buffer of the drawn line and between A and B → the segment it projects onto.
4. Otherwise → `excluded`, with the reason.
Distances are feet in the corridor's projected CRS.
"""

from __future__ import annotations

import math
from collections import Counter

from fastapi import APIRouter, HTTPException, Request

from . import crashes as crashes_mod
from . import network as network_mod
from . import study as study_mod
from .geo import Polyline

KINDS = ("intersection", "segment", "excluded", "unmatched")


def _pick_intersection(cands: list[tuple[float, dict]]) -> tuple[float, dict, str]:
    d, it = min(cands, key=lambda t: (t[0], t[1]["station_ft"]))
    return d, it, "influence_radius" if len(cands) == 1 else "nearest_of_overlapping_radii"


def assign(crashes: list[dict], net: dict, radius_ft: float, buffer_ft: float, include_freeway: bool = False) -> dict:
    line = Polyline([tuple(p) for p in net["line"]])
    studies = [i for i in net["intersections"] if i["is_study"]]
    pts = {i["id"]: line.proj.to_xy(i["lat"], i["lon"]) for i in studies}
    segs = net["segments"]
    out = []
    for c in crashes:
        base = {"crash_id": c["crash_id"], "location_provenance": c.get("location_source", "gps")}
        if c.get("is_freeway") and not include_freeway:     # CHP's IsFreeway: mainline/ramp crashes under or beside an arterial study
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": None, "rule": "freeway"})
            continue
        if c.get("lat") is None or c.get("lon") is None:
            out.append({**base, "kind": "unmatched", "location_id": None, "distance_ft": None, "rule": "no_coordinates"})
            continue
        x, y = line.proj.to_xy(c["lat"], c["lon"])
        cands = [(math.hypot(x - px, y - py), it) for it in studies for px, py in [pts[it["id"]]]
                 if math.hypot(x - px, y - py) <= radius_ft]
        if cands:
            d, it, rule = _pick_intersection(cands)
            out.append({**base, "kind": "intersection", "location_id": it["id"], "distance_ft": round(d, 1), "rule": rule})
            continue
        p = line.project_xy(x, y)
        if p.station_ext < 0 or p.station_ext > line.length_ft:
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": round(p.offset_ft, 1),
                        "rule": "outside_study_limits"})
            continue
        if p.offset_ft > buffer_ft:
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": round(p.offset_ft, 1),
                        "rule": "outside_buffer"})
            continue
        seg = next((s for s in segs if s["from_station_ft"] <= p.station_ft <= s["to_station_ft"]), None)
        if seg is None:   # station falls in a stub the network dropped (within 50 ft of a terminus intersection)
            seg = min(segs, key=lambda s: min(abs(p.station_ft - s["from_station_ft"]), abs(p.station_ft - s["to_station_ft"])),
                      default=None)
        if seg is None:
            out.append({**base, "kind": "excluded", "location_id": None, "distance_ft": round(p.offset_ft, 1),
                        "rule": "no_segment"})
            continue
        out.append({**base, "kind": "segment", "location_id": seg["id"], "distance_ft": round(p.offset_ft, 1),
                    "station_ft": round(p.station_ft, 1), "rule": "corridor_buffer"})
    counts = Counter(a["kind"] for a in out)
    totals = {k: counts.get(k, 0) for k in KINDS}
    totals["total"] = len(crashes)
    assert sum(totals[k] for k in KINDS) == totals["total"], "assignment lost a crash"
    return {"counts": totals, "by_location": dict(Counter(a["location_id"] for a in out if a["location_id"])),
            "excluded_by_rule": dict(Counter(a["rule"] for a in out if a["kind"] == "excluded")),
            "radius_ft": radius_ft, "buffer_ft": buffer_ft, "assignments": out}


def for_study(db, sid: str) -> tuple[dict, dict, dict, dict]:
    """(study, network, pull, assignment) — assignment recomputed from the cached pull, so radius/buffer edits apply."""
    study = study_mod.require(db, sid)
    net = network_mod.network(db, sid)
    if not net.get("line"):
        raise HTTPException(409, "Draw the corridor first.")
    pull = crashes_mod.get_cached(db, sid)
    if pull is None:
        raise HTTPException(409, "Pull the crashes first.")
    if pull.get("cache_key") != crashes_mod.cache_key(study, net):
        # the window, corridor or radius changed since this pull: never compute from the old crashes
        raise HTTPException(409, "The study changed since the crashes were pulled. Open Crash profile to pull them again.")
    return study, net, pull, assign(pull["crashes"], net, study["radius_ft"], study["buffer_ft"],
                                    bool(study.get("include_freeway")))


router = APIRouter()


@router.get("/studies/{sid}/assignment")
def get_assignment(sid: str, request: Request) -> dict:
    _, _, _, a = for_study(request.app.state.db, sid)
    return a
