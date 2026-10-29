"""Monte Carlo forecast (ADR 0002, Monte Carlo method).

One run picks days at random (with replacement) from the daily counts of done
value items, and adds them up day by day. The run's result is the number of
days k (k >= 1) at which the total first reaches N. The p% result is the
inverted-CDF percentile of 10,000 runs, and the p% date is t + k days.

Draw order (fixed, so a result can be checked by hand): the generator gives
blocks of `CHUNK_DAYS` day indexes for all runs at once, shape (runs,
CHUNK_DAYS), block after block. Run r uses row r of each block in turn. Blocks
are drawn for every run, also for runs that are already done.

The caller passes the daily counts of the window (84 days in the back-test,
ADR 0002); this module accepts any non-empty length.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

RUNS = 10_000
SEED = 20261028
PERCENTILES = (50, 85, 95)
CHUNK_DAYS = 64
MAX_DAYS = 100_000  # about 274 years: a safety stop, never a real forecast
_MAX_COUNT = 2**40  # a guard against wrap-around; real daily counts are far smaller


class MonteCarloError(ValueError):
    """A Monte Carlo forecast cannot be calculated from this input."""


def case_generator(project: int, t: date, n: int) -> np.random.Generator:
    """Return the random stream of one back-test case (ADR 0002, Back-test)."""
    return np.random.Generator(
        np.random.PCG64(np.random.SeedSequence([SEED, project, t.toordinal(), n]))
    )


def _check_counts(daily_counts: np.ndarray) -> np.ndarray:
    counts = np.asarray(daily_counts)
    if counts.ndim != 1 or counts.size == 0:
        raise MonteCarloError("daily counts must be a non-empty list of days")
    if counts.dtype.kind not in "iu":
        raise MonteCarloError(f"daily counts must be whole numbers, got {counts.dtype}")
    if (counts < 0).any():
        raise MonteCarloError("a daily count is below 0")
    if (counts > _MAX_COUNT).any():
        raise MonteCarloError(f"a daily count is above {_MAX_COUNT}")
    if not counts.any():
        raise MonteCarloError("no forecast: no value item was done in the history window")
    return counts.astype(np.int64)


def simulate_days(
    daily_counts: np.ndarray, n: int, rng: np.random.Generator, runs: int = RUNS
) -> np.ndarray:
    """Return, for each run, the number of days needed to finish n items."""
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 0:
        raise MonteCarloError(f"N must be a whole number of 0 or more, got {n!r}")
    if isinstance(runs, bool) or not isinstance(runs, (int, np.integer)) or runs < 1:
        raise MonteCarloError(f"runs must be a whole number of 1 or more, got {runs!r}")
    counts = _check_counts(daily_counts)
    if n == 0:
        return np.zeros(runs, dtype=np.int64)

    days = np.zeros(runs, dtype=np.int64)  # 0 = not done yet
    totals = np.zeros(runs, dtype=np.int64)
    used = 0
    while True:
        block = counts[rng.integers(0, counts.size, size=(runs, CHUNK_DAYS))]
        open_runs = np.flatnonzero(days == 0)
        running = totals[open_runs, None] + np.cumsum(block[open_runs], axis=1)
        reached = running >= n
        hit = reached.any(axis=1)
        days[open_runs[hit]] = used + reached[hit].argmax(axis=1) + 1
        totals[open_runs] = running[:, -1]
        used += CHUNK_DAYS
        if days.max() > MAX_DAYS or (not hit.all() and used >= MAX_DAYS):
            raise MonteCarloError(f"no result within {MAX_DAYS} days; throughput is too low")
        if hit.all():
            return days


def percentile_days(days: np.ndarray, p: float) -> int:
    """Return the smallest k such that at least p% of the runs are <= k."""
    if not 0 < p <= 100:
        raise MonteCarloError(f"percentile must be above 0 and at most 100, got {p}")
    if np.asarray(days).size == 0:
        raise MonteCarloError("no runs to take a percentile of")
    return int(np.quantile(np.asarray(days), p / 100, method="inverted_cdf"))


def forecast_dates(
    t: date,
    daily_counts: np.ndarray,
    n: int,
    rng: np.random.Generator,
    runs: int = RUNS,
    percentiles: tuple[int, ...] = PERCENTILES,
) -> dict[int, date]:
    """Return the p% date (t + k days) for each percentile."""
    days = simulate_days(daily_counts, n, rng, runs)
    try:
        return {p: t + timedelta(days=percentile_days(days, p)) for p in percentiles}
    except OverflowError as exc:
        raise MonteCarloError(
            f"no date: the forecast falls after the last calendar date ({exc})"
        ) from exc
