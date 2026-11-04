"""MCF-33 checks: the plain-language page (D41, design "MCF Page With Help Panel").

These test the page text and helpers in mcf.web.logic. The page itself is
tested in test_web_app.py (AppTest) and scripts/browser_check.py (browser).
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, timedelta

import pytest

from mcf.result import ForecastFacts
from mcf.web import logic

T = date(2026, 9, 30)


def facts(**kw) -> ForecastFacts:
    base = dict(
        t=T,
        backlog=40,
        window_start=T - timedelta(days=83),
        window_end=T,
        items_done=60,
        mc50=date(2026, 11, 17),
        mc85=date(2026, 11, 25),
        mc95=date(2026, 12, 1),
        runs=10_000,
        velocity_date=date(2026, 11, 17),
        velocity_per_sprint=20.0,
        points_needed=80.0,
        points_estimated=True,
        open_items=0,
        rows_no_date=0,
        bug_share_percent=None,
    )
    base.update(kw)
    return ForecastFacts(**base)


# --- Written-out dates (the CLI keeps ISO) -------------------------------------------------


@pytest.mark.parametrize(
    "day, long, short",
    [
        (date(2026, 11, 17), "Nov. 17, 2026", "Nov. 17"),
        (date(2026, 9, 30), "Sept. 30, 2026", "Sept. 30"),
        (date(2027, 1, 2), "Jan. 2, 2027", "Jan. 2"),
        (date(2027, 3, 5), "March 5, 2027", "March 5"),
        (date(2027, 6, 1), "June 1, 2027", "June 1"),
        (date(2027, 7, 31), "July 31, 2027", "July 31"),
    ],
)
def test_dates_are_written_out(day, long, short):
    assert logic.long_date(day) == long
    assert logic.short_date(day) == short


def test_the_cli_report_keeps_iso_dates():
    from argparse import Namespace

    from mcf.cli import render

    args = Namespace(as_of=None, seed=7)
    text = render(facts(), args)
    assert "50%: 2026-11-17" in text and "Nov." not in text


# --- Typed backlog (1 to 10,000) ------------------------------------------------------------


@pytest.mark.parametrize("text, n", [("40", 40), (" 7 ", 7), ("1", 1), ("10000", 10_000)])
def test_backlog_accepts_a_whole_number(text, n):
    assert logic.parse_backlog(text) == n


@pytest.mark.parametrize(
    "text", ["", "0", "-3", "10001", "4.5", "forty", "1e3", "１２", "10,000", "40 items"]
)
def test_backlog_rejects_other_input_with_a_clear_message(text):
    with pytest.raises(logic.WebError, match=r"^Type a whole number from 1 to 10,000\.$"):
        logic.parse_backlog(text)


# --- Cards --------------------------------------------------------------------------------------


def test_the_4_cards_have_the_agreed_labels_dates_notes_and_colours():
    got = [(c.label, c.value, c.note) for c in logic.cards(facts())]
    assert got == [
        ("50/50 date · P50", "Nov. 17, 2026", "As likely early as late"),
        ("Safer date · P85", "Nov. 25, 2026", "Recommended to share"),
        ("Safest date · P95", "Dec. 1, 2026", ""),  # design: no note; the sidebar says when
        ("Velocity date · story points", "Nov. 17, 2026", "Average pace · points left estimated"),
    ]
    by_label = {c.label: c for c in logic.cards(facts())}
    assert [c.label for c in logic.cards(facts()) if c.highlight] == ["Safer date · P85"]
    assert by_label["Velocity date · story points"].dashed


def test_the_velocity_card_says_given_points_and_not_available():
    given = logic.cards(facts(points_estimated=False))[3]
    assert given.note == "Average pace · points left given"
    none = logic.cards(facts(velocity_date=None, velocity_per_sprint=None, points_needed=None))[3]
    assert (none.value, none.note) == ("Not available", "Needs story points")


def test_card_and_chart_line_colours_match():
    f = facts()
    lines = dict(zip(logic.marker_table(f)["label"], logic.marker_table(f)["color"], strict=True))
    for card, line in zip(logic.cards(f), lines, strict=True):
        assert card.color == lines[line]
    assert lines == {
        "50/50 (P50)": logic.COLORS["p50"],
        "Safer (P85)": logic.COLORS["p85"],
        "Safest (P95)": logic.COLORS["p95"],
        "Velocity": logic.COLORS["velocity"],
    }


def _luminance(hex_colour: str) -> float:
    rgb = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


@pytest.mark.parametrize("name", ["p50", "p85", "p95", "velocity", "muted", "ink"])
def test_text_colours_have_4_5_to_1_contrast_on_white(name):
    lum = _luminance(logic.COLORS[name])
    assert (1.05) / (lum + 0.05) >= 4.5


def test_the_highlight_is_not_red():
    highlighted = [c for c in logic.cards(facts()) if c.highlight]
    assert highlighted[0].color != logic.COLORS["p95"]


def test_card_html_escapes_text_and_shows_no_iso_date():
    html = logic.cards_html(facts())
    assert "Nov. 25, 2026" in html and "2026-11-25" not in html
    assert html.count('class="mcf-card') == 4
    assert "<script" not in html


# --- Page text ----------------------------------------------------------------------------------


def test_heading_and_from_line():
    f = facts()
    assert logic.result_heading(f) == "40 work items left"
    assert logic.result_heading(replace(f, backlog=1)) == "1 work item left"
    assert logic.from_line(f, as_of_given=False) == (
        "Forecast from the last finished item in the file: Sept. 30, 2026"
    )
    assert (
        logic.from_line(f, as_of_given=True) == "Forecast from the date you chose: Sept. 30, 2026"
    )


def test_share_a_range_line():
    assert (
        logic.share_line(facts()) == 'Share a range: "Nov. 17 to Nov. 25 (85% chance by Nov. 25)."'
    )
    across = facts(mc50=date(2026, 12, 28), mc85=date(2027, 1, 4), mc95=date(2027, 1, 9))
    assert logic.share_line(across) == (
        'Share a range: "Dec. 28, 2026 to Jan. 4, 2027 (85% chance by Jan. 4, 2027)."'
    )


def test_sidebar_has_the_5_parts_in_order():
    heads = re.findall(r"^#### (.+)$", logic.SIDEBAR, flags=re.M)
    assert heads == ["You need", "Steps", "Which date to use", "Be careful", "Your data"]
    assert "Jira export works" in logic.SIDEBAR
    assert "1 time in 3" in logic.SIDEBAR  # the back-test result (69.0% correct)


def _sentences(text: str) -> set[str]:
    text = re.sub(r"[*_#>|`-]", " ", text)
    return {s.strip().lower() for s in re.split(r"[.!?\n]", text) if len(s.split()) >= 4}


def test_no_sentence_repeats_between_the_sidebar_and_the_page():
    page = " ".join([logic.INTRO, logic.BACKLOG_HELP, logic.CHART_CAPTION, logic.NOT_CERTAIN])
    page += " " + " ".join(c.note for c in logic.cards(facts()))
    assert not _sentences(logic.SIDEBAR) & _sentences(page)


def test_the_page_never_calls_the_50_date_certain():
    text = " ".join([logic.SIDEBAR, logic.INTRO, logic.NOT_CERTAIN, logic.cards_html(facts())])
    assert "certain" not in text.lower().replace("not certain", "")
