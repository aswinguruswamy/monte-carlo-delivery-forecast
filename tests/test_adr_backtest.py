"""MCF-8 acceptance checks: the back-test method ADR (G4, R2).

The back-test may start only when this ADR exists, has each required part,
and is accepted by the PM (CLAUDE.md, "Method before results").
"""

import re
from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    "rule",
    [
        "*N* = **10, 25 and 50**",  # backlog sizes
        "a forecast date every 14 days",  # forecast dates
        "**84 days from day *t* − 83 to day *t***",  # history window
        "**Runs:** 10,000",
        "**Seed:** 20261028",
        "SeedSequence([20261028, p, t.toordinal(), N])",  # per-case stream
        'method="inverted_cdf"',  # percentile rule
        "**median** absolute error",  # measure 2
        "from **75% to 95%**, both ends included (D07)",  # measure 1 band
        "Equal medians mean measure 2 fails",
    ],
)
def test_adr_fixes_each_method_rule(rule):
    assert rule in text()


def test_adr_is_accepted_with_a_pm_approval_date():
    status = next(line for line in text().splitlines() if line.startswith("**Status:**"))
    assert re.search(r"Accepted by the PM on \d{4}-\d{2}-\d{2}", status)
    assert "proposed" not in status.lower(), "an amendment waits for PM approval"
