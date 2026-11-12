"""Known-answer trajectory scenarios for the SSAM conflict tests (#484), built in code, metric units, 0.1 s steps.

Every vehicle is 4.5 m long and 1.8 m wide. Motion is piecewise constant acceleration, computed exactly.
The expected TTC/PET for each scenario is worked out by hand in tests/test_ssam_conflicts.py.
"""

from __future__ import annotations

import math

from crashiq.ssam import Trj, Veh

L, W, DT = 4.5, 1.8, 0.1


def motion(t: float, x0: float, v0: float, phases: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    """Position, speed, accel at t. phases = [(t_start, t_end, accel)], constant speed outside them."""
    x, v, last = x0, v0, 0.0
    a_now = 0.0
    for t0, t1, a in phases:
        if t <= t0:
            break
        x += v * (t0 - last)  # cruise up to the phase
        d = min(t, t1) - t0
        x += v * d + 0.5 * a * d * d
        v += a * d
        last = min(t, t1)
        a_now = a if t < t1 else 0.0
    x += v * (t - last)
    return x, v, a_now


def straight(vid, t, start, direction, v0, phases, lane=None, link=None, lateral=None):
    """A vehicle along a straight line. start = front bumper at t=0; lateral(t) -> (offset, rate) across the line."""
    s, v, a = motion(t, 0.0, v0, phases)
    hx, hy = direction
    off, rate = lateral(t) if lateral else (0.0, 0.0)
    nx, ny = -hy, hx  # left of travel
    fx, fy = start[0] + hx * s + nx * off, start[1] + hy * s + ny * off
    vx, vy = hx * v + nx * rate, hy * v + ny * rate
    sp = (vx * vx + vy * vy) ** 0.5
    ux, uy = (vx / sp, vy / sp) if sp > 0 else (hx, hy)
    return Veh(vid, link, lane(t) if callable(lane) else lane, fx, fy, fx - ux * L, fy - uy * L, L, W, sp, a)


def build(vehicles, t_end: float) -> Trj:
    steps = []
    for k in range(int(round(t_end / DT)) + 1):
        t = round(k * DT, 1)
        steps.append((t, [f(t) for f in vehicles]))
    xs = [c for _, vs in steps for v in vs for c in (v.fx, v.rx)]
    ys = [c for _, vs in steps for v in vs for c in (v.fy, v.ry)]
    return Trj(version=1.04, endian="L", units=1, scale=1.0,
               bounds=(int(min(xs)) - 1, int(min(ys)) - 1, int(max(xs)) + 1, int(max(ys)) + 1), z=False, steps=steps)


def rear_end() -> Trj:
    # Leader (1) at 15 m/s brakes at -5 m/s2 from t=1 to t=3 (down to 5 m/s). Follower (2), 22.25 m behind
    # (front to rear), reacts at t=3 and brakes at -5 until t=5. Same lane, link 1 lane 1.
    lead = lambda t: straight(1, t, (22.25 + L, 0.0), (1, 0), 15.0, [(1.0, 3.0, -5.0)], lane=1, link=1)
    foll = lambda t: straight(2, t, (0.0, 0.0), (1, 0), 15.0, [(3.0, 5.0, -5.0)], lane=1, link=1)
    # 20 s, not 10: FHWA's SSAM_MT drops an event still open when the file ends (it keeps this one open to ~14.5 s).
    return build([lead, foll], 20.0)


def follow_brake() -> Trj:
    # Leader (1) at a steady 12 m/s, its rear 12.5 m ahead of the follower (2) at 15 m/s. The follower brakes at
    # -4 m/s2 from t=3 to t=4 (down to 11 m/s) and drops back. No lanes. Its PET comes from a position the leader
    # held at a TTC step (Step 4.2 of the report), not from a later one.
    lead = lambda t: straight(1, t, (12.5 + L, 0.0), (1, 0), 12.0, [])
    foll = lambda t: straight(2, t, (0.0, 0.0), (1, 0), 15.0, [(3.0, 4.0, -4.0)])
    return build([lead, foll], 15.0)


def crossing() -> Trj:
    # A (1) eastbound on y=0 at 10 m/s, front at x=-40 at t=0. B (2) northbound on x=0 at 10 m/s, front at y=-40:
    # both would reach the crossing together; B brakes at -8 m/s2 from t=3 to t=4 (down to 2 m/s). No lanes.
    a = lambda t: straight(1, t, (-40.0, 0.0), (1, 0), 10.0, [])
    b = lambda t: straight(2, t, (0.0, -40.0), (0, 1), 10.0, [(3.0, 4.0, -8.0)])
    return build([a, b], 10.0)


def cut_in() -> Trj:
    # A (1) in lane 1 (y=0) at 15 m/s. B (2) starts in lane 2 (y=3.6) at 12 m/s, its rear 3.5 + 9 m ahead of A's
    # front, drifts into lane 1 between t=1 and t=3 (1.8 m/s sideways), then speeds up at +2 m/s2 to 16 m/s
    # (t=3..5). Its lane id flips 2 -> 1 when the move ends (t=3). Link 1 throughout.
    def lat(t):
        if t <= 1.0:
            return 3.6, 0.0
        if t < 3.0:
            return 3.6 - 1.8 * (t - 1.0), -1.8
        return 0.0, 0.0

    a = lambda t: straight(1, t, (0.0, 0.0), (1, 0), 15.0, [], lane=1, link=1)
    b = lambda t: straight(2, t, (12.5 + L, 0.0), (1, 0), 12.0, [(3.0, 5.0, 2.0)],
                           lane=lambda t: 2 if t < 3.0 else 1, link=1, lateral=lat)
    return build([a, b], 10.0)


def near_pass() -> Trj:
    # A (1) eastbound at 10 m/s as in crossing(). B (2) northbound at a steady 10 m/s, reaching A's path 2.5 s after
    # A has cleared it. C (3) overtakes A in the next lane (3.6 m to the left) at 14 m/s. No lanes.
    a = lambda t: straight(1, t, (-40.0, 0.0), (1, 0), 10.0, [])
    b = lambda t: straight(2, t, (0.0, -0.9 - 70.4), (0, 1), 10.0, [])
    c = lambda t: straight(3, t, (-60.0, 3.6), (1, 0), 14.0, [])
    return build([a, b, c], 10.0)


SCENARIOS = {"rear_end": rear_end, "follow_brake": follow_brake, "crossing": crossing, "cut_in": cut_in, "near_pass": near_pass}


def busy(seed: int = 484) -> Trj:
    # 60 s of 80 vehicles on straight paths through a 200 m square in four directions, random speeds, some
    # braking, small lateral jitter: a dense scene for checking that speed-ups leave the conflict list unchanged.
    import random

    rnd = random.Random(seed)
    dirs = [((1, 0), (-100.0, 0.0)), ((-1, 0), (100.0, 3.6)), ((0, 1), (1.8, -100.0)), ((0, -1), (-1.8, 100.0))]
    vehicles = []
    for vid in range(1, 81):
        (hx, hy), (sx, sy) = rnd.choice(dirs)
        t0, v0 = rnd.uniform(-20, 50), rnd.uniform(6, 16)
        start = (sx - hx * v0 * t0 + rnd.uniform(-0.3, 0.3) * hy, sy - hy * v0 * t0 + rnd.uniform(-0.3, 0.3) * hx)
        tb = rnd.uniform(0, 60)
        phases = [(tb, tb + rnd.uniform(0.5, 2.0), rnd.uniform(-6, -1))] if rnd.random() < 0.5 else []
        amp = rnd.uniform(0, 0.15)
        lat = (lambda a: lambda t: (a * math.sin(3 * t), 3 * a * math.cos(3 * t)))(amp)
        vehicles.append((lambda vid, s, d, v, ph, lt: lambda t: straight(vid, t, s, d, v, ph, lateral=lt))(
            vid, start, (hx, hy), v0, phases, lat))
    steps = build(vehicles, 60.0).steps
    keep = [(t, [v for v in vs if abs(v.fx) < 100 and abs(v.fy) < 100]) for t, vs in steps]
    return Trj(version=1.04, endian="L", units=1, scale=1.0, bounds=(-106, -106, 106, 106), z=False, steps=keep)
