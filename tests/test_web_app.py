"""MCF-24 acceptance checks for the Streamlit page itself (AppTest, no browser).

Needs the `web` extra. The AI transport is a fake (CLAUDE.md test rule 2).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from mcf.web import logic
from mcf.web.logic import forecast_from_bytes

from mcf.cli import compute
from mcf.forecast.montecarlo import SEED

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
    assert len(at.get("arrow_vega_lite_chart")) == 1
    text = " ".join(m.value for m in at.markdown + at.caption)
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
    assert at.toggle(key="explain").value is True
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
    assert not at.exception
    assert len(at.metric) == 4
    page = " ".join(m.value for m in at.markdown + at.caption + at.info + at.warning)
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
    assert "missing column(s): Resolution_Date, Story_Point" in at.error[0].value
    assert len(at.metric) == 0
    assert len(at.get("arrow_vega_lite_chart")) == 0


def test_upload_mode_with_no_file_asks_for_one(app):
    at = app()
    at.radio(key="source").set_value("Upload a CSV file").run()
    assert not at.exception and not at.error
    assert len(at.metric) == 0
    assert any("Upload a CSV file" in i.value for i in at.info)


def test_optional_inputs_change_the_forecast(app):
    at = app()
    at.toggle(key="points_given").set_value(True).run()
    at.number_input(key="backlog_points").set_value(100.0)
    at.number_input(key="seed").set_value(7)
    at.run()
    expected = forecast_from_bytes(
        SAMPLE.read_bytes(), backlog=40, backlog_points=100.0, seed=7
    ).facts
    assert metrics(at)["Velocity date"] == str(expected.velocity_date)
    assert metrics(at)["85% date"] == str(expected.mc85)
