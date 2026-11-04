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
        items_no_points=0,
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


@pytest.mark.parametrize(
    "text, n",
    [("40", 40), (" 7 ", 7), ("1", 1), ("10000", 10_000), ("1,000", 1_000), ("10,000", 10_000)],
)
def test_backlog_accepts_a_whole_number(text, n):
    assert logic.parse_backlog(text) == n


@pytest.mark.parametrize(
    "text",
    ["", "0", "-3", "10001", "10,001", "4.5", "forty", "1e3", "１２", "1,00", "40 items", "٤٠"],
)
def test_backlog_rejects_other_input_with_a_clear_message(text):
    with pytest.raises(logic.WebError, match=r"^Type a whole number from 1 to 10,000\.$"):
        logic.parse_backlog(text)


# --- Cards --------------------------------------------------------------------------------------


def test_the_4_cards_have_the_agreed_labels_dates_notes_and_colours():
    got = [(c.label, c.value, c.notes) for c in logic.cards(facts())]
    assert got == [
        ("50% chance of completion", "Nov. 17, 2026", ("P50",)),
        (
            "85% chance of completion",
            "Nov. 25, 2026",
            ("P85 · Recommended to share", "If a delay costs a lot, use 95%."),
        ),
        ("95% chance of completion", "Nov. 25, 2026".replace("Nov. 25", "Dec. 1"), ("P95",)),
        ("Velocity date", "Nov. 17, 2026", ("Uses story points",)),  # MCF-35
    ]
    by_label = {c.label: c for c in logic.cards(facts())}
    assert [c.label for c in logic.cards(facts()) if c.highlight] == ["85% chance of completion"]
    assert by_label["Velocity date"].dashed


def test_the_velocity_card_has_no_pace_line_and_says_not_available():
    """MCF-34 (D45): the "Average pace" line stays in the help sidebar."""
    for estimated in (True, False):
        card = logic.cards(facts(points_estimated=estimated))[3]
        assert card.notes == ("Uses story points",)
    html = logic.cards_html(facts())
    assert "Average pace" not in html and "points left" not in html
    none = logic.cards(facts(velocity_date=None, velocity_per_sprint=None, points_needed=None))[3]
    assert (none.value, none.notes) == ("Not available", ("Needs story points",))


def test_card_and_chart_line_colours_match():
    f = facts()
    lines = dict(zip(logic.marker_table(f)["label"], logic.marker_table(f)["color"], strict=True))
    for card, line in zip(logic.cards(f), lines, strict=True):
        assert card.color == lines[line]
    assert lines == {
        "50% chance": logic.COLORS["p50"],
        "85% chance": logic.COLORS["p85"],
        "95% chance": logic.COLORS["p95"],
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


@pytest.mark.parametrize("velocity", [True, False])
def test_card_text_has_4_5_to_1_contrast_on_its_own_background(velocity):
    """Review MCF-33: the label colour on the highlighted card background was 4.47:1."""
    f = (
        facts()
        if velocity
        else facts(velocity_date=None, velocity_per_sprint=None, points_needed=None)
    )
    for c in logic.cards(f):
        back = _luminance(logic.card_background(c))
        for fg in (c.color, logic.COLORS["muted"], logic.COLORS["ink"]):
            ratio = (back + 0.05) / (_luminance(fg) + 0.05)
            assert ratio >= 4.5, (c.label, fg, round(ratio, 2))


def test_the_highlight_is_not_red():
    highlighted = [c for c in logic.cards(facts()) if c.highlight]
    assert highlighted[0].color != logic.COLORS["p95"]


def test_card_html_escapes_text_and_shows_no_iso_date():
    html = logic.cards_html(facts())
    assert "Nov. 25, 2026" in html and "2026-11-25" not in html
    assert html.count("data-label=") == 4
    assert "<script" not in html


# --- Page text ----------------------------------------------------------------------------------


def test_heading_and_from_line():
    f = facts()
    assert logic.result_heading(f) == "40 work items left"
    assert logic.result_heading(replace(f, backlog=1)) == "1 work item left"
    assert logic.from_line(f, as_of_given=False) == (
        "Dates count from Sept. 30, 2026, the day the last item in your file was finished."
    )
    assert (
        logic.from_line(f, as_of_given=True)
        == "Dates count from Sept. 30, 2026, the date you chose."
    )


def test_message_to_sponsor_line():
    assert (
        logic.message_line(facts())
        == 'Message to sponsor: "Nov. 17 to Nov. 25 (85% chance of completion by Nov. 25)."'
    )
    across = facts(mc50=date(2026, 12, 28), mc85=date(2027, 1, 4), mc95=date(2027, 1, 9))
    assert logic.message_line(across) == (
        'Message to sponsor: "Dec. 28, 2026 to Jan. 4, 2027 '
        '(85% chance of completion by Jan. 4, 2027)."'
    )


def test_sidebar_has_the_5_parts_in_order():
    heads = re.findall(r"^#### (.+)$", logic.SIDEBAR, flags=re.M)
    assert heads == ["You need", "Steps", "Which date to use", "Be careful", "Privacy"]
    assert "Jira export works" in logic.SIDEBAR
    assert "1 time in 3" in logic.SIDEBAR  # the back-test result (69.0% correct)


def _sentences(text: str) -> set[str]:
    text = re.sub(r"[*_#>|`-]", " ", text)
    return {s.strip().lower() for s in re.split(r"[.!?\n]", text) if len(s.split()) >= 3}


def test_no_sentence_repeats_between_the_sidebar_and_the_page():
    page = " ".join([logic.INTRO, logic.BACKLOG_HELP, logic.CHART_CAPTION, logic.NOT_CERTAIN])
    none = facts(velocity_date=None, velocity_per_sprint=None, points_needed=None)
    for f in (facts(), none):
        page += " " + " ".join(n for c in logic.cards(f) for n in c.notes)
    page += " " + " ".join(logic.OPTION_HELP.values()) + " " + logic.PHONE_HELP
    assert not _sentences(logic.SIDEBAR) & _sentences(page)


def test_the_page_never_calls_the_50_date_certain():
    text = " ".join([logic.SIDEBAR, logic.INTRO, logic.NOT_CERTAIN, logic.cards_html(facts())])
    assert "certain" not in text.lower().replace("not certain", "")


def test_the_page_has_no_ai_line_text():
    """PM 2026-11-04: no AI line on a page with no key."""
    assert not hasattr(logic, "AI_NOT_AVAILABLE")


def test_phone_help_hint_shows_only_on_narrow_screens():
    html = logic.phone_help_html()
    assert logic.PHONE_HELP in html and "@media (min-width: 641px)" in html


def test_history_line():
    assert logic.history_line(facts()) == (
        "History: 60 work items done from July 9 to Sept. 30, 2026 (84 days)."
    )


@pytest.mark.parametrize(
    "mc95, fmt", [(date(2026, 12, 1), "%b %-d"), (date(2027, 1, 9), "%b %-d, %Y")]
)
def test_the_chart_axis_shows_the_year_when_the_dates_cross_a_year(mc95, fmt):
    assert logic.axis_format(facts(mc95=mc95)) == fmt


def test_the_demo_script_waits_for_text_that_the_page_shows():
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "scripts" / "record_demo.py").read_text()
    waits = re.findall(r'get_by_text\("([^"]+)"', script)
    assert waits
    page_src = " ".join(
        (Path(logic.__file__).parent / n).read_text() for n in ("logic.py", "app.py")
    )
    for text in waits:
        stem = re.sub(r"^\d+ ", "", text)  # "80 work items left" -> "work items left"
        assert stem in page_src or stem in logic.result_heading(facts()), text


