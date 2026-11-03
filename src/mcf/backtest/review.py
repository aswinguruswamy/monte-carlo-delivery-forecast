"""Forecast back-test review: the machine checks (MCF-20, D13).

`python -m mcf.backtest.review --repo .` lists each gap it finds, or says that
it found none. The skill `skills/forecast-backtest-review/SKILL.md` runs this
script and adds the judgement checks that a script cannot make.

Checks:
- files_present: the ADR, results/metrics.json and docs/backtest-report.md can be read.
- adr_locked: ADR 0002 has its accepted SHA-256 (D21.1).
- adr_before_run: the last ADR change is in git history before the first back-test code.
- pass_rules: measure 1 and 2 in metrics.json follow the pass rules (D07, ADR 0002).
- report_matches_metrics: the report equals a fresh render of metrics.json.
- failed_measure_shown: each failed measure shows as FAIL in the report summary (R3).
- required_sections: the report has each section that ADR 0002 asks for.
- project_rows: each project has its own row, and sizes with no case are listed.
- future_data_tests: the "no data after day t" tests pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from mcf.backtest.metrics import calibration_passes, error_passes
from mcf.backtest.report import ReportError, render_report

ACCEPTED_SHA256 = "b8ae61562465fb71ea234a447534af47f12f1e995895dbf0204f6e89b41f603b"
ADR = Path("docs/adr/0002-backtest-method.md")
METRICS = Path("results/metrics.json")
REPORT = Path("docs/backtest-report.md")
RUN_CODE = "src/mcf/backtest/run.py"
SECTIONS = (
    "## Summary",
    "## Results by backlog size",
    "## Results by project",
    "## Information only",
    "## Limits",
    "## Data and method",
    "## Reproduce",
)
FUTURE_TESTS = ("tests/test_backtest_run.py", "-k", "future or window or leak")


@dataclass(frozen=True)
class Gap:
    check: str
    detail: str


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _adr_before_run(repo: Path) -> Gap | None:
    try:
        adr_commit = _git(repo, "log", "-1", "--format=%H", "--", str(ADR))
        added = _git(repo, "log", "--diff-filter=A", "--format=%H", "--", RUN_CODE).splitlines()
        if not adr_commit or not added:
            return Gap("adr_before_run", "the git history has no ADR or no back-test code")
        run_commit = added[-1]
        subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", adr_commit, run_commit],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return Gap("adr_before_run", "no git history shows the ADR before the first back-test code")
    if adr_commit == run_commit:
        return Gap("adr_before_run", "the ADR changed in the same commit as the back-test code")
    return None


def info_from_report(report: str) -> dict:
    """Read the run information that the report prints (see report.render_report)."""

    def find(pattern: str) -> str:
        m = re.search(pattern, report)
        if not m:
            raise ReportError(f"the report has no line for {pattern!r}")
        return m.group(1)

    return {
        "code_commit": find(r"Code commit of the run: `([^`]+)`"),
        "cases_sha256": find(r"`cases.csv` SHA-256: `([0-9a-f]{64})`"),
        "projects_sha256": find(r"`projects.csv` SHA-256: `([0-9a-f]{64})`"),
        "rows_read": int(find(r"([\d,]+) rows read").replace(",", "")),
        "rows_no_date": int(find(r"(\d+) rows with no resolution date")),
    }


def review(repo: str | Path, *, run_tests: bool = True) -> list[Gap]:
    repo = Path(repo)
    gaps: list[Gap] = []
    try:
        adr_bytes = (repo / ADR).read_bytes()
        metrics = json.loads((repo / METRICS).read_text(encoding="utf-8"))
        report = (repo / REPORT).read_text(encoding="utf-8")
        s = metrics["summary"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [Gap("files_present", f"cannot read the review files: {type(exc).__name__}")]

    if hashlib.sha256(adr_bytes).hexdigest() != ACCEPTED_SHA256:
        gaps.append(Gap("adr_locked", "ADR 0002 differs from the accepted text (D21.1)"))
    gap = _adr_before_run(repo)
    if gap:
        gaps.append(gap)

    m1 = calibration_passes(s["calibration_85"])
    m2 = error_passes(s["median_error_mc50"], s["median_error_velocity"])
    if (m1, m2) != (s["measure_1_pass"], s["measure_2_pass"]):
        gaps.append(Gap("pass_rules", "a pass or fail in metrics.json does not follow the rules"))

    try:
        if render_report(metrics, info_from_report(report)) != report:
            gaps.append(Gap("report_matches_metrics", "the report differs from metrics.json"))
    except (ReportError, KeyError, TypeError, ValueError):
        gaps.append(Gap("report_matches_metrics", "the report cannot be rebuilt from metrics.json"))

    summary = report.split("## Summary", 1)[-1].split("\n## ", 1)[0]
    rows = [ln for ln in summary.splitlines() if ln.startswith(("| 1.", "| 2."))]
    for row, passed in zip(rows, (m1, m2), strict=False):
        if not passed and "**FAIL**" not in row:
            gaps.append(Gap("failed_measure_shown", f"a failed measure is not shown: {row[:40]}"))
    if len(rows) != 2:
        gaps.append(Gap("failed_measure_shown", "the summary does not show both measures"))

    missing = [h for h in SECTIONS if f"\n{h}\n" not in report]
    if missing:
        gaps.append(Gap("required_sections", "missing: " + ", ".join(missing)))

    projects = report.split("## Results by project", 1)[-1].split("\n## ", 1)[0]
    absent = [p for p in metrics["by_project"] if f"\n| {p} |" not in projects]
    if absent:
        gaps.append(Gap("project_rows", "no row for: " + ", ".join(absent)))
    if "Projects with no case for a size N:" not in report:
        gaps.append(Gap("project_rows", "sizes with no case are not listed"))

    if run_tests:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *FUTURE_TESTS],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            gaps.append(Gap("future_data_tests", "the no-future-data tests fail or are missing"))
    return gaps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mcf.backtest.review", description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."), help="repository folder")
    parser.add_argument("--no-tests", action="store_true", help="skip the pytest check")
    args = parser.parse_args(argv)
    gaps = review(args.repo, run_tests=not args.no_tests)
    for g in gaps:
        print(f"GAP {g.check}: {g.detail}")
    if not gaps:
        print("No gap found by the machine checks. Do the judgement checks in the skill next.")
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
