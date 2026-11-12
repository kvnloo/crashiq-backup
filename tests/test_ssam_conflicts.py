"""#484: conflict finding by the FHWA SSAM method, on known-answer scenarios (tests/ssam_scenarios.py).

TTC is found on SSAM's 0.1 s projection grid, so the expected value is the first 0.1 s step at or above the
continuous answer worked out below. PET is measured between 0.1 s timesteps, the same way.
All scenarios go through our own .trj writer and reader first.
"""

from __future__ import annotations

import pytest
from ssam_scenarios import SCENARIOS

from crashiq.ssam import find_conflicts, read_trj, write_trj
from crashiq.ssam.conflicts import classify


def run(tmp_path, name):
    p = tmp_path / f"{name}.trj"
    write_trj(p, SCENARIOS[name]())
    return find_conflicts(read_trj(p))


def test_rear_end_braking_leader(tmp_path):
    # Gap g (follower front to leader rear) 22.25 m; both at 15 m/s; TTC = g / closing speed with each vehicle
    # projected at its current speed.
    # t in [1,3], u=t-1: leader brakes, g = 22.25 - 2.5u^2, closing 5u -> TTC 1.225 at t=3.
    # t in [3,5], s=t-3, w=2-s: both brake, closing 5w, g = 2.5(w^2 + 0.9) -> TTC = w/2 + 0.45/w,
    #   minimum sqrt(0.9) = 0.949 s at t = 4.05; on the 0.1 s grid: 1.0.
    # After t=5 both hold 5 m/s with g = 2.25 m: PET = 2.25 / 5 = 0.45 s; between 0.1 s steps: 0.5.
    (c,) = run(tmp_path, "rear_end")
    assert (c["FirstVID"], c["SecondVID"], c["ConflictType"]) == (1, 2, "rear-end")
    assert c["TTC"] == pytest.approx(1.0)
    assert c["PET"] == pytest.approx(0.5)
    assert abs(c["ConflictAngle"]) < 1.0
    assert c["MaxD"] == pytest.approx(-5.0) and c["DR"] == pytest.approx(-5.0)
    assert c["MaxS"] == pytest.approx(15.0, abs=0.6)  # event starts at t=2.9 with the follower at 15 m/s


def test_right_angle_crossing(tmp_path):
    # Crossing box x,y in [-0.9, 0.9]. A (east, 10 m/s) is in it for t in [3.91, 4.54].
    # B (north) would arrive at 3.91 too; up to t=3 TTC = 3.91 - t (0.91 at t=3 -> grid 1.0).
    # B brakes from t=3: at t=3.1 v=9.2, 8.14 m to go -> enters at +0.885 s, A still inside until +1.44 -> 0.9;
    #   t=3.4: v=6.8, 5.74 m -> 0.844 (continuous minimum); every step 3.1..3.6 rounds up to 0.9; from 3.7
    #   B's projected entry comes after A has left -> no TTC.
    # PET: positions are recorded only at the TTC steps (report Step 4.2), t <= 3.6, when A's front is still west
    #   of x=-4. B never enters any of them, so no PET is observed. (FHWA's SSAM_MT lists no conflict here.)
    (c,) = run(tmp_path, "crossing")
    assert (c["FirstVID"], c["SecondVID"], c["ConflictType"]) == (1, 2, "crossing")
    assert c["TTC"] == pytest.approx(0.9)
    assert c["tMinTTC"] == pytest.approx(3.1)
    assert c["PET"] is None
    assert c["ConflictAngle"] == pytest.approx(90.0, abs=0.5)  # B comes from A's right
    assert c["MaxD"] == pytest.approx(-8.0) and c["DR"] == pytest.approx(-8.0)
    assert c["DeltaS"] > 0 and c["MaxDeltaV"] > 0


def test_pet_uses_positions_at_ttc_steps(tmp_path):
    # Leader rear 12.5 - 3t ahead up to t=3 (12 vs 15 m/s): TTC = g/3, under 1.5 from t=2.7, 1.2 at t=3.
    # The follower brakes at -4 from t=3 and its TTC ends after t=3.2. PET from a position the leader held at a
    #   TTC step: its rear at t=2.7 (x=44.9) is reached by the follower's front at 2.99 -> 0.29, between steps 0.3,
    #   at the leader's centre then (47.15). Positions after the last TTC step would give 0.2 (the old rule).
    # FHWA's SSAM_MT gives exactly this: PET 0.3, xMinPET 47.15 (tests/fixtures/ssam/fhwa/follow_brake.csv).
    (c,) = run(tmp_path, "follow_brake")
    assert (c["FirstVID"], c["SecondVID"], c["ConflictType"]) == (1, 2, "rear-end")
    assert c["TTC"] == pytest.approx(1.2) and c["tMinTTC"] == pytest.approx(3.0)
    assert c["PET"] == pytest.approx(0.3)
    assert c["xMinPET"] == pytest.approx(47.15, abs=0.01)


