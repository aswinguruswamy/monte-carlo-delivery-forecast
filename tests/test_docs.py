"""MCF-25 acceptance checks: README, method page, CITATION.cff, data terms (C2–C4, R10)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MSR = "10.1145/3524842.3528029"
ESEM = "10.1145/3544902.3546238"


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_citation_cff_is_valid_and_cites_both_papers():
    cff = yaml.safe_load(read("CITATION.cff"))
    assert cff["cff-version"] == "1.2.0"
    assert cff["license"] == "Apache-2.0"
    dois = {ref.get("doi") for ref in cff["references"]}
    assert {MSR, ESEM} <= dois
    titles = " ".join(ref["title"] for ref in cff["references"])
    assert "A Versatile Dataset of Agile Open Source Software Projects" in titles
    assert "On the Relationship Between Story Points and Development Effort" in titles


def test_citation_version_matches_the_package():
    from mcf import __version__

    assert yaml.safe_load(read("CITATION.cff"))["version"] == __version__


def test_readme_has_the_required_sections():
    readme = read("README.md")
    for heading in (
        "## Install",
        "## Use",
        "## How it works",
        "## Results",
        "## Limits",
        "## Data",
        "## Cite",
        "## Handover",
    ):
        assert f"\n{heading}" in readme, heading


def test_readme_states_the_data_terms_and_the_no_tracing_rule():
    readme = read("README.md")
    assert "https://github.com/SOLAR-group/TAWOS" in readme  # C3
    assert "subject to the TAWOS terms of use" in readme
    assert "individual contributors" in readme  # C2
    assert MSR in readme and ESEM in readme  # C4


def test_claude_rules_include_the_no_tracing_rule():
    assert "individual contributors" in read("CLAUDE.md")


def test_notice_cites_both_papers():
    notice = read("NOTICE")
    assert MSR in notice and ESEM in notice


def test_readme_results_equal_the_published_metrics():
    m = json.loads(read("results/metrics.json"))
    s = m["summary"]
    section = read("README.md").split("\n## Results")[1].split("\n## ")[0]
    rows = [r for r in section.splitlines() if r.startswith("| 1.") or r.startswith("| 2.")]
    verdict = {True: "**PASS**", False: "**FAIL**"}
    assert rows[0].endswith(f"| {verdict[s['measure_1_pass']]} |")
    assert rows[1].endswith(f"| {verdict[s['measure_2_pass']]} |")
    assert f"{s['calibration_85']:.1%}" in rows[0]
    assert f"{s['median_error_mc50']:g} days vs {s['median_error_velocity']:g} days" in rows[1]
    assert f"**{s['cases']:,}**" in section
    total = s["cases"] + s["no_forecast_cases"]
    assert (
        f"{s['no_forecast_cases']:,} of {total:,} cases ({s['no_forecast_share']:.1%})" in section
    )
    assert f"too early in {1 - s['calibration_85']:.1%}" in section
    lo, hi = m["bootstrap"]["median_error_difference_95ci"]
    assert f"{lo:g} to {hi:g} days" in section
    assert "docs/backtest-report.md" in section


def test_readme_limits_match_the_report():
    limits = read("README.md").split("\n## Limits")[1].split("\n## ")[0]
    for words in (
        "resolved as completed",
        "whatever its status",
        "Won't Fix (853)",
        "Invalid (335)",
        "mean points of that day",
        "knowledge of the future",
    ):
        assert words in limits, words


def test_readme_no_tracing_sentence_is_a_prohibition():
    assert "**Do not try to trace issues back to individual contributors.**" in read("README.md")


def test_readme_options_and_run_time_source():
    use = read("README.md").split("\n## Use")[1].split("\n## ")[0]
    assert "`--backlog N`" in use and "required" in use
    assert "20261028" in use
    data = read("README.md").split("\n## Data")[1].split("\n## ")[0]
    assert "python -m mcf.backtest.report" in data
    assert "measured on 2026-10-29" in data


def test_method_page_states_the_points_rules_and_d29_d30():
    method = read("docs/method.md")
    assert "mean points per value item in the window × N" in method  # D28 estimate
    assert "real points of the next N items" in method  # ADR Velocity method 2
    assert "D29" in method and "mean points of that day's items" in method
    assert "D30" in method and "2,000" in method and "20261028" in method
    assert "docs/adr/0002-backtest-method.md" in method or "adr/0002-backtest-method.md" in method


def test_method_page_explains_both_methods_and_the_pass_rules():
    method = read("docs/method.md")
    for words in ("Monte Carlo", "velocity", "back-test", "75%", "95%", "median", "84 days"):
        assert words in method, words
    assert "not certain" in method


def test_docs_do_not_overclaim():
    for name in ("README.md", "docs/method.md"):
        text = read(name).lower()
        for word in ("proves", "proven", "guarantee", "always correct", "will happen"):
            assert word not in text, (name, word)
