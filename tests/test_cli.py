"""MCF-16 acceptance checks: the command line (D25, proposed D28)."""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

from mcf.cli import main

HEADER = "Issue_Key,Type,Resolution_Date,Story_Point\n"
T = date(2020, 6, 30)


def write(tmp_path: Path, rows: list[str], name: str = "team.csv") -> Path:
    p = tmp_path / name
    p.write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return p


def steady(tmp_path: Path, per_day: int = 5, days: int = 84, points: float = 2.0) -> Path:
    """per_day value items done on each of the last `days` days up to T."""
    rows = []
    for d in range(days):
        day = T - timedelta(days=d)
        rows += [f"S-{d}-{i},Story,{day} 10:00:00,{points}" for i in range(per_day)]
    return write(tmp_path, rows)


def run(capsys, *args: str) -> tuple[int, str, str]:
    code = main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


# --- AC1: valid input prints the 3 Monte Carlo dates and the velocity date ----


def test_steady_team_prints_exact_dates(tmp_path, capsys):
    code, out, err = run(capsys, "forecast", str(steady(tmp_path)), "--backlog", "50")
    assert code == 0, err
    # 5 items a day, N = 50: every run takes 10 days.
    for p in ("50%", "85%", "95%"):
        assert f"{p}: {T + timedelta(days=10)}" in out
    # Velocity: 5 x 84 x 2 points / 6 = 140 points per sprint; 50 x 2 = 100 points
    # (estimated) -> 100 / 140 x 14 = 10 days.
    assert f"Velocity: {T + timedelta(days=10)}" in out
    assert "estimated" in out
    assert "not certain" in out  # the 50% date is never shown as certain


def test_day_t_default_is_the_last_done_day(tmp_path, capsys):
    _, out, _ = run(capsys, "forecast", str(steady(tmp_path)), "--backlog", "5")
    assert f"From {T}" in out
    assert "last done day in the file" in out


def test_as_of_sets_day_t(tmp_path, capsys):
    as_of = T - timedelta(days=20)
    code, out, _ = run(
        capsys, "forecast", str(steady(tmp_path)), "--backlog", "5", "--as-of", str(as_of)
    )
    assert code == 0
    assert f"From {as_of}" in out
    assert f"50%: {as_of + timedelta(days=1)}" in out


def test_as_of_ignores_items_done_after_it(tmp_path, capsys):
    rows = [f"A-{i},Story,{T - timedelta(days=100)},1" for i in range(3)]
    rows += [f"B-{i},Story,{T},1" for i in range(500)]  # after as-of: not used
    p = write(tmp_path, rows)
    code, out, _ = run(
        capsys, "forecast", str(p), "--backlog", "3", "--as-of", str(T - timedelta(days=90))
    )
    assert code == 0
    assert "3 value items done" in out


def test_backlog_points_gives_an_exact_velocity_date(tmp_path, capsys):
    _, out, _ = run(
        capsys, "forecast", str(steady(tmp_path)), "--backlog", "50", "--backlog-points", "280"
    )
    assert f"Velocity: {T + timedelta(days=28)}" in out  # 280 / 140 x 14
    assert "estimated" not in out


def test_same_seed_same_output_and_seed_changes_it(tmp_path, capsys):
    rows = []
    for d in range(84):
        rows += [f"S-{d}-{i},Story,{T - timedelta(days=d)},1" for i in range(d % 4)]
    p = write(tmp_path, rows)
    a = run(capsys, "forecast", str(p), "--backlog", "40")[1]
    b = run(capsys, "forecast", str(p), "--backlog", "40")[1]
    assert a == b
    outs = {
        run(capsys, "forecast", str(p), "--backlog", "40", "--seed", str(s))[1] for s in range(8)
    }
    assert len(outs) > 1


def test_open_items_are_skipped_and_counted(tmp_path, capsys):
    p = steady(tmp_path)
    with p.open("a", encoding="utf-8") as fh:
        fh.write("O-1,Story,,3\nO-2,Bug,,\nN-1,Story,NULL,1\n")
    code, out, _ = run(capsys, "forecast", str(p), "--backlog", "50")
    assert code == 0
    assert "Open items skipped: 2" in out
    assert "Rows with no date (NULL): 1" in out
    assert f"50%: {T + timedelta(days=10)}" in out


def test_bug_share_shows(tmp_path, capsys):
    p = write(tmp_path, [f"S-1,Story,{T},1", f"S-2,Story,{T},1", f"B-1,Bug,{T},"])
    _, out, _ = run(capsys, "forecast", str(p), "--backlog", "1")
    assert "Bug share: 33%" in out


# --- AC2: bad input gives a clear error and a non-zero exit code ------------


def test_missing_file(tmp_path, capsys):
    code, out, err = run(capsys, "forecast", str(tmp_path / "nope.csv"), "--backlog", "5")
    assert code == 1
    assert "file not found" in err
    assert out == ""


def test_unknown_issue_type(tmp_path, capsys):
    p = write(tmp_path, [f"X-1,Spike,{T},1"])
    code, _, err = run(capsys, "forecast", str(p), "--backlog", "5")
    assert code == 1
    assert "unknown issue type 'Spike'" in err


def test_bad_date(tmp_path, capsys):
    p = write(tmp_path, ["X-1,Story,31/12/2020,1"])
    code, _, err = run(capsys, "forecast", str(p), "--backlog", "5")
    assert code == 1
    assert "line 2" in err


def test_no_value_item_in_the_window_is_no_forecast(tmp_path, capsys):
    p = write(tmp_path, [f"S-1,Story,{T - timedelta(days=200)},1", f"B-1,Bug,{T},"])
    code, _, err = run(capsys, "forecast", str(p), "--backlog", "5")
    assert code == 1
    assert "no forecast" in err


def test_only_open_items_is_an_error(tmp_path, capsys):
    p = write(tmp_path, ["O-1,Story,,1"])
    code, _, err = run(capsys, "forecast", str(p), "--backlog", "5")
    assert code == 1
    assert "no done item" in err


@pytest.mark.parametrize(
    "args",
    [
        ["--backlog", "0"],
        ["--backlog", "-3"],
        ["--backlog", "ten"],
        [],
        ["--backlog", "5", "--as-of", "2020-02-30"],
        ["--backlog", "5", "--backlog-points", "-1"],
        ["--backlog", "5", "--backlog-points", "nan"],
        ["--backlog", "5", "--seed", "-1"],
    ],
)
def test_bad_command_line_exits_2(tmp_path, capsys, args):
    with pytest.raises(SystemExit) as exc:
        main(["forecast", str(steady(tmp_path)), *args])
    assert exc.value.code == 2
    assert "error" in capsys.readouterr().err


# --- AC3: --help describes each option --------------------------------------


def test_help_describes_each_option(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["forecast", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for option in ("FILE", "--backlog", "--as-of", "--backlog-points", "--seed"):
        assert option in out


def test_python_dash_m_works():
    result = subprocess.run(
        [sys.executable, "-m", "mcf", "forecast", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--backlog" in result.stdout


# --- NFR1: 100,000 rows and 10,000 runs in less than 2 minutes ---------------


def test_nfr1_100000_rows_end_to_end(tmp_path, capsys):
    rows = []
    for i in range(100_000):
        day = T - timedelta(days=i % 3000)
        rows.append(f"S-{i},Story,{day},{i % 8 + 1}")
    p = write(tmp_path, rows)
    start = time.perf_counter()
    code, out, err = run(capsys, "forecast", str(p), "--backlog", "50")
    assert code == 0, err
    assert time.perf_counter() - start < 120
