r"""NGSIM vehicle trajectories (US DOT data.transportation.gov, e.g. Lankershim Blvd 8ect-6jqj) -> SSAM .trj (#484).

    python -m crashiq.ssam.ngsim lankershim.csv <out folder>      writes <stem>_p1.trj, <stem>_p2.trj, ...

One .trj per recording period, in English units (ft, ft/s). The portal file joins the periods end to end, and each
period restarts its frame ids and reuses vehicle ids, so a period is told apart by its start time,
global_time - 100 ms * (frame_id - 1); (vehicle_id, frame_id) is unique only within a period. Duplicate
(vehicle, frame) rows inside a period are dropped (the first is kept).

local_y is the front of the vehicle along the road, local_x across it. The rear point is the front minus the
length along the heading, taken from the vehicle's successive front positions. Link = section_id, or 100 + int_id
inside an intersection; lane = lane_id (0 = unknown).
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

from .trj import Trj, Veh, write_trj

DIRECTION = {1: (1.0, 0.0), 2: (0.0, 1.0), 3: (-1.0, 0.0), 4: (0.0, -1.0)}  # NGSIM EB, NB, WB, SB
MOVED = 0.1  # ft between frames below which the heading is not re-estimated


def read_ngsim(path) -> dict[int, list[dict]]:
    """NGSIM CSV -> {period start (ms): rows}, duplicates dropped."""
    periods: dict[int, dict[tuple[int, int], dict]] = defaultdict(dict)
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            frame, gt = int(r["frame_id"]), int(r["global_time"])
            start = round((gt - 100 * (frame - 1)) / 1000) * 1000  # to the second: global_time jitters a little
            periods[start].setdefault((int(r["vehicle_id"]), frame), r)
    return {s: list(rows.values()) for s, rows in sorted(periods.items())}


def to_trj(rows: list[dict]) -> Trj:
    by_veh: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_veh[int(r["vehicle_id"])].append(r)
    steps: dict[int, list[Veh]] = defaultdict(list)
    for vid, rs in by_veh.items():
        rs.sort(key=lambda r: int(r["frame_id"]))
        pts = [(float(r["local_x"]), float(r["local_y"])) for r in rs]
        moves = [i for i in range(len(pts) - 1) if math.dist(pts[i], pts[i + 1]) >= MOVED]
        # shortcut: a vehicle that never moves faces its NGSIM direction (+y when that is missing).
        heading = DIRECTION.get(int(float(rs[0]["direction"] or 0)), (0.0, 1.0))
        if moves:  # still before its first move: it faces the way it then goes
            (ax, ay), (bx, by) = pts[moves[0]], pts[moves[0] + 1]
            d = math.hypot(bx - ax, by - ay)
            heading = ((bx - ax) / d, (by - ay) / d)
        for i, r in enumerate(rs):
            j = i if i + 1 < len(pts) else i - 1  # the last record keeps the heading of its arrival
            if j >= 0 and math.dist(pts[j], pts[j + 1]) >= MOVED:
                (ax, ay), (bx, by) = pts[j], pts[j + 1]
                d = math.hypot(bx - ax, by - ay)
                heading = ((bx - ax) / d, (by - ay) / d)
            (fx, fy), (hx, hy), length = pts[i], heading, float(r["v_length"])
            sec, inter = int(r["section_id"]), int(r["int_id"])
            steps[int(r["frame_id"])].append(Veh(
                vid, sec or (100 + inter if inter else None), int(r["lane_id"]) or None, fx, fy,
                fx - hx * length, fy - hy * length, length, float(r["v_width"]), float(r["v_vel"]),
                float(r["v_acc"])))
    out = [(round((k - 1) * 0.1, 1), sorted(steps[k], key=lambda v: v.vid)) for k in sorted(steps)]
    xs = [c for _, vs in out for v in vs for c in (v.fx, v.rx)]
    ys = [c for _, vs in out for v in vs for c in (v.fy, v.ry)]
    bounds = (math.floor(min(xs)) - 1, math.floor(min(ys)) - 1, math.ceil(max(xs)) + 1, math.ceil(max(ys)) + 1)
    return Trj(version=1.04, endian="L", units=0, scale=1.0, bounds=bounds, z=False, steps=out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m crashiq.ssam.ngsim", description=__doc__.splitlines()[0])
    ap.add_argument("csv", type=Path, help="NGSIM trajectory CSV (data.transportation.gov export)")
    ap.add_argument("out", type=Path, help="folder for the .trj files")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    for i, (start, rows) in enumerate(read_ngsim(a.csv).items(), 1):
        trj = to_trj(rows)
        p = a.out / f"{a.csv.stem}_p{i}.trj"
        write_trj(p, trj)
        n = sum(len(vs) for _, vs in trj.steps)
        print(f"{p}: period from global_time {start}, {len(trj.steps)} timesteps, {n} vehicle records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
