"""Checks on window detection, capacity and constellation construction."""

import numpy as np
import pytest

from leo_contact import (
    ContactWindow,
    GroundStation,
    Satellite,
    airtime,
    capacity,
    dwell_compliant,
    evaluate,
    find_windows,
    gaps,
    merge_windows,
    statistics,
    walker,
)
from leo_contact.capacity import TRAFFIC_REGIMES, daily_demand

SANTIAGO = GroundStation("Santiago", -33.45, -70.67, 0.57)


# --- airtime -----------------------------------------------------------------

def test_airtime_reproduces_prior_study_reference_case():
    """SF12, 50 bytes, 125 kHz -> 2.302 s, the value used in the energy paper."""
    assert airtime(12, 50) == pytest.approx(2.302, abs=0.002)


def test_reference_case_yields_260_packets_in_a_600s_pass():
    assert int(600 / airtime(12, 50)) == 260


def test_airtime_grows_with_spreading_factor():
    values = [airtime(sf, 20) for sf in range(7, 13)]
    assert all(a < b for a, b in zip(values, values[1:], strict=False))


def test_airtime_grows_with_payload():
    assert airtime(9, 50) > airtime(9, 20)


def test_airtime_rejects_invalid_spreading_factor():
    with pytest.raises(ValueError):
        airtime(6, 20)
    with pytest.raises(ValueError):
        airtime(13, 20)


@pytest.mark.parametrize("sf, compliant", [(7, True), (9, True), (10, True),
                                           (11, False), (12, False)])
def test_dwell_limit_excludes_the_two_highest_spreading_factors(sf, compliant):
    """Under an FCC-style regime (not applicable in Chile), SF11 and SF12
    exceed the 400 ms per-channel dwell limit for a 20-byte payload."""
    # Previous docstring (superseded): "Under the FCC-style regime applicable
    # in Chile, SF11 and SF12 exceed the 400 ms per-channel dwell limit..."
    assert dwell_compliant(sf, 20) is compliant


# --- windows -----------------------------------------------------------------

def test_single_satellite_gives_three_to_five_passes_per_day():
    sat = Satellite(altitude_km=550.0)
    windows = find_windows(sat, SANTIAGO, 10.0, duration_days=7.0, step_s=10.0)
    s = statistics(windows, 7.0)
    assert 3.0 <= s.passes_per_day <= 5.0


def test_pass_duration_below_analytical_maximum():
    """No pass can exceed the zenithal maximum, about 8 min at 550 km / 10 deg."""
    sat = Satellite(altitude_km=550.0)
    windows = find_windows(sat, SANTIAGO, 10.0, duration_days=7.0, step_s=5.0)
    assert max(w.duration_s for w in windows) / 60 < 8.5


def test_lower_elevation_threshold_gives_longer_passes():
    sat = Satellite(altitude_km=550.0)
    w10 = find_windows(sat, SANTIAGO, 10.0, 5.0, 10.0)
    w05 = find_windows(sat, SANTIAGO, 5.0, 5.0, 10.0)
    assert statistics(w05, 5.0).mean_duration_s > statistics(w10, 5.0).mean_duration_s


def test_max_elevation_never_below_threshold():
    sat = Satellite(altitude_km=550.0)
    for w in find_windows(sat, SANTIAGO, 10.0, 3.0, 10.0):
        assert w.max_elevation_deg >= 10.0


def test_windows_do_not_overlap_and_are_ordered():
    sat = Satellite(altitude_km=550.0)
    windows = find_windows(sat, SANTIAGO, 10.0, 5.0, 10.0)
    for a, b in zip(windows, windows[1:], strict=False):
        assert a.end_s < b.start_s


def test_merge_collapses_overlapping_windows():
    a = ContactWindow(0.0, 100.0, 30.0, "A")
    b = ContactWindow(50.0, 180.0, 40.0, "B")
    c = ContactWindow(500.0, 600.0, 20.0, "C")
    merged = merge_windows([a, b, c])
    assert len(merged) == 2
    assert merged[0].start_s == 0.0 and merged[0].end_s == 180.0
    assert merged[0].max_elevation_deg == 40.0


