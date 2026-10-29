"""MCF-17 acceptance checks: the back-test run (ADR 0002, D21.1; proposed D29).

Synthetic data only. The real run happens only after D29 is decided.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from mcf.backtest.run import (
    SIZES,
    BacktestError,
    actual_date,
    forecast_dates_for,
    points_needed,
    run_backtest,
    run_project,
    write_cases,
    write_summaries,
)
from mcf.data.types import sort_types
from mcf.forecast.montecarlo import case_generator, forecast_dates
from mcf.forecast.throughput import counts_from_ordinals, done_ordinals, window
from mcf.forecast.velocity import velocity_date, window_velocity

D0 = date(2020, 1, 1)


def table(rows: list[tuple[int, str, float]]) -> pd.DataFrame:
    """rows: (day offset from D0, type, points), in file order."""
    df = pd.DataFrame(
        {
            "issue_key": [f"P-{i}" for i in range(len(rows))],
            "type": [ty for _, ty, _ in rows],
            "done_day": [D0 + timedelta(days=o) for o, _, _ in rows],
            "story_point": [pt for _, _, pt in rows],
        }
    )
    return sort_types(df, "P.csv")[0]


def daily(days: int, per_day: int = 1, points: float = 1.0) -> list[tuple[int, str, float]]:
    return [(d, "Story", points) for d in range(days) for _ in range(per_day)]


# --- fixed values ------------------------------------------------------------


def test_sizes_are_the_adr_sizes():
    assert SIZES == (10, 25, 50)


# --- forecast dates (ADR: Forecast dates) ------------------------------------


def test_first_date_is_first_value_day_plus_83_then_every_14_days():
    # A bug 10 days before the first value item: it must not move the first date.
    issues = table([(-10, "Bug", float("nan"))] + daily(200))
    ts = forecast_dates_for(issues, 10)
    assert ts[0] == D0 + timedelta(days=83)
    assert all((b - a).days == 14 for a, b in zip(ts, ts[1:], strict=False))


def test_last_date_has_at_least_n_items_after_it():
    issues = table(daily(200))  # one item a day on days 0..199
    ts = forecast_dates_for(issues, 10)
    # day 83 + 14k; need >= 10 items on days > t: t <= 189 -> last is 83 + 14*7 = 181
    assert ts[-1] == D0 + timedelta(days=181)
    assert len(ts) == 8


def test_no_date_when_too_few_items():
    assert forecast_dates_for(table(daily(90)), 50) == []


# --- actual date (ADR: Forecast question) ------------------------------------


def test_actual_date_is_the_day_of_the_nth_value_item_after_t():
    issues = table(
        [
            (0, "Story", 1.0),
            (5, "Story", 1.0),
            (5, "Bug", float("nan")),
            (7, "Story", 1.0),
            (7, "Story", 1.0),
            (9, "Story", 1.0),
        ]
    )
    t = D0  # items on day t are history
    assert actual_date(issues, t, 1) == D0 + timedelta(days=5)
    assert actual_date(issues, t, 2) == D0 + timedelta(days=7)
    assert actual_date(issues, t, 3) == D0 + timedelta(days=7)
    assert actual_date(issues, t, 4) == D0 + timedelta(days=9)
    with pytest.raises(BacktestError):
        actual_date(issues, t, 5)


# --- points needed (ADR Velocity method 2; proposed D29 for same-day items) ---


def test_points_needed_sums_the_next_n_items():
    issues = table([(0, "Story", 9.0), (1, "Story", 2.0), (2, "Story", 3.0), (3, "Story", 5.0)])
    for rule in ("row", "mean"):
        assert points_needed(issues, D0, 2, rule) == 5.0


def test_same_day_rule_row_order_or_mean():
    # The 2nd item falls on day 2, which holds 3 items (3, 6, 9 points, in file order).
    issues = table([(1, "Story", 1.0), (2, "Story", 3.0), (2, "Story", 6.0), (2, "Story", 9.0)])
    assert points_needed(issues, D0, 2, "row") == 1.0 + 3.0
    assert points_needed(issues, D0, 2, "mean") == 1.0 + 6.0  # mean of day 2 x 1 needed
    assert points_needed(issues, D0, 3, "mean") == 1.0 + 2 * 6.0
    assert points_needed(issues, D0, 4, "mean") == points_needed(issues, D0, 4, "row") == 19.0


def test_unknown_tie_rule_is_an_error():
    with pytest.raises(BacktestError, match="rule"):
        points_needed(table(daily(5)), D0, 2, "first")


# --- one project ---------------------------------------------------------------


def test_case_matches_the_parts():
    rows = [(d, "Story", float(d % 3 + 1)) for d in range(150) for _ in range(d % 4)]
    rows += [(d, "Bug", float("nan")) for d in range(0, 150, 5)]
    issues = table(rows)
    cases, summary = run_project(issues, "P", 4, sizes=(10,), runs=300, tie_rule="row")
    case = cases[0]
    t = case.t
    counts = counts_from_ordinals(done_ordinals(issues), *window(t))
    mc = forecast_dates(t, counts, 10, case_generator(4, t, 10), runs=300)
    v = velocity_date(t, window_velocity(issues, t), points_needed(issues, t, 10, "row"))
    assert (case.mc50, case.mc85, case.mc95) == (mc[50], mc[85], mc[95])
    assert case.velocity == v
    assert case.actual == actual_date(issues, t, 10)
    assert (case.project, case.p, case.n, case.no_forecast) == ("P", 4, 10, False)
    assert summary.cases[10] == len(cases)


def test_no_future_data_is_used_by_the_forecasts():
    base = daily(300)
    a, _ = run_project(table(base), "P", 0, sizes=(10,), runs=200, tie_rule="row")
    t = a[2].t
    later = (t - D0).days + 1
    changed = [(o, ty, (pt * 5 if o >= later else pt)) for o, ty, pt in base]
    changed += [(o, "Story", 1.0) for o in range(later, 300) for _ in range(3)]
    b, _ = run_project(table(changed), "P", 0, sizes=(10,), runs=200, tie_rule="row")
    case_a = next(c for c in a if c.t == t)
    case_b = next(c for c in b if c.t == t)
    assert (case_a.mc50, case_a.mc85, case_a.mc95) == (case_b.mc50, case_b.mc85, case_b.mc95)
    # Velocity: same window speed; only points needed (future, by ADR design) may change.
    assert case_a.actual != case_b.actual or case_a.velocity != case_b.velocity


def test_window_with_no_value_item_is_a_no_forecast_case():
    rows = daily(84) + [(300 + d, "Story", 1.0) for d in range(60)]  # gap of 216 days
    cases, summary = run_project(table(rows), "P", 0, sizes=(10,), runs=100, tie_rule="row")
    empty = [c for c in cases if c.no_forecast]
    assert empty
    assert all(c.mc50 is None and c.velocity is None and c.actual for c in empty)
    assert summary.no_forecast[10] == len(empty)


def test_project_with_no_case_for_a_size_is_listed():
    cases, summary = run_project(
        table(daily(100)), "P", 0, sizes=(10, 50), runs=100, tie_rule="row"
    )
    assert summary.cases[10] > 0
    assert summary.cases[50] == 0
    assert all(c.n == 10 for c in cases)


def test_dates_with_too_few_items_after_are_counted():
    # dates 83, 97, ..., up to the last value day 199: 83 + 14k <= 199 -> k = 0..8 (9 dates)
    _, summary = run_project(table(daily(200)), "P", 0, sizes=(10,), runs=100, tie_rule="row")
    assert summary.cases[10] == 8
    assert summary.short_dates[10] == 1


# --- the full run ----------------------------------------------------------------


def write_project(folder: Path, name: str, rows: list[tuple[int, str, float]]) -> None:
    lines = ["Issue_Key,Type,Resolution_Date,Story_Point"]
    lines += [
        f"{name}-{i},{ty},{D0 + timedelta(days=o)} 10:00:00,{'' if pt != pt else pt}"
        for i, (o, ty, pt) in enumerate(rows)
    ]
    (folder / f"{name}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_projects_are_numbered_in_alphabetical_file_order(tmp_path):
    write_project(tmp_path, "ZED", daily(120))
    write_project(tmp_path, "ALPHA", daily(120, per_day=2))
    cases, summaries = run_backtest(tmp_path, sizes=(10,), runs=100, tie_rule="row")
    assert [(s.project, s.p) for s in summaries] == [("ALPHA", 0), ("ZED", 1)]
    assert {c.p for c in cases if c.project == "ZED"} == {1}


def test_same_seed_gives_the_same_output(tmp_path):
    write_project(tmp_path, "A", [(d, "Story", 2.0) for d in range(200) for _ in range(d % 3)])
    (tmp_path / "out").mkdir()
    out1, out2 = tmp_path / "out" / "1.csv", tmp_path / "out" / "2.csv"
    write_cases(run_backtest(tmp_path, sizes=(10, 25), runs=200, tie_rule="mean")[0], out1)
    write_cases(run_backtest(tmp_path, sizes=(10, 25), runs=200, tie_rule="mean")[0], out2)
    assert out1.read_bytes() == out2.read_bytes()
    text = out1.read_text()
    assert text.splitlines()[0] == "project,p,t,n,no_forecast,mc50,mc85,mc95,velocity,actual"
    assert "A-" not in text  # no issue rows (D08)


def test_back_test_loads_with_adr_rule_3_so_an_empty_date_stops_it(tmp_path):
    (tmp_path / "A.csv").write_text(
        "Issue_Key,Type,Resolution_Date,Story_Point\nA-1,Story,,1\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match="bad Resolution_Date"):
        run_backtest(tmp_path, sizes=(10,), runs=10, tie_rule="row")


def test_no_csv_files_is_an_error(tmp_path):
    with pytest.raises(BacktestError, match="no CSV"):
        run_backtest(tmp_path, sizes=(10,), runs=10, tie_rule="row")


def test_tie_rule_is_required(tmp_path):
    write_project(tmp_path, "A", daily(120))
    with pytest.raises(TypeError):
        run_backtest(tmp_path, sizes=(10,), runs=10)  # type: ignore[call-arg]


# --- review fixes (PR #17) ---------------------------------------------------


def test_velocity_speed_uses_only_the_window():
    base = daily(300)
    t = D0 + timedelta(days=83 + 28)
    later = (t - D0).days + 1
    changed = [(o, ty, (pt * 5 if o >= later else pt)) for o, ty, pt in base]
    changed += [(o, "Story", 1.0) for o in range(later, 300) for _ in range(3)]
    assert window_velocity(table(base), t) == window_velocity(table(changed), t)
    b, _ = run_project(table(changed), "P", 0, sizes=(10,), runs=50, tie_rule="row")
    case = next(c for c in b if c.t == t)
    speed = window_velocity(table(base), t)  # the speed known on day t
    assert case.velocity == velocity_date(t, speed, points_needed(table(changed), t, 10, "row"))


def test_rows_out_of_date_order_keep_file_order_within_a_day():
    # 20 rows, not in date order. Day 3 holds 4 items with 1, 2, 3, 4 points in file order,
    # mixed with other days. The 2nd item after day 0 is the 1st item of day 3.
    rows = []
    for k in range(4):
        rows.append((10 + k, "Story", 50.0))
        rows.append((3, "Story", float(k + 1)))
        rows.append((1, "Story", 7.0)) if k == 0 else rows.append((20 + k, "Story", 9.0))
    rows += [(30 + k, "Story", 2.0) for k in range(8)]
    rows = rows[::-1]  # reverse: day 3 file order is now 4, 3, 2, 1
    issues = table(rows)
    assert len(issues) == 20
    assert actual_date(issues, D0, 2) == D0 + timedelta(days=3)
    assert points_needed(issues, D0, 2, "row") == 7.0 + 4.0  # first day-3 row in the file
    assert points_needed(issues, D0, 3, "row") == 7.0 + 4.0 + 3.0
    assert points_needed(issues, D0, 2, "mean") == 7.0 + 2.5


def test_short_dates_counted_for_each_size():
    # one item a day on days 0..199; dates 83 + 14k <= 199 (k = 0..8, 9 dates)
    # N = 10: t <= 189 -> 8 dates, 1 short; N = 50: t <= 149 -> 5 dates, 4 short;
    # N = 25: t <= 174 -> 7 dates, 2 short.
    _, summary = run_project(table(daily(200)), "P", 0, sizes=(10, 25, 50), runs=20, tie_rule="row")
    assert summary.cases == {10: 8, 25: 7, 50: 5}
    assert summary.short_dates == {10: 1, 25: 2, 50: 4}


def test_summaries_are_written_with_the_load_counts(tmp_path):
    write_project(tmp_path, "A", daily(120) + [(5, "Story", 1.0)])
    (tmp_path / "A.csv").write_text(
        (tmp_path / "A.csv").read_text() + "A-x,Story,NULL,1\n", encoding="utf-8"
    )
    _, summaries = run_backtest(tmp_path, sizes=(10, 50), runs=20, tie_rule="row")
    out = tmp_path / "out"
    out.mkdir()
    write_summaries(summaries, out / "projects.csv")
    lines = (out / "projects.csv").read_text().splitlines()
    assert lines[0] == "project,p,rows_read,rows_no_date,n,cases,no_forecast,short_dates"
    assert lines[1].startswith("A,0,122,1,10,")
    assert lines[2] == "A,0,122,1,50,0,0," + lines[2].split(",")[-1]  # listed with 0 cases


def test_files_must_match_the_manifest(tmp_path):
    write_project(tmp_path, "A", daily(120))
    good = {"files": [{"name": "A.csv", "sha256": _sha(tmp_path / "A.csv")}]}
    run_backtest(tmp_path, sizes=(10,), runs=10, tie_rule="row", manifest=good)
    write_project(tmp_path, "B", daily(120))
    with pytest.raises(BacktestError, match="B.csv"):
        run_backtest(tmp_path, sizes=(10,), runs=10, tie_rule="row", manifest=good)
    (tmp_path / "B.csv").unlink()
    bad = {"files": [{"name": "A.csv", "sha256": "0" * 64}]}
    with pytest.raises(BacktestError, match="checksum"):
        run_backtest(tmp_path, sizes=(10,), runs=10, tie_rule="row", manifest=bad)
    missing = {"files": [*good["files"], {"name": "C.csv", "sha256": "0" * 64}]}
    with pytest.raises(BacktestError, match="C.csv"):
        run_backtest(tmp_path, sizes=(10,), runs=10, tie_rule="row", manifest=missing)


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- command line: python -m mcf.backtest --------------------------------------


def test_command_line_writes_cases_and_summaries(tmp_path, monkeypatch):
    import mcf.backtest.__main__ as cli

    data = tmp_path / "data"
    data.mkdir()
    write_project(data, "A", daily(150))
    manifest = {"files": [{"name": "A.csv", "sha256": _sha(data / "A.csv")}]}
    monkeypatch.setattr(cli, "load_manifest", lambda: manifest)
    out = tmp_path / "out"
    code = cli.main(["--data", str(data), "--out", str(out), "--tie-rule", "mean", "--runs", "50"])
    assert code == 0
    assert (out / "cases.csv").read_text().startswith("project,p,t,n,")
    assert (out / "projects.csv").read_text().startswith("project,p,rows_read,")


def test_command_line_needs_the_tie_rule(tmp_path):
    import mcf.backtest.__main__ as cli

    with pytest.raises(SystemExit) as exc:
        cli.main(["--data", str(tmp_path), "--out", str(tmp_path / "o")])
    assert exc.value.code == 2


def test_command_line_stops_on_a_file_not_in_the_manifest(tmp_path, monkeypatch, capsys):
    import mcf.backtest.__main__ as cli

    write_project(tmp_path, "A", daily(150))
    monkeypatch.setattr(cli, "load_manifest", lambda: {"files": []})
    code = cli.main(["--data", str(tmp_path), "--out", str(tmp_path / "o"), "--tie-rule", "row"])
    assert code == 1
    assert "A.csv" in capsys.readouterr().err
