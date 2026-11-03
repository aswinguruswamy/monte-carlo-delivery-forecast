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