def test_the_help_explains_the_velocity_date():
    """MCF-34 (D45): pace and estimated points are in the Velocity help line."""
    side = logic.SIDEBAR
    line = next(s for s in side.splitlines() if s.startswith("- **Velocity date:**"))
    assert "average pace" in line and "story points" in line
    assert "estimates" in line and "More options" in line


def test_the_help_names_the_real_options_expander():
    """MCF-34 review: the help says "More options"; the page must keep that label."""
    from pathlib import Path

    app = (Path(logic.__file__).parent / "app.py").read_text()
    assert 'st.expander("More options")' in app
    assert '"Story points left"' in app


# --- MCF-35: plain wording for sponsors ----------------------------------------------------


def test_the_page_says_chance_of_completion_not_50_50_or_simulated_runs():
    text = " ".join(
        [logic.INTRO, logic.NOT_CERTAIN, logic.SIDEBAR, logic.cards_html(facts())]
        + [logic.message_line(facts())]
    )
    assert "chance of completion" in logic.INTRO
    for old in ("50/50", "Safer date", "Safest date", "simulated runs", "Share a range"):
        assert old not in text, old


def test_intro_and_not_certain_text():
    assert logic.INTRO == (
        "Upload your team's finished work items, or try the sample file. See the dates with "
        "a 50%, 85% and 95% chance of completion, from your team's real pace (throughput)."
    )
    assert (
        logic.NOT_CERTAIN
        == "The 50% date is not certain: half of the time the work finishes later."
    )


def test_sidebar_has_4_steps_and_a_privacy_part():
    side = logic.SIDEBAR
    assert "4. Copy the message to your sponsor." in side
    assert "#### Privacy" in side and "#### Your data" not in side
    assert "Choose the sample file (an example team) or upload your file." in side
    assert "A Jira export works with no changes." in side


def test_each_option_has_a_plain_explanation():
    assert set(logic.OPTION_HELP) == {"backlog_points", "as_of", "seed"}
    assert "same dates again" in logic.OPTION_HELP["seed"]
    assert "last item in your file" in logic.OPTION_HELP["as_of"]


def test_sample_and_report_labels():
    assert logic.SAMPLE_LABEL == "Sample file (example team, not real data)"
    assert logic.REPORT_LABEL == "Full report (technical)"


def test_the_points_option_help_says_off_for_the_toggle():
    """MCF-35 review: the story points option is a toggle, so the help says "Off"."""
    assert (
        logic.OPTION_HELP["backlog_points"]
        == "For the velocity date. Off: the tool estimates them."
    )


def test_the_demo_script_waits_for_the_cards_not_old_metrics():
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "scripts" / "record_demo.py").read_text()
    assert "stMetric" not in script and ".mcf-card" in script


def test_the_demo_guide_names_the_current_ai_check():
    from pathlib import Path

    guide = (Path(__file__).resolve().parents[1] / "docs" / "demo.md").read_text()
    assert "AI off without a key" not in guide and "no AI line without a key" in guide
