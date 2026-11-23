"""One forecast from daily counts – the function that SRG calls (MCF v2 spec R6).

The caller passes the daily counts of done items for consecutive days that end on
day t; it also chooses which ticket types count (R6.5). The method is the v1 method
(ADR 0002): the last 84 days, days with 0 stay in, 10,000 runs, the same random
stream as the command line for the same seed (R6.2, R6.3). This module adds the
chance to finish by a charter date (R1) and the thin-history warning (R2).
Code writes every number and date here; nothing is AI text.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from mcf.forecast.montecarlo import RUNS, SEED, MonteCarloError, dates_from_days, simulate_days
from mcf.forecast.throughput import WINDOW_DAYS

THIN_HISTORY_ITEMS = 30  # R2: fewer than this many done items in the window gives a warning


@dataclass(frozen=True)
class TeamForecast:
    t: date
    backlog: int
    window_start: date
    window_days: int
    items_done: int
    mc50: date
    mc85: date
    mc95: date
    charter: date | None
    chance_runs: int | None  # runs that finish by the charter date
    runs: int
    warnings: tuple[str, ...]

    @property
    def chance_percent(self) -> int | None:
        """The chance as a whole percent, rounded down (spec §4)."""
        if self.chance_runs is None:
            return None
        return self.chance_runs * 100 // self.runs


def chance_label(hits: int, runs: int) -> str:
    """'100%' only when every run finishes; 'under 1%' when some, but fewer than 1%, do."""
    percent = hits * 100 // runs
    if percent == 0 and hits > 0:
        return "under 1%"
    return f"{percent}%"


def chance_text(forecast: TeamForecast) -> str:
    if forecast.chance_runs is None or forecast.charter is None:
        raise ValueError("this forecast has no charter date")
    label = chance_label(forecast.chance_runs, forecast.runs)
    return f"{label} chance to finish by {forecast.charter.isoformat()}"


def thin_history_warning(items_done: int) -> str | None:
    if items_done < THIN_HISTORY_ITEMS:
        return f"Only {items_done} items finished in the last 12 weeks. Treat the dates with care."
    return None


def _window(daily_counts: Sequence[int] | np.ndarray) -> np.ndarray:
    counts = np.asarray(daily_counts)
    if counts.ndim != 1 or counts.size == 0:
        raise MonteCarloError("daily counts must be a non-empty list of days")
    if counts.dtype.kind not in "iu":
        raise MonteCarloError(f"daily counts must be whole numbers, got {counts.dtype}")
    if (counts < 0).any():
        raise MonteCarloError("a daily count is below 0")
    counts = counts.astype(np.int64)[-WINDOW_DAYS:]
    if counts.size < WINDOW_DAYS:  # v1: days before the first item count as 0
        counts = np.concatenate([np.zeros(WINDOW_DAYS - counts.size, dtype=np.int64), counts])
    if not counts.any():
        raise MonteCarloError("no forecast: no value item was done in the history window")
    return counts


def forecast_from_counts(
    daily_counts: Sequence[int] | np.ndarray,
    t: date,
    backlog: int,
    *,
    seed: int = SEED,
    charter: date | None = None,
) -> TeamForecast:
    """Return the 50/85/95% dates, the chance by the charter date and the warnings."""
    if isinstance(backlog, bool) or not isinstance(backlog, (int, np.integer)) or backlog < 1:
        raise MonteCarloError(f"N must be a whole number of 1 or more, got {backlog!r}")
    if charter is not None and charter <= t:
        raise MonteCarloError(f"The charter date must be after {t.isoformat()}.")
    counts = _window(daily_counts)
    rng = np.random.Generator(np.random.PCG64(seed))  # the same stream as the command line
    days = simulate_days(counts, int(backlog), rng)
    dates = dates_from_days(t, days)
    chance_runs = None
    if charter is not None:
        chance_runs = int((days <= (charter - t).days).sum())
    items_done = int(counts.sum())
    warning = thin_history_warning(items_done)
    return TeamForecast(
        t=t,
        backlog=int(backlog),
        window_start=t - timedelta(days=WINDOW_DAYS - 1),
        window_days=WINDOW_DAYS,
        items_done=items_done,
        mc50=dates[50],
        mc85=dates[85],
        mc95=dates[95],
        charter=charter,
        chance_runs=chance_runs,
        runs=RUNS,
        warnings=(warning,) if warning else (),
    )
