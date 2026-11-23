"""MCF v2 spec R6 (function for SRG), R1 (charter-date chance), R2 (thin-history warning)."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from mcf import cli
from mcf.forecast.api import TeamForecast, chance_text, forecast_from_counts
from mcf.forecast.montecarlo import MonteCarloError

T = date(2026, 12, 1)
ONE_A_DAY = [1] * 84  # Example A: every run needs exactly N days
ROOT = Path(__file__).resolve().parent.parent


def test_example_a_dates_are_exact():  # AC1
    f = forecast_from_counts(ONE_A_DAY, T, 20)
    assert isinstance(f, TeamForecast)
    assert (f.mc50, f.mc85, f.mc95) == (date(2026, 12, 21),) * 3
    assert (f.window_start, f.window_days, f.items_done) == (T - timedelta(days=83), 84, 84)


def test_chance_is_100_when_every_run_finishes_by_the_charter_date():  # AC2
    f = forecast_from_counts(ONE_A_DAY, T, 20, charter=date(2026, 12, 21))
    assert f.chance_percent == 100
    assert chance_text(f) == "100% chance to finish by 2026-12-21"


def test_chance_is_0_one_day_earlier():  # AC3
    f = forecast_from_counts(ONE_A_DAY, T, 20, charter=date(2026, 12, 20))
    assert f.chance_percent == 0
    assert chance_text(f) == "0% chance to finish by 2026-12-20"


@pytest.mark.parametrize(
    ("hits", "text"), [(9_960, "99%"), (50, "under 1%"), (10_000, "100%"), (0, "0%")]
)
def test_chance_is_rounded_down(hits, text):  # AC4, AC5
    from mcf.forecast.api import chance_label

    assert chance_label(hits, 10_000) == text


def test_charter_date_must_be_after_day_t():  # AC6
    with pytest.raises(MonteCarloError, match=r"^The charter date must be after 2026-12-01\.$"):
        forecast_from_counts(ONE_A_DAY, T, 20, charter=T)


def _random_cases(n: int, max_count: int, max_backlog: int):
    rng = np.random.default_rng(20261123)  # fixed seed (CLAUDE.md test rule 4)
    for _ in range(n):
        counts = rng.integers(0, max_count + 1, size=84)
        counts[rng.integers(0, 84)] += 1  # at least one done item
        yield counts, int(rng.integers(1, max_backlog + 1)), int(rng.integers(0, 2**32))


def test_chance_by_the_85_percent_date_is_at_least_85():  # AC7
    for counts, backlog, seed in _random_cases(25, 4, 60):
        plain = forecast_from_counts(counts, T, backlog, seed=seed)
        f = forecast_from_counts(counts, T, backlog, seed=seed, charter=plain.mc85)
        assert f.chance_percent >= 85


def test_warning_below_30_items():  # AC8
    counts = [0] * 84
    for i in range(29):
        counts[i * 2] = 1
    f = forecast_from_counts(counts, T, 5)
    assert f.warnings == (
        "Only 29 items finished in the last 12 weeks. Treat the dates with care.",
    )


def test_no_warning_at_30_items():  # AC9
    counts = [0] * 84
    for i in range(30):
        counts[i * 2] = 1
    assert forecast_from_counts(counts, T, 5).warnings == ()


def test_function_equals_the_command_line_for_the_sample_file():  # AC14
    args = argparse.Namespace(
        file=str(ROOT / "examples" / "sample_team.csv"),
        backlog=40,
        as_of=None,
        seed=20261028,
        backlog_points=None,
    )
    facts, load, _ = cli.compute_full(args)
    from mcf.data.load import load_issues
    from mcf.data.types import sort_types
    from mcf.forecast.throughput import counts_from_ordinals, done_ordinals

    issues, _ = load_issues(args.file, open_items=True)
    issues, _ = sort_types(issues, load.file, points_required=False)
    ordinals = done_ordinals(issues)
    counts = counts_from_ordinals(ordinals, facts.t - timedelta(days=200), facts.t)
    f = forecast_from_counts(counts, facts.t, 40)
    assert (f.mc50, f.mc85, f.mc95) == (facts.mc50, facts.mc85, facts.mc95)
    assert f.items_done == facts.items_done


def test_function_chance_equals_the_command_line(capsys):  # AC14, R6.3 (chance too)
    sample = str(ROOT / "examples" / "sample_team.csv")
    assert cli.main(["forecast", sample, "--backlog", "40", "--charter", "2026-11-15"]) == 0
    out = capsys.readouterr().out
    args = argparse.Namespace(
        file=sample, backlog=40, as_of=None, seed=20261028, backlog_points=None
    )
    facts, load, _ = cli.compute_full(args)
    from mcf.data.load import load_issues
    from mcf.data.types import sort_types
    from mcf.forecast.throughput import counts_from_ordinals, done_ordinals

    issues, _ = load_issues(sample, open_items=True)
    issues, _ = sort_types(issues, load.file, points_required=False)
    counts = counts_from_ordinals(done_ordinals(issues), facts.t - timedelta(days=200), facts.t)
    f = forecast_from_counts(counts, facts.t, 40, charter=date(2026, 11, 15))
    assert chance_text(f) in out
    assert f.warnings == ()  # 70 items: no warning in either
    assert "Warning:" not in out


def test_only_the_last_84_days_are_used():  # AC15
    long = [3] * 16 + [1] * 84
    assert forecast_from_counts(long, T, 30) == forecast_from_counts([1] * 84, T, 30)


def test_short_history_is_padded_with_zero_days_as_in_v1():  # AC16
    short = forecast_from_counts([1] * 31, T, 10)
    padded = forecast_from_counts([0] * 53 + [1] * 31, T, 10)
    assert short == padded
    assert short.window_days == 84


def test_no_done_item_is_an_error_with_the_v1_text():  # AC17
    with pytest.raises(
        MonteCarloError, match="no forecast: no value item was done in the history window"
    ):
        forecast_from_counts([0] * 84, T, 5)


@pytest.mark.parametrize("backlog", [0, -1])
def test_backlog_below_1_is_an_error(backlog):  # AC18
    with pytest.raises(MonteCarloError, match="N must be a whole number of 1 or more"):
        forecast_from_counts(ONE_A_DAY, T, backlog)


def test_negative_count_is_an_error():
    with pytest.raises(MonteCarloError, match="a daily count is below 0"):
        forecast_from_counts([1] * 83 + [-1], T, 5)


def test_properties():  # AC19 (part)
    for counts, backlog, seed in _random_cases(25, 5, 80):
        a = forecast_from_counts(counts, T, backlog, seed=seed)
        assert a == forecast_from_counts(counts, T, backlog, seed=seed)  # same seed, same output
        assert a.mc50 <= a.mc85 <= a.mc95
        b = forecast_from_counts(counts, T, backlog + 1, seed=seed)
        assert b.mc85 >= a.mc85 and b.mc50 >= a.mc50 and b.mc95 >= a.mc95


def test_counts_can_be_a_numpy_array():
    assert forecast_from_counts(np.ones(84, dtype=np.int64), T, 20).mc85 == date(2026, 12, 21)
