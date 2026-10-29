"""MCF-18 acceptance checks: calibration and error (ADR 0002 Metrics and Pass rules, D07)."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from mcf.backtest.metrics import (
    BOOTSTRAP_RESAMPLES,
    MetricsError,
    calibration_passes,
    compute_metrics,
    error_passes,
    load_cases,
    write_metrics,
)

from mcf.backtest.run import Case, write_cases

T = date(2020, 1, 1)


def case(project="A", p=0, n=10, mc=(5, 8, 10), velocity=7, actual=6, no_forecast=False):
    d = lambda k: None if k is None else T + timedelta(days=k)  # noqa: E731
    if no_forecast:
        return Case(project, p, T, n, True, None, None, None, None, d(actual))
    return Case(project, p, T, n, False, d(mc[0]), d(mc[1]), d(mc[2]), d(velocity), d(actual))


# --- band and tie rules (D07, ADR Pass rules) -------------------------------


@pytest.mark.parametrize(
    "value, ok", [(0.75, True), (0.95, True), (0.85, True), (0.749, False), (0.951, False)]
)
def test_calibration_band_edges(value, ok):
    assert calibration_passes(value) is ok


def test_error_rule_needs_monte_carlo_strictly_smaller():
    assert error_passes(3.0, 4.0) is True
    assert error_passes(4.0, 4.0) is False  # a tie fails
    assert error_passes(5.0, 4.0) is False


# --- hand calculation -------------------------------------------------------


def hand_cases():
    # 4 forecast cases + 1 no-forecast case. Day offsets from T.
    return [
        case("A", 0, 10, mc=(5, 8, 10), velocity=7, actual=6),  # 85% hit; err MC 1, vel 1
        case("A", 0, 25, mc=(10, 12, 14), velocity=20, actual=13),  # 85% miss; MC 3, vel 7
        case("B", 1, 10, mc=(4, 6, 9), velocity=2, actual=4),  # hit; MC 0, vel 2
        case("B", 1, 10, mc=(3, 5, 6), velocity=9, actual=5),  # hit (on the day); MC 2, vel 4
        case("B", 1, 25, actual=30, no_forecast=True),
    ]


def test_metrics_match_a_hand_calculation():
    m = compute_metrics(hand_cases())
    s = m["summary"]
    assert s["cases"] == 4
    assert s["no_forecast_cases"] == 1
    assert s["calibration_85"] == pytest.approx(3 / 4)
    assert s["calibration_50"] == pytest.approx(1 / 4)
    assert s["calibration_95"] == pytest.approx(4 / 4)
    assert s["median_error_mc50"] == pytest.approx(1.5)  # errors 1, 3, 0, 2
    assert s["median_error_velocity"] == pytest.approx(3.0)  # errors 1, 7, 2, 4
    assert s["mean_error_mc50"] == pytest.approx(1.5)
    assert s["mean_error_velocity"] == pytest.approx(3.5)
    assert s["bias_mc50"] == pytest.approx((-1 - 3 + 0 - 2) / 4)  # forecast - actual
    assert s["bias_velocity"] == pytest.approx((1 + 7 - 2 + 4) / 4)
    assert s["measure_1_pass"] is True  # 75% is in the band
    assert s["measure_2_pass"] is True  # 1.5 < 3.0
    assert s["calibration_85_no_forecast_as_miss"] == pytest.approx(3 / 5)
    assert s["mean_project_calibration_85"] == pytest.approx((1 / 2 + 2 / 2) / 2)
    assert s["no_forecast_share"] == pytest.approx(1 / 5)
    assert s["no_forecast_over_10_percent"] is True


def test_calibration_50_by_hand():
    # A10: actual 6 > 5 miss; A25: 13 > 10 miss; B: 4 <= 4 hit; B: 5 <= 3? miss
    m = compute_metrics(hand_cases())
    assert m["summary"]["calibration_50"] == pytest.approx(1 / 4)


def test_per_n_and_per_project_rows():
    m = compute_metrics(hand_cases())
    assert m["by_n"]["10"]["cases"] == 3
    assert m["by_n"]["10"]["calibration_85"] == pytest.approx(1.0)
    assert m["by_n"]["25"]["cases"] == 1
    assert m["by_n"]["25"]["no_forecast_cases"] == 1
    assert m["by_project"]["A"]["cases"] == 2
    assert m["by_project"]["B"]["no_forecast_cases"] == 1
    assert m["by_project"]["B"]["median_error_velocity"] == pytest.approx(3.0)


def test_project_with_only_no_forecast_cases_is_listed_without_rates():
    m = compute_metrics([*hand_cases(), case("C", 2, 10, actual=3, no_forecast=True)])
    c = m["by_project"]["C"]
    assert (c["cases"], c["no_forecast_cases"]) == (0, 1)
    assert c["calibration_85"] is None
    # the mean of per-project calibrations uses projects with at least one forecast case
    assert m["summary"]["mean_project_calibration_85"] == pytest.approx(0.75)


def test_tie_in_the_real_numbers_fails_measure_2():
    cases = [case(mc=(5, 8, 10), velocity=5, actual=6), case(mc=(5, 8, 10), velocity=7, actual=6)]
    s = compute_metrics(cases)["summary"]
    assert s["median_error_mc50"] == s["median_error_velocity"] == 1.0
    assert s["measure_2_pass"] is False


def test_no_forecast_case_is_not_scored():
    base = compute_metrics(hand_cases()[:4])["summary"]
    with_nf = compute_metrics(hand_cases())["summary"]
    for key in ("calibration_85", "median_error_mc50", "median_error_velocity"):
        assert base[key] == with_nf[key]


# --- bootstrap (information only) -------------------------------------------


def test_bootstrap_is_by_project_and_repeatable():
    cases = []
    for p in range(6):
        for k in range(5):
            cases.append(
                case(f"P{p}", p, 10, mc=(5, 8, 10), velocity=8 + p, actual=6 + (k + p) % 5)
            )
    a = compute_metrics(cases)["bootstrap"]
    b = compute_metrics(cases)["bootstrap"]
    assert a == b
    assert a["resamples"] == BOOTSTRAP_RESAMPLES == 2000
    assert a["seed"] == 20261028
    lo, hi = a["calibration_85_95ci"]
    assert 0.0 <= lo <= compute_metrics(cases)["summary"]["calibration_85"] <= hi <= 1.0
    lo, hi = a["median_error_difference_95ci"]  # velocity median - MC median
    assert lo <= hi


def test_one_project_gives_a_zero_width_interval():
    cases = [case("A", 0, 10, actual=k) for k in range(4, 10)]
    ci = compute_metrics(cases)["bootstrap"]["calibration_85_95ci"]
    assert ci[0] == ci[1]


# --- errors -----------------------------------------------------------------


def test_no_forecast_case_at_all_is_an_error():
    with pytest.raises(MetricsError, match="no forecast case"):
        compute_metrics([case(no_forecast=True)])


def test_empty_input_is_an_error():
    with pytest.raises(MetricsError):
        compute_metrics([])


# --- files ------------------------------------------------------------------


def test_cases_file_round_trip_and_json_output(tmp_path):
    write_cases(hand_cases(), tmp_path / "cases.csv")
    loaded = load_cases(tmp_path / "cases.csv")
    assert loaded == hand_cases()
    write_metrics(compute_metrics(loaded), tmp_path / "metrics.json")
    data = json.loads((tmp_path / "metrics.json").read_text())
    assert data["summary"]["cases"] == 4
    assert "A-" not in (tmp_path / "metrics.json").read_text()


def test_bad_cases_file_is_an_error(tmp_path):
    (tmp_path / "cases.csv").write_text("project,p\nA,0\n", encoding="utf-8")
    with pytest.raises(MetricsError, match="column"):
        load_cases(tmp_path / "cases.csv")
