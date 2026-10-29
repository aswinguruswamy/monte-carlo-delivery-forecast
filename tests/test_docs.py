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
    s = json.loads(read("results/metrics.json"))["summary"]
    section = read("README.md").split("\n## Results")[1].split("\n## ")[0]
    assert f"{s['calibration_85']:.1%}" in section
    assert re.search(r"\*\*FAIL\*\*|did not pass", section)  # measure 1 shown as failed
    assert f"{s['median_error_mc50']:g} days" in section
    assert f"{s['median_error_velocity']:g} days" in section
    assert f"{s['cases']:,}" in section
    assert "docs/backtest-report.md" in section


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
