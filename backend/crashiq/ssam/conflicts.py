"""Conflict finding by the method published in FHWA-HRT-08-051 Ch. 2 (independent implementation, not FHWA's SSAM).

Per timestep:
1. Each vehicle is projected along its own next 10 s of trajectory (front-bumper path), a distance
   speed * tau for projection times tau = 0, 0.1, ... MaxTTC. The vehicle is the rectangle behind that point,
   facing along the path.
2. A 50 ft / 15.25 m zone grid keeps comparisons to vehicles whose swept area shares a zone.
3. TTC for a pair is the first tau whose two projected rectangles overlap (0 = touching now: a crash).
4. Pairs with a TTC open (or continue) a conflict event. Each step with a TTC records both vehicles' actual
   rectangles (report Step 4.2); PET is the time since the other vehicle last occupied any part of a vehicle's
   current rectangle, against those recorded positions only.
5. An event ends when the pair is off a collision course and no later encroachment could lower its PET (the time
   since its last TTC step reaches the minimum PET, or MaxPET), or a vehicle leaves; its measures and type are
   computed then. A pair that comes back on a collision course after that is a new event.

Choices the report leaves open, made here:
- Projected positions past the end of a vehicle's recorded path continue straight along its last heading.
- An event with no PET observed is still a conflict, with PET None. (FHWA's SSAM_MT drops it.)
- Events still open when the file ends are listed. (FHWA's SSAM_MT drops them.)
- PostCrashV/DeltaV treat the two vehicles as equal mass (the report gives no masses).
- Positions (CSP/CEP, heading, xMinPET) use the vehicle centre, midway between the bumpers.
- Z (format 3.0) is read but not used to separate levels yet.
"""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from collections import defaultdict
from itertools import combinations

from .trj import Trj, Veh

ZONE = {0: 50.0, 1: 15.25}  # zone side, ft / m
LOOKAHEAD = 10.0  # s of future trajectory used as the path
STEP = 0.1  # TTC refinement step, s
EPS = 1e-6


class _Track:
    """One vehicle's records in time order, with cumulative distance along its front-bumper path."""

    def __init__(self):
        self.t: list[float] = []
        self.recs: list[Veh] = []

    def finish(self):
        self.cum = [0.0]
        for a, b in zip(self.recs, self.recs[1:]):
            self.cum.append(self.cum[-1] + math.hypot(b.fx - a.fx, b.fy - a.fy))
        self.end = [bisect_right(self.t, t + LOOKAHEAD + EPS) - 1 for t in self.t]


def _facing(r: Veh) -> tuple[float, float]:
    dx, dy = r.fx - r.rx, r.fy - r.ry
    d = math.hypot(dx, dy)
    return (dx / d, dy / d) if d > EPS else (1.0, 0.0)


def _project(tr: _Track, i: int, tau: float) -> tuple[float, float, float, float]:
    """Front point and unit heading after travelling speed * tau along the vehicle's future path."""
    r = tr.recs[i]
    dist = r.speed * tau
    if dist <= EPS:
        return (r.fx, r.fy, *_facing(r))
    target, end = tr.cum[i] + dist, tr.end[i]
    j = bisect_left(tr.cum, target, i + 1, end + 1)
    if j <= end:  # cum[j-1] < target <= cum[j], so the segment has length
        a, b = tr.recs[j - 1], tr.recs[j]
        seg = tr.cum[j] - tr.cum[j - 1]
        f = (target - tr.cum[j - 1]) / seg
        return (a.fx + (b.fx - a.fx) * f, a.fy + (b.fy - a.fy) * f, (b.fx - a.fx) / seg, (b.fy - a.fy) / seg)
    last = tr.recs[end]
    hx, hy = _facing(last)
    over = target - tr.cum[end]
    return (last.fx + hx * over, last.fy + hy * over, hx, hy)


class _Rect(tuple):
    """Four corners, plus their bounding box (min x, min y, max x, max y) for a quick reject."""

    def __new__(cls, corners):
        r = super().__new__(cls, corners)
        xs, ys = [c[0] for c in corners], [c[1] for c in corners]
        r.box = (min(xs), min(ys), max(xs), max(ys))
        return r


def _rect(fx, fy, hx, hy, length, width):
    nx, ny = -hy * width / 2, hx * width / 2
    bx, by = fx - hx * length, fy - hy * length
    return _Rect(((fx + nx, fy + ny), (fx - nx, fy - ny), (bx - nx, by - ny), (bx + nx, by + ny)))


