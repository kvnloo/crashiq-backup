import math

import pytest

from crashiq.geo import FT_PER_M, LocalProjection, Polyline, angle_diff, buffer_ring, haversine_ft


def vincenty_ft(p, q):
    """Independent WGS84 ellipsoidal distance (Vincenty inverse) as the reference geodesic."""
    a, f = 6378137.0, 1 / 298.257223563
    b = (1 - f) * a
    L = math.radians(q[1] - p[1])
    U1, U2 = math.atan((1 - f) * math.tan(math.radians(p[0]))), math.atan((1 - f) * math.tan(math.radians(q[0])))
    sU1, cU1, sU2, cU2 = math.sin(U1), math.cos(U1), math.sin(U2), math.cos(U2)
    lam = L
    for _ in range(200):
        sl, cl = math.sin(lam), math.cos(lam)
        ss = math.hypot(cU2 * sl, cU1 * sU2 - sU1 * cU2 * cl)
        if ss == 0:
            return 0.0
        cs = sU1 * sU2 + cU1 * cU2 * cl
        sig = math.atan2(ss, cs)
        sa = cU1 * cU2 * sl / ss
        c2a = 1 - sa * sa
        c2sm = cs - 2 * sU1 * sU2 / c2a if c2a else 0.0
        C = f / 16 * c2a * (4 + f * (4 - 3 * c2a))
        prev, lam = lam, L + (1 - C) * f * sa * (sig + C * ss * (c2sm + C * cs * (-1 + 2 * c2sm ** 2)))
        if abs(lam - prev) < 1e-12:
            break
    u2 = c2a * (a * a - b * b) / (b * b)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    ds = B * ss * (c2sm + B / 4 * (cs * (-1 + 2 * c2sm ** 2) - B / 6 * c2sm * (-3 + 4 * ss ** 2) * (-3 + 4 * c2sm ** 2)))
    return b * A * (sig - ds) * FT_PER_M


def test_projection_matches_geodesic_within_0_1_percent():
    a, b = (33.8953, -118.32662), (33.9123, -118.32662)     # ~1.17 mi N-S
    c = (33.9040, -118.3200)                                 # off to the east
    proj = LocalProjection.around([a, b, c])
    for p, q in ((a, b), (a, c), (b, c)):
        x1, y1 = proj.to_xy(*p)
        x2, y2 = proj.to_xy(*q)
        planar = math.hypot(x2 - x1, y2 - y1)
        assert planar == pytest.approx(vincenty_ft(p, q), rel=1e-3)
        assert haversine_ft(p, q) == pytest.approx(vincenty_ft(p, q), rel=5e-3)   # sphere: good to ~0.3%


def test_round_trip():
    proj = LocalProjection(33.9, -118.3)
    lat, lon = proj.to_ll(*proj.to_xy(33.91, -118.31))
    assert (lat, lon) == pytest.approx((33.91, -118.31), abs=1e-9)


def test_polyline_projection_station_and_offset():
    line = Polyline([(33.8953, -118.32662), (33.9123, -118.32662)])
    mid = line.project(33.9038, -118.32662)
    assert mid.offset_ft == pytest.approx(0, abs=0.01)
    assert mid.station_ft == pytest.approx(line.length_ft / 2, rel=1e-3)
    east = line.project(33.9038, -118.32630)                  # ~97 ft east
    assert east.offset_ft == pytest.approx(vincenty_ft((33.9038, -118.32662), (33.9038, -118.32630)), rel=1e-3)
    before = line.project(33.8940, -118.32662)                # before A: clamps to station 0 ...
    assert before.station_ft == 0
    assert before.station_ext == pytest.approx(-vincenty_ft((33.8940, -118.32662), (33.8953, -118.32662)), rel=1e-3)
    after = line.project(33.9130, -118.32662)                 # ... and past B continues beyond the length
    assert after.station_ext > line.length_ft


def test_point_at_and_bearing():
    line = Polyline([(0.0, 0.0), (0.001, 0.0), (0.001, 0.001)])
    assert line.bearing_at(0) == pytest.approx(0)
    assert line.bearing_at(1) == pytest.approx(90, abs=0.5)
    lat, lon = line.point_at(line.cum[1])
    assert (lat, lon) == pytest.approx((0.001, 0.0), abs=1e-9)


def test_angle_diff_is_undirected():
    assert angle_diff(5, 175) == 10
    assert angle_diff(0, 90) == 90


def test_polyline_needs_two_distinct_points():
    with pytest.raises(ValueError):
        Polyline([(1.0, 1.0)])
    with pytest.raises(ValueError):
        Polyline([(1.0, 1.0), (1.0, 1.0)])


def test_buffer_ring_is_closed_and_at_the_buffer_distance():
    line = Polyline([(33.8953, -118.32662), (33.9040, -118.32662), (33.9123, -118.3250)])
    ring = buffer_ring(line, 100)
    assert ring[0] == ring[-1] and len(ring) > 20
    offs = [line.project(lat, lon).offset_ft for lat, lon in ring[:-1]]
    assert max(offs) <= 100.5                     # never wider than the buffer
    assert min(offs) >= 97                        # inner side of a bend can sit slightly inside (display only)
    assert sum(abs(o - 100) <= 0.5 for o in offs) / len(offs) > 0.98
