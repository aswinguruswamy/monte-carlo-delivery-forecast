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


def test_command_line_writes_metrics_and_prints_pass_or_fail(tmp_path, capsys):
    from mcf.backtest.metrics import main

    write_cases(hand_cases(), tmp_path / "cases.csv")
    code = main(["--cases", str(tmp_path / "cases.csv"), "--out", str(tmp_path / "m.json")])
    assert code == 0
    out = capsys.readouterr().out
    assert "Measure 1 (85% calibration 75.0%, band 75-95%): PASS" in out
    assert "Measure 2 (median error MC 1.5 d vs velocity 3.0 d): PASS" in out
    assert json.loads((tmp_path / "m.json").read_text())["summary"]["cases"] == 4


def test_command_line_bad_file_exits_1(tmp_path, capsys):
    from mcf.backtest.metrics import main

    (tmp_path / "c.csv").write_text("x\n", encoding="utf-8")
    assert main(["--cases", str(tmp_path / "c.csv"), "--out", str(tmp_path / "m.json")]) == 1
    assert "error" in capsys.readouterr().err


# --- review fixes (PR #18) ---------------------------------------------------

HEADER = "project,p,t,n,no_forecast,mc50,mc85,mc95,velocity,actual\n"


@pytest.mark.parametrize(
    "row, message",
    [
        (
            "A,0,2020-01-01,10,yes,2020-01-05,2020-01-08,2020-01-10,2020-01-07,2020-01-06",
            "no_forecast",
        ),
        ("A,0,2020-01-01,10,0,2020-01-05,2020-01-08,2020-01-10,,2020-01-06", "date"),
        ("A,0,2020-01-01,10,1,2020-01-05,,,,2020-01-06", "no-forecast"),
        ("A,0,2020-01-01,10,0,2020-01-05,2020-01-08,2020-01-10,2020-01-07,2020-01-01", "after t"),
        ("A,0,2020-01-01,7,0,2020-01-05,2020-01-08,2020-01-10,2020-01-07,2020-01-06", "N"),
        ("A,0,2020-01-01,10,0,2020-01-05,2020-01-08,2020-01-10,2020-01-07,bad", "line 2"),
    ],
)
def test_bad_case_rows_are_errors(tmp_path, row, message):
    (tmp_path / "c.csv").write_text(HEADER + row + "\n", encoding="utf-8")
    with pytest.raises(MetricsError, match=message):
        load_cases(tmp_path / "c.csv")


def test_one_project_name_with_two_numbers_is_an_error():
    with pytest.raises(MetricsError, match="project"):
        compute_metrics([case("A", 0), case("A", 1)])


def test_unknown_size_is_an_error():
    with pytest.raises(MetricsError, match="N"):
        compute_metrics([case(n=7)])


def test_rows_for_every_adr_size_even_with_no_case():
    m = compute_metrics([case(n=10)])
    assert sorted(m["by_n"]) == ["10", "25", "50"]
    assert m["by_n"]["50"]["cases"] == 0
    assert m["by_n"]["50"]["calibration_85"] is None


def summaries():
    from mcf.backtest.run import ProjectSummary

    a = ProjectSummary(
        "A",
        0,
        cases={10: 2, 25: 1, 50: 0},
        no_forecast={10: 0, 25: 0, 50: 0},
        short_dates={10: 1, 25: 2, 50: 3},
    )
    b = ProjectSummary(
        "B",
        1,
        cases={10: 2, 25: 1, 50: 0},
        no_forecast={10: 0, 25: 1, 50: 0},
        short_dates={10: 0, 25: 0, 50: 4},
    )
    z = ProjectSummary(
        "Z",
        2,
        cases={10: 0, 25: 0, 50: 0},
        no_forecast={10: 0, 25: 0, 50: 0},
        short_dates={10: 5, 25: 5, 50: 5},
    )
    return [a, b, z]


def test_every_project_from_the_summaries_is_listed_with_short_dates():
    m = compute_metrics(hand_cases(), summaries())
    assert list(m["by_project"]) == ["A", "B", "Z"]
    assert m["by_project"]["Z"]["cases"] == 0
    assert m["by_project"]["Z"]["short_dates"] == {"10": 5, "25": 5, "50": 5}
    assert m["summary"]["short_dates"] == {"10": 6, "25": 7, "50": 12}
    assert m["summary"]["projects"] == 3


