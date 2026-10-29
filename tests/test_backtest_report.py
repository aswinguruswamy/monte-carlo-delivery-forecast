"""MCF-19 acceptance checks: the back-test report (ADR 0002 What is reported; R3, R5, I1)."""

from __future__ import annotations

import re
from datetime import date, timedelta

import pytest

from mcf.backtest.metrics import compute_metrics
from mcf.backtest.report import ReportError, render_report
from mcf.backtest.run import Case, ProjectSummary

T = date(2020, 1, 1)
INFO = {
    "code_commit": "abc1234",
    "cases_sha256": "1" * 64,
    "projects_sha256": "2" * 64,
    "rows_read": 47205,
    "rows_no_date": 19,
}


def case(project, p, n, hit=True, mc_err=1, v_err=3, no_forecast=False):
    actual = T + timedelta(days=10)
    if no_forecast:
        return Case(project, p, T, n, True, None, None, None, None, actual)
    d85 = actual if hit else actual - timedelta(days=1)
    return Case(
        project,
        p,
        T,
        n,
        False,
        actual - timedelta(days=mc_err),
        d85,
        actual + timedelta(days=5),
        actual + timedelta(days=v_err),
        actual,
    )


def summaries(names=("ALPHA", "BETA", "GAMMA")):
    return [
        ProjectSummary(
            name,
            p,
            cases={10: 2, 25: 1, 50: 0},
            no_forecast={10: 0, 25: 0, 50: 0},
            short_dates={10: 1, 25: 2, 50: 3},
        )
        for p, name in enumerate(names)
    ]


def metrics(hits=4, total=4, mc_err=1, v_err=3, no_forecast=0):
    cases = [
        case("ALPHA" if i % 2 else "BETA", i % 2 == 0, 10, hit=i < hits, mc_err=mc_err, v_err=v_err)
        for i in range(total)
    ]
    cases = [
        Case(c.project, 0 if c.project == "ALPHA" else 1, *list(c.__dict__.values())[2:])
        for c in cases
    ]
    cases += [case("GAMMA", 2, 25, no_forecast=True) for _ in range(no_forecast)]
    return compute_metrics(cases, summaries())


def test_summary_shows_both_measures_with_pass_or_fail():
    text = render_report(metrics(hits=3, total=4), INFO)  # 75% -> pass; 1 < 3 -> pass
    assert "| 1. Calibration of the 85% date | 75.0% | 75–95% | **PASS** |" in text
    assert "| 2. Median absolute error, Monte Carlo 50% vs velocity | 1 d vs 3 d |" in text


def test_a_failed_measure_is_shown_as_failed():
    text = render_report(metrics(hits=1, total=4, mc_err=3, v_err=3), INFO)
    assert "25.0% | 75–95% | **FAIL** |" in text
    assert "3 d vs 3 d | Monte Carlo smaller | **FAIL** |" in text
    assert "did not pass" in text


def test_one_row_for_each_project_including_ones_with_no_case():
    text = render_report(metrics(no_forecast=1), INFO)
    section = text.split("## Results by project")[1].split("\n## ")[0]
    rows = [r for r in section.splitlines() if r.startswith("| ") and not r.startswith("| Project")]
    rows = [r for r in rows if not r.startswith("| ---")]
    assert [r.split("|")[1].strip() for r in rows] == ["ALPHA", "BETA", "GAMMA"]
    assert "| GAMMA | 0 | — | — | — | 1 | 6 |" in section


def test_one_row_for_each_n():
    section = (
        render_report(metrics(), INFO).split("## Results by backlog size")[1].split("\n## ")[0]
    )
    for n in ("10", "25", "50"):
        assert f"\n| {n} |" in section


def test_no_forecast_over_10_percent_is_stated_in_the_summary():
    text = render_report(metrics(no_forecast=1), INFO)  # 1 of 5 = 20%
    summary = text.split("## Summary")[1].split("\n## ")[0]
    assert "More than 10% of cases have no forecast" in summary
    assert "More than 10%" not in render_report(metrics(), INFO)


