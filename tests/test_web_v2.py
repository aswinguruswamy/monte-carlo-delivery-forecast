"""MCF v2 task M2: the page shows the charter-date chance (R1.1) and the warning (R2.2)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from mcf.forecast.api import chance_label
from mcf.web import logic
from mcf.web.logic import WebError, forecast_from_bytes

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "examples" / "sample_team.csv").read_bytes()
T = date(2020, 6, 30)


def thin_csv(items: int) -> bytes:
    rows = [f"S-{d},Story,{T - timedelta(days=2 * d)} 10:00:00,1" for d in range(items)]
    return ("Issue_Key,Type,Resolution_Date,Story_Point\n" + "\n".join(rows) + "\n").encode()


def test_page_chance_uses_the_same_runs_as_the_dates():  # R1.3
    plain = forecast_from_bytes(SAMPLE, backlog=40)
    charter = plain.facts.mc85
    result = forecast_from_bytes(SAMPLE, backlog=40, charter=charter)
    hits = int((result.finish_days <= (charter - result.facts.t).days).sum())
    label = chance_label(hits, result.finish_days.size)
    assert result.chance == f"{label} chance to finish by {logic.long_date(charter)}"
    assert int(label.rstrip("%")) >= 85


def test_no_charter_no_chance():
    assert forecast_from_bytes(SAMPLE, backlog=40).chance is None


def test_charter_on_day_t_is_a_page_error():  # R1.2
    t = forecast_from_bytes(SAMPLE, backlog=40).facts.t
    with pytest.raises(WebError, match=f"The charter date must be after {logic.long_date(t)}"):
        forecast_from_bytes(SAMPLE, backlog=40, charter=t)


def test_thin_history_gives_the_warning():  # AC8, AC10
    result = forecast_from_bytes(thin_csv(29), backlog=5)
    assert result.warnings == (
        "Only 29 items finished in the last 12 weeks. Treat the dates with care.",
    )


def test_enough_history_gives_no_warning():  # AC9
    assert forecast_from_bytes(thin_csv(30), backlog=5).warnings == ()


pytest.importorskip("streamlit.testing.v1")
from tests.test_web_app import app  # noqa: E402,F401  (the page fixture)


def test_page_has_a_charter_input_and_shows_the_chance(app):  # noqa: F811
    at = app()
    assert not any("Charter date:" in m.value for m in at.markdown)
    at.date_input(key="charter").set_value(date(2026, 11, 15)).run()
    assert any("**Charter date:**" in m.value and "Nov. 15, 2026" in m.value for m in at.markdown)