def test_case_from_an_unknown_project_is_an_error():
    with pytest.raises(MetricsError, match="C"):
        compute_metrics([*hand_cases(), case("C", 2)], summaries()[:2])


def test_summaries_file_round_trip(tmp_path):
    from mcf.backtest.metrics import load_summaries
    from mcf.backtest.run import write_summaries

    write_summaries(summaries(), tmp_path / "projects.csv")
    loaded = load_summaries(tmp_path / "projects.csv")
    assert [(s.project, s.p, s.short_dates) for s in loaded] == [
        (s.project, s.p, s.short_dates) for s in summaries()
    ]


def test_bootstrap_resamples_whole_projects_and_the_difference_sign():
    # Project A: 10 hits, MC error 1, velocity error 5. Project B: 10 misses, errors 2 and 2.
    a = [case("A", 0, mc=(5, 8, 10), velocity=11, actual=6) for _ in range(10)]
    b = [case("B", 1, mc=(5, 8, 10), velocity=9, actual=11) for _ in range(10)]
    # B: actual 11 > 85% date 8 -> miss; MC error |5-11| = 6; velocity error |9-11| = 2.
    boot = compute_metrics(a + b)["bootstrap"]
    # Whole-project resamples give only 0, 0.5 or 1; case resampling would give a narrow band.
    assert boot["calibration_85_95ci"] == [0.0, 1.0]
    # Differences (velocity median - MC median): AA 5-1 = 4, BB 2-6 = -4, AB 3.5-3.5 = 0.
    assert boot["median_error_difference_95ci"] == [-4.0, 4.0]


def test_projects_with_only_no_forecast_cases_are_not_resampled():
    cases = [case("A", 0, actual=6), case("B", 1, actual=30, no_forecast=True)]
    assert compute_metrics(cases)["bootstrap"]["projects"] == 1


@pytest.mark.parametrize(
    "hits, total, ok",
    [
        (15, 20, True),
        (19, 20, True),
        (14, 20, False),
        (20, 20, False),
        (14999, 20000, False),
        (19001, 20000, False),
        (18999, 20000, True),
    ],
)
def test_band_edges_through_compute_metrics(hits, total, ok):
    cases = [case(actual=6 if i < hits else 9) for i in range(total)]  # 85% date is day 8
    s = compute_metrics(cases)["summary"]
    assert s["measure_1_pass"] is ok


def test_measure_1_fail_is_printed(tmp_path, capsys):
    from mcf.backtest.metrics import main

    write_cases([case(actual=9)] * 4, tmp_path / "cases.csv")
    assert main(["--cases", str(tmp_path / "cases.csv"), "--out", str(tmp_path / "m.json")]) == 0
    out = capsys.readouterr().out
    assert "): FAIL" in out.splitlines()[1]


def test_exactly_10_percent_no_forecast_is_not_flagged():
    cases = [case(actual=6)] * 9 + [case(actual=6, no_forecast=True)]
    s = compute_metrics(cases)["summary"]
    assert s["no_forecast_share"] == pytest.approx(0.10)
    assert s["no_forecast_over_10_percent"] is False


def test_flag_is_printed(tmp_path, capsys):
    from mcf.backtest.metrics import main

    write_cases(hand_cases(), tmp_path / "cases.csv")
    main(["--cases", str(tmp_path / "cases.csv"), "--out", str(tmp_path / "m.json")])
    assert "more than 10% of cases have no forecast" in capsys.readouterr().out


# --- separate-chat review fixes (PR #19) -------------------------------------


def test_cases_per_size_and_sizes_with_no_case_come_from_the_summaries():
    m = compute_metrics(hand_cases(), summaries())
    assert m["by_project"]["A"]["cases_by_n"] == {"10": 2, "25": 1, "50": 0}
    assert m["summary"]["no_case_sizes"] == [["A", 50], ["B", 50], ["Z", 10], ["Z", 25], ["Z", 50]]
