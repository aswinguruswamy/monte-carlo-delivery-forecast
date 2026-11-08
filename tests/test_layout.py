"""MCF-37 checks: numbered sections in boxes (design "MCF Page With Help Panel")."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from mcf.result import ForecastFacts
from mcf.web import logic

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "mcf" / "web" / "app.py"
SAMPLE = ROOT / "examples" / "sample_team.csv"
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


# --- Section headings and descriptions -------------------------------------------------------


def test_the_4_sections_have_numbered_headings_and_a_description():
    f = facts()
    sections = logic.sections(f)
    assert [s.heading for s in sections] == [
        "1. Your inputs",
        "2. When the 40 work items will be done",
        "3. All possible finish dates",
        "4. How this forecast works",
    ]
    assert all(s.description for s in sections)
    assert (
        logic.sections(replace(f, backlog=1))[1].heading == "2. When the 1 work item will be done"
    )


def test_the_history_line_says_value_items_only():
    assert logic.history_line(facts()) == (
        "History used: 60 work items (not bugs or epics) finished from July 9 to "
        "Sept. 30, 2026 (84 days)."
    )


def test_the_page_style_gives_a_grey_page_and_white_boxes():
    css = logic.page_css()
    assert "#f5f6f8" in css and "#ffffff" in css
    assert "<script" not in css


def test_captions_get_a_4_5_to_1_colour():
    """Review MCF-37: Streamlit's caption (60% opacity) was 3.7:1 on white."""
    css = logic.page_css()
    assert '[data-testid="stCaptionContainer"]{color:#5f6370;opacity:1}' in css


def test_section_labels_look_like_headings():
    """MCF-41: a section label has heading size; the inner expanders keep the normal size."""
    css = logic.page_css()
    for n in range(1, 5):
        assert f'.st-key-section-{n}>[data-testid="stExpander"]>details>summary p' in css
    sel = ",".join(
        f'.st-key-section-{n}>[data-testid="stExpander"]>details>summary p' for n in range(1, 5)
    )
    assert sel + "{font-size:1.5rem;font-weight:600;line-height:1.3}" in css  # review MCF-41


def test_each_section_has_a_hidden_heading_for_screen_readers(app):
    """Review MCF-41: the sections were h3 headings; expander labels are not headings."""
    hidden = [m.value for m in app.markdown if 'class="mcf-sr-only"' in m.value]
    assert hidden == [f'<h2 class="mcf-sr-only">{h}</h2>' for h in HEADS]
    css = logic.page_css()
    assert ".mcf-sr-only{position:absolute;width:1px;height:1px;overflow:hidden;" in css


def test_cards_stack_one_per_line_on_a_phone():
    html = logic.cards_html(facts())
    assert "@media (max-width: 640px)" in html and "grid-template-columns:1fr" in html


# --- Chart: velocity on the same day as the 50% date ------------------------------------------


def test_same_day_note_only_when_the_dates_are_equal():
    assert logic.same_day_note(facts()) == (
        "The velocity date is the same day as the 50% date, so the two lines are drawn "
        "side by side."
    )
    assert logic.same_day_note(facts(velocity_date=date(2026, 11, 20))) is None
    none = facts(velocity_date=None, velocity_per_sprint=None, points_needed=None)
    assert logic.same_day_note(none) is None


def test_both_lines_show_side_by_side_when_the_dates_are_equal():
    marks = logic.marker_table(facts())
    offsets = dict(zip(marks["label"], marks["offset"], strict=True))
    assert offsets["50% chance"] < 0 < offsets["Velocity"]
    apart = logic.marker_table(facts(velocity_date=date(2026, 11, 20)))
    assert set(apart["offset"]) == {0}


# --- The page (AppTest) ------------------------------------------------------------------------

streamlit_testing = pytest.importorskip("streamlit.testing.v1")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import streamlit as st

    st.cache_data.clear()
    at = streamlit_testing.AppTest.from_file(str(APP), default_timeout=60)
    return at.run()


HEADS = [
    "1. Your inputs",
    "2. When the 40 work items will be done",
    "3. All possible finish dates",
    "4. How this forecast works",
]


def test_page_shows_the_4_sections_in_order(app):
    assert not app.exception
    assert [e.label for e in app.expander if e.label in HEADS] == HEADS


def test_the_4_sections_can_close_and_are_open_on_load(app):
    """MCF-41 (PM user test 2026-11-07): collapsible sections, open by default."""
    sections = [e for e in app.expander if e.label in HEADS]
    assert [e.proto.expanded for e in sections] == [True] * 4
    assert list(app.subheader) == []  # the heading is the expander label, not a second line
    inside = [[x.label for x in s.expander] for s in sections]
    parts = [p.title for p in logic.how_it_works()]
    assert inside == [["More options"], [], [], parts]  # inner parts stay inside, closed
    assert not any(e.proto.expanded for e in app.expander if e.label not in HEADS)


def test_each_section_starts_with_its_description(app):
    sections = [e for e in app.expander if e.label in HEADS]
    for sec in sections:
        assert sec.caption[0].value.endswith(".")
    assert sections[0].caption[0].value == logic.INPUTS_SECTION.description


def test_the_report_box_stays_outside_the_sections(app):
    report = next(e for e in app.expander if e.label == logic.REPORT_LABEL)
    assert not report.proto.expanded
    sections = [e for e in app.expander if e.label in HEADS]
    assert all(logic.REPORT_LABEL not in [x.label for x in s.expander] for s in sections)


def test_page_puts_the_history_line_in_section_2(app):
    texts = [c.value for c in app.caption]
    history = next(i for i, t in enumerate(texts) if t.startswith("History used:"))
    chart_caption = next(i for i, t in enumerate(texts) if t.startswith("Each bar:"))
    assert history < chart_caption


def test_section_2_description_comes_right_after_its_heading(app):
    """Review MCF-37: every box starts with heading, then its one-line description."""
    texts = [c.value for c in app.caption]
    desc = next(i for i, t in enumerate(texts) if t.startswith("Each card shows"))
    dates = next(i for i, t in enumerate(texts) if t.startswith("Dates count from"))
    assert desc < dates


def test_the_full_report_box_has_a_description(app):
    texts = [c.value for c in app.caption]
    assert logic.REPORT_DESCRIPTION in texts
