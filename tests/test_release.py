"""MCF-27 checks: release v1.0.0 (G7, G8); MCF-44: release v1.1.0; MCF-45: release v1.2.0.

AC1: the tag equals the package version, and a clean install works.
The tag is made after the PM's go; CI builds the wheel, installs it in a clean
environment with the lock file, and runs `mcf --help`.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.2.0"  # MCF-45


def test_package_version_is_the_release_version():
    from mcf import __version__

    assert __version__ == VERSION


def test_citation_has_the_version_and_a_release_date():
    cff = yaml.safe_load((ROOT / "CITATION.cff").read_text())
    assert cff["version"] == VERSION
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cff["date-released"]))


def test_changelog_has_the_release_and_the_known_limits():
    text = (ROOT / "CHANGELOG.md").read_text()
    assert f"## [{VERSION}]" in text
    assert "Measure 1" in text and "FAIL" in text  # published as it is (R3)
    assert "known limits" in text.lower()


def test_lock_file_pins_every_runtime_package_exactly():
    lines = [
        ln.split("#")[0].strip()
        for ln in (ROOT / "constraints.txt").read_text().splitlines()
        if ln.split("#")[0].strip()
    ]
    assert lines, "constraints.txt is empty"
    for ln in lines:
        assert re.fullmatch(r"[A-Za-z0-9_.\-]+==[A-Za-z0-9_.+\-]+", ln), ln
    names = {ln.split("==")[0].lower() for ln in lines}
    assert {"numpy", "pandas", "streamlit", "altair"} <= names
    assert "mcf" not in names


def test_ci_installs_with_the_lock_file_and_checks_a_clean_wheel_install():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert ci.count('pip install -e ".[dev,web]" -c constraints.txt') == 2
    assert "python -m build --wheel" in ci or "pip wheel" in ci
    assert "mcf --help" in ci


def test_readme_names_the_release():
    readme = (ROOT / "README.md").read_text()
    assert f"**Status:** version {VERSION}" in readme


def test_changelog_date_equals_the_citation_date():
    cff = yaml.safe_load((ROOT / "CITATION.cff").read_text())
    text = (ROOT / "CHANGELOG.md").read_text()
    assert f"## [{VERSION}] - {cff['date-released']}" in text


def test_clean_install_runs_on_both_pythons_with_a_time_limit():
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text())
    job = ci["jobs"]["package"]
    assert job["strategy"]["matrix"]["python-version"] == ["3.11", "3.12"]
    assert job["timeout-minutes"] <= 30


def test_every_install_command_uses_the_lock_file():
    readme = (ROOT / "README.md").read_text()
    assert 'pip install -e ".[web]" -c constraints.txt' in readme
    evalwf = (ROOT / ".github" / "workflows" / "eval.yml").read_text()
    assert "pip install -e . -c constraints.txt" in evalwf


def _section(version: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text()
    start = text.index(f"## [{version}]")
    end = text.find("\n## [", start + 1)
    return text[start : end if end > 0 else None]


def test_the_1_1_0_entry_keeps_the_backtest_and_names_the_ai_prompt():
    """MCF-44: the back-test is unchanged since v1.0.0; the AI prompt is version 5."""
    entry = _section("1.1.0")
    assert "69.0%" in entry and "7,692" in entry and "unchanged" in entry
    assert "prompt version 5" in entry
    for part in ("### Added", "### Changed", "### Fixed", "### Known limits"):
        assert part in entry, part
    assert (
        "[1.1.0]: https://github.com/aswinguruswamy/monte-carlo-delivery-forecast/releases/tag/v1.1.0"
        in (ROOT / "CHANGELOG.md").read_text()
    )


def test_the_lock_file_header_names_the_release():
    assert f"Lock file for v{VERSION}" in (ROOT / "constraints.txt").read_text().splitlines()[0]


def test_the_1_1_0_entry_has_the_ai_evaluation_result():
    """MCF-44: the evaluation on prompt version 5 ran before the tag (go condition)."""
    entry = _section("1.1.0")
    assert "To run before the tag" not in entry
    assert "**PASS** on 2026-11-08" in entry and "30 of 30" in entry


def test_the_1_2_0_entry_has_both_backtests_the_evaluation_and_the_limits():
    """MCF-45: v1 unchanged; v2 published as it is (R3), with its limits (D54.3)."""
    entry = _section("1.2.0")
    for part in ("### Added", "### Changed", "### Fixed", "### Known limits"):
        assert part in entry, part
    assert "[Unreleased]" not in (ROOT / "CHANGELOG.md").read_text()
    # v1 result unchanged; v2 result with its warnings
    assert "69.0%" in entry and "7,692" in entry
    assert "75.0%" in entry and "not robust" in entry and "73.5%" in entry
    assert "D54.3" in entry
    # AI evaluation evidence on the merged code (prompt version 5 unchanged)
    assert "**PASS** on 2026-11-09" in entry and "30 of 30" in entry
    assert "prompt version 5" in entry
    assert "light-dark()" in entry  # older browsers (D48.1)
    assert (
        "[1.2.0]: https://github.com/aswinguruswamy/monte-carlo-delivery-forecast/releases/tag/v1.2.0"
        in (ROOT / "CHANGELOG.md").read_text()
    )


# --- Review MCF-45 ------------------------------------------------------------------------------


def test_the_1_2_0_entry_numbers_come_from_the_metrics_files():
    import json

    v1 = json.loads((ROOT / "results" / "metrics.json").read_text())["summary"]
    full = json.loads((ROOT / "results" / "metrics-full.json").read_text())
    a, c = full["any"]["summary"], full["completed"]["summary"]
    ci = full["any"]["bootstrap"]["calibration_85_95ci"]
    p = full["any"]["pointed_only"]
    entry = _section("1.2.0")
    hits = round(a["calibration_85"] * a["cases"])
    for text in (
        f"{v1['calibration_85']:.1%} of {v1['cases']:,} cases",
        f"{a['projects']} projects, {a['cases']:,} scored cases",
        f"{a['calibration_85']:.1%} ({hits:,} of {a['cases']:,})",
        f"({ci[0]:.1%} to {ci[1]:.1%})",
        f"it is {c['calibration_85']:.1%} (**FAIL**)",
        f"{a['median_error_mc50']:g} days vs {a['median_error_velocity']:g} days "
        f"on {a['measure_2_cases']:,} cases",
        f"the {p['measure_2_cases']:,} fully pointed cases with a velocity date: "
        f"{p['median_error_mc50']:g} days vs {p['median_error_velocity']:g} days",
    ):
        assert text in entry, text
    assert "**FAIL**" in entry and "not certain" in entry
    # v2 "done" includes Won't Fix and Duplicate; no new demo video (D55)
    assert "Won't Fix" in entry and "D55" in entry


def test_the_readme_ai_result_is_the_release_evaluation_and_dates_match():
    cff = yaml.safe_load((ROOT / "CITATION.cff").read_text())
    readme = (ROOT / "README.md").read_text()
    assert f"released {cff['date-released']}" in readme
    assert "**AI evaluation (measure 3): PASS** on 2026-11-09" in readme
    assert "prompt version 5" in readme
    assert "PASS** on 2026-11-09" in _section(VERSION)


def test_the_citation_and_readme_name_the_full_tawos_dataset():
    cff = yaml.safe_load((ROOT / "CITATION.cff").read_text())
    assert any(r.get("doi") == "10.5522/04/21308124" for r in cff["references"])
    intro = (ROOT / "README.md").read_text().split("## Install")[0]
    assert "39" in intro and "full" in intro


def test_the_demo_page_says_1_2_0_has_no_new_video():
    demo = (ROOT / "docs" / "demo.md").read_text()
    assert "**v1.2.0:** no new video (D55" in demo
