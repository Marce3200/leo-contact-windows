"""Loading of YAML configuration files."""

from __future__ import annotations

from pathlib import Path

import yaml

from .geometry import GroundStation

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _load(name: str) -> dict:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_stations(name: str = "ground_stations.yaml") -> dict[str, GroundStation]:
    """Return the candidate ground stations keyed by name."""
    data = _load(name)
    return {
        entry["name"]: GroundStation(
            name=entry["name"],
            latitude_deg=entry["latitude_deg"],
            longitude_deg=entry["longitude_deg"],
            altitude_km=entry.get("altitude_km", 0.0),
            hazard=entry.get("hazard", ""),
        )
        for entry in data["stations"]
    }


def default_station(name: str = "ground_stations.yaml") -> GroundStation:
    data = _load(name)
    return load_stations(name)[data["default_station"]]


def load_scenario(name: str = "scenario.yaml") -> dict:
    """Return the reference scenario parameters."""
    return _load(name)
