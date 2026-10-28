"""MCF-7 acceptance checks: repository hygiene and CI configuration.

These checks run in CI on each pull request. They prove the setup rules
from the build-setup skill and the Test Plan (groups 5 and 6).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"

# Data file types that must never be committed (D08, NFR7).
DATA_SUFFIXES = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".parquet",
    ".sql",
    ".zip",
    ".gz",
    ".db",
    ".sqlite",
}
# Small made-up samples are allowed only here.
ALLOWED_DATA_DIRS = ("examples/", "tests/fixtures/", "eval/samples/")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line]


def test_package_imports_and_has_version():
    import mcf

    assert isinstance(mcf.__version__, str)
    assert mcf.__version__.count(".") == 2


def test_env_file_is_ignored_and_example_has_no_values():
    gitignore = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in gitignore
    example = (ROOT / ".env.example").read_text().splitlines()
    for line in example:
        if line.strip() and not line.startswith("#"):
            name, _, value = line.partition("=")
            assert name.strip(), "each line names a secret"
            assert value.strip() == "", f"{name} has a value in .env.example"


def test_no_env_file_is_tracked():
    assert ".env" not in tracked_files()


def test_no_dataset_files_are_tracked():
    bad = [
        f
        for f in tracked_files()
        if Path(f).suffix.lower() in DATA_SUFFIXES and not f.startswith(ALLOWED_DATA_DIRS)
    ]
    assert bad == [], f"dataset files must not be committed (D08): {bad}"


@pytest.mark.parametrize(
    "needle",
    [
        "pull_request",  # runs on each PR
        '"3.11"',  # supported versions (NFR9)
        '"3.12"',
        "ruff check",  # style
        "pytest",  # tests
        "gitleaks",  # secret scan (NFR6)
        "pip-audit",  # dependency scan
        "pip-licenses",  # licence scan
    ],
)
def test_ci_runs_each_required_check(needle):
    assert needle in CI.read_text()


def test_ci_actions_are_pinned_to_commits():
    for line in CI.read_text().splitlines():
        stripped = line.strip().lstrip("- ")
        if stripped.startswith("uses:"):
            ref = stripped.split("@", 1)[1].split()[0]
            assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), line


def test_dependency_alerts_are_configured():
    text = (ROOT / ".github" / "dependabot.yml").read_text()
    assert "package-ecosystem: pip" in text
    assert "package-ecosystem: github-actions" in text


def test_stack_adr_names_versions():
    text = (ROOT / "docs" / "adr" / "0001-stack.md").read_text()
    for lib in ("Python", "numpy", "pandas", "pytest", "ruff"):
        assert lib in text
