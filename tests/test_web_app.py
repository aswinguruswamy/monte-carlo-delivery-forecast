"""MCF-24 acceptance checks for the Streamlit page itself (AppTest, no browser).

Needs the `web` extra. The AI transport is a fake (CLAUDE.md test rule 2).
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
from datetime import date
from pathlib import Path

import pytest

from mcf.cli import compute
from mcf.forecast.montecarlo import SEED
from mcf.web import logic
from mcf.web.logic import forecast_from_bytes

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample_team.csv"
FIXTURE = ROOT / "tests" / "fixtures" / "cli_team.csv"
APP = ROOT / "src" / "mcf" / "web" / "app.py"
MANDATORY = "fifty_not_certain"


def cli_args(path: Path, backlog: int, **over) -> argparse.Namespace:
    base = dict(file=str(path), backlog=backlog, as_of=None, backlog_points=None, seed=SEED)
    base.update(over)
    return argparse.Namespace(**base)


streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest


def fake_transport(ids: list[str] | None = None, calls: list | None = None):
    def send(url, headers, body, timeout):
        if calls is not None:
            calls.append(body)
        choice = ids or [MANDATORY, "share_85", "range"]  # always applicable
        text = json.dumps({"sentences": choice})
        return json.dumps(
            {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}
        ).encode()

    return send


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import streamlit as st

    st.cache_data.clear()

    def make():
        at = AppTest.from_file(str(APP), default_timeout=60)
        return at.run()

    return make


CARD = re.compile(r'data-label="([^"]+)".*?class="mcf-card-value"[^>]*>([^<]+)<', re.S)


def metrics(at) -> dict[str, str]:
    """The 4 date cards (MCF-33): label -> the date as shown."""
    html = " ".join(m.value for m in at.markdown if "mcf-card" in m.value)
    return {html_lib.unescape(a): html_lib.unescape(b) for a, b in CARD.findall(html)}


def page_text(at) -> str:
    groups = (at.markdown, at.caption, at.info, at.warning, at.subheader)
    return " ".join(e.value for group in groups for e in group)


def sidebar_text(at) -> str:
    return " ".join(m.value for m in at.sidebar.markdown)


def ld(d) -> str:
    return logic.long_date(d)


def test_page_with_the_sample_shows_the_3_dates_the_velocity_date_and_the_chart(app):
    at = app()
    assert not at.exception
    assert not at.error
    expected = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40).facts
    assert metrics(at) == {
        "50% chance of completion": ld(expected.mc50),
        "85% chance of completion": ld(expected.mc85),
        "95% chance of completion": ld(expected.mc95),
        "Velocity date": ld(expected.velocity_date),
    }
    assert len(at.get("vega_lite_chart")) == 1
    text = " ".join(e.value for group in (at.markdown, at.caption) for e in group)
    assert logic.NOT_CERTAIN in text
    assert "SAMPLE-" not in text


def test_page_without_a_key_shows_no_ai_text_and_says_why(app):
    at = app()
    assert not [t for t in at.toggle if t.key == "explain"]
    assert "AI explanation" not in page_text(at)  # PM 2026-11-04: no AI line without a key
    assert "ANTHROPIC_API_KEY" not in page_text(at)  # no server jargon on the page (#10)


def test_page_has_the_plain_labels_and_the_5_part_sidebar(app):
    at = app()
    assert at.title[0].value == "When will your work be done?"
    assert at.text_input(key="backlog").label == "How many work items are left? (backlog)"
    assert not at.text_input(key="backlog").help  # no help button inside the label (#14)
    side = sidebar_text(at)
    for part in ("You need", "Steps", "Which date to use", "Be careful", "Your data"):
        assert f"#### {part}" in side
    expected = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40).facts
    text = page_text(at)
    assert logic.message_line(expected) in text
    assert logic.from_line(expected, as_of_given=False) in text
    assert "40 work items left" in text


@pytest.mark.parametrize("bad", ["", "0", "10001", "4.5", "forty"])
def test_a_bad_backlog_shows_a_clear_message_and_no_dates(app, bad):
    at = app()
    at.text_input(key="backlog").set_value(bad).run()
    assert not at.exception
    assert [e.value for e in at.error] == ["Type a whole number from 1 to 10,000."]
    assert metrics(at) == {}


def test_page_with_a_key_shows_the_approved_explanation(app, monkeypatch):
    calls: list = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(logic, "TRANSPORT", fake_transport(calls=calls))
    at = app()
    assert not at.exception
    assert at.toggle(key="explain").value is False  # off by default: no paid call
    assert not at.toggle(key="explain").disabled
    assert len(calls) == 0
    at.toggle(key="explain").set_value(True).run()
    assert len(calls) == 1
    shown = [m.value for m in at.markdown]
    assert any(
        "The 50% date is not certain: up to half of the simulated runs finish after it." in s
        for s in shown
    )
    assert any("AI-selected, approved sentences" in c.value for c in at.caption)
    body = calls[0].decode()
    assert "SAMPLE-" not in body and "test-key-not-real" not in body


def test_page_with_a_bad_ai_reply_shows_the_plain_report(app, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    def bad(url, headers, body, timeout):
        return json.dumps(
            {
                "content": [{"type": "text", "text": "Done by 2026-11-17 for sure."}],
                "stop_reason": "end_turn",
            }
        ).encode()

    monkeypatch.setattr(logic, "TRANSPORT", bad)
    at = app()
    at.toggle(key="explain").set_value(True).run()
    assert not at.exception
    assert len(metrics(at)) == 4
    groups = (at.markdown, at.caption, at.info, at.warning)
    page = " ".join(e.value for group in groups for e in group)
    assert "for sure" not in page
    assert "AI explanation not shown" in page


def test_upload_a_good_file(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    at.file_uploader(key="upload").set_value(("team.csv", FIXTURE.read_bytes(), "text/csv"))
    at.text_input(key="backlog").set_value("25")
    at.run()
    assert not at.exception and not at.error
    expected = compute(cli_args(FIXTURE, 25))
    assert metrics(at)["85% chance of completion"] == ld(expected.mc85)


def test_upload_a_bad_file_shows_a_clear_error_and_no_stack_trace(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    at.file_uploader(key="upload").set_value(("bad.csv", b"Issue_Key,Type\nA,Story\n", "text/csv"))
    at.run()
    assert not at.exception
    assert len(at.error) == 1
    assert logic.plain("missing column(s): Resolution_Date. ") in at.error[0].value
    assert metrics(at) == {}
    assert len(at.get("vega_lite_chart")) == 0


def test_upload_mode_with_no_file_asks_for_one(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    assert not at.exception and not at.error
    assert metrics(at) == {}
    assert any("Upload a CSV file" in i.value for i in at.info)


def test_optional_inputs_change_the_forecast(app):
    at = app()
    at.toggle(key="points_given").set_value(True).run()
    at.number_input(key="backlog_points").set_value(123.0)
    at.number_input(key="seed").set_value(7)
    at.run()
    expected = forecast_from_bytes(
        SAMPLE.read_bytes(), backlog=40, backlog_points=123.0, seed=7
    ).facts
    assert metrics(at)["Velocity date"] == ld(expected.velocity_date)
    assert metrics(at)["85% chance of completion"] == ld(expected.mc85)
    assert "seed 7)" in at.code[0].value  # the page uses the seed it was given


def test_the_ai_call_is_cached_and_only_made_when_turned_on(app, monkeypatch):
    calls: list = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(logic, "TRANSPORT", fake_transport(calls=calls))
    at = app()
    at.text_input(key="backlog").set_value("41").run()
    assert len(calls) == 0  # toggle off: no call
    at.toggle(key="explain").set_value(True).run()
    at.run()
    at.run()
    assert len(calls) == 1  # same forecast: one call
    at.text_input(key="backlog").set_value("42").run()
    assert len(calls) == 2  # new forecast: one more call
    at.text_input(key="backlog").set_value("41").run()
    assert len(calls) == 2  # back to a forecast seen before: cached


def test_the_forecast_date_option(app):
    at = app()
    assert at.date_input(key="as_of").value is None  # default: the last done day
    at.date_input(key="as_of").set_value(date(2026, 8, 31)).run()
    assert not at.exception and not at.error
    expected = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40, as_of=date(2026, 8, 31)).facts
    assert metrics(at)["85% chance of completion"] == ld(expected.mc85)
    assert "Dates count from Aug. 31, 2026, the date you chose." in page_text(at)


def test_an_error_is_shown_as_plain_text(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    bad = b"Issue_Key,Type,Resolution_Date,Story_Point\nA-1,Story,[x](http://e),3\n"
    at.file_uploader(key="upload").set_value(("bad.csv", bad, "text/csv"))
    at.run()
    assert len(at.error) == 1
    assert "\\[x\\]\\(http://e\\)" in at.error[0].value


def test_upload_with_no_story_points_shows_dates_and_no_velocity(app):
    """MCF-32 (D43): the page works for a team with no story points."""
    from datetime import timedelta

    t = date(2026, 9, 30)
    lines = ["Issue_Key,Type,Resolution_Date"]
    lines += [f"A-{i},Story,{t - timedelta(days=i)}" for i in range(40)]
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    at.file_uploader(key="upload").set_value(("team.csv", "\n".join(lines).encode(), "text/csv"))
    at.run()
    assert not at.exception and not at.error
    shown = metrics(at)
    assert len(shown) == 4
    assert shown["Velocity date"] == "Not available"
    text = page_text(at)
    assert "Needs story points" in text
    assert "40 work items done between" in text


def test_the_chart_legend_has_room_for_all_4_lines(app):
    """Review MCF-33: on a phone the bottom legend lost "Velocity"."""
    from mcf.web import app as page

    result = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40)
    spec = page._chart(result).to_dict()
    legend = spec["layer"][1]["encoding"]["color"]["legend"]
    assert legend["orient"] == "bottom" and legend["columns"] == 2


def test_page_shows_the_new_labels_and_option_help(app):
    """MCF-35: sample label, option explanations, report label, sidebar privacy part."""
    at = app()
    assert not at.exception
    assert at.radio(key="source").options[0] == logic.SAMPLE_LABEL
    text = page_text(at)
    for help_text in logic.OPTION_HELP.values():
        assert help_text in text
    assert [e.label for e in at.expander] == ["More options", logic.REPORT_LABEL]
    assert "#### Privacy" in sidebar_text(at)
