"""Regression (MCF-20, 2026-11-03): the review tests failed in CI only.

Cause: the test job checked out one commit (fetch-depth 1). The review's
adr_before_run check needs the git history to prove that ADR 0002 came before
the first back-test code, so the real repository showed a gap in CI.
"""

from pathlib import Path

import yaml

CI = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def test_the_test_job_checks_out_the_full_history():
    jobs = yaml.safe_load(CI.read_text())["jobs"]
    test_job = next(j for name, j in jobs.items() if name != "security")
    checkout = next(s for s in test_job["steps"] if "actions/checkout" in s.get("uses", ""))
    assert checkout.get("with", {}).get("fetch-depth") == 0
