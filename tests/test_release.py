"""MCF-27 checks: release v1.0.0 (G7, G8).

AC1: the tag equals the package version, and a clean install works.
The tag is made after the PM's go; CI builds the wheel, installs it in a clean
environment with the lock file, and runs `mcf --help`.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"


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
