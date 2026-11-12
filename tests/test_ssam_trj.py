"""#484: SSAM .trj reader/writer (format 1.04 and 3.0, both endians) and the trajectory CSV reader."""

from __future__ import annotations

import pytest
from ssam_scenarios import SCENARIOS

from conftest import FIXTURES
from crashiq.ssam import Trj, Veh, read_trajectory_csv, read_trj, write_trj

STEPS = [
    (0.0, [Veh(7, 12, 1, 10.0, 2.0, 5.5, 2.0, 4.5, 1.8, 15.0, -1.5, 0.0, 0.0),
           Veh(9, 13, 2, -4.0, 8.5, -4.0, 4.0, 4.5, 1.9, 0.0, 0.0, 1.0, 1.0)]),
    (0.1, [Veh(7, 12, 1, 11.5, 2.0, 7.0, 2.0, 4.5, 1.8, 14.75, -1.5, 0.0, 0.0)]),
    (0.2, []),
]


def _trj(version, endian, z):
    steps = STEPS if z else [(t, [v._replace(fz=None, rz=None) for v in vs]) for t, vs in STEPS]
    return Trj(version=version, endian=endian, units=1, scale=0.5, bounds=(-20, -10, 40, 30), z=z, steps=steps)


@pytest.mark.parametrize("endian", ["L", "B"])
@pytest.mark.parametrize("version,z", [(1.04, False), (3.0, False), (3.0, True)])
def test_round_trip(tmp_path, endian, version, z):
    p = tmp_path / "a.trj"
    write_trj(p, _trj(version, endian, z))
    # Record sizes from the spec: FORMAT 6 (+1 Z-option byte in 3.0), DIMENSIONS 22, TIMESTEP 5, VEHICLE 42 (+8 Z).
    assert p.stat().st_size == (6 + (version >= 3)) + 22 + 3 * 5 + 3 * (42 + 8 * z)
    got = read_trj(p)
    assert (got.endian, got.units, got.scale, got.bounds, got.z) == (endian, 1, 0.5, (-20, -10, 40, 30), z)
    assert got.version == pytest.approx(version)
    assert [t for t, _ in got.steps] == pytest.approx([0.0, 0.1, 0.2])
    want = _trj(version, endian, z).steps
    for (_, a), (_, b) in zip(got.steps, want):
        assert len(a) == len(b)
        for va, vb in zip(a, b):
            assert va == pytest.approx(vb)


def test_coordinates_are_scaled(tmp_path):
    p = tmp_path / "a.trj"
    write_trj(p, _trj(1.04, "L", False))
    raw = p.read_bytes()
    import struct
    # First VEHICLE record starts after FORMAT(6) + DIMENSIONS(22) + TIMESTEP(5); front x is stored as 10.0 / 0.5.
    assert struct.unpack_from("<f", raw, 33 + 10)[0] == 20.0


def test_big_endian_bytes(tmp_path):
    p = tmp_path / "b.trj"
    write_trj(p, _trj(1.04, "B", False))
    assert p.read_bytes()[:6] == b"\x00B" + bytes.fromhex("3f851eb8")  # 1.04 as a big-endian float


def test_bad_files(tmp_path):
    p = tmp_path / "x.trj"
    p.write_bytes(b"hello")
    with pytest.raises(ValueError, match="FORMAT"):
        read_trj(p)
    write_trj(p, _trj(1.04, "L", False))
    p.write_bytes(p.read_bytes()[:-3])
    with pytest.raises(ValueError, match="truncated"):
        read_trj(p)
    with pytest.raises(ValueError):
        write_trj(p, _trj(1.04, "L", False)._replace(z=True))  # 1.04 has no Z fields


def test_csv_reader(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("t,vehicle_id,front_x,front_y,rear_x,rear_y,length,width,speed,accel,lane\n"
                 "0.1,5,1,0,-3.5,0,4.5,1.8,10,0,2\n"
                 "0.0,5,0,0,-4.5,0,4.5,1.8,10,0,2\n"
                 "0.0,6,0,9,0,4.5,4.5,1.8,0,0,\n")
    got = read_trajectory_csv(p)
    assert got.units == 1 and got.z is False
    assert [t for t, _ in got.steps] == [0.0, 0.1]
    assert got.steps[0][1] == [Veh(5, None, 2, 0.0, 0.0, -4.5, 0.0, 4.5, 1.8, 10.0, 0.0),
                               Veh(6, None, None, 0.0, 9.0, 0.0, 4.5, 4.5, 1.8, 0.0, 0.0)]
    assert got.steps[1][1][0].fx == 1.0
    p.write_text("t,vehicle_id,front_x\n0,1,2\n")
    with pytest.raises(ValueError, match="missing columns"):
        read_trajectory_csv(p)


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_fixtures_are_current(tmp_path, name):
    """tests/fixtures/ssam/<name>.trj are the files given to FHWA's SSAM; they must match the scenario code."""
    p = tmp_path / f"{name}.trj"
    write_trj(p, SCENARIOS[name]())
    assert p.read_bytes() == (FIXTURES / "ssam" / f"{name}.trj").read_bytes()
