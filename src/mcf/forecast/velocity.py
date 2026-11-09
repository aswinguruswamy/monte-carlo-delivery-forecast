"""Velocity baseline (ADR 0002, Velocity method; D05).

Velocity = the story points of value items done in the 84-day window ending on
day t, divided by 6 two-week sprints. A sprint with 0 points counts as 0.
The velocity date = t + (points needed / velocity) x 14 days, rounded up to a
whole day. There is no rounding to the end of a sprint.

Velocity 0 means "no forecast" (ADR 0002, Cases with no forecast): an error,
never a date.

Day t must be a calendar date (`datetime.date`), not a date and time, so the
window holds whole days. Story points are checked on every value row, also rows
done after t: `load_issues` already rejects bad points, so a bad point here is a
bad input table.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from mcf.data.types import VALUE
from mcf.forecast.throughput import WINDOW_DAYS, ThroughputError, done_ordinals, window

SPRINT_DAYS = 14
SPRINTS = WINDOW_DAYS // SPRINT_DAYS  # 6
# Float error in points / velocity x 14 is about 1e-13 days for real data. Real
# results that are not whole days differ from a whole day by far more than 1e-9
# (points have at most a few decimals), so this never rounds a real fraction down.
_FLOAT_TOLERANCE = 1e-9


class VelocityError(ValueError):
    """Velocity or a velocity date cannot be calculated from this input."""


class VelocityTooFar(VelocityError):
    """The velocity date would be after the last calendar date (9999-12-31)."""


def _check_day(t: object) -> None:
    if isinstance(t, datetime) or not isinstance(t, date):
        raise VelocityError(f"day t must be a calendar date (datetime.date), got {t!r}")


def _number(value: object, name: str) -> float:
    if isinstance(value, bool | np.bool_) or not isinstance(value, int | float | np.number):
        raise VelocityError(f"bad {name} {value!r}")
    return float(value)


def window_velocity(issues: pd.DataFrame, t: date) -> float:
    """Return the story points per 2-week sprint in the 84-day window ending on day t."""
    _check_day(t)
    if "story_point" not in issues.columns:
        raise VelocityError("the table has no 'story_point' column; run sort_types first")
    try:
        ordinals = done_ordinals(issues)
    except ThroughputError as exc:
        raise VelocityError(str(exc)) from exc

    value_rows = issues[issues["kind"] == VALUE]
    points = np.empty(len(value_rows), dtype=float)
    for i, (key, point) in enumerate(
        zip(value_rows["issue_key"], value_rows["story_point"], strict=True)
    ):
        try:
            number = _number(point, "story point")
        except VelocityError:
            raise VelocityError(f"value item {key} has a bad story point {point!r}") from None
        if not math.isfinite(number) or number <= 0:
            raise VelocityError(f"value item {key} has a bad story point {point!r}")
        points[i] = number

    start, end = window(t)
    in_window = (ordinals >= start.toordinal()) & (ordinals <= end.toordinal())
    return float(points[in_window].sum()) / SPRINTS


def velocity_date(t: date, velocity: float, points_needed: float) -> date:
    """Return t + (points_needed / velocity) x 14 days, rounded up to a whole day."""
    _check_day(t)
    velocity = _number(velocity, "velocity")
    points_needed = _number(points_needed, "points needed")
    if not math.isfinite(velocity) or velocity < 0:
        raise VelocityError(f"bad velocity {velocity!r}")
    if velocity == 0:
        raise VelocityError("no forecast: velocity is 0 (no value item done in the window)")
    if not math.isfinite(points_needed) or points_needed < 0:
        raise VelocityError(f"bad points needed {points_needed!r}")

    exact = points_needed / velocity * SPRINT_DAYS
    if not math.isfinite(exact):
        raise VelocityTooFar(f"no date: {points_needed} points at velocity {velocity} is too far")
    nearest = round(exact)
    days = nearest if abs(exact - nearest) <= _FLOAT_TOLERANCE else math.ceil(exact)
    try:
        return t + timedelta(days=days)
    except OverflowError as exc:
        raise VelocityTooFar(f"no date: {days} days after {t} is past the last date") from exc
