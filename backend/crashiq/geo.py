"""Distances for corridor work, in feet, in a projected CRS (never in degrees).

`LocalProjection` is an equirectangular projection centred on the corridor, using the WGS84
meridional and prime-vertical radii at the centre latitude. Over a corridor of a few miles its
error against the geodesic is well under 0.1% (tested), which is far below crash-location noise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

FT_PER_M = 1 / 0.3048
FT_PER_MI = 5280.0
_A = 6378137.0                 # WGS84 semi-major axis (m)
_E2 = 6.69437999014e-3         # WGS84 first eccentricity squared


def haversine_ft(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between (lat, lon) points, in feet (mean Earth radius)."""
    R = 6371008.8
    la1, la2 = math.radians(a[0]), math.radians(b[0])
    dla, dlo = la2 - la1, math.radians(b[1] - a[1])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h)) * FT_PER_M


@dataclass(frozen=True)
class LocalProjection:
    lat0: float
    lon0: float

    @property
    def _scale(self) -> tuple[float, float]:
        phi = math.radians(self.lat0)
        s = 1 - _E2 * math.sin(phi) ** 2
        m_per_rad_lat = _A * (1 - _E2) / s ** 1.5          # meridional radius
        m_per_rad_lon = _A / math.sqrt(s) * math.cos(phi)   # prime vertical × cos φ
        return m_per_rad_lon * math.pi / 180 * FT_PER_M, m_per_rad_lat * math.pi / 180 * FT_PER_M

    def to_xy(self, lat: float, lon: float) -> tuple[float, float]:
        kx, ky = self._scale
        return (lon - self.lon0) * kx, (lat - self.lat0) * ky

    def to_ll(self, x: float, y: float) -> tuple[float, float]:
        kx, ky = self._scale
        return self.lat0 + y / ky, self.lon0 + x / kx

    @classmethod
    def around(cls, pts: list[tuple[float, float]]) -> "LocalProjection":
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        return cls((min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2)


@dataclass(frozen=True)
class Projected:
    station_ft: float    # distance along the line from its start to the foot of the perpendicular
    offset_ft: float     # perpendicular distance from the line
    index: int           # which line segment the foot lies on
    x: float
    y: float
    station_ext: float   # like station_ft, but continues past A (negative) and B (> length) along the end segments


class Polyline:
    """A drawn corridor in projected feet: stations, projection of points, tangent bearings."""

    def __init__(self, pts_ll: list[tuple[float, float]], proj: LocalProjection | None = None):
        if len(pts_ll) < 2:
            raise ValueError("A corridor needs at least two points.")
        self.proj = proj or LocalProjection.around(pts_ll)
        self.ll = [tuple(p) for p in pts_ll]
        self.xy = [self.proj.to_xy(*p) for p in pts_ll]
        self.cum = [0.0]
        for (x1, y1), (x2, y2) in zip(self.xy, self.xy[1:]):
            self.cum.append(self.cum[-1] + math.hypot(x2 - x1, y2 - y1))
        if self.length_ft <= 0:
            raise ValueError("The corridor line has zero length.")

    @property
    def length_ft(self) -> float:
        return self.cum[-1]

    def project_xy(self, x: float, y: float) -> Projected:
        best = None
        last = len(self.xy) - 2
        for i, ((x1, y1), (x2, y2)) in enumerate(zip(self.xy, self.xy[1:])):
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy
            raw = 0.0 if L2 == 0 else ((x - x1) * dx + (y - y1) * dy) / L2
            t = max(0.0, min(1.0, raw))
            fx, fy = x1 + t * dx, y1 + t * dy
            d = math.hypot(x - fx, y - fy)
            if best is None or d < best[0] - 1e-9:
                seg = math.sqrt(L2)
                ext = raw if (i == 0 and raw < 0) or (i == last and raw > 1) else t
                best = (d, self.cum[i] + t * seg, i, fx, fy, self.cum[i] + ext * seg)
        d, st, i, fx, fy, ext = best
        return Projected(st, d, i, fx, fy, ext)

    def project(self, lat: float, lon: float) -> Projected:
        return self.project_xy(*self.proj.to_xy(lat, lon))

    def point_at(self, station_ft: float) -> tuple[float, float]:
        """(lat, lon) on the line at a station (clamped to the line)."""
        s = max(0.0, min(self.length_ft, station_ft))
        for i in range(len(self.cum) - 1):
            if s <= self.cum[i + 1] or i == len(self.cum) - 2:
                seg = self.cum[i + 1] - self.cum[i]
                t = 0.0 if seg == 0 else (s - self.cum[i]) / seg
                (x1, y1), (x2, y2) = self.xy[i], self.xy[i + 1]
                return self.proj.to_ll(x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return self.ll[-1]

    def bearing_at(self, index: int) -> float:
        """Direction of line segment `index`, degrees in [0, 180) (undirected)."""
        (x1, y1), (x2, y2) = self.xy[index], self.xy[index + 1]
        return math.degrees(math.atan2(x2 - x1, y2 - y1)) % 180


def angle_diff(a: float, b: float) -> float:
    """Smallest difference between two undirected bearings in [0, 180)."""
    d = abs(a - b) % 180
    return min(d, 180 - d)
