"""MCF-8 acceptance checks: the back-test method ADR (G4, R2).

The back-test may start only when this ADR exists, has each required part,
and is accepted by the PM (CLAUDE.md, "Method before results").
"""

import re
from pathlib import Path

ADR = Path(__file__).resolve().parents[1] / "docs" / "adr" / "0002-backtest-method.md"

REQUIRED_SECTIONS = [
    "## Data rules",
    "## Forecast question",
    "## Forecast dates",
    "## Backlog sizes",
    "## History window",
    "## Runs and seed",
    "## Monte Carlo method",
    "## Velocity method",
    "## Metrics",
    "## Pass rules",
    "## Cases with no forecast",
    "## What is reported",
    "## Change rule",
]


def text() -> str:
    return ADR.read_text(encoding="utf-8")


def test_adr_has_each_required_section():
    missing = [s for s in REQUIRED_SECTIONS if s not in text()]
    assert missing == []


def test_adr_states_pass_band_of_d07():
    assert "75%" in text() and "95%" in text() and "D07" in text()


def test_adr_states_a_fixed_seed_and_run_count():
    assert re.search(r"Seed:\*\*\s*\d+", text())
    assert re.search(r"Runs:\*\*\s*[\d,]+", text())


def test_adr_is_accepted_with_a_pm_approval_date():
    assert re.search(r"\*\*Status:\*\* Accepted by the PM on \d{4}-\d{2}-\d{2}", text())
