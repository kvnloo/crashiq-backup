"""#70: a no-GPS report at a cross street just past the study end, with a reported distance back toward the stretch,
is placed from that corner and assigned by the normal rules; only a point still off the stretch keeps
`cross_street_not_on_corridor`. Synthetic map only."""

from __future__ import annotations

import pytest

from crashiq import assign, placement

LAT0, LON = 37.6000, -122.0500
FT_LAT = 1 / 364000                                 # degrees of latitude per foot
END = LAT0 + 3640 * FT_LAT                          # study end B, 3,640 ft north of A
WHIPPLE = END + 200 * FT_LAT                        # Whipple Rd meets the corridor 200 ft past B


def raw() -> dict:
    lats = [LAT0, LAT0 + 1800 * FT_LAT, END, WHIPPLE, WHIPPLE + 600 * FT_LAT]
    nodes = [{"type": "node", "id": i + 1, "lat": la, "lon": LON} for i, la in enumerate(lats)]
    cross = []
    for j, (name, at) in enumerate((("Alvarado Boulevard", 1), ("Decoto Road", 3), ("Whipple Road", 4))):
        w, e = 100 + 2 * j, 101 + 2 * j
        nodes += [{"type": "node", "id": w, "lat": lats[at - 1], "lon": LON - 0.002},
                  {"type": "node", "id": e, "lat": lats[at - 1], "lon": LON + 0.002}]
        cross.append({"type": "way", "id": 20 + j, "nodes": [w, at, e], "tags": {"highway": "secondary", "name": name}})
    return {"elements": nodes + [{"type": "way", "id": 10, "nodes": [1, 2, 3, 4, 5],
                                  "tags": {"highway": "primary", "name": "Union City Boulevard"}}] + cross}


NET = {"line": [(LAT0, LON), (END, LON)], "radius_ft": 250, "buffer_ft": 100, "is_freeway": False,
       "corridor_names": ["Union City Boulevard"],
       "intersections": [{"id": "I1", "name": "Alvarado Boulevard", "is_study": True, "lat": LAT0, "lon": LON, "station_ft": 0},
                         {"id": "I2", "name": "Decoto Road", "is_study": True, "lat": END, "lon": LON, "station_ft": 3640}],
       "segments": [{"id": "S1", "from_station_ft": 0, "to_station_ft": 3640, "length_mi": 3640 / 5280}]}


def outside(cid, ft, direction, cross="WHIPPLE RD"):
    return {"crash_id": cid, "primary_road": "UNION CITY BLVD", "secondary_road": cross, "offset_ft": ft,
            "offset_dir": direction, "lat": None, "lon": None, "location_source": "unmatched", "is_freeway": False,
            "exclude_rule": "cross_street_not_on_corridor"}


def run(*cs):
    return list(cs), placement.outside_corners(NET, list(cs), raw())


def test_an_outside_corner_200_ft_past_the_end_with_300_ft_inward_is_kept_and_assigned_normally():
    (c,), counts = run(outside("in", 300, "S"))
    assert c.get("exclude_rule") is None and c["location_source"] == "exact"
    assert c["lat"] == pytest.approx(WHIPPLE - 300 * FT_LAT, abs=2 * FT_LAT)       # 100 ft inside B
    assert c["outside_corner"] == {"cross_street": "WHIPPLE RD", "offset_ft": 300, "offset_dir": "S"}
    a = assign.assign([c], NET, 250, 100)["assignments"][0]
    assert a["kind"] == "intersection" and a["location_id"] == "I2"                 # within 250 ft of B
    assert counts == {"tried": 1, "kept": 1}


def test_far_enough_inward_it_is_a_segment_crash():
    (c,), _ = run(outside("seg", 1200, "S"))
    assert assign.assign([c], NET, 250, 100)["assignments"][0]["kind"] == "segment"


def test_an_outward_offset_stays_excluded():
    (c,), counts = run(outside("out", 300, "N"))
    assert c["exclude_rule"] == "cross_street_not_on_corridor" and c["lat"] is None and "outside_corner" not in c
    assert counts == {"tried": 1, "kept": 0}


