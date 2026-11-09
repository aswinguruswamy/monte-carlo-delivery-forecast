"""MCF-46 checks: the one case loop and the shared metrics of the v1 and v2 back-tests.

Review MCF-46: direct tests of `run_cases`, one explicit mode, a required v2 flag,
and v1 metrics that stop on a forecast case with no velocity date.
"""

from __future__ import annotations

import inspect
from datetime import date, timedelta

import numpy as np
import pytest

from mcf.backtest import metrics
from mcf.backtest.run import BacktestError, Case, FullCase, run_cases

START = date(2026, 1, 1)


def _project(days: int = 120, *, points: float = 3.0, missing_every: int = 0):
    ordinals = np.array([(START + timedelta(days=d)).toordinal() for d in range(days)])
    pts = np.full(days, points)
    if missing_every:
        pts[::missing_every] = np.nan
    return ordinals, pts


def test_the_mode_parameters_are_required():
    params = inspect.signature(run_cases).parameters
    for name in ("velocity_for", "too_far_raises"):
        assert params[name].default is inspect.Parameter.empty, name
    ordinals, pts = _project()
    with pytest.raises(TypeError):
        run_cases(ordinals, pts, "AA", 0, tie_rule="mean")


def test_v2_mode_gives_cases_with_the_fully_pointed_flag():
    ordinals, pts = _project(missing_every=4)
    cases, counts = run_cases(
        ordinals,
        pts,
        "AA",
        0,
        tie_rule="mean",
        sizes=(10,),
        runs=50,
        velocity_for=None,
        too_far_raises=False,
    )
    assert cases and all(isinstance(c, FullCase) for c in cases)
    assert not cases[0].fully_pointed  # 1 item in 4 has no points
    assert counts.cases[10] == len(cases)
    assert counts.no_pointed_item[10] == counts.velocity_too_far[10] == 0


def test_v1_mode_uses_the_given_velocity_and_raises_too_far():
    ordinals, pts = _project(points=1e300)
    with pytest.raises(BacktestError, match="tie rule"):
        run_cases(
            ordinals,
            pts,
            "AA",
            0,
            tie_rule="x",
            velocity_for=lambda t: 1.0,
            too_far_raises=True,
        )
    from mcf.forecast.velocity import VelocityTooFar

    with pytest.raises(VelocityTooFar):
        run_cases(
            ordinals,
            pts,
            "AA",
            0,
            tie_rule="mean",
            sizes=(10,),
            runs=20,
            velocity_for=lambda t: 1e-9,
            too_far_raises=True,
        )


def test_full_case_needs_the_fully_pointed_flag():
    args = ("AA", 0, START, 10, True, None, None, None, None, START + timedelta(days=1))
    with pytest.raises(TypeError):
        FullCase(*args)
    assert FullCase(*args, fully_pointed=False).fully_pointed is False


def test_v1_metrics_stop_on_a_forecast_case_with_no_velocity_date():
    d = START + timedelta(days=100)
    c = Case("AA", 0, START, 10, False, d, d, d, None, d)
    with pytest.raises(metrics.MetricsError, match="velocity"):
        metrics.group([c])
    assert metrics.group([c], velocity_cases=True)["measure_2_cases"] == 0


def test_the_v1_group_keeps_its_key_order():
    d = START + timedelta(days=100)
    c = Case("AA", 0, START, 10, False, d, d, d, d, d)
    assert list(metrics.group([c])) == [
        "cases",
        "no_forecast_cases",
        "calibration_50",
        "calibration_85",
        "calibration_95",
        "median_error_mc50",
        "median_error_velocity",
        "mean_error_mc50",
        "mean_error_velocity",
        "bias_mc50",
        "bias_velocity",
    ]