def test_merge_preserves_disjoint_windows():
    a = ContactWindow(0.0, 100.0, 30.0)
    b = ContactWindow(200.0, 300.0, 25.0)
    assert len(merge_windows([a, b])) == 2


def test_gaps_are_positive_and_one_fewer_than_windows():
    sat = Satellite(altitude_km=550.0)
    windows = find_windows(sat, SANTIAGO, 10.0, 5.0, 10.0)
    g = gaps(windows)
    assert len(g) == len(windows) - 1
    assert (g > 0).all()


def test_statistics_of_empty_plan_are_degenerate():
    s = statistics([], 7.0)
    assert s.n_windows == 0
    assert np.isinf(s.max_gap_s)


# --- constellation -----------------------------------------------------------

def test_walker_returns_the_requested_number_of_satellites():
    assert len(walker(4, 3)) == 12


def test_walker_rejects_degenerate_input():
    with pytest.raises(ValueError):
        walker(0, 3)


def test_walker_planes_have_distinct_raan():
    sats = walker(4, 2)
    raans = {round(s.raan_deg, 6) for s in sats}
    assert len(raans) == 4


def test_more_satellites_never_worsen_the_gap():
    small = evaluate(walker(1, 1), SANTIAGO, 10.0, 7.0, 20.0)
    large = evaluate(walker(4, 3), SANTIAGO, 10.0, 7.0, 20.0)
    assert large.stats.max_gap_s < small.stats.max_gap_s
    assert large.stats.passes_per_day > small.stats.passes_per_day


def test_single_satellite_gap_exceeds_the_deadline_by_an_order_of_magnitude():
    """The finding that motivates the constellation sizing: with one satellite
    the worst-case wait is hours against a deadline of 30 minutes."""
    result = evaluate(walker(1, 1), SANTIAGO, 10.0, 7.0, 10.0)
    assert result.stats.max_gap_s > 10 * 1800


# --- capacity ----------------------------------------------------------------

def test_capacity_scales_with_contact_time():
    windows = [ContactWindow(0.0, 600.0, 40.0)]
    one = capacity(windows, 1.0, 12, 50, demand_per_day=1000)
    two = capacity(windows * 2, 1.0, 12, 50, demand_per_day=1000)
    assert two.packets_per_day == pytest.approx(2 * one.packets_per_day, rel=0.01)


def test_reference_capacity_of_a_single_600s_pass():
    report = capacity([ContactWindow(0.0, 600.0, 40.0)], 1.0, 12, 50)
    assert report.packets_per_day == 260


def test_lower_spreading_factor_multiplies_capacity():
    windows = [ContactWindow(0.0, 600.0, 40.0)]
    sf12 = capacity(windows, 1.0, 12, 50)
    sf10 = capacity(windows, 1.0, 10, 50)
    assert sf10.packets_per_day > 3 * sf12.packets_per_day


def test_single_satellite_fails_the_disaster_regime():
    result = evaluate(walker(1, 1), SANTIAGO, 10.0, 7.0, 10.0)
    report = capacity(result.windows, 7.0, 12, 50, demand_per_day=1600)
    assert not report.meets_demand


def test_four_satellites_meet_the_disaster_regime():
    result = evaluate(walker(2, 2), SANTIAGO, 10.0, 7.0, 10.0)
    report = capacity(result.windows, 7.0, 12, 50, demand_per_day=1600)
    assert report.meets_demand


def test_daily_demand_of_each_regime():
    assert daily_demand("normal", 4.0) == 200
    assert daily_demand("emergency", 4.0) == 600
    assert daily_demand("disaster", 4.0) == 1600


def test_unknown_regime_raises():
    with pytest.raises(KeyError):
        daily_demand("apocalypse")


def test_regimes_are_ordered():
    assert (
        TRAFFIC_REGIMES["normal"]
        < TRAFFIC_REGIMES["emergency"]
        < TRAFFIC_REGIMES["disaster"]
    )
