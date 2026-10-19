"""LoRa airtime and channel capacity of a contact plan.

The airtime model follows the standard formulation given by the transceiver
manufacturer. It is the quantity that turns a contact plan, expressed in
seconds of visibility, into a capacity expressed in packets.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .constants import DWELL_TIME_LIMIT_S, LORA_BANDWIDTH_HZ
from .windows import ContactWindow


def airtime(
    spreading_factor: int,
    payload_bytes: int,
    bandwidth_hz: int = LORA_BANDWIDTH_HZ,
    coding_rate: int = 1,
    preamble_symbols: int = 8,
    crc: bool = True,
    implicit_header: bool = False,
) -> float:
    """Time on air of one LoRa packet [s].

    Parameters
    ----------
    spreading_factor:
        7 to 12.
    payload_bytes:
        Application payload length.
    coding_rate:
        1 to 4, meaning 4/5 through 4/8.
    """
    if not 7 <= spreading_factor <= 12:
        raise ValueError("spreading_factor must be between 7 and 12.")
    if not 1 <= coding_rate <= 4:
        raise ValueError("coding_rate must be between 1 and 4.")

    low_data_rate = 1 if (bandwidth_hz == 125_000 and spreading_factor >= 11) else 0
    t_sym = (2**spreading_factor) / bandwidth_hz
    t_preamble = (preamble_symbols + 4.25) * t_sym

    numerator = (
        8 * payload_bytes
        - 4 * spreading_factor
        + 28
        + 16 * int(crc)
        - 20 * int(implicit_header)
    )
    denominator = 4 * (spreading_factor - 2 * low_data_rate)
    n_payload = 8 + max(math.ceil(numerator / denominator) * (coding_rate + 4), 0)

    return t_preamble + n_payload * t_sym


def bitrate(
    spreading_factor: int,
    bandwidth_hz: int = LORA_BANDWIDTH_HZ,
    coding_rate: int = 1,
) -> float:
    """Nominal LoRa bit rate [bps]."""
    return (
        spreading_factor
        * (bandwidth_hz / 2**spreading_factor)
        * (4 / (4 + coding_rate))
    )


def dwell_compliant(spreading_factor: int, payload_bytes: int, **kwargs) -> bool:
    """Whether a configuration fits within the per-channel dwell time limit.

    Relevant for the 915-928 MHz band under FCC-style regimes, which is the
    case in Chile. It excludes SF11 and SF12 at 125 kHz for typical payloads.
    """
    return airtime(spreading_factor, payload_bytes, **kwargs) <= DWELL_TIME_LIMIT_S


@dataclass(frozen=True)
class CapacityReport:
    """Capacity of a contact plan under a given link configuration."""

    spreading_factor: int
    payload_bytes: int
    airtime_s: float
    dwell_compliant: bool
    packets_per_day: int
    demand_per_day: int

    @property
    def meets_demand(self) -> bool:
        return self.packets_per_day >= self.demand_per_day

    @property
    def utilisation(self) -> float:
        if not self.packets_per_day:
            return float("inf")
        return self.demand_per_day / self.packets_per_day

    def as_dict(self) -> dict:
        return {
            "spreading_factor": self.spreading_factor,
            "payload_bytes": self.payload_bytes,
            "airtime_ms": round(1000 * self.airtime_s, 1),
            "dwell_compliant": self.dwell_compliant,
            "packets_per_day": self.packets_per_day,
            "demand_per_day": self.demand_per_day,
            "meets_demand": self.meets_demand,
            "utilisation_pct": round(100 * self.utilisation, 1),
        }


def capacity(
    windows: Sequence[ContactWindow],
    duration_days: float,
    spreading_factor: int = 12,
    payload_bytes: int = 50,
    demand_per_day: int = 1600,
) -> CapacityReport:
    """Packets deliverable per day given a contact plan.

    The default configuration reproduces the reference case of the prior
    energy study: SF12, 50-byte payload, 2.302 s of airtime, which yields
    260 packets in a 600 s pass.
    """
    t_air = airtime(spreading_factor, payload_bytes)
    contact_per_day = sum(w.duration_s for w in windows) / duration_days
    return CapacityReport(
        spreading_factor=spreading_factor,
        payload_bytes=payload_bytes,
        airtime_s=t_air,
        dwell_compliant=dwell_compliant(spreading_factor, payload_bytes),
        packets_per_day=int(contact_per_day / t_air),
        demand_per_day=demand_per_day,
    )


TRAFFIC_REGIMES = {
    "normal": 50,
    "emergency": 150,
    "disaster": 400,
}
"""Packets per pass for each regime, as defined in the prior energy study."""


def daily_demand(regime: str, passes_per_day: float = 4.0) -> int:
    """Daily message demand implied by a traffic regime."""
    if regime not in TRAFFIC_REGIMES:
        raise KeyError(f"Unknown regime {regime!r}. Options: {list(TRAFFIC_REGIMES)}")
    return int(TRAFFIC_REGIMES[regime] * passes_per_day)
