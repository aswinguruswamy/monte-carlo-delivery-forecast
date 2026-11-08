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
    # editable install: the app then finds examples/sample_team.csv in the checkout
    # (a normal install puts the package in site-packages, and the sample is lost)
    # the public demo uses the release lock file too (D20, D26)
    assert lines == ["-c constraints.txt", "-e .[web]"]


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
        "wake",
        "?embed=true",
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


def test_the_sample_file_is_found_from_the_package_path():
    from mcf.web import logic

    assert logic.SAMPLE_FILE == ROOT / "examples" / "sample_team.csv"
    assert logic.sample_bytes() is not None


def test_videos_and_cloud_secrets_are_never_committed():
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    assert "*.mp4" in ignored
    assert ".streamlit/secrets.toml" in ignored


def test_a_url_is_used_as_given():
    source = (ROOT / "scripts" / "browser_check.py").read_text()
    assert "url = args.url\n" in source


def test_the_record_script_follows_the_v1_1_page():
    """MCF-43: since MCF-41 the section titles are expander labels, not stHeading."""
    source = (ROOT / "scripts" / "record_demo.py").read_text()
    assert "stHeading" not in source
    assert ".st-key-section-" in source  # scrolls by the section boxes
    assert "close_and_open(" in source  # shows that a section can close and open
    assert 'locator("summary").get_by_text(' in source  # not the hidden heading
    # the help sidebar also says "More options" (MCF-34), so click only the expander label
    assert 'page.get_by_text("More options")' not in source
