"""Walker constellation construction and evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import GroundStation
from .orbit import Satellite
from .windows import (
    ContactWindow,
    WindowStatistics,
    find_windows,
    merge_windows,
    statistics,
)


def walker(
    n_planes: int,
    sats_per_plane: int,
    altitude_km: float = 550.0,
    raan_span_deg: float = 180.0,
    phasing: int = 1,
    inclination_deg: float | None = None,
) -> list[Satellite]:
    """Build a Walker-star constellation.

    Planes are spread uniformly over ``raan_span_deg`` of right ascension.
    A span of 180 degrees is the usual choice for near-polar orbits, where a
    full 360-degree spread would duplicate ground coverage.

    Parameters
    ----------
    n_planes:
        Number of orbital planes.
    sats_per_plane:
        Satellites evenly spaced in argument of latitude within each plane.
    phasing:
        Walker phasing factor. Offsets successive planes in argument of
        latitude to avoid simultaneous crossings.
    inclination_deg:
        Defaults to the sun-synchronous value for the altitude.
    """
    if n_planes < 1 or sats_per_plane < 1:
        raise ValueError("n_planes and sats_per_plane must be positive.")

    total = n_planes * sats_per_plane
    sats: list[Satellite] = []
    for p in range(n_planes):
        raan = p * raan_span_deg / n_planes
        for s in range(sats_per_plane):
            u = s * 360.0 / sats_per_plane + phasing * p * 360.0 / total
            sats.append(
                Satellite(
                    altitude_km=altitude_km,
                    inclination_deg=inclination_deg,
                    raan_deg=raan,
                    arg_latitude_deg=u % 360.0,
                    name=f"SAT-P{p + 1}-{s + 1}",
                )
            )
    return sats


@dataclass(frozen=True)
class ConstellationResult:
    """Outcome of evaluating one constellation against one ground station."""

    n_satellites: int
    n_planes: int
    sats_per_plane: int
    stats: WindowStatistics
    windows: list[ContactWindow]

    def as_row(self) -> dict:
        s = self.stats
        return {
            "n_satellites": self.n_satellites,
            "n_planes": self.n_planes,
            "sats_per_plane": self.sats_per_plane,
            "passes_per_day": round(s.passes_per_day, 2),
            "contact_per_day_s": round(s.total_contact_per_day_s, 1),
            "availability_pct": round(100 * s.availability_fraction, 3),
            "mean_gap_min": round(s.mean_gap_s / 60, 1),
            "max_gap_min": round(s.max_gap_s / 60, 1),
            "p90_gap_min": round(s.p90_gap_s / 60, 1),
        }


def evaluate(
    satellites: list[Satellite],
    station: GroundStation,
    min_elevation_deg: float = 10.0,
    duration_days: float = 7.0,
    step_s: float = 5.0,
    n_planes: int = 0,
    sats_per_plane: int = 0,
) -> ConstellationResult:
    """Propagate a constellation and summarise its contact plan."""
    all_windows: list[ContactWindow] = []
    for sat in satellites:
        all_windows.extend(
            find_windows(sat, station, min_elevation_deg, duration_days, step_s)
        )
    merged = merge_windows(all_windows)
    return ConstellationResult(
        n_satellites=len(satellites),
        n_planes=n_planes or len(satellites),
        sats_per_plane=sats_per_plane or 1,
        stats=statistics(merged, duration_days),
        windows=merged,
    )
