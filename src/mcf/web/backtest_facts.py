"""Published back-test figures shown on the web page (MCF-36).

These values come from `results/metrics.json` (summary) and
`docs/backtest-report.md`. A test checks that they match, so the page cannot
show a figure that the back-test did not produce (CLAUDE.md AI rule 1, R3).
The package does not ship the results file, so the values live here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestFacts:
    cases: int  # scored forecast cases
    no_forecast: int  # cases with too little history (counted, not scored)
    projects: int
    calibration_85: float  # share of cases done by the 85% date, 3 decimals
    measure_1_pass: bool  # D07: 75–95%


BACKTEST = BacktestFacts(
    cases=7692, no_forecast=903, projects=29, calibration_85=0.690, measure_1_pass=False
)

# MCF v2 spec R3.1: the latest test, on the full TAWOS data (results/metrics-full.json,
# "any" summary; ADR 0003). A test checks these values against the file.
BACKTEST_FULL = BacktestFacts(
    cases=22619, no_forecast=536, projects=39, calibration_85=0.750, measure_1_pass=True
)