def test_information_only_numbers_are_present_and_labelled():
    text = render_report(metrics(no_forecast=1), INFO)
    section = text.split("## Information only")[1].split("\n## ")[0]
    for label in (
        "Mean of the per-project calibrations",
        "Calibration with no-forecast cases as misses",
        "Bootstrap 95% interval of the calibration",
        "Bootstrap 95% interval of the error difference",
        "Calibration of the 50% date",
        "Calibration of the 95% date",
        "Mean absolute error",
        "Bias",
    ):
        assert label in section
    assert "not used for pass or fail" in section


def test_limits_are_listed():
    limits = render_report(metrics(), INFO).split("## Limits")[1].split("\n## ")[0]
    for words in (
        "only issues with story points",
        "resolved as completed",
        "2-week periods",
        "whatever its status",
        "real points of the next N items",
        "overlap",
    ):
        assert words in limits


def test_data_terms_and_citations():
    text = render_report(metrics(), INFO)
    assert "https://github.com/SOLAR-group/TAWOS" in text
    assert "individual contributors" in text
    assert "10.1145/3524842.3528029" in text
    assert "10.1145/3544902.3546238" in text


def test_reproduce_steps_and_checksums():
    text = render_report(metrics(), INFO)
    assert "python -m mcf.backtest --data data --out results" in text
    assert "1" * 64 in text and "2" * 64 in text
    assert "abc1234" in text
    assert "47,205 rows" in text and "19 rows" in text


def test_no_overclaiming_words():
    text = render_report(metrics(), INFO).lower()
    for word in ("proves", "proven", "guarantee", "always correct", "certainly", "will happen"):
        assert word not in text
    assert re.search(r"\bcertain\b", text) is None or "not certain" in text


def test_report_is_repeatable():
    assert render_report(metrics(), INFO) == render_report(metrics(), INFO)


def test_missing_run_info_is_an_error():
    with pytest.raises(ReportError, match="cases_sha256"):
        render_report(metrics(), {k: v for k, v in INFO.items() if k != "cases_sha256"})


def test_metrics_without_project_summaries_is_an_error():
    m = metrics()
    del m["summary"]["short_dates"]
    with pytest.raises(ReportError, match="projects.csv"):
        render_report(m, INFO)


# --- published files (D08) ----------------------------------------------------


def test_only_the_summary_metrics_file_may_be_committed_from_results():
    from test_repo_hygiene import dataset_violations

    def size(_):
        return 18_000

    assert dataset_violations(["results/metrics.json"], size) == []
    assert dataset_violations(["results/cases.csv"], size) == ["results/cases.csv"]
    assert dataset_violations(["results/projects.csv"], size) == ["results/projects.csv"]


def test_results_csv_files_are_git_ignored():
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for name in ("results/cases.csv", "results/projects.csv"):
        out = subprocess.run(["git", "check-ignore", "--no-index", "-q", name], cwd=root)
        assert out.returncode == 0, name
    out = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "results/metrics.json"], cwd=root
    )
    assert out.returncode == 1


def test_published_report_matches_the_published_metrics():
    """Every number in docs/backtest-report.md comes from results/metrics.json."""
    import json
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    report = (root / "docs" / "backtest-report.md").read_text(encoding="utf-8")
    metrics = json.loads((root / "results" / "metrics.json").read_text(encoding="utf-8"))
    info = {
        "code_commit": re.search(r"Code commit of the run: `([^`]+)`", report).group(1),
        "cases_sha256": re.search(r"`cases.csv` SHA-256: `([0-9a-f]{64})`", report).group(1),
        "projects_sha256": re.search(r"`projects.csv` SHA-256: `([0-9a-f]{64})`", report).group(1),
        "rows_read": int(re.search(r"([\d,]+) rows read", report).group(1).replace(",", "")),
        "rows_no_date": int(re.search(r"(\d+) rows with no resolution date", report).group(1)),
    }
    assert render_report(metrics, info) == report


