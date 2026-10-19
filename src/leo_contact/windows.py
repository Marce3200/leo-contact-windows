"""Detection and statistics of contact windows."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

import numpy as np

from .constants import SECONDS_PER_DAY
from .geometry import GroundStation
from .orbit import Satellite


@dataclass(frozen=True)
class ContactWindow:
    """A single interval of visibility above the elevation threshold."""

    start_s: float
    end_s: float
    max_elevation_deg: float
    satellite: str = ""

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    def as_dict(self) -> dict:
        d = asdict(self)
        d["duration_s"] = self.duration_s
        return d


@dataclass(frozen=True)
class WindowStatistics:
    """Aggregate figures describing a contact plan."""

    n_windows: int
    duration_days: float
    passes_per_day: float
    mean_duration_s: float
    max_duration_s: float
    total_contact_per_day_s: float
    availability_fraction: float
    mean_gap_s: float
    max_gap_s: float
    p90_gap_s: float

    def as_dict(self) -> dict:
        return asdict(self)


def _intervals(mask: np.ndarray) -> list[tuple[int, int]]:
    """Index pairs bounding each run of ``True`` in a boolean array."""
    if mask.size == 0 or not mask.any():
        return []
    edges = np.diff(mask.astype(np.int8))
    starts = np.flatnonzero(edges == 1) + 1
    ends = np.flatnonzero(edges == -1) + 1
    if mask[0]:
        starts = np.r_[0, starts]
    if mask[-1]:
        ends = np.r_[ends, mask.size - 1]
    return list(zip(starts.tolist(), ends.tolist(), strict=True))


def find_windows(
    satellite: Satellite,
    station: GroundStation,
    min_elevation_deg: float = 10.0,
    duration_days: float = 7.0,
    step_s: float = 5.0,
) -> list[ContactWindow]:
    """Contact windows of one satellite over one ground station."""
    t = np.arange(0.0, duration_days * SECONDS_PER_DAY, step_s)
    elevation = station.elevation(satellite.propagate(t), t)
    visible = elevation >= min_elevation_deg
    return [
        ContactWindow(
            start_s=float(t[a]),
            end_s=float(t[b]),
            max_elevation_deg=float(elevation[a : b + 1].max()),
            satellite=satellite.name,
        )
        for a, b in _intervals(visible)
    ]


def merge_windows(windows: Iterable[ContactWindow]) -> list[ContactWindow]:
    """Union of overlapping windows, as seen by the gateway.

    A constellation offers a single logical link: what matters operationally
    is whether *some* satellite is in view, not which one.
    """
    ordered = sorted(windows, key=lambda w: w.start_s)
    merged: list[ContactWindow] = []
    for w in ordered:
        if merged and w.start_s <= merged[-1].end_s:
            last = merged[-1]
            merged[-1] = ContactWindow(
                start_s=last.start_s,
                end_s=max(last.end_s, w.end_s),
                max_elevation_deg=max(last.max_elevation_deg, w.max_elevation_deg),
                satellite="merged",
            )
        else:
            merged.append(w)
    return merged


def gaps(windows: Sequence[ContactWindow]) -> np.ndarray:
    """Idle intervals between consecutive windows [s]."""
    if len(windows) < 2:
        return np.array([])
    ordered = sorted(windows, key=lambda w: w.start_s)
    return np.array(
        [ordered[k + 1].start_s - ordered[k].end_s for k in range(len(ordered) - 1)]
    )


def statistics(
    windows: Sequence[ContactWindow], duration_days: float
) -> WindowStatistics:
    """Summarise a contact plan."""
    if not windows:
        return WindowStatistics(
            0, duration_days, 0.0, 0.0, 0.0, 0.0, 0.0,
            float("inf"), float("inf"), float("inf"),
        )
    durations = np.array([w.duration_s for w in windows])
    g = gaps(windows)
    total = durations.sum()
    return WindowStatistics(
        n_windows=len(windows),
        duration_days=duration_days,
        passes_per_day=len(windows) / duration_days,
        mean_duration_s=float(durations.mean()),
        max_duration_s=float(durations.max()),
        total_contact_per_day_s=float(total / duration_days),
        availability_fraction=float(total / (duration_days * SECONDS_PER_DAY)),
        mean_gap_s=float(g.mean()) if g.size else float("nan"),
        max_gap_s=float(g.max()) if g.size else float("nan"),
        p90_gap_s=float(np.percentile(g, 90)) if g.size else float("nan"),
    )
