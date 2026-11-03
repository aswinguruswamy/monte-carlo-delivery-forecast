"""MCF-24 acceptance checks for the Streamlit page itself (AppTest, no browser).

Needs the `web` extra. The AI transport is a fake (CLAUDE.md test rule 2).
"""

from __future__ import annotations

import argparse
import json
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


def metrics(at) -> dict[str, str]:
    return {m.label: m.value for m in at.metric}


def test_page_with_the_sample_shows_the_3_dates_the_velocity_date_and_the_chart(app):
    at = app()
    assert not at.exception
    assert not at.error
    expected = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40).facts
    assert metrics(at) == {
        "50% date": str(expected.mc50),
        "85% date": str(expected.mc85),
        "95% date": str(expected.mc95),
        "Velocity date": str(expected.velocity_date),
    }
    assert len(at.get("vega_lite_chart")) == 1
    text = " ".join(e.value for group in (at.markdown, at.caption) for e in group)
    assert "The 50% date is not certain" in text
    assert "SAMPLE-" not in text


def test_page_without_a_key_shows_no_ai_text_and_says_why(app):
    at = app()
    assert at.toggle(key="explain").value is False
    assert at.toggle(key="explain").disabled
    assert any("ANTHROPIC_API_KEY" in c.value for c in at.caption)


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
    assert len(at.metric) == 4
    groups = (at.markdown, at.caption, at.info, at.warning)
    page = " ".join(e.value for group in groups for e in group)
    assert "for sure" not in page
    assert "AI explanation not shown" in page


def test_upload_a_good_file(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    at.file_uploader(key="upload").set_value(("team.csv", FIXTURE.read_bytes(), "text/csv"))
    at.number_input(key="backlog").set_value(25)
    at.run()
    assert not at.exception and not at.error
    expected = compute(cli_args(FIXTURE, 25))
    assert metrics(at)["85% date"] == str(expected.mc85)


def test_upload_a_bad_file_shows_a_clear_error_and_no_stack_trace(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    at.file_uploader(key="upload").set_value(("bad.csv", b"Issue_Key,Type\nA,Story\n", "text/csv"))
    at.run()
    assert not at.exception
    assert len(at.error) == 1
    assert logic.plain("missing column(s): Resolution_Date, Story_Point") in at.error[0].value
    assert len(at.metric) == 0
    assert len(at.get("vega_lite_chart")) == 0


def test_upload_mode_with_no_file_asks_for_one(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    assert not at.exception and not at.error
    assert len(at.metric) == 0
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
    assert metrics(at)["Velocity date"] == str(expected.velocity_date)
    assert metrics(at)["85% date"] == str(expected.mc85)
    assert "seed 7)" in at.code[0].value  # the page uses the seed it was given


def test_the_ai_call_is_cached_and_only_made_when_turned_on(app, monkeypatch):
    calls: list = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(logic, "TRANSPORT", fake_transport(calls=calls))
    at = app()
    at.number_input(key="backlog").set_value(41).run()
    assert len(calls) == 0  # toggle off: no call
    at.toggle(key="explain").set_value(True).run()
    at.run()
    at.run()
    assert len(calls) == 1  # same forecast: one call
    at.number_input(key="backlog").set_value(42).run()
    assert len(calls) == 2  # new forecast: one more call
    at.number_input(key="backlog").set_value(41).run()
    assert len(calls) == 2  # back to a forecast seen before: cached


def test_the_forecast_date_option(app):
    at = app()
    assert at.date_input(key="as_of").value is None  # default: the last done day
    at.date_input(key="as_of").set_value(date(2026, 8, 31)).run()
    assert not at.exception and not at.error
    expected = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40, as_of=date(2026, 8, 31)).facts
    assert metrics(at)["85% date"] == str(expected.mc85)
    assert any("from 2026-08-31" in h.value for h in at.subheader)


def test_an_error_is_shown_as_plain_text(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    bad = b"Issue_Key,Type,Resolution_Date,Story_Point\nA-1,Story,[x](http://e),3\n"
    at.file_uploader(key="upload").set_value(("bad.csv", bad, "text/csv"))
    at.run()
    assert len(at.error) == 1
    assert "\\[x\\]\\(http://e\\)" in at.error[0].value