def _orient(p, q, r) -> int:
    v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return 0 if abs(v) <= EPS else (1 if v > 0 else -1)


def _on(p, q, r) -> bool:
    """r, collinear with pq, lies within pq's box."""
    return (min(p[0], q[0]) - EPS <= r[0] <= max(p[0], q[0]) + EPS
            and min(p[1], q[1]) - EPS <= r[1] <= max(p[1], q[1]) + EPS)


def _side_cross(a, b, c, d) -> bool:
    """Segments ab and cd intersect (touching counts)."""
    o1, o2, o3, o4 = _orient(a, b, c), _orient(a, b, d), _orient(c, d, a), _orient(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return ((o1 == 0 and _on(a, b, c)) or (o2 == 0 and _on(a, b, d)) or (o3 == 0 and _on(c, d, a))
            or (o4 == 0 and _on(c, d, b)))


def _overlap(p: _Rect, q: _Rect) -> bool:
    """Report Step 3 / figure 13: some side of one rectangle intersects some side of the other (touching counts).
    A rectangle wholly inside the other is no overlap, as in FHWA's SSAM_MT."""
    (px0, py0, px1, py1), (qx0, qy0, qx1, qy1) = p.box, q.box
    if px1 < qx0 - EPS or qx1 < px0 - EPS or py1 < qy0 - EPS or qy1 < py0 - EPS:
        return False
    return any(_side_cross(p[i], p[(i + 1) % 4], q[j], q[(j + 1) % 4]) for i in range(4) for j in range(4))


def _centre(r: Veh) -> tuple[float, float]:
    return ((r.fx + r.rx) / 2, (r.fy + r.ry) / 2)


def _angle_deg(x, y) -> float:
    return math.degrees(math.atan2(y, x)) % 360.0


def classify(angle: float, start=None, end=None) -> str:
    """Conflict type. start/end = ((link, lane) of first, (link, lane) of second) at event start/end, or None."""
    by_angle = "rear-end" if abs(angle) < 30 else "crossing" if abs(angle) > 85 else "lane-change"
    if start is None or end is None or None in (*start[0], *start[1], *end[0], *end[1]):
        return by_angle
    (f0, s0), (f1, s1) = start, end
    same_start, same_end = f0 == s0, f1 == s1
    if not (same_start or same_end):
        return by_angle
    if f0[0] == f1[0] and s0[0] == s1[0]:  # neither changed link
        if same_start and same_end:
            return "rear-end"
        if f0[1] != f1[1] or s0[1] != s1[1]:
            return "lane-change"
        return by_angle
    if same_start:  # started in the same lane, then changed links: rear-end or lane change only
        return "rear-end" if abs(angle) < 30 else "lane-change"
    return by_angle


class _Event:
    def __init__(self, a: int, b: int):
        self.a, self.b = a, b
        self.ttc = math.inf
        self.min_at = None  # (t, rec a, rec b) at the minimum TTC
        self.order = None  # (first, second) from the TTC geometry, used when no PET is seen
        self.ttc_steps: list[tuple[float, Veh, Veh]] = []  # (t, rec a, rec b) while TTC is under the threshold
        self.hist: list[tuple] = []  # (t, rect a, rect b, rec a, rec b): actual positions, for PET
        self.pet = None  # (pet, first vid, centre of first vehicle at the encroached position)
        self.last_pet = None  # (t, rec a, rec b) of the last step a PET was seen
        self.start = None  # (rec a, rec b) at the first step


def _pet(ev: _Event, t: float, ra, rb, recs, max_pet: float) -> None:
    for cur, theirs, other in ((rb, 1, ev.a), (ra, 2, ev.b)):
        for h in reversed(ev.hist):
            if t - h[0] > max_pet + EPS:
                break
            if _overlap(cur, h[theirs]):
                pet = round(t - h[0], 3)
                if ev.pet is None or pet < ev.pet[0]:
                    ev.pet = (pet, other, _centre(h[theirs + 2]))
                ev.last_pet = (t, *recs)
                break


def _finish(ev: _Event, units: int) -> dict:
    first = ev.pet[1] if ev.pet else ev.order[0]
    swap = first != ev.a
    pick = (lambda ra, rb: (rb, ra)) if swap else (lambda ra, rb: (ra, rb))
    tmin, ra_min, rb_min = ev.min_at
    f_min, s_min = pick(ra_min, rb_min)
    f0, s0 = pick(*ev.start)
    last_ttc = ev.ttc_steps[-1]
    cep = ev.last_pet if ev.last_pet and ev.last_pet[0] > last_ttc[0] else last_ttc
    f1, s1 = pick(cep[1], cep[2])

    def heading(r0, r1):
        (x0, y0), (x1, y1) = _centre(r0), _centre(r1)
        return _angle_deg(x1 - x0, y1 - y0) if math.hypot(x1 - x0, y1 - y0) > EPS else _angle_deg(*_facing(r0))

    h1, h2 = heading(f0, f1), heading(s0, s1)
    angle = (h2 - h1 + 180.0) % 360.0 - 180.0
    vel = lambda r, h: (r.speed * math.cos(math.radians(h)), r.speed * math.sin(math.radians(h)))
    (u1x, u1y), (u2x, u2y) = _facing(f_min), _facing(s_min)
    delta_s = math.hypot(f_min.speed * u1x - s_min.speed * u2x, f_min.speed * u1y - s_min.speed * u2y)
    (v1x, v1y), (v2x, v2y) = vel(f_min, h1), vel(s_min, h2)
    px, py = (v1x + v2x) / 2, (v1y + v2y) / 2  # equal masses, perfectly inelastic
    dv1, dv2 = math.hypot(v1x - px, v1y - py), math.hypot(v2x - px, v2y - py)
    second_acc = [pick(ra, rb)[1].accel for _, ra, rb in ev.ttc_steps]
    dr = next((a for a in second_acc if a < 0), min(second_acc))
    (xf0, yf0), (xs0, ys0) = _centre(f_min), _centre(s_min)
    (xf1, yf1), (xs1, ys1) = _centre(f1), _centre(s1)
    return {
        "tMinTTC": tmin, "TTC": ev.ttc, "PET": ev.pet[0] if ev.pet else None,
        "xMinPET": ev.pet[2][0] if ev.pet else None, "yMinPET": ev.pet[2][1] if ev.pet else None,
        "MaxS": max(max(ra.speed, rb.speed) for _, ra, rb in ev.ttc_steps), "DeltaS": delta_s,
        "DR": dr, "MaxD": min(second_acc), "MaxDeltaV": max(dv1, dv2),
        "ConflictAngle": angle,
        "ConflictType": classify(angle, ((f0.link, f0.lane), (s0.link, s0.lane)),
                                 ((f1.link, f1.lane), (s1.link, s1.lane))),
        "PostCrashV": math.hypot(px, py), "PostCrashHeading": _angle_deg(px, py),
        "FirstVID": f_min.vid, "SecondVID": s_min.vid,
        "FirstLink": f_min.link, "SecondLink": s_min.link, "FirstLane": f_min.lane, "SecondLane": s_min.lane,
        "FirstHeading": h1, "SecondHeading": h2, "FirstVMinTTC": f_min.speed, "SecondVMinTTC": s_min.speed,
        "FirstDeltaV": dv1, "SecondDeltaV": dv2,
        "xFirstCSP": xf0, "yFirstCSP": yf0, "xSecondCSP": xs0, "ySecondCSP": ys0,
        "xFirstCEP": xf1, "yFirstCEP": yf1, "xSecondCEP": xs1, "ySecondCEP": ys1,
        "Units": "ft" if units == 0 else "m",
    }


def find_conflicts(trj: Trj, max_ttc: float = 1.5, max_pet: float = 5.0) -> list[dict]:
    """All conflicts in one trajectory file, in the order they end. Keys follow SSAM's conflict-table names."""
    tracks: dict[int, _Track] = defaultdict(_Track)
    for t, vehs in trj.steps:
        for v in vehs:
            tracks[v.vid].t.append(t)
            tracks[v.vid].recs.append(v)
    for tr in tracks.values():
        tr.finish()
    zone = ZONE[trj.units]
    taus = [k * STEP for k in range(int(round(max_ttc / STEP)) + 1)]
    ptr: dict[int, int] = defaultdict(int)
    events: dict[tuple[int, int], _Event] = {}
    out: list[dict] = []

    for t, vehs in trj.steps:
        here: dict[int, int] = {}
        for v in vehs:
            here[v.vid] = ptr[v.vid]
            ptr[v.vid] += 1
        cache: dict[tuple[int, int], tuple] = {}
        circles: dict[tuple[int, int], tuple] = {}

        def rect(vid, k):
            key = (vid, k)
            if key not in cache:
                r = tracks[vid].recs[here[vid]]
                cache[key] = _rect(*proj(vid, k), r.length, r.width)
            return cache[key]

        projs: dict[tuple[int, int], tuple] = {}

        def proj(vid, k):
            key = (vid, k)
            if key not in projs:
                projs[key] = _project(tracks[vid], here[vid], taus[k])
            return projs[key]

        def circle(vid, k):
            """Centre and half diagonal of the projected rectangle: far-apart pairs skip the side test."""
            key = (vid, k)
            if key not in circles:
                r = tracks[vid].recs[here[vid]]
                fx, fy, hx, hy = proj(vid, k)
                circles[key] = (fx - hx * r.length / 2, fy - hy * r.length / 2, math.hypot(r.length, r.width) / 2)
            return circles[key]

        # Zone grid over each vehicle's swept area: its front path out to the MaxTTC point, padded by its size.
        grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        boxes = {}
        for vid, i in here.items():
            tr = tracks[vid]
            r = tr.recs[i]
            fx, fy, _, _ = _project(tr, i, max_ttc)
            j = bisect_right(tr.cum, tr.cum[i] + r.speed * max_ttc, i, tr.end[i] + 1)
            xs = [r.fx, fx] + [p.fx for p in tr.recs[i + 1:j]]
            ys = [r.fy, fy] + [p.fy for p in tr.recs[i + 1:j]]
            pad = math.hypot(r.length, r.width / 2)
            box = boxes[vid] = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
            for cx in range(math.floor(box[0] / zone), math.floor(box[2] / zone) + 1):
                for cy in range(math.floor(box[1] / zone), math.floor(box[3] / zone) + 1):
                    grid[(cx, cy)].append(vid)
        pairs = set()
        for occ in grid.values():
            for a, b in combinations(occ, 2):
                pa, pb = boxes[a], boxes[b]
                if pa[0] <= pb[2] and pb[0] <= pa[2] and pa[1] <= pb[3] and pb[1] <= pa[3]:
                    pairs.add((a, b) if a < b else (b, a))

        active = set()
        for a, b in pairs:
            for k, tau in enumerate(taus):
                (xa, ya, ra_), (xb, yb, rb_) = circle(a, k), circle(b, k)
                if math.hypot(xa - xb, ya - yb) > ra_ + rb_ + 1e-3 or not _overlap(rect(a, k), rect(b, k)):
                    continue
                active.add((a, b))
                ev = events.get((a, b))
                if ev is None:
                    ev = events[(a, b)] = _Event(a, b)
                ra, rb = tracks[a].recs[here[a]], tracks[b].recs[here[b]]
                ev.ttc_steps.append((t, ra, rb))
                if tau < ev.ttc - EPS:
                    ev.ttc, ev.min_at = tau, (t, ra, rb)
                    # Fallback order when no PET is seen: the second vehicle's projected front is nearer the other.
                    pa, pb = rect(a, k), rect(b, k)
                    ca, cb = [sum(c) / 4 for c in zip(*pa)], [sum(c) / 4 for c in zip(*pb)]
                    front_a = ((pa[0][0] + pa[1][0]) / 2, (pa[0][1] + pa[1][1]) / 2)
                    front_b = ((pb[0][0] + pb[1][0]) / 2, (pb[0][1] + pb[1][1]) / 2)
                    ev.order = (b, a) if math.dist(front_a, cb) < math.dist(front_b, ca) else (a, b)
                break

        for key, ev in list(events.items()):
            a, b = key
            if a not in here or b not in here:
                out.append(_finish(events.pop(key), trj.units))
                continue
            ra_rec, rb_rec = tracks[a].recs[here[a]], tracks[b].recs[here[b]]
            if ev.start is None:
                ev.start = (ra_rec, rb_rec)
            window_end = ev.ttc_steps[-1][0]
            if key in active:  # Step 4.2: positions are recorded at the steps with a TTC
                ev.hist.append((t, rect(a, 0), rect(b, 0), ra_rec, rb_rec))
            _pet(ev, t, rect(a, 0), rect(b, 0), (ra_rec, rb_rec), max_pet)
            # Off a collision course and no later encroachment could lower the PET (or MaxPET has passed): done.
            best = ev.pet[0] if ev.pet else max_pet
            if key not in active and t - window_end >= min(best, max_pet) - EPS:
                out.append(_finish(events.pop(key), trj.units))
    out.extend(_finish(ev, trj.units) for ev in events.values())
    return out
