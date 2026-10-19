"""Circular orbit propagation with J2 nodal regression.

The model is deliberately simple. For the seven-day horizons used to size a
contact plan, a circular orbit with secular J2 precession reproduces pass
geometry to well within the resolution of the analysis, and it keeps the
package free of external ephemeris dependencies.

Not modelled: atmospheric drag, higher-order gravitational harmonics,
third-body perturbations, station-keeping manoeuvres.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import (
    J2,
    MU_EARTH,
    RE_EQUATORIAL,
    SECONDS_PER_DAY,
    SOLAR_YEAR_DAYS,
)


def semi_major_axis(altitude_km: float) -> float:
    """Orbital radius of a circular orbit at a given altitude [km]."""
    return RE_EQUATORIAL + altitude_km


def mean_motion(altitude_km: float) -> float:
    """Mean motion of a circular orbit [rad/s]."""
    a = semi_major_axis(altitude_km)
    return np.sqrt(MU_EARTH / a**3)


def orbital_period(altitude_km: float) -> float:
    """Orbital period of a circular orbit [s]."""
    return 2 * np.pi / mean_motion(altitude_km)


def sun_synchronous_inclination(altitude_km: float) -> float:
    """Inclination that makes a circular orbit sun-synchronous [deg].

    The condition is that the J2-induced nodal regression equals the mean
    apparent motion of the Sun in right ascension, 360 deg per tropical year.
    """
    a = semi_major_axis(altitude_km)
    n = mean_motion(altitude_km)
    target_rate = np.radians(360.0 / SOLAR_YEAR_DAYS) / SECONDS_PER_DAY
    cos_i = -target_rate * 2 * a**2 / (3 * J2 * RE_EQUATORIAL**2 * n)
    if not -1.0 <= cos_i <= 1.0:
        raise ValueError(
            f"No sun-synchronous inclination exists at {altitude_km} km altitude."
        )
    return float(np.degrees(np.arccos(cos_i)))


def nodal_regression_rate(altitude_km: float, inclination_deg: float) -> float:
    """Secular drift of the right ascension of the ascending node [rad/s]."""
    a = semi_major_axis(altitude_km)
    n = mean_motion(altitude_km)
    return -1.5 * n * J2 * (RE_EQUATORIAL / a) ** 2 * np.cos(np.radians(inclination_deg))


@dataclass(frozen=True)
class Satellite:
    """A single satellite in a circular orbit.

    Attributes
    ----------
    altitude_km:
        Altitude above the WGS84 equatorial radius.
    inclination_deg:
        Orbital inclination. If ``None`` the sun-synchronous value for the
        given altitude is used.
    raan_deg:
        Right ascension of the ascending node at epoch.
    arg_latitude_deg:
        Argument of latitude at epoch, i.e. the in-plane angular position
        measured from the ascending node.
    name:
        Optional identifier, useful when exporting contact plans.
    """

    altitude_km: float = 550.0
    inclination_deg: float | None = None
    raan_deg: float = 0.0
    arg_latitude_deg: float = 0.0
    name: str = "SAT-1"

    @property
    def inclination(self) -> float:
        """Effective inclination in degrees."""
        if self.inclination_deg is None:
            return sun_synchronous_inclination(self.altitude_km)
        return self.inclination_deg

    def period(self) -> float:
        """Orbital period [s]."""
        return orbital_period(self.altitude_km)

    def propagate(self, t: np.ndarray) -> np.ndarray:
        """Position in the Earth-centred inertial frame.

        Parameters
        ----------
        t:
            Times since epoch [s], shape ``(n,)``.

        Returns
        -------
        np.ndarray
            Positions [km], shape ``(n, 3)``.
        """
        t = np.asarray(t, dtype=float)
        a = semi_major_axis(self.altitude_km)
        n = mean_motion(self.altitude_km)
        inc = np.radians(self.inclination)

        raan = np.radians(self.raan_deg) + nodal_regression_rate(
            self.altitude_km, self.inclination
        ) * t
        u = np.radians(self.arg_latitude_deg) + n * t

        cos_u, sin_u = np.cos(u), np.sin(u)
        cos_o, sin_o = np.cos(raan), np.sin(raan)
        cos_i, sin_i = np.cos(inc), np.sin(inc)

        x = a * (cos_u * cos_o - sin_u * sin_o * cos_i)
        y = a * (cos_u * sin_o + sin_u * cos_o * cos_i)
        z = a * (sin_u * sin_i)
        return np.column_stack([x, y, z])
