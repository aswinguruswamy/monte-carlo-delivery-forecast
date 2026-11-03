"""MCF-26 checks: the demo on Streamlit Community Cloud, and the recorded video (A5).

Community Cloud uses the first dependency file it finds, in this order:
uv.lock, Pipfile, environment.yml, requirements.txt, pyproject.toml.
So requirements.txt decides the install, and no file before it may exist.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DOC = ROOT / "docs" / "demo.md"


def test_requirements_installs_this_package_with_the_web_extra():
    lines = [
        ln.strip()
        for ln in (ROOT / "requirements.txt").read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert lines == [".[web]"]


def test_no_dependency_file_takes_priority_over_requirements_txt():
    for name in ("uv.lock", "Pipfile", "environment.yml"):
        assert not (ROOT / name).exists(), name


def test_requirements_holds_no_secret():
    text = (ROOT / "requirements.txt").read_text().lower()
    assert not re.search(r"key|token|secret|password|sk-", text)


def test_demo_doc_gives_the_deploy_settings():
    doc = DEMO_DOC.read_text()
    for needed in (
        "streamlit_app.py",
        "Python version: 3.12",
        "share.streamlit.io",
        "Do not add `ANTHROPIC_API_KEY`",
        "scripts/browser_check.py --url",
        "scripts/record_demo.py",
    ):
        assert needed in doc, needed


def test_browser_check_can_test_a_deployed_url():
    source = (ROOT / "scripts" / "browser_check.py").read_text()
    assert '"--url"' in source


def test_record_script_writes_an_mp4_without_a_key():
    source = (ROOT / "scripts" / "record_demo.py").read_text()
    assert "record_video_dir" in source
    assert ".mp4" in source
    assert 'k != "ANTHROPIC_API_KEY"' in source


def test_readme_links_the_demo_doc():
    assert "docs/demo.md" in (ROOT / "README.md").read_text()
