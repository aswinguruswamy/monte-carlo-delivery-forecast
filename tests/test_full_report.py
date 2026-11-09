"""MCF-28 checks: the side-by-side report of the v1 (extract) and v2 (full TAWOS) back-test.

Every number comes from the two metrics files. The data here is made up.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from mcf.backtest.full import full_metrics, run_full
from mcf.backtest.full_report import FullReportError, render_full_report

ROOT = Path(__file__).resolve().parents[1]
V1 = json.loads((ROOT / "results" / "metrics.json").read_text())
HEADER = "Project_Key,Type,Status,Resolution,Resolution_Date,Story_Point\n"
INFO = {
    "code_commit": "abc1234",
    "export_sha256": "0" * 64,
    "rows": 400,
    "runs": 200,
    "cases_any_sha256": "1" * 64,
    "cases_completed_sha256": "2" * 64,
}


@pytest.fixture(scope="module")
def v2(tmp_path_factory) -> dict:
    p = tmp_path_factory.mktemp("d") / "issues.csv"
    start = date(2026, 1, 1)
    lines = [
        f"AA,Story,Closed,{'Fixed' if d % 3 else 'Duplicate'},{start + timedelta(days=d)} 10:00:00,"
        f"{'' if d % 4 == 0 else '3'}\n"
        for d in range(200)
    ] + [f"BB,Story,Closed,Fixed,{start + timedelta(days=2 * d)} 10:00:00,\n" for d in range(100)]
    p.write_text(HEADER + "".join(lines), encoding="utf-8")
    out = {}
    for rule in ("any", "completed"):
        out[rule] = full_metrics(*run_full(p, done_rule=rule, runs=200))
    return out


def report(v2: dict) -> str:
    return render_full_report(V1, v2, INFO)


def test_the_summary_puts_v1_and_v2_side_by_side(v2):
    text = report(v2)
    assert text.startswith("# Back-test report — full TAWOS data (v2) next to the extract (v1)")
    s = v2["any"]["summary"]
    row = next(line for line in text.splitlines() if line.startswith("| 1. Calibration"))
    assert "69.0%" in row  # v1
    assert f"{s['calibration_85']:.1%}" in row
    assert ("**PASS**" if s["measure_1_pass"] else "**FAIL**") in row


def test_completed_only_is_shown_next_to_it_for_information(v2):
    text = report(v2)
    c = v2["completed"]["summary"]
    assert "Done = completed only (information)" in text
    assert f"{c['calibration_85']:.1%}" in text


def test_measure_2_names_its_cases_and_the_fully_pointed_view(v2):
    text = report(v2)
    s = v2["any"]["summary"]
    assert f"{s['measure_2_cases']:,} cases with a velocity date" in text
    assert "Fully pointed cases (information)" in text


def test_counts_per_project_and_the_d54_rules_are_in_the_report(v2):
    text = report(v2)
    assert "| Project | Issues read | No resolution date | Not a value item |" in text
    assert "| AA | 200 |" in text
    for word in ("D54.1", "D54.2", "not certain", "R3"):
        assert word in text


def test_no_issue_rows_or_keys(v2):
    text = report(v2)
    assert "AA-1" not in text and "10:00:00" not in text and "Story," not in text


def test_missing_run_information_is_an_error(v2):
    with pytest.raises(FullReportError, match="code_commit"):
        render_full_report(V1, v2, {k: v for k, v in INFO.items() if k != "code_commit"})


def test_no_measure_2_case_shows_a_dash(v2):
    bare = json.loads(json.dumps(v2))
    bare["any"]["summary"].update(
        measure_2_cases=0, measure_2_pass=None, median_error_mc50=None, median_error_velocity=None
    )
    row = next(
        line for line in render_full_report(V1, bare, INFO).splitlines() if line.startswith("| 2.")
    )
    assert "no case" in row
