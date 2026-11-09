"""MCF-28 checks: the v2 back-test on the full TAWOS data (ADR 0003; ADR 0002 method unchanged).

The data here is made up. The real allowed-columns file stays outside the repo (D08).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from mcf.backtest.full import (
    COMPLETED,
    FULL_KIND,
    FullBacktestError,
    full_metrics,
    load_projects,
    run_full,
    run_project_full,
)
from mcf.backtest.run import run_project
from mcf.data.load import load_issues
from mcf.data.types import BUG, NOT_COUNTED, VALUE, sort_types

HEADER = "Project_Key,Type,Status,Resolution,Resolution_Date,Story_Point\n"
START = date(2026, 1, 1)


def _rows(project: str, days: int, *, points: str = "2.0", every: int = 1, res: str = "Fixed"):
    """One value item done every `every` days for `days` days."""
    out = []
    for d in range(0, days, every):
        day = START + timedelta(days=d)
        out.append(f"{project},Story,Closed,{res},{day} 10:00:00,{points}\n")
    return out


def write(tmp_path: Path, lines: list[str], name: str = "issues.csv") -> Path:
    p = tmp_path / name
    p.write_text(HEADER + "".join(lines), encoding="utf-8")
    return p


# --- ADR 0003 rule 6: types -----------------------------------------------------------------


def test_the_7_new_types_follow_d54():
    assert FULL_KIND["Support Request"] == VALUE
    assert FULL_KIND["Test Task"] == FULL_KIND["Test"] == FULL_KIND["Investigation"] == VALUE
    assert FULL_KIND["Milestone"] == FULL_KIND["Release"] == NOT_COUNTED
    assert FULL_KIND["Public Security Vulnerability"] == BUG
    assert FULL_KIND["Story"] == VALUE and FULL_KIND["Epic"] == NOT_COUNTED  # D04.2 kept


def test_an_unknown_type_stops_the_run(tmp_path):
    p = write(tmp_path, ["AA,Spike,Closed,Fixed,2026-01-02 00:00:00,1\n"])
    with pytest.raises(FullBacktestError, match="unknown issue type 'Spike'"):
        load_projects(p)


# --- ADR 0003 decision 1: done ----------------------------------------------------------------


def test_done_is_any_resolution_date_and_completed_is_the_7_values(tmp_path):
    assert COMPLETED == {
        "Fixed",
        "Done",
        "Complete",
        "Completed",
        "Implemented",
        "Deployed",
        "Resolved",
    }
    p = write(
        tmp_path,
        [
            "AA,Story,Closed,Fixed,2026-01-02 00:00:00,1\n",
            "AA,Story,Closed,Duplicate,2026-01-03 00:00:00,1\n",
            "AA,Story,Open,,,1\n",  # open: not done
            "AA,Bug,Closed,Fixed,2026-01-04 00:00:00,\n",  # not a value item
        ],
    )
    assert len(load_projects(p)["AA"][0]) == 2
    assert len(load_projects(p, done_rule="completed")["AA"][0]) == 1


def test_projects_are_numbered_in_alphabetical_order(tmp_path):
    p = write(tmp_path, _rows("ZZ", 3) + _rows("AA", 3))
    assert list(load_projects(p)) == ["AA", "ZZ"]


# --- ADR 0002 method unchanged ----------------------------------------------------------------


def test_a_fully_pointed_project_gives_exactly_the_v1_dates(tmp_path):
    """Same Monte Carlo, window, seed stream, velocity and tie rule as v1 (D23)."""
    lines = _rows("AA", 200, every=1) + _rows("AA", 200, every=3, points="5.0")
    full = load_projects(write(tmp_path, lines))
    ordinals, points = full["AA"]
    v2_cases, _ = run_project_full(ordinals, points, "AA", 0, sizes=(10, 25), runs=500)

    v1 = tmp_path / "AA.csv"
    v1.write_text(
        "Issue_Key,Type,Resolution_Date,Story_Point\n"
        + "".join(
            f"AA-{i},Story,{line.split(',')[4][:10]},{line.split(',')[5].strip()}\n"
            for i, line in enumerate(lines)
        ),
        encoding="utf-8",
    )
    issues, _ = load_issues(v1)
    issues, _ = sort_types(issues, "AA.csv")
    v1_cases, _ = run_project(issues, "AA", 0, tie_rule="mean", sizes=(10, 25), runs=500)

    assert len(v2_cases) == len(v1_cases) > 0
    for a, b in zip(v2_cases, v1_cases, strict=True):
        assert (a.t, a.n, a.mc50, a.mc85, a.mc95, a.velocity, a.actual) == (
            b.t,
            b.n,
            b.mc50,
            b.mc85,
            b.mc95,
            b.velocity,
            b.actual,
        )
        assert a.fully_pointed


# --- ADR 0003 decision 2: missing story points -------------------------------------------------


def test_missing_points_use_the_mean_of_the_pointed_items_in_the_window(tmp_path):
    lines = _rows("AA", 120, points="4.0")  # 1 a day, 4 points each
    lines += [f"AA,Story,Closed,Fixed,{START + timedelta(days=d)} 12:00:00,\n" for d in range(120)]
    ordinals, points = load_projects(write(tmp_path, lines))["AA"]
    assert int(np.isnan(points).sum()) == 120
    cases, _ = run_project_full(ordinals, points, "AA", 0, sizes=(10,), runs=200)
    c = cases[0]
    # window: 84 pointed items x 4 = 336 points / 6 = 56 a sprint; next 10 items = 10 x 4
    assert c.velocity == c.t + timedelta(days=math.ceil(40 / 56 * 14))
    assert not c.fully_pointed


def test_no_pointed_item_in_the_window_means_no_velocity_date(tmp_path):
    lines = [f"AA,Story,Closed,Fixed,{START + timedelta(days=d)} 12:00:00,\n" for d in range(120)]
    ordinals, points = load_projects(write(tmp_path, lines))["AA"]
    cases, summary = run_project_full(ordinals, points, "AA", 0, sizes=(10,), runs=200)
    assert cases and all(c.velocity is None and c.mc85 is not None for c in cases)
    assert summary.no_velocity[10] == len(cases)


# --- metrics ---------------------------------------------------------------------------------


def test_metrics_use_the_same_cases_for_measure_2_and_report_the_pointed_view(tmp_path):
    lines = _rows("AA", 200) + [
        f"BB,Story,Closed,Fixed,{START + timedelta(days=d)} 12:00:00,\n" for d in range(200)
    ]
    cases, summaries = run_full(write(tmp_path, lines), sizes=(10,), runs=200)
    m = full_metrics(cases, summaries)
    s = m["summary"]
    assert s["projects"] == 2
    assert s["cases"] == sum(1 for c in cases if not c.no_forecast)
    assert s["measure_2_cases"] == sum(1 for c in cases if c.velocity is not None)
    assert s["measure_2_cases"] < s["cases"]  # BB has no points, so no velocity date
    assert m["pointed_only"]["cases"] == sum(1 for c in cases if c.fully_pointed)
    assert set(s) >= {
        "calibration_85",
        "measure_1_pass",
        "median_error_mc50",
        "median_error_velocity",
        "measure_2_pass",
    }


def test_the_run_checks_the_file_checksum(tmp_path):
    p = write(tmp_path, _rows("AA", 10))
    with pytest.raises(FullBacktestError, match="checksum"):
        run_full(p, sizes=(10,), runs=10, expected_sha256="0" * 64)


def test_the_command_writes_both_done_rules_and_no_issue_rows(tmp_path):
    import json

    from mcf.backtest.full import main

    data = write(tmp_path, _rows("AA", 200))
    out = tmp_path / "out"
    assert main(["--data", str(data), "--out", str(out), "--runs", "200", "--no-checksum"]) == 0
    m = json.loads((out / "metrics-full.json").read_text())
    assert set(m) == {"input", "any", "completed"}
    assert m["input"]["sha256"] and m["input"]["rows"] == 200
    assert (out / "cases-full-any.csv").exists() and (out / "cases-full-completed.csv").exists()
    header = (out / "cases-full-any.csv").read_text().splitlines()[0]
    assert header == "project,p,t,n,no_forecast,mc50,mc85,mc95,velocity,actual,fully_pointed"


def test_the_command_needs_the_checksum_by_default(tmp_path, capsys):
    from mcf.backtest.full import main

    data = write(tmp_path, _rows("AA", 20))
    assert main(["--data", str(data), "--out", str(tmp_path / "o")]) == 1
    assert "checksum" in capsys.readouterr().err


# --- Review MCF-28 (pre-run): D54.1, D54.2 and the mutations the tests missed -----------------

T0 = START + timedelta(days=83)  # the first forecast date: first value day + 83


def _window_rows() -> list[str]:
    """84 pointed items in the first window: 2 and 6 in turn (mean 4, max 6), velocity 56."""
    return [
        f"AA,Story,Closed,Fixed,{START + timedelta(days=d)} 10:00:00,{2.0 if d % 2 else 6.0}\n"
        for d in range(84)
    ]


def _item(d: int, points: str = "") -> str:
    return f"AA,Story,Closed,Fixed,{START + timedelta(days=d)} 10:00:00,{points}\n"


def _case(cases, t, n):
    return next(c for c in cases if c.t == t and c.n == n)


def test_d54_1_a_0_point_item_has_no_story_point(tmp_path):
    p = write(tmp_path, ["AA,Story,Closed,Fixed,2026-01-02 00:00:00,0\n"])
    _, points = load_projects(p)["AA"]
    assert np.isnan(points).all()


def test_the_fill_is_the_mean_of_the_window_only(tmp_path):
    """Not the window maximum (6), and no item after t (100 points each) is used."""
    lines = _window_rows()
    lines += [_item(d) for d in range(84, 94)]
    lines += [_item(d, "100") for d in range(94, 200)]
    ordinals, points = load_projects(write(tmp_path, lines))["AA"]
    cases, _ = run_project_full(ordinals, points, "AA", 0, sizes=(10,), runs=50)
    c = _case(cases, T0, 10)
    # 10 unpointed items x 4 (window mean) = 40 points; 40 / 56 x 14 = 10 days
    assert c.velocity == T0 + timedelta(days=10)
    assert not c.fully_pointed


def test_the_tie_rule_is_mean_and_tie_day_items_decide_fully_pointed(tmp_path):
    """D29 "mean": the 10th item's day has 3 items (20, 2, none); the unpointed one is last."""
    lines = _window_rows()
    lines += [_item(d, "4") for d in range(84, 93)]
    day = START + timedelta(days=93)
    lines += [f"AA,Story,Closed,Fixed,{day} 10:00:00,{p}\n" for p in ("20", "2", "")]
    lines += [_item(d, "4") for d in range(94, 120)]
    ordinals, points = load_projects(write(tmp_path, lines))["AA"]
    cases, _ = run_project_full(ordinals, points, "AA", 0, sizes=(10,), runs=50)
    c = _case(cases, T0, 10)
    # 9 x 4 + mean(20, 2, 4 filled) = 36 + 8.667 = 44.667; / 56 x 14 = 11.17 -> 12 days
    # (the "row" rule gives 36 + 20 = 56 -> 14 days)
    assert c.velocity == T0 + timedelta(days=12)
    assert not c.fully_pointed


