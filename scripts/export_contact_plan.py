#!/usr/bin/env python3
"""Export a contact plan for the discrete-event simulator.

The resulting CSV is the input of the satellite-window extension (E1), which
replaces the permanently available coordinator of the original simulator with
one gated by this schedule.

Usage
-----
    python scripts/export_contact_plan.py
    python scripts/export_contact_plan.py --planes 4 --per-plane 3 --days 30
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leo_contact import evaluate, walker  # noqa: E402
from leo_contact.config import load_scenario, load_stations  # noqa: E402


def main() -> None:
    scenario = load_scenario()
    prop = scenario["propagation"]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", default=None)
    parser.add_argument("--planes", type=int, default=1)
    parser.add_argument("--per-plane", type=int, default=1)
    parser.add_argument("--altitude", type=float, default=prop["altitude_km"])
    parser.add_argument("--min-elevation", type=float, default=prop["min_elevation_deg"])
    parser.add_argument("--days", type=float, default=prop["duration_days"])
    parser.add_argument("--step", type=float, default=prop["step_s"])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    stations = load_stations()
    station = stations[args.station] if args.station else next(iter(stations.values()))
    n = args.planes * args.per_plane

    sats = walker(args.planes, args.per_plane, altitude_km=args.altitude)
    result = evaluate(
        sats, station, args.min_elevation, args.days, args.step,
        n_planes=args.planes, sats_per_plane=args.per_plane,
    )

    out = args.out or ROOT / "results" / f"contact_plan_{n}sat_{int(args.days)}d.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["window_id", "start_s", "end_s", "duration_s", "max_elevation_deg"])
        for i, w in enumerate(result.windows, start=1):
            writer.writerow(
                [i, f"{w.start_s:.1f}", f"{w.end_s:.1f}",
                 f"{w.duration_s:.1f}", f"{w.max_elevation_deg:.2f}"]
            )

    meta = out.with_suffix(".json")
    with meta.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "station": station.name,
                "latitude_deg": station.latitude_deg,
                "longitude_deg": station.longitude_deg,
                "n_satellites": n,
                "n_planes": args.planes,
                "sats_per_plane": args.per_plane,
                "altitude_km": args.altitude,
                "min_elevation_deg": args.min_elevation,
                "duration_days": args.days,
                "step_s": args.step,
                "statistics": result.stats.as_dict(),
            },
            fh,
            indent=2,
        )

    print(f"{len(result.windows)} windows over {args.days:g} days")
    print(f"Max gap: {result.stats.max_gap_s / 60:.1f} min")
    print(f"Written: {out.relative_to(ROOT)}")
    print(f"Written: {meta.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
