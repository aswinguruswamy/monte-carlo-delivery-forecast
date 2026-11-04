"""MCF-36 checks: "How this forecast works", the footer and the README "Try it" line.

The back-test figures on the page must equal the published results
(`results/metrics.json`, `docs/backtest-report.md`), so the page can never show a
number that the back-test did not produce (CLAUDE.md AI rule 1, R3).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import mcf
from mcf.web import logic
from mcf.web.backtest_facts import BACKTEST

ROOT = Path(__file__).resolve().parents[1]
METRICS = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
REPORT = (ROOT / "docs" / "backtest-report.md").read_text(encoding="utf-8")


# --- The figures come from the back-test --------------------------------------------------


def test_backtest_facts_equal_the_published_metrics():
    s = METRICS["summary"]
    assert BACKTEST.cases == s["cases"] == 7692
    assert BACKTEST.projects == s["projects"] == 29
    assert BACKTEST.calibration_85 == round(s["calibration_85"], 3)
    assert BACKTEST.measure_1_pass is s["measure_1_pass"] is False


def test_backtest_facts_match_the_report():
    assert f"Cases scored: {BACKTEST.cases:,} from {BACKTEST.projects} projects" in REPORT
    assert f"| {BACKTEST.calibration_85 * 100:.1f}% | 75–95% | **FAIL** |" in REPORT


def test_the_page_figures_are_computed_from_the_facts():
    assert logic.done_by_85_of_100() == 69  # 69.0% → 69 of 100
    assert logic.later_than_85_of_100() == 31
    assert logic.about_one_in(logic.later_than_85_of_100()) == "about 1 in 3"


@pytest.mark.parametrize(
    "later, text", [(31, "about 1 in 3"), (25, "about 1 in 4"), (50, "about 1 in 2")]
)
def test_about_one_in(later, text):
    assert logic.about_one_in(later) == text


# --- "How this forecast works" -------------------------------------------------------------


def test_the_section_has_2_parts_and_keeps_monte_carlo_and_the_backtest_apart():
    parts = logic.how_it_works()
    assert [p.title for p in parts][0] == "How the dates are made (Monte Carlo)"
    assert parts[1].title.startswith("How accurate is it? (back-test")
    monte_carlo, backtest = parts[0].body, parts[1].body
    assert "10,000 tries" in monte_carlo and "back-test" not in monte_carlo.lower()
    assert "29 real open-source projects" in backtest and "10,000 tries" not in backtest


def test_the_backtest_title_shows_the_warning_without_opening_it():
    """D46 condition: the warning about the 85% date is visible on the page."""
    title = logic.how_it_works()[1].title
    assert title == (
        "How accurate is it? (back-test: the 85% date was too early about 1 in 3 times)"
    )


def test_the_backtest_part_says_what_a_forecast_is_and_the_figures():
    body = logic.how_it_works()[1].body
    assert "A forecast is one prediction of when the next 10, 25 or 50 work items" in body
    assert "**7,692** past forecasts checked" in body
    assert "**69 of 100** done by the 85% date (target: 75 to 95 of 100)" in body
    assert "Use the 95% date when a late finish costs a lot." in body
    assert "published as it is, although it missed the target" in body


def test_the_monte_carlo_part_has_5_steps():
    body = logic.how_it_works()[0].body
    assert len(re.findall(r"^\d\. ", body, flags=re.M)) == 5
    assert "Story points are not needed for these dates." in body


def test_the_chart_caption_points_to_the_section():
    assert 'see "How this forecast works"' in logic.CHART_CAPTION


def test_the_sidebar_points_to_the_page_and_does_not_repeat_the_warning():
    side = logic.SIDEBAR
    assert 'See "How accurate is it?" on the page.' in side
    assert "1 time in 3" not in side and "1 in 3" not in side


def test_the_page_never_calls_the_50_date_certain():
    text = " ".join(p.title + " " + p.body for p in logic.how_it_works())
    assert "certain" not in text.lower()


# --- Footer --------------------------------------------------------------------------------


def test_footer_text_and_links():
    foot = logic.footer_markdown()
    assert (
        "Built by Aswin Guruswamy with Claude. Python and Streamlit. Open source (Apache 2.0)."
        in foot
    )
    assert "TAWOS, 29 open-source projects (Tawosi et al., MSR 2022)" in foot
    assert "(https://github.com/aswinguruswamy/monte-carlo-delivery-forecast)" in foot
    assert "docs/backtest-report.md)" in foot
    assert f"Version {mcf.__version__}" in foot


# --- README --------------------------------------------------------------------------------


def test_readme_has_the_try_it_line_under_the_title():
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# ")
    first_text = next(line for line in lines[1:] if line.strip())
    assert first_text == (
        "**Try it:** [mcf-forecast.streamlit.app](https://mcf-forecast.streamlit.app)"
        " — no install, sample data included."
    )
