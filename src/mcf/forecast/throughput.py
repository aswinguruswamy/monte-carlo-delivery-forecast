"""Daily throughput of done value items (ADR 0002, Monte Carlo method step 1).

Only items with kind == "value" count (D04.1). Every calendar day in the range
stays in, including days with 0 items. An unknown kind or a value item with no
done day is an error, never a silent 0.

For many windows on one project (the back-test), call `done_ordinals` once and
then `counts_from_ordinals` for each window.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from mcf.data.types import BUG, NOT_COUNTED, VALUE

WINDOW_DAYS = 84  # ADR 0002: the 84 days from day t - 83 to day t
KINDS = {VALUE, BUG, NOT_COUNTED}
_EPOCH_ORDINAL = date(1970, 1, 1).toordinal()


class ThroughputError(ValueError):
    """Throughput cannot be calculated from this input."""


def window(t: date, days: int = WINDOW_DAYS) -> tuple[date, date]:
    """Return the first and last day of the history window that ends on day t."""
    if days < 1:
        raise ThroughputError(f"the window needs at least 1 day, got {days}")
    return t - timedelta(days=days - 1), t


def done_ordinals(issues: pd.DataFrame) -> np.ndarray:
    """Return the done day of each value item as a date ordinal (int64).

    The calendar day is the day as recorded (a time zone is not converted).
    """
    for column in ("kind", "done_day"):
        if column not in issues.columns:
            raise ThroughputError(f"the table has no {column!r} column; run sort_types first")

    bad_kind = ~issues["kind"].isin(KINDS)
    if bad_kind.any():
        row = issues[bad_kind].iloc[0]
        raise ThroughputError(f"unknown kind {row['kind']!r} for {row['issue_key']}")

    value_rows = issues[issues["kind"] == VALUE]
    days = pd.to_datetime(value_rows["done_day"], errors="coerce")
    if days.isna().any():
        key = value_rows.loc[days.isna(), "issue_key"].iloc[0]
        raise ThroughputError(f"value item {key} has no done day")
    if getattr(days.dt, "tz", None) is not None:
        days = days.dt.tz_localize(None)  # keep the recorded wall-clock day
    epoch_days = days.to_numpy().astype("datetime64[D]").astype(np.int64)
    return epoch_days + _EPOCH_ORDINAL


def counts_from_ordinals(ordinals: np.ndarray, start: date, end: date) -> np.ndarray:
    """Count ordinals for each day from start to end (both included)."""
    if start > end:
        raise ThroughputError(f"start day {start} is after end day {end}")
    n_days = (end - start).days + 1
    offsets = np.asarray(ordinals, dtype=np.int64) - start.toordinal()
    offsets = offsets[(offsets >= 0) & (offsets < n_days)]
    return np.bincount(offsets, minlength=n_days).astype(np.int64)


def daily_throughput(issues: pd.DataFrame, start: date, end: date) -> np.ndarray:
    """Count done value items for each day from start to end (both included)."""
    if start > end:
        raise ThroughputError(f"start day {start} is after end day {end}")
    return counts_from_ordinals(done_ordinals(issues), start, end)
