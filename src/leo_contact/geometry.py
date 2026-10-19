"""Coordinate transforms and topocentric elevation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import ECCENTRICITY_SQ, OMEGA_EARTH, RE_EQUATORIAL


def geodetic_to_ecef(
    latitude_deg: float, longitude_deg: float, altitude_km: float = 0.0
) -> np.ndarray:
    """Convert WGS84 geodetic coordinates to Earth-centred, Earth-fixed [km]."""
    lat = np.radians(latitude_deg)
    lon = np.radians(longitude_deg)
    n = RE_EQUATORIAL / np.sqrt(1 - ECCENTRICITY_SQ * np.sin(lat) ** 2)
    return np.array(
        [
            (n + altitude_km) * np.cos(lat) * np.cos(lon),
            (n + altitude_km) * np.cos(lat) * np.sin(lon),
            (n * (1 - ECCENTRICITY_SQ) + altitude_km) * np.sin(lat),
        ]
    )


def eci_to_ecef(r_eci: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Rotate inertial positions into the Earth-fixed frame.

    The Greenwich hour angle at epoch is taken as zero, which only shifts the
    longitude origin and therefore the wall-clock time at which passes occur.
    Pass durations, counts and gap statistics are unaffected.
    """
    theta = OMEGA_EARTH * np.asarray(t, dtype=float)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    return np.column_stack(
        [
            r_eci[:, 0] * cos_t + r_eci[:, 1] * sin_t,
            -r_eci[:, 0] * sin_t + r_eci[:, 1] * cos_t,
            r_eci[:, 2],
        ]
    )


def local_zenith(latitude_deg: float, longitude_deg: float) -> np.ndarray:
    """Unit vector pointing to the local zenith, expressed in ECEF."""
    lat = np.radians(latitude_deg)
    lon = np.radians(longitude_deg)
    return np.array(
        [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)]
    )


@dataclass(frozen=True)
class GroundStation:
    """A fixed point on the Earth's surface.

    In the emergency architecture under study this is the gateway: the single
    node where the terrestrial mesh converges and the only one holding a link
    to the space segment.
    """

    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float = 0.0
    hazard: str = ""

    def position_ecef(self) -> np.ndarray:
        return geodetic_to_ecef(
            self.latitude_deg, self.longitude_deg, self.altitude_km
        )

    def elevation(self, r_eci: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Topocentric elevation of a satellite track [deg].

        Parameters
        ----------
        r_eci:
            Satellite positions in the inertial frame [km], shape ``(n, 3)``.
        t:
            Matching times since epoch [s], shape ``(n,)``.
        """
        r_ecef = eci_to_ecef(r_eci, t)
        rho = r_ecef - self.position_ecef()
        rho_unit = rho / np.linalg.norm(rho, axis=1)[:, None]
        up = local_zenith(self.latitude_deg, self.longitude_deg)
        return np.degrees(np.arcsin(np.clip(rho_unit @ up, -1.0, 1.0)))


def max_central_angle(altitude_km: float, min_elevation_deg: float) -> float:
    """Half-angle of the visibility circle seen from Earth's centre [deg].

    Useful as an analytical cross-check on the numerically detected windows.
    """
    a = RE_EQUATORIAL + altitude_km
    eps = np.radians(min_elevation_deg)
    return float(
        np.degrees(np.arccos(RE_EQUATORIAL / a * np.cos(eps)) - eps)
    )
