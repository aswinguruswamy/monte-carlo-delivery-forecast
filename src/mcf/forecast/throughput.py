"""Daily throughput of done value items (ADR 0002, Monte Carlo method step 1).

Only items with kind == "value" count (D04.1). Every calendar day in the range
stays in, including days with 0 items.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from mcf.data.types import VALUE

WINDOW_DAYS = 84  # ADR 0002: the 84 days from day t - 83 to day t


class ThroughputError(ValueError):
    """Throughput cannot be calculated from this input."""


def window(t: date, days: int = WINDOW_DAYS) -> tuple[date, date]:
    """Return the first and last day of the history window that ends on day t."""
    if days < 1:
        raise ThroughputError(f"the window needs at least 1 day, got {days}")
    return t - timedelta(days=days - 1), t


def daily_throughput(issues: pd.DataFrame, start: date, end: date) -> np.ndarray:
    """Count done value items for each day from start to end (both included)."""
    if start > end:
        raise ThroughputError(f"start day {start} is after end day {end}")
    if "kind" not in issues.columns:
        raise ThroughputError("the table has no 'kind' column; run sort_types first")

    n_days = (end - start).days + 1
    days = issues.loc[issues["kind"] == VALUE, "done_day"]
    offsets = np.fromiter((d.toordinal() for d in days), dtype=np.int64, count=len(days))
    offsets -= start.toordinal()
    offsets = offsets[(offsets >= 0) & (offsets < n_days)]
    return np.bincount(offsets, minlength=n_days).astype(np.int64)
