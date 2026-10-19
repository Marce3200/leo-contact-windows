# leo-contact-windows

Contact window analysis and constellation sizing for a LoRa mesh network with
LEO satellite backhaul, in the context of emergency communications.

Companion code to a master's thesis on the performance evaluation of that
architecture, and a continuation of
[`cubesat-eps-sim`](https://github.com/Marce3200/cubesat-eps-sim), which
established that the operational constraint of such a backhaul is channel
capacity rather than the energy budget.

## What the code answers

Two questions, and the gap between their answers is the point.

1. **How often, and for how long, is the satellite link available?**
   Given a gateway on the ground and a satellite in a sun-synchronous orbit,
   the code propagates the orbit, detects every interval of visibility above
   an elevation threshold, and reports the resulting contact plan.

2. **How many satellites does the constellation need?**
   Two independent acceptance criteria are evaluated. The *capacity* criterion
   asks whether the accumulated contact time can carry the daily message
   demand. The *deadline* criterion asks whether the longest gap between
   windows stays below the expiration time of an emergency message.

## Headline results

For a gateway in the Metropolitan Region of Chile, a sun-synchronous orbit at
550 km and a minimum elevation of 10 degrees:

| | Value |
|---|---|
| Passes per day, one satellite | 3.4 |
| Mean pass duration | 6.0 min |
| Link availability | 1.42 % of the time |
| Longest gap between windows | 11.6 h |
| Satellites to meet the capacity criterion | **4** |
| Satellites to meet the 30-minute deadline | **35** |

The two criteria are satisfied at constellation sizes that differ by close to
a factor of nine. Between them lies a wide range of configurations with ample
transport capacity and no ability to deliver on time, because the binding
question stops being how much data fits and becomes when the next opportunity
to transmit opens.

A second result is that the four candidate gateway locations, spanning 33 to
45 degrees of southern latitude, are near-equivalent in orbital terms: passes
per day rise only from 3.4 to 4.0 and the longest gap stays at 11.5 hours in
all four. The gap is set by the twice-daily clustering intrinsic to a
sun-synchronous orbit, not by latitude.

## Installation

```bash
git clone https://github.com/Marce3200/leo-contact-windows.git
cd leo-contact-windows
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Python 3.10 or later. The only runtime dependencies are NumPy, Matplotlib and
PyYAML; there is no external ephemeris service to configure.

## Usage

Compare the candidate gateway locations under a single satellite:

```bash
python scripts/run_single_satellite.py
python scripts/run_single_satellite.py --min-elevation 5 --days 14
```

Size the constellation against both criteria:

```bash
python scripts/run_constellation_sweep.py
python scripts/run_constellation_sweep.py --station Constitucion --sf 10
```

Export a contact plan for the discrete-event simulator:

```bash
python scripts/export_contact_plan.py --planes 4 --per-plane 3 --days 30
```

Each script writes to `results/`, which is git-ignored: every artefact is
regenerable from the code and the configuration.

### As a library

```python
from leo_contact import GroundStation, Satellite, find_windows, statistics

gateway = GroundStation("gateway", latitude_deg=-33.45, longitude_deg=-70.67)
satellite = Satellite(altitude_km=550.0)          # inclination defaults to SSO

windows = find_windows(satellite, gateway, min_elevation_deg=10.0, duration_days=7)
print(statistics(windows, duration_days=7))
```

## Configuration

Two YAML files under `config/` hold everything that a user might reasonably
want to change without touching code.

- `ground_stations.yaml` — candidate gateway locations and their hazard profile.
- `scenario.yaml` — orbit, link, traffic regime and the constellation sweep grid.

## Project layout

```
src/leo_contact/
  constants.py       Physical, geodetic and LoRa constants
  orbit.py           Circular orbit propagation with J2 nodal regression
  geometry.py        Coordinate transforms, ground stations, elevation
  windows.py         Window detection, merging and gap statistics
  constellation.py   Walker constellation construction and evaluation
  capacity.py        LoRa airtime, optional dwell-time check, channel capacity
  config.py          YAML loading
scripts/             Command-line entry points
tests/               47 tests, mostly analytical cross-checks
config/              Scenario and station definitions
```

## Model and its limits

The propagator uses a circular orbit with secular J2 nodal regression and a
sidereal Earth rotation. Over the seven-day horizons used to size a contact
plan this reproduces pass geometry well within the resolution of the analysis,
and it keeps the package dependency-free.

Deliberately not modelled: atmospheric drag, higher-order gravitational
harmonics, third-body perturbations, station-keeping manoeuvres, link budget
closure as a function of elevation, and terrain masking. The visibility
criterion is purely geometric, so low-elevation passes are counted as fully
usable when in practice they are not.

The Greenwich hour angle at epoch is taken as zero. This shifts the wall-clock
time at which passes occur but leaves durations, counts and gap statistics
unchanged.

## Validation

The test suite favours analytical cross-checks over regression fixtures:
Kepler's third law computed independently, sun-synchronous inclinations against
published tables, orbital radius invariance, maximum latitude bounded by
inclination, elevation of exactly 90 degrees at the sub-satellite point, and
pass durations bounded by the zenithal maximum derived from the central angle.

The LoRa airtime model is checked against the reference case of the prior
energy study: SF12 with a 50-byte payload gives 2.302 s, hence 260 packets in
a 600-second pass.

```bash
pytest
```

## Citation

If this code contributes to your work, please cite the companion study:

```
Quezada-Araya, M. (2026). When night is not the problem: energy analysis of a
3U CubeSat relaying emergency LoRa traffic.
```

## License

MIT. See [LICENSE](LICENSE).
