"""MCF-20 acceptance checks: the forecast back-test review script and skill (D13)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mcf.backtest.review import ACCEPTED_SHA256, review

ROOT = Path(__file__).resolve().parents[1]


def copy_repo(tmp_path: Path) -> Path:
    """A copy of the reviewed files, without git history."""
    for folder in ("docs", "results"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    return tmp_path


def names(gaps) -> set[str]:
    return {g.check for g in gaps}


def test_the_real_repository_has_no_gap():
    assert review(ROOT, run_tests=False) == []


def test_the_lock_matches_the_adr_test():
    from test_adr_backtest import ACCEPTED_SHA256 as in_test

    assert ACCEPTED_SHA256 == in_test


def test_future_data_tests_are_run_and_pass():
    assert review(ROOT, run_tests=True) == []


def test_a_copy_without_git_cannot_prove_the_order(tmp_path):
    gaps = review(copy_repo(tmp_path), run_tests=False)
    assert names(gaps) == {"adr_before_run"}


def test_a_changed_adr_is_a_gap(tmp_path):
    repo = copy_repo(tmp_path)
    adr = repo / "docs" / "adr" / "0002-backtest-method.md"
    adr.write_text(adr.read_text() + "\nchanged\n")
    assert "adr_locked" in names(review(repo, run_tests=False))


def test_a_flipped_pass_rule_is_a_gap(tmp_path):
    repo = copy_repo(tmp_path)
    m = json.loads((repo / "results" / "metrics.json").read_text())
    m["summary"]["measure_1_pass"] = True  # 69.0% is outside 75–95%
    (repo / "results" / "metrics.json").write_text(json.dumps(m))
    assert "pass_rules" in names(review(repo, run_tests=False))


def test_an_edited_report_is_a_gap(tmp_path):
    repo = copy_repo(tmp_path)
    report = repo / "docs" / "backtest-report.md"
    report.write_text(report.read_text().replace("69.0%", "79.0%", 1))
    assert "report_matches_metrics" in names(review(repo, run_tests=False))


def test_a_hidden_failure_is_a_gap(tmp_path):
    repo = copy_repo(tmp_path)
    report = repo / "docs" / "backtest-report.md"
    report.write_text(report.read_text().replace("**FAIL**", "**PASS**"))
    assert "failed_measure_shown" in names(review(repo, run_tests=False))


def test_a_missing_project_row_is_a_gap(tmp_path):
    repo = copy_repo(tmp_path)
    report = repo / "docs" / "backtest-report.md"
    lines = [ln for ln in report.read_text().splitlines() if not ln.startswith("| APSTUD |")]
    report.write_text("\n".join(lines) + "\n")
    assert "project_rows" in names(review(repo, run_tests=False))


def test_a_missing_limits_section_is_a_gap(tmp_path):
    repo = copy_repo(tmp_path)
    report = repo / "docs" / "backtest-report.md"
    report.write_text(report.read_text().replace("## Limits", "## Notes"))
    assert "required_sections" in names(review(repo, run_tests=False))


def test_missing_files_are_a_gap_not_a_crash(tmp_path):
    gaps = review(tmp_path, run_tests=False)
    assert "files_present" in names(gaps)


def test_command_line_lists_gaps_and_exit_code(tmp_path, capsys):
    from mcf.backtest.review import main

    assert main(["--repo", str(ROOT), "--no-tests"]) == 0
    assert "No gap found" in capsys.readouterr().out
    assert main(["--repo", str(tmp_path), "--no-tests"]) == 1
    assert "GAP files_present" in capsys.readouterr().out


def test_the_skill_file_exists_and_names_the_script_and_the_judgement_checks():
    skill = (ROOT / "skills" / "forecast-backtest-review" / "SKILL.md").read_text()
    assert skill.startswith("---\nname: forecast-backtest-review\n")
    assert "python -m mcf.backtest.review" in skill
    for words in ("overclaim", "D29", "D30", "REVIEW RESULT START", "method before results"):
        assert words in skill, words


@pytest.mark.parametrize("bad", ["", "{not json"])
def test_bad_metrics_file_is_a_gap(tmp_path, bad):
    repo = copy_repo(tmp_path)
    (repo / "results" / "metrics.json").write_text(bad)
    assert "files_present" in names(review(repo, run_tests=False))


# --- review fixes (PR #23) ---------------------------------------------------


def edit_json(repo: Path, change) -> None:
    path = repo / "results" / "metrics.json"
    m = json.loads(path.read_text())
    change(m)
    path.write_text(json.dumps(m))


def test_the_band_is_fixed_in_the_review_not_taken_from_the_code():
    from fractions import Fraction

    from mcf.backtest import review as rv

    assert rv.BAND == (Fraction(75, 100), Fraction(95, 100))


def test_a_changed_band_in_the_code_is_a_gap(monkeypatch):
    from fractions import Fraction

    import mcf.backtest.metrics as metrics

    monkeypatch.setattr(metrics, "BAND", (Fraction(60, 100), Fraction(95, 100)))
    assert "band_fixed" in names(review(ROOT, run_tests=False))


@pytest.mark.parametrize(
    "change, check",
    [
        (lambda m: m["bootstrap"].update(resamples=500), "fixed_method_values"),
        (lambda m: m["bootstrap"].update(seed=1), "fixed_method_values"),
        (lambda m: m["by_project"].pop("APSTUD"), "project_count"),
    ],
)
def test_changed_method_values_are_gaps(tmp_path, change, check):
    repo = copy_repo(tmp_path)
    edit_json(repo, change)
    assert check in names(review(repo, run_tests=False))


def test_rows_with_no_date_must_be_19(tmp_path):
    repo = copy_repo(tmp_path)
    report = repo / "docs" / "backtest-report.md"
    report.write_text(
        report.read_text().replace(
            " 19 rows with no resolution date", " 25 rows with no resolution date"
        )
    )
    assert "fixed_method_values" in names(review(repo, run_tests=False))


def test_the_future_data_tests_are_named_exactly():
    from mcf.backtest.review import FUTURE_TESTS

    assert FUTURE_TESTS == (
        "tests/test_backtest_run.py::test_no_future_data_is_used_by_the_forecasts",
        "tests/test_backtest_run.py::test_velocity_speed_uses_only_the_window",
        "tests/test_backtest_run.py::test_window_with_no_value_item_is_a_no_forecast_case",
    )


def test_future_data_tests_run_against_the_reviewed_copy(tmp_path):
    """A copy whose run tests are missing must give a gap, even if the main checkout has them."""
    repo = copy_repo(tmp_path)
    (repo / "src").mkdir()
    shutil.copytree(ROOT / "src" / "mcf", repo / "src" / "mcf")
    (repo / "tests").mkdir()
    gaps = review(repo, run_tests=True)
    assert "future_data_tests" in names(gaps)


def git(repo: Path, *args: str) -> None:
    import subprocess

    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": "/usr/bin:/bin",
        },
    )


def test_adr_committed_after_the_run_code_is_a_gap(tmp_path):
    repo = copy_repo(tmp_path)
    git(repo, "init", "-q")
    (repo / "src" / "mcf" / "backtest").mkdir(parents=True)
    (repo / "src" / "mcf" / "backtest" / "run.py").write_text("# run\n")
    git(repo, "add", "src")
    git(repo, "commit", "-q", "-m", "run first")
    git(repo, "add", "docs", "results")
    git(repo, "commit", "-q", "-m", "ADR later")
    gaps = review(repo, run_tests=False)
    assert "adr_before_run" in names(gaps)


def test_skill_command_sets_the_python_path():
    skill = (ROOT / "skills" / "forecast-backtest-review" / "SKILL.md").read_text()
    assert "PYTHONPATH=src python -m mcf.backtest.review --repo ." in skill
    for words in ("data rules 3 and 6", "84-day window", "10,000 runs", "no issue rows"):
        assert words in skill, words