def test_projects_are_numbered_alphabetically_in_the_run(tmp_path):
    p = write(tmp_path, _rows("CC", 120) + _rows("AA", 120) + _rows("BB", 120))
    cases, summaries = run_full(p, sizes=(10,), runs=20)
    assert {c.project: c.p for c in cases} == {"AA": 0, "BB": 1, "CC": 2}
    assert [(s.project, s.p) for s in summaries] == [("AA", 0), ("BB", 1), ("CC", 2)]


def test_d54_2_huge_points_are_kept_and_a_date_past_9999_is_counted_apart(tmp_path):
    """As recorded (D54.2). A velocity date that cannot exist is "too far", not "no points"."""
    lines = [_item(d, "0.001") for d in range(84)]
    lines += [_item(d, "26710114") for d in range(84, 120)]
    ordinals, points = load_projects(write(tmp_path, lines))["AA"]
    assert points.max() == 26710114
    cases, summary = run_project_full(ordinals, points, "AA", 0, sizes=(10,), runs=20)
    c = _case(cases, T0, 10)
    assert c.velocity is None and c.mc85 is not None
    assert summary.velocity_too_far[10] >= 1
    assert summary.no_pointed_item[10] == 0


def test_the_counts_per_project_follow_adr_0003_report_item_3(tmp_path):
    p = write(
        tmp_path,
        [
            "AA,Story,Closed,Fixed,2026-01-02 00:00:00,1\n",
            "AA,Story,Closed,Duplicate,2026-01-03 00:00:00,0\n",
            "AA,Story,Open,,,1\n",
            "AA,Bug,Closed,Fixed,2026-01-04 00:00:00,\n",
            "AA,Epic,Closed,Done,2026-01-05 00:00:00,\n",
        ],
    )
    from mcf.backtest.full import project_counts

    assert project_counts(p, "any")["AA"] == {
        "issues_read": 5,
        "no_resolution_date": 1,
        "not_value_item": 2,
        "not_completed": 0,
        "value_items_done": 2,
        "zero_points": 1,
        "over_100_points": 0,
    }
    assert project_counts(p, "completed")["AA"]["not_completed"] == 1
    assert project_counts(p, "completed")["AA"]["value_items_done"] == 1


