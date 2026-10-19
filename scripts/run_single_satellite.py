#!/usr/bin/env python3
"""Compare the candidate ground stations under a single satellite.

Usage
-----
    python scripts/run_single_satellite.py
    python scripts/run_single_satellite.py --min-elevation 5 --days 14
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leo_contact import Satellite, find_windows, statistics  # noqa: E402
from leo_contact.config import load_scenario, load_stations  # noqa: E402
from leo_contact.orbit import sun_synchronous_inclination  # noqa: E402


def main() -> None:
    scenario = load_scenario()
    prop = scenario["propagation"]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--altitude", type=float, default=prop["altitude_km"])
    parser.add_argument("--min-elevation", type=float, default=prop["min_elevation_deg"])
    parser.add_argument("--days", type=float, default=prop["duration_days"])
    parser.add_argument("--step", type=float, default=prop["step_s"])
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "single_satellite.csv")
    args = parser.parse_args()

    inc = sun_synchronous_inclination(args.altitude)
    print(f"Sun-synchronous inclination at {args.altitude:g} km: {inc:.3f} deg")
    print(
        f"Propagating {args.days:g} days, step {args.step:g} s, "
        f"minimum elevation {args.min_elevation:g} deg\n"
    )

    satellite = Satellite(altitude_km=args.altitude)
    header = (
        f"{'Station':24s}{'lat':>9}{'passes/day':>12}"
        f"{'mean dur':>10}{'max dur':>10}{'avail':>9}{'max gap':>10}"
    )
    print(header)
    print("-" * len(header))

    rows = []
    for station in load_stations().values():
        windows = find_windows(
            satellite, station, args.min_elevation, args.days, args.step
        )
        s = statistics(windows, args.days)
        print(
            f"{station.name:24s}{station.latitude_deg:9.2f}{s.passes_per_day:12.1f}"
            f"{s.mean_duration_s / 60:9.1f}m{s.max_duration_s / 60:9.1f}m"
            f"{100 * s.availability_fraction:8.2f}%{s.max_gap_s / 3600:9.1f}h"
        )
        rows.append({"station": station.name, "latitude_deg": station.latitude_deg,
                     "hazard": station.hazard, **s.as_dict()})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWritten: {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
