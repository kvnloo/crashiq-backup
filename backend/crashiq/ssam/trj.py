"""SSAM trajectory files: the binary .trj format (spec v1.04 and v3.0) and a plain trajectory CSV.

.trj layout (from the public spec): one FORMAT record, one DIMENSIONS record, then TIMESTEP records each followed by
its VEHICLE records. Every record starts with its type byte. Bytes are unsigned; Integer and Float are 4-byte signed,
in the byte order the FORMAT record names ('L' little, 'B' big). v3.0 adds a Z-option byte to FORMAT and, when it is
set, Front Z / Rear Z floats to every VEHICLE. X/Y are stored in units of Scale (real = stored * Scale); lengths,
speeds and accelerations are stored unscaled. Units: 0 = feet, 1 = meters. Link/lane id 0 is read as unknown.
"""

from __future__ import annotations

import csv
import struct
from pathlib import Path
from typing import NamedTuple


class Veh(NamedTuple):
    """One vehicle at one timestep; coordinates in real units (already multiplied by Scale)."""
    vid: int
    link: int | None
    lane: int | None
    fx: float
    fy: float
    rx: float
    ry: float
    length: float
    width: float
    speed: float
    accel: float
    fz: float | None = None
    rz: float | None = None


class Trj(NamedTuple):
    version: float
    endian: str  # "L" or "B"
    units: int  # 0 English (ft), 1 metric (m)
    scale: float
    bounds: tuple[int, int, int, int]  # MinX, MinY, MaxX, MaxY, stored (scaled) units
    z: bool
    steps: list[tuple[float, list[Veh]]]


def _veh_struct(e: str, z: bool) -> struct.Struct:
    # type, vehicle id, link id, lane id, front x/y, rear x/y, length, width, speed, accel (+ front z, rear z)
    return struct.Struct(e + "BiiB8f" + ("2f" if z else ""))


def read_trj(path) -> Trj:
    b = Path(path).read_bytes()
    if len(b) < 6 or b[0] != 0 or b[1] not in b"LB":
        raise ValueError(f"{path}: not an SSAM .trj file (no FORMAT record)")
    endian = chr(b[1])
    e = "<" if endian == "L" else ">"
    version = struct.unpack_from(e + "f", b, 2)[0]
    pos, z = 6, False
    if version >= 2.99:  # v3.0 adds the Z-option byte; blank (space) or zero means no elevations
        if len(b) < 7:
            raise ValueError(f"{path}: truncated FORMAT record")
        z, pos = b[6] not in (0, 32), 7
    if len(b) < pos + 22 or b[pos] != 1:
        raise ValueError(f"{path}: no DIMENSIONS record after FORMAT")
    units, scale, *bounds = struct.unpack_from(e + "Bf4i", b, pos + 1)
    pos += 22
    veh = _veh_struct(e, z)
    ts = struct.Struct(e + "f")
    steps: list[tuple[float, list[Veh]]] = []
    n = len(b)
    while pos < n:
        rt = b[pos]
        if rt == 2:
            if pos + 5 > n:
                raise ValueError(f"{path}: truncated TIMESTEP record at byte {pos}")
            steps.append((ts.unpack_from(b, pos + 1)[0], []))
            pos += 5
        elif rt == 3:
            if pos + veh.size > n:
                raise ValueError(f"{path}: truncated VEHICLE record at byte {pos}")
            if not steps:
                raise ValueError(f"{path}: VEHICLE record before any TIMESTEP at byte {pos}")
            _, vid, link, lane, fx, fy, rx, ry, ln, wd, sp, ac, *zz = veh.unpack_from(b, pos)
            # 0 is how files say "no link/lane" (and how write_trj stores None)
            steps[-1][1].append(Veh(vid, link or None, lane or None, fx * scale, fy * scale, rx * scale, ry * scale,
                                    ln, wd, sp, ac, *zz))
            pos += veh.size
        else:
            raise ValueError(f"{path}: unknown record type {rt} at byte {pos}")
    return Trj(version, endian, units, scale, tuple(bounds), z, steps)


def write_trj(path, trj: Trj) -> None:
    if trj.z and trj.version < 2.99:
        raise ValueError("Z values need trajectory format 3.0")
    e = "<" if trj.endian == "L" else ">"
    out = bytearray(struct.pack(e + "BBf", 0, ord(trj.endian), trj.version))
    if trj.version >= 2.99:
        out.append(1 if trj.z else 0)
    out += struct.pack(e + "BBf4i", 1, trj.units, trj.scale, *trj.bounds)
    veh, s = _veh_struct(e, trj.z), trj.scale
    for t, vehs in trj.steps:
        out += struct.pack(e + "Bf", 2, t)
        for v in vehs:
            zz = (v.fz, v.rz) if trj.z else ()
            out += veh.pack(3, v.vid, v.link or 0, v.lane or 0, v.fx / s, v.fy / s, v.rx / s, v.ry / s,
                            v.length, v.width, v.speed, v.accel, *zz)
    Path(path).write_bytes(bytes(out))


CSV_COLUMNS = ("t", "vehicle_id", "front_x", "front_y", "rear_x", "rear_y", "length", "width", "speed", "accel")


def read_trajectory_csv(path, units: int = 1) -> Trj:
    """CSV with CSV_COLUMNS plus optional link, lane, z (one elevation for both bumpers); one row per vehicle-step."""
    rows: dict[float, list[Veh]] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        missing = [c for c in CSV_COLUMNS if c not in (r.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(missing)}")
        has_z = "z" in r.fieldnames
        opt = lambda row, k: int(row[k]) if row.get(k) not in (None, "") else None
        for i, row in enumerate(r, start=2):
            try:
                z = float(row["z"]) if has_z and row["z"] != "" else None
                t = float(row["t"])
                v = Veh(int(row["vehicle_id"]), opt(row, "link"), opt(row, "lane"),
                        *(float(row[k]) for k in CSV_COLUMNS[2:]), z, z)
            except ValueError as ex:
                raise ValueError(f"{path} line {i}: {ex}") from None
            rows.setdefault(t, []).append(v)
    steps = sorted(rows.items())
    xs = [c for _, vs in steps for v in vs for c in (v.fx, v.rx)] or [0.0]
    ys = [c for _, vs in steps for v in vs for c in (v.fy, v.ry)] or [0.0]
    bounds = (int(min(xs)) - 1, int(min(ys)) - 1, int(max(xs)) + 1, int(max(ys)) + 1)
    return Trj(3.0 if has_z else 1.04, "L", units, 1.0, bounds, has_z, steps)
