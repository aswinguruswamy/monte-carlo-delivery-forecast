"""Regression test for MCF-29: a date near year 1 gave a raw OverflowError traceback.

Found in the MCF-24 independent review (2026-11-03). Expected: a clear
"mcf: error: ..." line and exit 1, like other bad input.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from mcf.cli import main

HEADER = "Issue_Key,Type,Resolution_Date,Story_Point\n"


@pytest.mark.parametrize(
    "rows, extra",
    [
        (["A-1,Story,0001-01-02,3"], []),
        (["A-1,Story,0001-03-01,3"], []),  # day t inside the first 84 days of year 1
        (["A-1,Story,2020-06-30,3"], ["--as-of", "0001-01-01"]),
    ],
)
def test_a_date_near_year_1_gives_a_clear_error(tmp_path, capsys, rows, extra):
    path = tmp_path / "team.csv"
    path.write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    code = main(["forecast", str(path), "--backlog", "10", *extra])
    out, err = capsys.readouterr()
    assert code == 1
    assert err.startswith("mcf: error: ")
    assert "the 84-day history window starts before the first calendar date" in err
    assert "Traceback" not in err and out == ""


def test_no_traceback_from_the_installed_command(tmp_path):
    path = tmp_path / "team.csv"
    path.write_text(HEADER + "A-1,Story,0001-01-02,3\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from mcf.cli import main; sys.exit(main(sys.argv[1:]))",
            *["forecast", str(path), "--backlog", "10"],
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith("mcf: error: ")


def test_the_web_page_shows_the_same_clear_text():
    from mcf.web.logic import WebError, forecast_from_bytes

    with pytest.raises(WebError, match="history window starts before the first calendar date"):
        forecast_from_bytes((HEADER + "A-1,Story,0001-01-02,3\n").encode(), backlog=10)
