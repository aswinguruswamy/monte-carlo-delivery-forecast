"""MCF-7 acceptance checks: repository hygiene and CI configuration.

These checks run in CI on each pull request. They prove the setup rules
from the build-setup skill and the Test Plan (groups 5 and 6).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CI_FILE = ROOT / ".github" / "workflows" / "ci.yml"

# Data file types that must never be committed (D08, NFR7).
DATA_SUFFIXES = {
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".xlsx",
    ".xls",
    ".parquet",
    ".feather",
    ".arrow",
    ".pkl",
    ".pickle",
    ".npy",
    ".npz",
    ".h5",
    ".hdf5",
    ".sql",
    ".db",
    ".sqlite",
    ".zip",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".tar",
}
# Small made-up samples are allowed only in these folders, and only when small.
ALLOWED_DATA_DIRS = ("examples/", "tests/fixtures/", "eval/samples/")
MAX_SAMPLE_BYTES = 100 * 1024
# Named metadata files that hold no data rows (file names, checksums, counts only).
METADATA_FILES = {
    "src/mcf/data/tawos_manifest.json",
    "results/metrics.json",  # summary numbers only (MCF-19)
}
REQUIRED_PYTHONS = ["3.11", "3.12"]


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line]


def dataset_violations(files: list[str], size_of) -> list[str]:
    """Return the tracked files that break the no-dataset rule (D08)."""
    bad = []
    for f in files:
        if Path(f).suffix.lower() not in DATA_SUFFIXES:
            continue
        if f in METADATA_FILES and size_of(f) <= MAX_SAMPLE_BYTES:
            continue
        if not f.startswith(ALLOWED_DATA_DIRS) or size_of(f) > MAX_SAMPLE_BYTES:
            bad.append(f)
    return bad


def env_violations(files: list[str]) -> list[str]:
    return [f for f in files if Path(f).name.startswith(".env") and Path(f).name != ".env.example"]


def load_ci() -> dict:
    data = yaml.safe_load(CI_FILE.read_text(encoding="utf-8"))
    # PyYAML reads the bare key `on` as the boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return data


def run_commands(job: dict) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


# --- package -----------------------------------------------------------------


def test_package_imports_and_has_version():
    import mcf

    assert isinstance(mcf.__version__, str)
    assert mcf.__version__.count(".") == 2


# --- secrets (NFR6) ----------------------------------------------------------


def test_env_files_are_ignored_and_example_has_no_values():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env*" in gitignore
    assert "!.env.example" in gitignore
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, _, value = line.partition("=")
            assert name.strip(), "each line names a secret"
            assert value.strip() == "", f"{name} has a value in .env.example"


def test_no_env_file_is_tracked():
    assert env_violations(tracked_files()) == []


@pytest.mark.parametrize("name", [".env", ".env.local", "config/.env.prod"])
def test_env_rule_catches_env_files(name):
    assert env_violations([name, ".env.example"]) == [name]


# --- data (D08, NFR7) --------------------------------------------------------


def test_no_dataset_files_are_tracked():
    bad = dataset_violations(tracked_files(), lambda f: (ROOT / f).stat().st_size)
    assert bad == [], f"dataset files must not be committed (D08): {bad}"


@pytest.mark.parametrize(
    "path, size",
    [
        ("tawos.csv", 10),  # data file outside the sample folders
        ("data/tawos.json", 10),
        ("tawos.7z", 10),
        ("model.pkl", 10),
        ("tests/fixtures/tawos_full.csv", 5_000_000),  # too large for a sample
    ],
)
def test_dataset_rule_catches_data_files(path, size):
    assert dataset_violations([path], lambda f: size) == [path]


def test_dataset_rule_allows_small_samples_and_code():
    files = ["tests/fixtures/tiny.csv", "examples/sample.csv", "src/mcf/__init__.py"]
    assert dataset_violations(files, lambda f: 2_000) == []


# --- CI (Test Plan groups 5 and 6) -------------------------------------------


def test_ci_runs_on_each_pull_request():
    assert "pull_request" in load_ci()["on"]


def test_ci_tests_run_on_each_supported_python():
    job = load_ci()["jobs"]["test"]
    assert job["strategy"]["matrix"]["python-version"] == REQUIRED_PYTHONS
    commands = "\n".join(run_commands(job))
    assert "ruff check ." in commands
    assert "ruff format --check ." in commands
    assert "pytest" in commands


def test_ci_runs_each_security_scan():
    job = load_ci()["jobs"]["security"]
    uses = [step.get("uses", "") for step in job["steps"]]
    assert any(u.startswith("gitleaks/gitleaks-action@") for u in uses)
    commands = "\n".join(run_commands(job))
    assert "pip-audit" in commands
    assert "pip-licenses" in commands and "--fail-on" in commands
    # D19: scan runtime dependencies only, by exact licence name.
    assert "--python /tmp/runtime/bin/python" in commands
    assert "--partial-match" not in commands


def test_ci_actions_are_pinned_to_commits():
    for job in load_ci()["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                ref = step["uses"].split("@", 1)[1]
                assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), step


def test_dependency_alerts_are_configured():
    data = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = {u["package-ecosystem"] for u in data["updates"]}
    assert {"pip", "github-actions"} <= ecosystems


def test_stack_adr_names_libraries_and_python_versions():
    text = (ROOT / "docs" / "adr" / "0001-stack.md").read_text(encoding="utf-8")
    for name in ("numpy", "pandas", "pytest", "ruff", "pip-audit", "pip-licenses", "gitleaks"):
        assert name in text
    for version in REQUIRED_PYTHONS:
        assert f"Python {version}" in text


def checksum_violations(files: list[str], sha_of, dataset: set[str]) -> list[str]:
    """Return the tracked files whose SHA-256 is a dataset file's SHA-256 (D08)."""
    return [f for f in files if sha_of(f) in dataset]


def test_no_tracked_file_matches_a_dataset_checksum():
    """D08: catches a dataset file even if it is renamed (follow-up from the MCF-7 review)."""
    import hashlib

    from mcf.data.download import load_manifest

    dataset = {f["sha256"] for f in load_manifest()["files"]}
    files = [f for f in tracked_files() if (ROOT / f).is_file()]
    hits = checksum_violations(
        files, lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest(), dataset
    )
    assert hits == []


def test_checksum_rule_catches_a_renamed_dataset_file():
    sha = {"docs/notes.txt": "aaa", "src/x.py": "bbb", "renamed_mesos.md": "ccc"}
    assert checksum_violations(list(sha), sha.get, {"ccc"}) == ["renamed_mesos.md"]
