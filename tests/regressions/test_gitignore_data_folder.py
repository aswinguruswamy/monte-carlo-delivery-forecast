"""Regression (MCF-10, 2026-10-28): `.gitignore` had `data/`, which ignores
every folder named data, including the code package `src/mcf/data/`.
Only the root `data/` folder (the downloaded dataset, D08) must be ignored.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ignored(path: str) -> bool:
    # --no-index: also test tracked paths against the rules (MCF-10 review).
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", path], cwd=ROOT, check=False
    )
    return result.returncode == 0


def test_code_package_named_data_is_not_ignored():
    assert not ignored("src/mcf/data/download.py")
    assert not ignored("src/mcf/data/tawos_manifest.json")
    assert not ignored("src/mcf/data/new_module.py")  # untracked path too


def test_downloaded_dataset_folder_is_ignored():
    assert ignored("data/MESOS.csv")
