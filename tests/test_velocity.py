"""MCF-14 acceptance checks: velocity baseline (ADR 0002, Velocity method; D05)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from mcf.data.types import BUG, NOT_COUNTED, VALUE
from mcf.forecast.velocity import VelocityError, velocity_date, window_velocity

T = date(2020, 6, 30)


def items(rows: list[tuple[int, str, float]]) -> pd.DataFrame:
    """rows: (days before t, kind, story points). 0 = day t."""
    return pd.DataFrame(
        {
            "issue_key": [f"P-{i}" for i in range(len(rows))],
            "type": ["Story" if k == VALUE else "Bug" for _, k, _ in rows],
            "done_day": [T - timedelta(days=d) for d, _, _ in rows],
            "story_point": [p for _, _, p in rows],
            "kind": [k for _, k, _ in rows],
        }
    )


# --- window_velocity ---------------------------------------------------------


def test_velocity_is_window_points_divided_by_6_sprints():
    # 60 points in the window -> 10 points per 2-week sprint (hand calculation).
    df = items([(0, VALUE, 20.0), (40, VALUE, 25.0), (83, VALUE, 15.0)])
    assert window_velocity(df, T) == pytest.approx(10.0)


def test_only_days_t_minus_83_to_t_count():
    df = items([(-1, VALUE, 100.0), (0, VALUE, 6.0), (83, VALUE, 6.0), (84, VALUE, 100.0)])
    assert window_velocity(df, T) == pytest.approx(2.0)  # (6 + 6) / 6


def test_only_value_items_count():
    df = items([(1, VALUE, 12.0), (1, BUG, 50.0), (2, NOT_COUNTED, 50.0)])
    assert window_velocity(df, T) == pytest.approx(2.0)


def test_empty_sprints_count_as_zero():
    # All points in one sprint: the other 5 sprints still divide.
    df = items([(0, VALUE, 30.0)])
    assert window_velocity(df, T) == pytest.approx(5.0)


def test_no_value_item_in_window_gives_velocity_zero():
    assert window_velocity(items([(90, VALUE, 5.0)]), T) == 0.0


def test_missing_columns_are_an_error():
    df = items([(0, VALUE, 1.0)])
    for column in ("kind", "done_day", "story_point"):
        with pytest.raises(VelocityError, match=column):
            window_velocity(df.drop(columns=column), T)


# --- velocity_date -----------------------------------------------------------


def test_date_matches_a_hand_calculation():
    # 25 points / 10 per sprint = 2.5 sprints = 35 days.
    assert velocity_date(T, 10.0, 25.0) == T + timedelta(days=35)


def test_date_rounds_up_to_a_whole_day():
    # 7 / 10 * 14 = 9.8 days -> 10 days.
    assert velocity_date(T, 10.0, 7.0) == T + timedelta(days=10)


def test_exact_multiples_are_not_pushed_late_by_float_error():
    # 0.1 + 0.2 style error: 3 sprints of 0.3 points each, velocity 0.1 + 0.2.
    assert velocity_date(T, 0.1 + 0.2, 0.9) == T + timedelta(days=42)
    # 2.8 points / 1.4 per sprint = exactly 2 sprints = 28 days.
    assert velocity_date(T, 1.4, 2.8) == T + timedelta(days=28)


def test_zero_points_needed_is_day_t():
    assert velocity_date(T, 10.0, 0.0) == T


def test_velocity_zero_is_no_forecast():
    with pytest.raises(VelocityError, match="no forecast: velocity is 0"):
        velocity_date(T, 0.0, 10.0)


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
def test_bad_points_needed_is_an_error(bad):
    with pytest.raises(VelocityError, match="points needed"):
        velocity_date(T, 10.0, bad)


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
def test_bad_velocity_is_an_error(bad):
    with pytest.raises(VelocityError, match="velocity"):
        velocity_date(T, bad, 10.0)


# --- review fixes (PR #14) ---------------------------------------------------


@pytest.mark.parametrize("t", [pd.Timestamp("2020-06-30 12:00"), datetime(2020, 6, 30, 12)])
def test_datetime_t_is_an_error_not_a_shifted_window(t):
    df = items([(83, VALUE, 6.0)])
    with pytest.raises(VelocityError, match="calendar date"):
        window_velocity(df, t)
    with pytest.raises(VelocityError, match="calendar date"):
        velocity_date(t, 1.0, 1.0)


def test_float_tolerance_keeps_an_exact_day():
    # 6.5 points in the window, 32.5 needed: exactly 30 sprints = 420 days.
    # Plain ceil gives 421 (420.00000000000006).
    assert velocity_date(T, 6.5 / 6, 32.5) == T + timedelta(days=420)


def test_a_real_fraction_still_rounds_up():
    assert velocity_date(T, 3.0, 1.0) == T + timedelta(days=5)  # 4.67 -> 5


def test_unknown_kind_is_an_error():
    df = items([(0, VALUE, 1.0)]).assign(kind="vaule")
    with pytest.raises(VelocityError, match="unknown kind"):
        window_velocity(df, T)


@pytest.mark.parametrize("bad", [None, "not a date"])
def test_value_item_with_no_done_day_is_an_error(bad):
    df = items([(0, VALUE, 1.0)])
    df["done_day"] = [bad]
    with pytest.raises(VelocityError, match="done day"):
        window_velocity(df, T)


@pytest.mark.parametrize("bad", [0.0, -2.0, float("nan"), float("inf"), "abc", True])
def test_bad_story_point_is_an_error(bad):
    df = items([(0, VALUE, 1.0)]).astype({"story_point": object})
    df.loc[0, "story_point"] = bad
    with pytest.raises(VelocityError, match="story point"):
        window_velocity(df, T)


def test_timezone_done_day_keeps_the_recorded_day():
    df = items([(83, VALUE, 6.0)])
    df["done_day"] = pd.to_datetime(["2020-04-08 23:30"]).tz_localize("America/Toronto")
    assert window_velocity(df, T) == pytest.approx(1.0)


def test_missing_issue_key_column_is_an_error():
    with pytest.raises(VelocityError, match="issue_key"):
        window_velocity(items([(0, VALUE, 1.0)]).drop(columns="issue_key"), T)


@pytest.mark.parametrize("velocity, needed", [(1e-308, 1e10), (1.0, 1e305)])
def test_overflow_is_a_velocity_error(velocity, needed):
    with pytest.raises(VelocityError):
        velocity_date(T, velocity, needed)


@pytest.mark.parametrize("velocity, needed", [(True, 1.0), (1.0, True)])
def test_bool_inputs_are_an_error(velocity, needed):
    with pytest.raises(VelocityError):
        velocity_date(T, velocity, needed)