def test_lane_change_cut_in(tmp_path):
    # Gap g (A front to B rear) = 12.5 - 3t up to t=3 (B at 12 m/s, A at 15), so 3.5 m when B lands in lane 1.
    # t in [2.7, 3]: B already overlaps A's lane, TTC = g/3 (1.2 at t=3 on the grid).
    # t in [3,5], s=t-3, w=3-2s: B speeds up, closing w, g = (w^2 + 5)/4 -> TTC = w/4 + 1.25/w,
    #   minimum sqrt(5)/2 = 1.118 s; on the grid 1.2.
    # Closest at t=4.5: g = 1.25 m, both at 15 m/s -> PET 0.083 s; between steps 0.1 s.
    # The angle is ~0 (rear-end by angle alone) but B's lane id goes 2 -> 1 within link 1: lane change.
    (c,) = run(tmp_path, "cut_in")
    assert (c["FirstVID"], c["SecondVID"], c["ConflictType"]) == (2, 1, "lane-change")
    assert c["TTC"] == pytest.approx(1.2)
    assert c["PET"] == pytest.approx(0.1)
    assert abs(c["ConflictAngle"]) < 30


def test_near_pass_is_not_a_conflict(tmp_path):
    # B reaches the crossing 2.5 s after A clears it (PET 2.5 < 5) but at their speeds the two never share space
    # within 1.5 s, so there is no TTC and no conflict. C passes A in the next lane with 1.8 m between them.
    assert run(tmp_path, "near_pass") == []


def test_thresholds(tmp_path):
    p = tmp_path / "x.trj"
    write_trj(p, SCENARIOS["crossing"]())
    assert find_conflicts(read_trj(p), max_ttc=0.8) == []  # crossing TTC is 0.9


@pytest.mark.parametrize("angle,start,end,want", [
    (10, None, None, "rear-end"), (-29.9, None, None, "rear-end"), (50, None, None, "lane-change"),
    (-86, None, None, "crossing"), (179, None, None, "crossing"),
    (60, ((1, 1), (1, 1)), ((1, 1), (1, 1)), "rear-end"),        # same lane start and end
    (5, ((1, 2), (1, 1)), ((1, 1), (1, 1)), "lane-change"),       # one changed lane within the link
    (90, ((1, 1), (1, 1)), ((2, 1), (3, 1)), "lane-change"),      # same lane at start, links change: no crossing
    (10, ((1, 1), (1, 1)), ((2, 1), (3, 1)), "rear-end"),
    (90, ((1, 1), (2, 1)), ((1, 1), (2, 1)), "crossing"),         # never in the same lane: angle decides
])
def test_classify(angle, start, end, want):
    assert classify(angle, start, end) == want


def test_overlap_is_sides_crossing(tmp_path):
    # The report (Step 3, figure 13) tests every side of one rectangle for intersection with every side of the
    # other, so a car wholly inside a bus outline (a tracking error) is no overlap. Car (4 x 1.6) sits inside a
    # stopped bus (12 x 2.6, x 0..12) and drives off at 5 m/s from t=3: its front crosses the bus front (x=12)
    # at t=3.8, the first step with a crossing side. FHWA's SSAM_MT gives tMinTTC 3.8, TTC 0, PET 0 for this.
    from ssam_scenarios import build

    from crashiq.ssam import Veh
    bus = lambda t: Veh(1, None, None, 12.0, 0.0, 0.0, 0.0, 12.0, 2.6, 0.0, 0.0)
    car = lambda t: Veh(2, None, None, 8.0 + 5 * max(t - 3, 0), 0.0, 4.0 + 5 * max(t - 3, 0), 0.0, 4.0, 1.6,
                        5.0 if t >= 3 else 0.0, 0.0)
    p = tmp_path / "contain.trj"
    write_trj(p, build([bus, car], 20.0))
    (c,) = find_conflicts(read_trj(p))
    assert (c["tMinTTC"], c["TTC"], c["PET"]) == pytest.approx((3.8, 0.0, 0.0))


def test_busy_scene_unchanged():
    # Speed-ups must not change any result: the full conflict list of a dense synthetic scene (ssam_scenarios.busy)
    # is frozen in tests/fixtures/ssam/busy_conflicts.json, written by the engine before the speed work.
    # Floats compared to 9 digits: Linux CI and Windows differ in the last bit of atan2 (FirstHeading).
    import json

    from conftest import FIXTURES
    from ssam_scenarios import busy

    def r(rows):
        return [{k: round(v, 9) if isinstance(v, float) else v for k, v in c.items()} for c in rows]
    assert r(find_conflicts(busy())) == r(json.loads((FIXTURES / "ssam" / "busy_conflicts.json").read_text()))
