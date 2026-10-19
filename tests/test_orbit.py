"""Analytical cross-checks on the propagator."""

import numpy as np
import pytest

from leo_contact.geometry import GroundStation, max_central_angle
from leo_contact.orbit import (
    Satellite,
    orbital_period,
    semi_major_axis,
    sun_synchronous_inclination,
)


def test_period_matches_kepler():
    # Kepler's third law, computed independently of the module.
    a = 6378.137 + 550.0
    expected = 2 * np.pi * np.sqrt(a**3 / 398600.4418)
    assert orbital_period(550.0) == pytest.approx(expected, rel=1e-12)


def test_period_is_about_95_minutes_at_550km():
    assert orbital_period(550.0) / 60 == pytest.approx(95.6, abs=0.3)


@pytest.mark.parametrize(
    "altitude, expected",
    [(500.0, 97.40), (550.0, 97.59), (600.0, 97.79), (800.0, 98.60)],
)
def test_sun_synchronous_inclination_matches_tables(altitude, expected):
    assert sun_synchronous_inclination(altitude) == pytest.approx(expected, abs=0.05)


def test_sun_synchronous_is_retrograde():
    assert sun_synchronous_inclination(550.0) > 90.0


def test_no_sun_synchronous_orbit_at_extreme_altitude():
    with pytest.raises(ValueError):
        sun_synchronous_inclination(20_000.0)


def test_orbit_radius_is_constant():
    sat = Satellite(altitude_km=550.0)
    t = np.linspace(0, 3 * sat.period(), 500)
    r = np.linalg.norm(sat.propagate(t), axis=1)
    assert np.allclose(r, semi_major_axis(550.0), rtol=1e-12)


def test_position_nearly_returns_after_one_period():
    """After one revolution the satellite returns to within the J2 drift.

    The residual is the nodal regression accumulated over one period, about
    8 km at 550 km altitude, i.e. roughly 0.1 percent of the orbital radius.
    """
    sat = Satellite(altitude_km=550.0, raan_deg=0.0, arg_latitude_deg=0.0)
    r = sat.propagate(np.array([0.0, sat.period()]))
    residual = np.linalg.norm(r[0] - r[1])
    assert 1.0 < residual < 20.0
    assert residual / semi_major_axis(550.0) < 3e-3


def test_max_latitude_bounded_by_inclination():
    sat = Satellite(altitude_km=550.0)
    t = np.linspace(0, 2 * sat.period(), 2000)
    r = sat.propagate(t)
    lat = np.degrees(np.arcsin(r[:, 2] / np.linalg.norm(r, axis=1)))
    bound = min(sat.inclination, 180 - sat.inclination)
    assert lat.max() <= bound + 0.1
    assert lat.min() >= -bound - 0.1


def test_central_angle_decreases_with_elevation():
    assert max_central_angle(550.0, 5.0) > max_central_angle(550.0, 10.0)


def test_central_angle_matches_hand_calculation():
    # arccos(Re/a * cos(10 deg)) - 10 deg, with Re = 6378.137, a = 6928.137
    # gives arccos(0.906622) - 10 deg = 24.957 - 10 = 14.957 deg.
    assert max_central_angle(550.0, 10.0) == pytest.approx(14.957, abs=0.01)


def test_elevation_at_subsatellite_point_is_ninety_degrees():
    """A satellite directly overhead must give 90 degrees of elevation."""
    sat = Satellite(altitude_km=550.0, inclination_deg=0.0, arg_latitude_deg=0.0)
    t = np.array([0.0])
    r = sat.propagate(t)
    # At t = 0 with zero inclination and zero RAAN the satellite sits above
    # the equator at zero longitude.
    station = GroundStation("subsat", 0.0, 0.0)
    assert station.elevation(r, t)[0] == pytest.approx(90.0, abs=0.2)


def test_elevation_is_negative_on_the_far_side():
    sat = Satellite(altitude_km=550.0, inclination_deg=0.0, arg_latitude_deg=180.0)
    t = np.array([0.0])
    station = GroundStation("antipode", 0.0, 0.0)
    assert station.elevation(sat.propagate(t), t)[0] < -50.0