def test_a_short_inward_offset_past_the_end_but_within_250_ft_of_it_counts_at_the_end_intersection():
    (c,), _ = run(outside("short", 100, "S"))                          # 100 ft past B: B's influence area (C5)
    a = assign.assign([c], NET, 250, 100)["assignments"][0]
    assert c.get("exclude_rule") is None and (a["kind"], a["location_id"]) == ("intersection", "I2")


def test_with_no_map_corner_it_stays_excluded():
    (c,), _ = run(outside("nomap", 300, "S", cross="NOWHERE RD"))
    assert c["exclude_rule"] == "cross_street_not_on_corridor"


# -- the pull: candidates are decided before the party and injury lookups -------------------------------------------
from test_agency_bugs import NET_X, STUDY, FakeCkan, _fixture, _row  # noqa: E402
from crashiq import crashes  # noqa: E402
from crashiq.crashes import Ckan  # noqa: E402


def _pull(dist, direction, raw_net, monkeypatch=None, keep=False):
    d = _fixture(no_gps=True)
    _, r = _row(d, 9200001)                     # CRENSHAW BL & W 144TH ST, no GPS
    r.update(SecondaryRoad="W 190TH ST", SecondaryDistance=dist, SecondaryDirection=direction, SecondaryUnitOfMeasure="F")
    seen = []
    if monkeypatch is not None:
        def fake(net, cands, raw):
            seen.extend(c["crash_id"] for c in cands)
            for c in cands:
                if keep:
                    del c["exclude_rule"]
                    c.update(lat=33.90, lon=-118.3266, location_source="exact", outside_corner={"cross_street": "W 190TH ST"})
            return {"tried": len(cands), "kept": len(cands) if keep else 0}
        monkeypatch.setattr(placement, "outside_corners", fake)
    out = crashes.pull(STUDY, NET_X, Ckan(FakeCkan(d)), raw=raw_net)
    return out, next(c for c in out["crashes"] if c["crash_id"] == "9200001"), seen


def test_a_kept_candidate_is_looked_up_like_any_counted_crash(monkeypatch):
    out, c, seen = _pull("300", "S", {"elements": []}, monkeypatch, keep=True)
    assert "9200001" in seen and c.get("exclude_rule") is None and c["severity"] is not None
    assert c.get("details") != "not_looked_up" and out["cleaning"]["outside_corner"]["kept"] >= 1


def test_a_candidate_not_kept_is_excluded_and_never_looked_up(monkeypatch):
    out, c, seen = _pull("300", "S", {"elements": []}, monkeypatch, keep=False)
    assert "9200001" in seen and c["exclude_rule"] == "cross_street_not_on_corridor"
    assert c["details"] == "not_looked_up" and "outside_corner" not in c


def test_no_distance_is_no_candidate(monkeypatch):
    _, c, seen = _pull("", "", {"elements": []}, monkeypatch)
    assert "9200001" not in seen and c["exclude_rule"] == "cross_street_not_on_corridor"


def test_without_the_locator_map_nothing_is_tried():
    _, c, _ = _pull("300", "S", None)
    assert c["exclude_rule"] == "cross_street_not_on_corridor" and "outside_corner" not in c


def test_the_profile_says_how_many_crashes_came_back_from_an_outside_corner():
    from crashiq import profile
    from test_profile import golden
    study, n, pull, asg = golden()
    s1 = sorted(a["crash_id"] for a in asg["assignments"] if a["location_id"] == "S1")[:2]
    pull = {**pull, "crashes": [{**c, "outside_corner": {"cross_street": "X ST", "offset_ft": 300, "offset_dir": "S"}}
                                if c["crash_id"] in s1 else c for c in pull["crashes"]]}
    cav = {c["key"]: c for c in profile.build(study, n, pull, asg)["caveats"]}["outside_corner"]
    assert cav["count"] == 2 and cav["text"].startswith("2 crash reports name a cross street just outside the study stretch")
