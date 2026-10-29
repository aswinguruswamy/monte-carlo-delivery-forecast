"""Velocity baseline (ADR 0002, Velocity method; D05).

Velocity = the story points of value items done in the 84-day window ending on
day t, divided by 6 two-week sprints. A sprint with 0 points counts as 0.
The velocity date = t + (points needed / velocity) x 14 days, rounded up to a
whole day. There is no rounding to the end of a sprint.

Velocity 0 means "no forecast" (ADR 0002, Cases with no forecast): an error,
never a date.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import pandas as pd

from mcf.data.types import VALUE
from mcf.forecast.throughput import KINDS, WINDOW_DAYS, window

SPRINT_DAYS = 14
SPRINTS = WINDOW_DAYS // SPRINT_DAYS  # 6
_FLOAT_TOLERANCE = 1e-9  # in days; float error is far smaller, real data steps are 1 day


class VelocityError(ValueError):
    """Velocity or a velocity date cannot be calculated from this input."""


def window_velocity(issues: pd.DataFrame, t: date) -> float:
    """Return the story points per 2-week sprint in the 84-day window ending on day t."""
    for column in ("kind", "done_day", "story_point"):
        if column not in issues.columns:
            raise VelocityError(f"the table has no {column!r} column; run sort_types first")

    bad_kind = ~issues["kind"].isin(KINDS)
    if bad_kind.any():
        raise VelocityError(f"unknown kind {issues.loc[bad_kind, 'kind'].iloc[0]!r}")

    value_rows = issues[issues["kind"] == VALUE]
    days = pd.to_datetime(value_rows["done_day"], errors="coerce")
    if days.isna().any():
        key = value_rows.loc[days.isna(), "issue_key"].iloc[0]
        raise VelocityError(f"value item {key} has no done day")
    if getattr(days.dt, "tz", None) is not None:
        days = days.dt.tz_localize(None)  # keep the recorded wall-clock day
    days = days.dt.normalize()

    points = value_rows["story_point"].astype(float)
    if points.isna().any() or not points.map(math.isfinite).all() or (points <= 0).any():
        key = value_rows.loc[~(points > 0) | ~points.map(math.isfinite), "issue_key"].iloc[0]
        raise VelocityError(f"value item {key} has a bad story point")

    start, end = window(t)
    in_window = (days >= pd.Timestamp(start)) & (days <= pd.Timestamp(end))
    return float(points[in_window].sum()) / SPRINTS


def velocity_date(t: date, velocity: float, points_needed: float) -> date:
    """Return t + (points_needed / velocity) x 14 days, rounded up to a whole day."""
    if not math.isfinite(velocity) or velocity < 0:
        raise VelocityError(f"bad velocity {velocity!r}")
    if velocity == 0:
        raise VelocityError("no forecast: velocity is 0 (no value item done in the window)")
    if not math.isfinite(points_needed) or points_needed < 0:
        raise VelocityError(f"bad points needed {points_needed!r}")

    exact = points_needed / velocity * SPRINT_DAYS
    nearest = round(exact)
    days = nearest if abs(exact - nearest) <= _FLOAT_TOLERANCE else math.ceil(exact)
    return t + timedelta(days=days)
