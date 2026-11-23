"""MCF v2 task M1: the command line shows the charter-date chance (R1) and the warning (R2)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from tests.test_cli import T, run, steady, write


def test_charter_on_the_exact_finish_day_is_100_percent(tmp_path, capsys):  # AC2
    # 5 items a day, N = 50: every run takes 10 days.
    day = T + timedelta(days=10)
    code, out, err = run(
        capsys, "forecast", str(steady(tmp_path)), "--backlog", "50", "--charter", str(day)
    )
    assert code == 0, err
    assert f"Charter date: 100% chance to finish by {day}" in out


def test_charter_one_day_earlier_is_0_percent(tmp_path, capsys):  # AC3
    day = T + timedelta(days=9)
    _, out, _ = run(
        capsys, "forecast", str(steady(tmp_path)), "--backlog", "50", "--charter", str(day)
    )
    assert f"Charter date: 0% chance to finish by {day}" in out


def test_chance_line_comes_right_after_the_dates(tmp_path, capsys):
    _, out, _ = run(
        capsys,
        "forecast",
        str(steady(tmp_path)),
        "--backlog",
        "50",
        "--charter",
        str(T + timedelta(days=10)),
    )
    lines = out.splitlines()
    assert lines[
        lines.index("  The 50% date is not certain: half of the runs finish later.") + 1
    ].startswith("  Charter date:")


def test_charter_on_or_before_day_t_is_an_error(tmp_path, capsys):  # AC6
    code, out, err = run(
        capsys, "forecast", str(steady(tmp_path)), "--backlog", "50", "--charter", str(T)
    )
    assert code == 1
    assert out == ""
    assert f"The charter date must be after {T}." in err


def test_no_charter_no_chance_line(tmp_path, capsys):
    _, out, _ = run(capsys, "forecast", str(steady(tmp_path)), "--backlog", "50")
    assert "Charter date" not in out


def test_thin_history_warning_is_above_the_dates(tmp_path, capsys):  # AC8, AC10
    rows = [f"S-{d},Story,{T - timedelta(days=d)} 10:00:00,1" for d in range(0, 58, 2)]  # 29 items
    _, out, _ = run(capsys, "forecast", str(write(tmp_path, rows)), "--backlog", "5")
    warning = "Warning: Only 29 items finished in the last 12 weeks. Treat the dates with care."
    assert warning in out
    assert out.index(warning) < out.index("Monte Carlo (")


def test_no_warning_at_30_items(tmp_path, capsys):  # AC9
    rows = [f"S-{d},Story,{T - timedelta(days=d)} 10:00:00,1" for d in range(0, 60, 2)]  # 30 items
    _, out, _ = run(capsys, "forecast", str(write(tmp_path, rows)), "--backlog", "5")
    assert "Warning:" not in out


def test_bad_charter_text_exits_2(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        run(capsys, "forecast", str(steady(tmp_path)), "--backlog", "5", "--charter", "15 Dec")
    assert exc.value.code == 2


def test_charter_before_day_t_is_an_error(tmp_path, capsys):
    code, _, err = run(
        capsys,
        "forecast",
        str(steady(tmp_path)),
        "--backlog",
        "50",
        "--charter",
        str(T - timedelta(days=1)),
    )
    assert code == 1
    assert f"The charter date must be after {T}." in err
