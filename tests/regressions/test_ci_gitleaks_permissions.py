"""Regression (MCF-7, 2026-10-28): gitleaks failed on PR #1.

Cause: gitleaks-action reads the PR commit list (GET /pulls/{n}/commits).
The workflow granted only `contents: read`, so the call failed on the
private repository and the secret scan job failed with no leak found.
"""

from pathlib import Path

CI = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def _security_job() -> str:
    text = CI.read_text()
    return text[text.index("  security:") :]


def test_security_job_can_read_pull_requests():
    job = _security_job()
    assert "pull-requests: read" in job


def test_gitleaks_does_not_need_write_access_for_comments():
    job = _security_job()
    assert 'GITLEAKS_ENABLE_COMMENTS: "false"' in job
