"""MCF-24 acceptance checks: the page logic (D01). The page itself: test_web_app.py.

AC1: the sample file with a backlog shows the chart, the 3 dates and the explanation.
AC2: a bad file shows a clear error (never a stack trace).
AC3 (webapp-testing skill not available): the browser check in scripts/browser_check.py.

The AI transport is a fake: no test calls the paid API (CLAUDE.md test rule 2).
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from mcf.cli import compute, render
from mcf.forecast.montecarlo import SEED, percentile_days
from mcf.web import logic
from mcf.web.logic import MAX_UPLOAD_BYTES, WebError, forecast_from_bytes

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample_team.csv"
FIXTURE = ROOT / "tests" / "fixtures" / "cli_team.csv"
APP = ROOT / "src" / "mcf" / "web" / "app.py"
HEADER = "Issue_Key,Type,Resolution_Date,Story_Point\n"
MANDATORY = "fifty_not_certain"


def cli_args(path: Path, backlog: int, **over) -> argparse.Namespace:
    base = dict(file=str(path), backlog=backlog, as_of=None, backlog_points=None, seed=SEED)
    base.update(over)
    return argparse.Namespace(**base)


# --- the sample file ------------------------------------------------------------


def test_sample_file_is_small_made_up_and_has_open_items():
    text = SAMPLE.read_text(encoding="utf-8")
    assert SAMPLE.stat().st_size < 100 * 1024
    assert text.startswith(HEADER)
    rows = text.splitlines()[1:]
    assert all(r.startswith("SAMPLE-") for r in rows)
    assert sum(1 for r in rows if r.split(",")[2] == "") == 6


def test_sample_bytes_reads_the_examples_file():
    assert logic.sample_bytes() == SAMPLE.read_bytes()


# --- same numbers as the CLI ----------------------------------------------------------


@pytest.mark.parametrize(
    "path, backlog, over",
    [
        (SAMPLE, 40, {}),
        (FIXTURE, 25, {}),
        (FIXTURE, 10, {"backlog_points": 30.0, "as_of": date(2020, 6, 20), "seed": 7}),
    ],
)
def test_page_numbers_equal_the_cli(path, backlog, over):
    result = forecast_from_bytes(path.read_bytes(), backlog=backlog, **over)
    args = cli_args(path, backlog, **over)
    assert result.facts == compute(args)
    assert result.report == render(compute(args), args)


def test_simulated_finish_days_give_the_same_percentile_dates():
    result = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40)
    f = result.facts
    days = result.finish_days
    assert len(days) == f.runs
    for p, d in ((50, f.mc50), (85, f.mc85), (95, f.mc95)):
        assert f.t + timedelta(days=percentile_days(days, p)) == d


def test_chart_tables():
    result = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40)
    hist = logic.chart_table(result)
    assert list(hist.columns) == ["finish_date", "runs"]
    assert int(hist["runs"].sum()) == result.facts.runs
    assert hist["finish_date"].is_monotonic_increasing
    marks = logic.marker_table(result.facts)
    assert list(marks["label"]) == ["50%", "85%", "95%", "Velocity"]
    f = result.facts
    assert list(marks["date"]) == [f.mc50, f.mc85, f.mc95, f.velocity_date]


def test_same_input_gives_the_same_result():
    a = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40)
    b = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40)
    assert a.facts == b.facts
    assert np.array_equal(a.finish_days, b.finish_days)


def test_report_shows_no_issue_keys():
    result = forecast_from_bytes(SAMPLE.read_bytes(), backlog=40)
    assert "SAMPLE-" not in result.report


# --- AC2: bad files give a clear error ---------------------------------------------------


@pytest.mark.parametrize(
    "data, expected",
    [
        (b"", "empty file"),
        (b"Issue_Key,Type\nA-1,Story\n", "missing column(s): Resolution_Date. "),
        (HEADER.encode() + b"A-1,Story,not a date,3\n", "line 2: bad Resolution_Date"),
        (HEADER.encode() + b"A-1,Story,2020-06-30,lots\n", "line 2: bad Story_Point"),
        (HEADER.encode() + b"A-1,Spaceship,2020-06-30,3\n", "Spaceship"),
        (HEADER.encode() + b"A-1,Story,,3\n", "no done item"),
        (b"\xff\xfe\x00bad", "not UTF-8 text"),
        (HEADER.encode(), "no rows"),
    ],
)
def test_bad_file_gives_a_clear_error(data, expected):
    with pytest.raises(WebError) as info:
        forecast_from_bytes(data, backlog=10)
    message = str(info.value)
    assert expected in message
    assert message.startswith("The file cannot be used:")
    assert "/tmp" not in message and "Traceback" not in message and "upload.csv" not in message


def test_error_names_no_temporary_path():
    with pytest.raises(WebError) as info:
        forecast_from_bytes(HEADER.encode() + b"A-1,Story,x,3\n", backlog=10)
    assert str(info.value).startswith("The file cannot be used: line 2")


def test_too_large_file_is_refused_before_reading():
    with pytest.raises(WebError, match="larger than 10 MB"):
        forecast_from_bytes(b"x" * (MAX_UPLOAD_BYTES + 1), backlog=10)


def test_no_value_item_in_the_window_is_a_clear_error():
    data = HEADER.encode() + b"A-1,Story,2020-01-01,3\n"
    with pytest.raises(WebError, match="no value item was done"):
        forecast_from_bytes(data, backlog=10, as_of=date(2020, 12, 31))


def test_unexpected_error_gives_a_fixed_message(monkeypatch):
    def boom(*a, **k):
        raise KeyError("internal detail")

    monkeypatch.setattr(logic, "compute_full", boom)
    with pytest.raises(WebError) as info:
        forecast_from_bytes(SAMPLE.read_bytes(), backlog=10)
    assert "internal detail" not in str(info.value)
    assert "could not be read" in str(info.value)


@pytest.mark.parametrize(
    "over",
    [{"backlog": 0}, {"backlog": -1}, {"backlog_points": 0.0}, {"seed": -1}],
)
def test_bad_inputs_are_a_clear_error(over):
    kwargs = {"backlog": 10, **over}
    with pytest.raises(WebError):
        forecast_from_bytes(SAMPLE.read_bytes(), **kwargs)


# --- packaging and settings ----------------------------------------------------------------


def test_streamlit_is_an_optional_extra_not_a_core_dependency():
    import tomllib

    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert not any(d.startswith("streamlit") for d in project["dependencies"])
    assert any(d.startswith("streamlit") for d in project["optional-dependencies"]["web"])


def test_streamlit_settings_limit_uploads_and_send_no_usage_data():
    import tomllib

    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())
    assert cfg["server"]["maxUploadSize"] == 10
    assert cfg["browser"]["gatherUsageStats"] is False


def test_logic_module_does_not_import_streamlit():
    source = (ROOT / "src" / "mcf" / "web" / "logic.py").read_text()
    assert "import streamlit" not in source


def test_ci_tests_and_licence_scan_cover_the_web_extra():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert ci.count('pip install -e ".[dev,web]"') == 2  # tests and security jobs
    assert '/tmp/runtime/bin/pip install --quiet ".[web]"' in ci  # D19 licence scan


# --- review fixes (PR #25) -------------------------------------------------------------


def test_page_words_replace_cli_words_in_errors():
    cases = {
        HEADER.encode() + b"A-1,Story,2020-01-01,3\n": "choose another forecast date",
        HEADER.encode() + b"A-1,Story,2020-06-30,3\nA-2,Spaceship,,2\n": "known issue type",
        HEADER.encode() + b"A-1,Story,2020-06-30,3\n\x80\n": "Save the file as CSV UTF-8",
    }
    for data, words in cases.items():
        with pytest.raises(WebError) as info:
            forecast_from_bytes(data, backlog=10, as_of=date(2020, 12, 31))
        message = str(info.value)
        assert words in message, message
        for cli_word in ("--as-of", "D04", "decision", "codec", "position"):
            assert cli_word not in message, message


def test_a_date_out_of_range_gets_its_own_message_and_is_logged(monkeypatch, caplog):
    # Year 1 itself is now a clear CLI error (MCF-29); this keeps the page's own
    # guard for any other date overflow.
    def boom(*a, **k):
        raise OverflowError("date value out of range")

    monkeypatch.setattr(logic, "compute_full", boom)
    with caplog.at_level("ERROR", logger="mcf.web.logic"):
        with pytest.raises(WebError, match="a date is too early or too late"):
            forecast_from_bytes(SAMPLE.read_bytes(), backlog=10)
    assert any(r.exc_info for r in caplog.records)


def test_an_unexpected_error_is_logged_on_the_server(monkeypatch, caplog):
    def boom(*a, **k):
        raise KeyError("internal detail")

    monkeypatch.setattr(logic, "compute_full", boom)
    with caplog.at_level("ERROR", logger="mcf.web.logic"):
        with pytest.raises(WebError):
            forecast_from_bytes(SAMPLE.read_bytes(), backlog=10)
    assert any("internal detail" in (r.exc_text or "") for r in caplog.records)


def test_an_error_never_shows_an_issue_key_from_the_file(monkeypatch):
    from mcf.forecast.throughput import ThroughputError

    def boom(*a, **k):
        raise ThroughputError("value item SECRET-77 has no done day")

    monkeypatch.setattr(logic, "compute_full", boom)
    data = HEADER.encode() + b"SECRET-77,Story,2020-06-30,3\n"
    with pytest.raises(WebError) as info:
        forecast_from_bytes(data, backlog=10)
    assert "SECRET-77" not in str(info.value)
    assert "an item" in str(info.value)


def test_error_text_is_escaped_for_markdown():
    assert logic.plain("a [link](http://x) *b* <i>") == r"a \[link\]\(http://x\) \*b\* \<i\>"


def test_the_shared_calculation_has_a_public_name():
    import mcf.cli

    assert mcf.cli.compute_full is logic.compute_full


def test_streamlit_minimum_supports_the_chart_width_argument():
    import tomllib

    web = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["optional-dependencies"][
        "web"
    ]
    assert "streamlit>=1.51" in web


def test_toolbar_hides_the_deploy_button():
    import tomllib

    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())
    assert cfg["client"]["toolbarMode"] == "viewer"


def test_readme_says_where_to_start_the_page_and_what_it_shows():
    readme = (ROOT / "README.md").read_text()
    assert "Start it from the repository root" in readme
    assert "The forecast and the report show no issue keys or file names" in readme
