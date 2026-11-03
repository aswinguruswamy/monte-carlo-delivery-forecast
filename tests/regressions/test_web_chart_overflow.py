"""Regression test for MCF-30: the web chart raised OverflowError when a
simulated run ends after 9999-12-31 (found in the MCF-29 review).

The 50/85/95% dates come from all runs and do not change; the chart leaves out
the runs after the last calendar date and the page says how many.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from mcf.web import logic
from mcf.web.logic import forecast_from_bytes

HEADER = "Issue_Key,Type,Resolution_Date,Story_Point\n"


def late_file() -> bytes:
    """60 Story items done from 9999-11-01 to 9999-11-28."""
    rows = [f"L-{i},Story,{date(9999, 11, 1) + timedelta(days=i % 28)},3" for i in range(60)]
    return (HEADER + "\n".join(rows) + "\n").encode()


def test_the_chart_leaves_out_runs_after_the_last_date():
    result = forecast_from_bytes(late_file(), backlog=5)
    hist = logic.chart_table(result)  # raised OverflowError before the fix
    left_out = logic.runs_not_drawn(result)
    assert left_out > 0
    assert int(hist["runs"].sum()) + left_out == result.facts.runs
    assert max(hist["finish_date"]) <= date.max


def test_a_normal_forecast_draws_every_run():
    data = (HEADER + "A-1,Story,2020-06-30,3\nA-2,Story,2020-06-29,2\n").encode()
    result = forecast_from_bytes(data, backlog=3)
    assert logic.runs_not_drawn(result) == 0
    assert int(logic.chart_table(result)["runs"].sum()) == result.facts.runs


def test_the_page_draws_the_chart_and_says_how_many_runs_are_left_out():
    testing = pytest.importorskip("streamlit.testing.v1")
    from pathlib import Path

    app = Path(__file__).resolve().parents[2] / "src" / "mcf" / "web" / "app.py"
    at = testing.AppTest.from_file(str(app), default_timeout=60).run()
    at.radio(key="source").set_value("Upload a CSV file").run()
    at.file_uploader(key="upload").set_value(("late.csv", late_file(), "text/csv"))
    at.number_input(key="backlog").set_value(5)
    at.run()
    assert not at.exception and not at.error
    assert len(at.get("vega_lite_chart")) == 1
    assert any("end after 9999-12-31 and are not drawn" in c.value for c in at.caption)
