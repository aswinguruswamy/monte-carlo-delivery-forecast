"""MCF-15 acceptance checks: Monte Carlo forecast (ADR 0002, Monte Carlo method)."""

from __future__ import annotations

import time
from datetime import date, timedelta

import numpy as np
import pytest

from mcf.forecast.montecarlo import (
    PERCENTILES,
    RUNS,
    SEED,
    MonteCarloError,
    case_generator,
    forecast_dates,
    percentile_days,
    simulate_days,
)

T = date(2020, 6, 30)


def rng(seed: int = 1) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


# --- fixed values from ADR 0002 ----------------------------------------------


def test_adr_constants():
    assert RUNS == 10_000
    assert SEED == 20261028
    assert PERCENTILES == (50, 85, 95)


def test_case_generator_is_the_adr_stream():
    expected = np.random.Generator(
        np.random.PCG64(np.random.SeedSequence([20261028, 3, T.toordinal(), 25]))
    ).integers(0, 1_000_000, 5)
    assert (case_generator(3, T, 25).integers(0, 1_000_000, 5) == expected).all()


def test_case_streams_differ_by_project_date_and_n():
    first = case_generator(0, T, 10).integers(0, 1_000_000, 5)
    for other in (case_generator(1, T, 10), case_generator(0, T + timedelta(14), 10)):
        assert (other.integers(0, 1_000_000, 5) != first).any()
    assert (case_generator(0, T, 25).integers(0, 1_000_000, 5) != first).any()


# --- simulate_days -----------------------------------------------------------


def test_constant_5_a_day_needs_exactly_10_days_for_50():
    days = simulate_days(np.full(84, 5), 50, rng())
    assert days.shape == (RUNS,)
    assert (days == 10).all()


def test_constant_throughput_rounds_up_to_the_day_that_reaches_n():
    assert (simulate_days(np.full(84, 3), 10, rng(), runs=200) == 4).all()  # 3, 6, 9, 12


def test_k_is_at_least_1():
    assert (simulate_days(np.full(84, 100), 1, rng(), runs=100) == 1).all()


def test_zero_days_still_count_as_days():
    # Half the days are 0, half are 2: N = 2 takes 1 day or more, never 0.
    counts = np.array([0, 2] * 42)
    days = simulate_days(counts, 2, rng(), runs=5000)
    assert days.min() == 1
    # P(first non-zero day is day k) = 0.5^k: the share of k = 1 is near 0.5.
    assert 0.47 < (days == 1).mean() < 0.53


def test_n_0_needs_0_days():
    assert (simulate_days(np.full(84, 1), 0, rng(), runs=10) == 0).all()


def test_rare_throughput_finishes():
    counts = np.zeros(84, dtype=int)
    counts[0] = 1  # 1 item in 84 days
    days = simulate_days(counts, 10, rng(), runs=500)
    assert days.min() >= 10
    assert 600 < days.mean() < 1100  # expected 840


def test_all_zero_history_is_no_forecast():
    with pytest.raises(MonteCarloError, match="no forecast"):
        simulate_days(np.zeros(84, dtype=int), 10, rng())


@pytest.mark.parametrize(
    "counts",
    [np.array([]), np.array([1, -1, 2]), np.array([1.5, 2.0]), np.array([[1, 2], [3, 4]])],
)
def test_bad_counts_are_an_error(counts):
    with pytest.raises(MonteCarloError):
        simulate_days(counts, 10, rng())


@pytest.mark.parametrize("n", [-1, 2.5, True])
def test_bad_n_is_an_error(n):
    with pytest.raises(MonteCarloError, match="N"):
        simulate_days(np.full(84, 1), n, rng())


def test_same_stream_gives_same_result():
    counts = np.array([0, 1, 3, 0, 2, 5, 0] * 12)
    a = simulate_days(counts, 50, case_generator(0, T, 50))
    b = simulate_days(counts, 50, case_generator(0, T, 50))
    assert (a == b).all()


def test_result_matches_a_plain_loop_with_the_same_draw_order():
    """The vector code gives the same k as a one-run-at-a-time loop on the same draws."""
    counts = np.array([0, 1, 3, 0, 2, 5, 0] * 12)
    days = simulate_days(counts, 25, rng(7), runs=300)
    # Rebuild the draws in the documented order: blocks of (runs, CHUNK_DAYS) indexes.
    from mcf.forecast.montecarlo import CHUNK_DAYS

    g = rng(7)
    blocks = [g.integers(0, len(counts), size=(300, CHUNK_DAYS)) for _ in range(4)]
    draws = np.concatenate(blocks, axis=1)
    for r in range(300):
        total, k = 0, 0
        while total < 25:
            total += counts[draws[r, k]]
            k += 1
        assert days[r] == k


# --- percentile_days ---------------------------------------------------------


def test_percentile_is_inverted_cdf():
    days = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert percentile_days(days, 50) == 5
    assert percentile_days(days, 85) == 9
    assert percentile_days(days, 95) == 10
    assert percentile_days(np.array([3, 3, 4]), 50) == 3


@pytest.mark.parametrize("p", [0, 101, -5])
def test_bad_percentile_is_an_error(p):
    with pytest.raises(MonteCarloError, match="percentile"):
        percentile_days(np.array([1, 2]), p)


# --- forecast_dates ----------------------------------------------------------


def test_forecast_dates_are_t_plus_k():
    dates = forecast_dates(T, np.full(84, 5), 50, rng())
    assert dates == {50: T + timedelta(10), 85: T + timedelta(10), 95: T + timedelta(10)}


def test_forecast_dates_are_in_order():
    counts = np.array([0, 1, 3, 0, 2, 5, 0] * 12)
    dates = forecast_dates(T, counts, 50, case_generator(0, T, 50))
    assert dates[50] <= dates[85] <= dates[95]
    assert dates[50] > T


def test_nfr1_10000_runs_are_fast():
    counts = np.zeros(84, dtype=int)
    counts[::7] = 1  # sparse: 12 items in 84 days, N = 50 needs about 350 days
    start = time.perf_counter()
    forecast_dates(T, counts, 50, case_generator(0, T, 50))
    assert time.perf_counter() - start < 120