# --- separate-chat review fixes (PR #19) -------------------------------------


def test_projects_with_no_case_for_a_size_are_listed():
    text = render_report(metrics(), INFO)
    assert (
        "Projects with no case for a size N: ALPHA (N = 50), BETA (N = 50), GAMMA (N = 50)." in text
    )


def test_scored_cases_column_name():
    text = render_report(metrics(), INFO)
    assert "| Project | Cases scored | Calibration 85%" in text
    assert "| N | Cases scored |" in text


def test_status_versus_resolution_is_explained_with_counts():
    limits = render_report(metrics(), INFO).split("## Limits")[1].split("\n## ")[0]
    assert "value items with another status: Won't Fix (853), Invalid (335)" in limits
    assert "Automation" not in limits  # no value item has this status
    assert "every Resolution value in the extract is a completed value" in limits


def test_measure_2_limit_sentence_depends_on_the_result():
    win = render_report(metrics(mc_err=1, v_err=3), INFO)
    loss = render_report(metrics(mc_err=3, v_err=1), INFO)
    assert "this Monte Carlo win on measure 2 is conservative" in win
    assert "conservative" not in loss
    assert "a Monte Carlo loss on measure 2 tells less" in loss


def test_small_non_robust_win_is_named_in_the_limit():
    # one project: interval is a single value, so build two projects with a known 0 lower end
    m = metrics(mc_err=1, v_err=3)
    m["bootstrap"]["median_error_difference_95ci"] = [0.0, 6.0]
    limits = render_report(m, INFO).split("## Limits")[1].split("\n## ")[0]
    assert "small and not robust" in limits


def test_d29_and_d30_are_named_next_to_the_no_change_statement():
    text = render_report(metrics(hits=1, total=4), INFO)
    assert "D29 and D30 completed two details that the ADR did not set" in text
    assert "D29 came before the run, and D30 came before the metrics" in text


def test_case_selection_limit():
    limits = render_report(metrics(), INFO).split("## Limits")[1].split("\n## ")[0]
    assert "a forecast date exists only when at least N value items were done after it" in limits


def test_reproduce_steps_are_complete():
    section = render_report(metrics(), INFO).split("## Reproduce")[1]
    assert 'pip install -e ".[dev]"' in section
    assert "python -m mcf.backtest.report --results results" in section


def test_status_counts_match_the_data():
    """The fixed status counts in the report equal the TAWOS extract.

    Known gap: CI has no data, so this test is skipped there. It runs where the data is
    downloaded, and the separate-chat re-run checklist includes it (MCF-19 re-check).
    """
    import csv
    from collections import Counter
    from pathlib import Path

    from mcf.backtest.report import STATUS_COUNTS
    from mcf.data.types import D04_KIND

    data = Path(__file__).resolve().parents[1] / "data"
    files = sorted(data.glob("*.csv"))
    if len(files) != 29:
        pytest.skip("TAWOS data not downloaded")
    counts = Counter()
    for f in files:
        with f.open(newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                if row["Resolution_Date"] != "NULL" and D04_KIND.get(row["Type"]) == "value":
                    counts[row["Status"]] += 1
    assert {k: counts[k] for k in STATUS_COUNTS} == STATUS_COUNTS


def test_d29_d30_sentence_shows_also_when_both_measures_pass():
    text = render_report(metrics(hits=3, total=4), INFO)
    summary = text.split("## Summary")[1].split("\n## ")[0]
    assert "D29 and D30 completed two details that the ADR did not set" in summary


def test_direction_of_the_85_percent_miss_in_plain_words():
    text = render_report(metrics(hits=3, total=4), INFO)
    assert "The 85% date was too early in 25.0% of the scored cases." in text
