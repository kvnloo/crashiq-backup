"""#484: NGSIM trajectory CSV -> SSAM .trj, on a few synthetic rows (no NGSIM data is committed: CC BY-SA)."""

from __future__ import annotations

import pytest

from crashiq.ssam import read_trj
from crashiq.ssam.ngsim import main, read_ngsim, to_trj

HEAD = ("vehicle_id,frame_id,global_time,local_x,local_y,v_length,v_width,v_class,v_vel,v_acc,lane_id,int_id,"
        "section_id,direction,movement\n")
T0, T1 = 1118935680000, 1118936700000  # two periods; the second restarts frames and reuses vehicle id 1


def rows():
    return [
        # vehicle 1, period 1: northbound 2 ft per frame (20 ft/s), length 15, lane 2 of section 3
        "1,1,{},0,100,15,6,2,20,0,2,0,3,2,1".format(T0),
        "1,2,{},0,102,15,6,2,20,0,2,0,3,2,1".format(T0 + 100),
        "1,2,{},9,999,15,6,2,20,0,2,0,3,2,1".format(T0 + 100),  # duplicate (vehicle, frame): dropped
        "1,3,{},0,104,15,6,2,20,0,2,0,3,2,1".format(T0 + 200),
        # vehicle 2, period 1: stands still at first, then moves east 3 ft per frame, inside intersection 2
        "2,1,{},50,10,10,5,2,0,0,0,2,0,1,2".format(T0),
        "2,2,{},50,10,10,5,2,0,0,0,2,0,1,2".format(T0 + 100),
        "2,3,{},53,10,10,5,2,30,0,0,2,0,1,2".format(T0 + 200),
        # vehicle 1 again, period 2 (another car): frames restart at 1; never moves, direction SB
        "1,1,{},5,500,12,6,2,0,0,1,0,4,4,1".format(T1 + 37),
        "1,2,{},5,500,12,6,2,0,0,1,0,4,4,1".format(T1 + 100),
    ]


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "lank.csv"
    p.write_text(HEAD + "\n".join(rows()) + "\n")
    return p


def test_periods_and_duplicates(csv_path):
    periods = read_ngsim(csv_path)
    assert list(periods) == [T0, T1]
    assert [len(r) for r in periods.values()] == [6, 2]


def test_to_trj(csv_path):
    p1, p2 = (to_trj(r) for r in read_ngsim(csv_path).values())
    assert p1.units == 0 and [t for t, _ in p1.steps] == [0.0, 0.1, 0.2]
    v1, v2 = p1.steps[0][1]
    assert (v1.vid, v1.link, v1.lane, v1.fx, v1.fy, v1.rx, v1.ry) == (1, 3, 2, 0.0, 100.0, 0.0, 85.0)
    assert (v2.link, v2.lane, v2.rx, v2.ry) == (102, None, 40.0, 10.0)  # still: faces the way it then moves
    last = p1.steps[2][1][0]
    assert (last.fy, last.ry) == (104.0, 89.0)  # the last record keeps its arrival heading
    (s,) = p2.steps[0][1]
    assert (s.rx, s.ry) == (5.0, 512.0)  # never moves: faces its NGSIM direction (SB)


def test_main_writes_one_trj_per_period(csv_path, tmp_path):
    out = tmp_path / "trj"
    assert main([str(csv_path), str(out)]) == 0
    files = sorted(out.glob("*.trj"))
    assert [f.name for f in files] == ["lank_p1.trj", "lank_p2.trj"]
    assert sum(len(vs) for _, vs in read_trj(files[0]).steps) == 6
