#!/usr/bin/env python3
"""Size the constellation against two independent acceptance criteria.

The capacity criterion asks whether the accumulated contact time can carry the
daily message demand. The deadline criterion asks whether the longest gap
between windows stays below the message expiration time. They are satisfied at
very different constellation sizes, and that separation is the point of the
analysis.

Usage
-----
    python scripts/run_constellation_sweep.py
    python scripts/run_constellation_sweep.py --station Constitucion --sf 10
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leo_contact import evaluate, walker  # noqa: E402
from leo_contact.capacity import capacity, daily_demand  # noqa: E402
from leo_contact.config import load_scenario, load_stations  # noqa: E402


def main() -> None:
    scenario = load_scenario()
    prop, link, traffic = scenario["propagation"], scenario["link"], scenario["traffic"]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", default=None, help="Ground station name.")
    parser.add_argument("--altitude", type=float, default=prop["altitude_km"])
    parser.add_argument("--min-elevation", type=float, default=prop["min_elevation_deg"])
    parser.add_argument("--days", type=float, default=prop["duration_days"])
    parser.add_argument("--step", type=float, default=prop["step_s"])
    parser.add_argument("--sf", type=int, default=link["spreading_factor"])
    parser.add_argument("--payload", type=int, default=link["payload_bytes"])
    parser.add_argument("--regime", default=traffic["regime"])
    parser.add_argument("--deadline", type=float, default=traffic["deadline_s"])
    parser.add_argument(
        "--out", type=Path, default=ROOT / "results" / "constellation_sweep.csv"
    )
    args = parser.parse_args()

    stations = load_stations()
    station = stations[args.station] if args.station else next(iter(stations.values()))
    demand = daily_demand(args.regime, traffic["passes_per_day_assumed"])

    print(f"Station: {station.name} ({station.latitude_deg:.2f}, {station.longitude_deg:.2f})")
    print(f"Link: SF{args.sf}, {args.payload} B payload")
    print(f"Demand: {demand} messages/day ({args.regime} regime)")
    print(f"Deadline: {args.deadline / 60:.0f} min\n")

    header = (
        f"{'N':>4}{'planes':>8}{'per plane':>11}{'passes/day':>12}"
        f"{'capacity':>10}{'max gap':>10}{'capacity?':>11}{'deadline?':>11}"
    )
    print(header)
    print("-" * len(header))

    rows = []
    first_capacity = first_deadline = None
    for n_planes, per_plane in scenario["constellation_sweep"]["configurations"]:
        sats = walker(n_planes, per_plane, altitude_km=args.altitude)
        result = evaluate(
            sats, station, args.min_elevation, args.days, args.step,
            n_planes=n_planes, sats_per_plane=per_plane,
        )
        cap = capacity(result.windows, args.days, args.sf, args.payload, demand)
        gap_ok = result.stats.max_gap_s <= args.deadline

        n = n_planes * per_plane
        if cap.meets_demand and first_capacity is None:
            first_capacity = n
        if gap_ok and first_deadline is None:
            first_deadline = n

        print(
            f"{n:>4}{n_planes:>8}{per_plane:>11}{result.stats.passes_per_day:12.1f}"
            f"{cap.packets_per_day:>10}{result.stats.max_gap_s / 60:9.1f}m"
            f"{'yes' if cap.meets_demand else 'no':>11}{'yes' if gap_ok else 'no':>11}"
        )
        rows.append({**result.as_row(), **cap.as_dict(), "deadline_met": gap_ok})

    print()
    print(f"Capacity criterion first met at:  {first_capacity} satellites")
    print(f"Deadline criterion first met at:  {first_deadline} satellites")
    if first_capacity and first_deadline:
        print(f"Ratio between criteria: {first_deadline / first_capacity:.1f}x")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWritten: {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
