"""MCF-11 acceptance checks: load and check an issue CSV (D02, ADR 0002 Data rules).

Made-up data only. The TAWOS check runs when the downloaded data exists
(`python -m mcf.data.download --dest data`) and is skipped otherwise (CI).
"""

from __future__ import annotations

import math
import time
from datetime import date
from pathlib import Path

import pytest

from mcf.data.load import LoadError, load_issues

HEADER = "Issue_Key,Type,Status,Resolution_Date,Story_Point\n"
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def write(tmp_path: Path, body: str, header: str = HEADER, name: str = "P.csv") -> Path:
    p = tmp_path / name
    p.write_text(header + body, encoding="utf-8")
    return p


# --- good input --------------------------------------------------------------


def test_loads_rows_with_done_day_and_decimal_points(tmp_path):
    p = write(
        tmp_path,
        "P-1,Story,Done,2020-01-31 23:59:59,3\nP-2,Bug,Won't Fix,2020-02-01 00:00:00,1.5\n",
    )
    issues, report = load_issues(p)
    assert list(issues["issue_key"]) == ["P-1", "P-2"]
    assert list(issues["type"]) == ["Story", "Bug"]
    # Done day = first 10 characters; no time zone conversion (ADR 0002 rule 5).
    assert list(issues["done_day"]) == [date(2020, 1, 31), date(2020, 2, 1)]
    assert list(issues["story_point"]) == [3.0, 1.5]
    assert (report.rows_read, report.rows_no_date, report.rows_kept) == (2, 0, 2)
    assert report.file == "P.csv"


def test_rows_with_no_date_are_removed_and_counted(tmp_path):
    p = write(
        tmp_path,
        "P-1,Story,Done,2020-01-01 10:00:00,2\nP-2,Story,Open,NULL,2\nP-3,Story,Open,,2\n",
    )
    issues, report = load_issues(p)
    assert list(issues["issue_key"]) == ["P-1"]
    assert (report.rows_read, report.rows_no_date, report.rows_kept) == (3, 2, 1)


def test_empty_story_point_is_kept_as_missing_for_mcf12(tmp_path):
    issues, _ = load_issues(write(tmp_path, "P-1,Story,Done,2020-01-01 10:00:00,\n"))
    assert math.isnan(issues["story_point"].iloc[0])


def test_extra_columns_are_ignored(tmp_path):
    p = write(
        tmp_path,
        "1,P-1,Story,x,2020-01-01 10:00:00,2,99\n",
        header="ID,Issue_Key,Type,Status,Resolution_Date,Story_Point,Timespent\n",
    )
    issues, _ = load_issues(p)
    assert list(issues.columns) == ["issue_key", "type", "done_day", "story_point"]


# --- bad input: clear errors that name the file and the row ------------------


def test_missing_column_names_the_file_and_the_column(tmp_path):
    p = write(tmp_path, "P-1,Story,2020-01-01\n", header="Issue_Key,Type,Resolution_Date\n")
    with pytest.raises(LoadError, match=r"P\.csv: missing column\(s\): Story_Point"):
        load_issues(p)


@pytest.mark.parametrize("bad", ["2020-13-45 10:00:00", "31/01/2020", "yesterday", "2020-1-5"])
def test_bad_date_names_the_file_and_the_line(tmp_path, bad):
    p = write(tmp_path, f"P-1,Story,Done,2020-01-01 10:00:00,1\nP-2,Story,Done,{bad},1\n")
    with pytest.raises(LoadError, match=r"P\.csv, line 3: bad Resolution_Date"):
        load_issues(p)


def test_bad_story_point_names_the_file_and_the_line(tmp_path):
    p = write(tmp_path, "P-1,Story,Done,2020-01-01 10:00:00,abc\n")
    with pytest.raises(LoadError, match=r"P\.csv, line 2: bad Story_Point 'abc'"):
        load_issues(p)


def test_header_only_file_has_no_rows(tmp_path):
    with pytest.raises(LoadError, match=r"P\.csv: no rows"):
        load_issues(write(tmp_path, ""))


def test_empty_file_is_a_clear_error(tmp_path):
    p = tmp_path / "P.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(LoadError, match=r"P\.csv: (no rows|empty file)"):
        load_issues(p)


def test_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(LoadError, match=r"nope\.csv: file not found"):
        load_issues(tmp_path / "nope.csv")


# --- size (AC3) --------------------------------------------------------------


def test_100000_rows_load_quickly(tmp_path):
    body = "".join(
        f"P-{i},Story,Done,2020-01-{i % 28 + 1:02d} 10:00:00,{i % 8}\n" for i in range(100_000)
    )
    p = write(tmp_path, body)
    start = time.perf_counter()
    issues, report = load_issues(p)
    assert time.perf_counter() - start < 10
    assert len(issues) == report.rows_kept == 100_000


# --- the real TAWOS data (AC2; runs locally, skipped in CI) -----------------

TAWOS_FILES = sorted(DATA.glob("*.csv")) if DATA.is_dir() else []


@pytest.mark.skipif(len(TAWOS_FILES) != 29, reason="TAWOS data not downloaded")
def test_tawos_data_loads_with_19_rows_with_no_date():
    reports = {p.stem: load_issues(p)[1] for p in TAWOS_FILES}
    assert sum(r.rows_read for r in reports.values()) == 47_205
    assert sum(r.rows_no_date for r in reports.values()) == 19
    no_date = {k: r.rows_no_date for k, r in reports.items() if r.rows_no_date}
    assert no_date == {"APIKIT": 1, "DM": 2, "JSWCLOUD": 5, "MDL": 11}
