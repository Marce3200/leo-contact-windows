"""Contact window analysis and constellation sizing for a LEO emergency backhaul.

Companion code to the master's thesis on performance evaluation of a LoRa
mesh network with LEO satellite backhaul for emergency communications.
"""

from .capacity import CapacityReport, airtime, capacity, dwell_compliant
from .constellation import ConstellationResult, evaluate, walker
from .geometry import GroundStation, max_central_angle
from .orbit import Satellite, orbital_period, sun_synchronous_inclination
from .windows import ContactWindow, find_windows, gaps, merge_windows, statistics

__version__ = "0.1.0"

__all__ = [
    "Satellite",
    "GroundStation",
    "ContactWindow",
    "ConstellationResult",
    "CapacityReport",
    "walker",
    "evaluate",
    "find_windows",
    "merge_windows",
    "statistics",
    "gaps",
    "airtime",
    "capacity",
    "dwell_compliant",
    "orbital_period",
    "sun_synchronous_inclination",
    "max_central_angle",
]
