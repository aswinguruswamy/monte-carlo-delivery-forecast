"""MCF-13 acceptance checks: daily throughput of value items (ADR 0002)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from mcf.data.types import BUG, NOT_COUNTED, VALUE
from mcf.forecast.throughput import ThroughputError, daily_throughput, window

D = date(2020, 3, 1)


def items(rows: list[tuple[int, str]]) -> pd.DataFrame:
    """rows: (day offset from D, kind)."""
    return pd.DataFrame(
        {
            "issue_key": [f"P-{i}" for i in range(len(rows))],
            "type": ["Story" if k == VALUE else "Bug" for _, k in rows],
            "done_day": [D + timedelta(days=o) for o, _ in rows],
            "story_point": [1.0] * len(rows),
            "kind": [k for _, k in rows],
        }
    )


def test_daily_counts_match_a_hand_calculation():
    df = items([(0, VALUE), (0, VALUE), (2, VALUE), (4, VALUE), (4, VALUE), (4, VALUE)])
    counts = daily_throughput(df, D, D + timedelta(days=4))
    assert counts.tolist() == [2, 0, 1, 0, 3]
    assert counts.dtype == np.int64


def test_days_with_no_items_stay_in_with_zero():
    counts = daily_throughput(items([(0, VALUE)]), D, D + timedelta(days=6))
    assert len(counts) == 7
    assert counts.tolist() == [1, 0, 0, 0, 0, 0, 0]


def test_bugs_and_epics_are_not_counted():
    df = items([(0, VALUE), (0, BUG), (1, NOT_COUNTED), (1, BUG)])
    assert daily_throughput(df, D, D + timedelta(days=1)).tolist() == [1, 0]


def test_items_outside_the_range_are_not_counted():
    df = items([(-1, VALUE), (0, VALUE), (3, VALUE), (4, VALUE)])
    assert daily_throughput(df, D, D + timedelta(days=3)).tolist() == [1, 0, 0, 1]


def test_one_day_range_and_empty_table():
    assert daily_throughput(items([(0, VALUE)]), D, D).tolist() == [1]
    assert daily_throughput(items([]), D, D + timedelta(days=2)).tolist() == [0, 0, 0]


def test_start_after_end_is_an_error():
    with pytest.raises(ThroughputError, match="start day 2020-03-02 is after end day 2020-03-01"):
        daily_throughput(items([]), D + timedelta(days=1), D)


def test_table_without_kind_column_is_an_error():
    with pytest.raises(ThroughputError, match="sort_types"):
        daily_throughput(items([(0, VALUE)]).drop(columns="kind"), D, D)


def test_window_is_84_days_from_t_minus_83_to_t():
    t = date(2020, 6, 30)
    start, end = window(t)
    assert (start, end) == (t - timedelta(days=83), t)
    counts = daily_throughput(items([]), start, end)
    assert len(counts) == 84


def test_window_counts_the_first_and_last_day():
    t = D + timedelta(days=83)
    df = items([(-1, VALUE), (0, VALUE), (83, VALUE), (84, VALUE)])
    counts = daily_throughput(df, *window(t))
    assert counts.sum() == 2 and counts[0] == 1 and counts[-1] == 1


def test_window_needs_at_least_one_day():
    with pytest.raises(ThroughputError, match="at least 1 day"):
        window(D, days=0)


# --- review findings ---------------------------------------------------------


@pytest.mark.parametrize("bad_kind", ["Value", None, float("nan"), "story"])
def test_unknown_kind_is_an_error_not_a_silent_zero(bad_kind):
    df = items([(0, VALUE), (1, VALUE)])
    df.loc[1, "kind"] = bad_kind
    with pytest.raises(ThroughputError, match=r"unknown kind .* P-1"):
        daily_throughput(df, D, D + timedelta(days=1))


@pytest.mark.parametrize("missing", [pd.NaT, None])
def test_value_item_with_no_done_day_is_a_clear_error(missing):
    df = items([(0, VALUE), (1, VALUE)]).astype({"done_day": object})
    df.loc[1, "done_day"] = missing
    with pytest.raises(ThroughputError, match=r"value item P-1 has no done day"):
        daily_throughput(df, D, D + timedelta(days=1))


def test_table_without_done_day_column_is_an_error():
    with pytest.raises(ThroughputError, match="done_day"):
        daily_throughput(items([(0, VALUE)]).drop(columns="done_day"), D, D)


@pytest.mark.parametrize(
    "as_type",
    [
        lambda d: pd.Timestamp(d),
        lambda d: pd.Timestamp(d).replace(hour=23, minute=59),
        lambda d: pd.Timestamp(d).replace(hour=23).tz_localize("America/Toronto"),
        lambda d: __import__("datetime").datetime(d.year, d.month, d.day, 10, 0),
    ],
)
def test_datetime_like_done_days_count_on_their_calendar_day(as_type):
    df = items([(0, VALUE), (2, VALUE)])
    df["done_day"] = [as_type(d) for d in df["done_day"]]
    assert daily_throughput(df, D, D + timedelta(days=2)).tolist() == [1, 0, 1]


def test_precomputed_ordinals_give_the_same_counts():
    from mcf.forecast.throughput import counts_from_ordinals, done_ordinals

    df = items([(0, VALUE), (0, VALUE), (2, BUG), (3, VALUE)])
    ords = done_ordinals(df)
    start, end = D, D + timedelta(days=3)
    assert (
        counts_from_ordinals(ords, start, end).tolist() == daily_throughput(df, start, end).tolist()
    )


# --- review fixes (PR #14) ---------------------------------------------------


def test_missing_issue_key_column_is_an_error():
    with pytest.raises(ThroughputError, match="issue_key"):
        daily_throughput(items([(0, VALUE)]).drop(columns="issue_key"), D, D)


def test_mixed_timezone_days_are_a_clear_error():
    df = items([(0, VALUE), (1, VALUE)]).astype({"done_day": object})
    df.loc[0, "done_day"] = pd.Timestamp("2020-03-01 10:00", tz="UTC")
    df.loc[1, "done_day"] = pd.Timestamp("2020-03-02 10:00")
    with pytest.raises(ThroughputError, match="done day"):
        daily_throughput(df, D, D + timedelta(days=1))