def test_metrics_hold_the_adr_0002_report_items(tmp_path):
    lines = _rows("AA", 200) + _rows("BB", 200, every=2)
    cases, summaries = run_full(write(tmp_path, lines), sizes=(10, 25, 50), runs=50)
    m = full_metrics(cases, summaries)
    s = m["summary"]
    for key in (
        "mean_error_mc50",
        "mean_error_velocity",
        "bias_mc50",
        "bias_velocity",
        "calibration_85_no_forecast_as_miss",
        "no_forecast_share",
        "no_forecast_over_10_percent",
        "mean_project_calibration_85",
        "short_dates",
        "no_pointed_item",
        "velocity_too_far",
    ):
        assert key in s, key
    assert set(m["bootstrap"]) >= {"calibration_85_95ci", "median_error_difference_95ci"}
    assert set(m["by_project"]["AA"]) >= {"short_dates", "cases_by_n", "p"}
    # measure 2 compares both methods on the same cases
    with_v = [c for c in cases if c.velocity is not None]
    errors = [abs((c.mc50 - c.actual).days) for c in with_v]
    assert s["median_error_mc50"] == float(np.median(errors))


def test_the_manifest_ties_the_export_checksum_to_the_dump():
    """Review MCF-28, finding 7: the run checks the export; the manifest names its source dump."""
    import json

    from mcf.backtest.full import EXPORT_SHA256

    root = Path(__file__).resolve().parents[1]
    m = json.loads((root / "src" / "mcf" / "data" / "tawos_full_manifest.json").read_text())
    assert m["dump"]["sha256"] == "97dc0deaaa02ac75017d2b9cbe0765ac3377b5d7c10f9f88bc62de838f34badd"
    assert m["dump"]["bytes"] == 4_313_856_480
    assert m["export"]["sha256"] == EXPORT_SHA256
    assert m["export"]["rows"] == 458_232
    assert m["export"]["made_with"] == "mcf.data.tawos_dump.export_csv"
