"""Load an issue CSV and check it (D02, ADR 0002 Data rules).

Rules:
- Required columns: Issue_Key, Type, Resolution_Date, Story_Point. Other columns are ignored.
- The done day is the first 10 characters of Resolution_Date (YYYY-MM-DD).
  There is no time zone conversion.
- A row whose Resolution_Date is "NULL" or empty has no done day. It is removed
  and counted in the report. No other row is removed or changed.
- Story_Point is a decimal number. An empty or "NULL" value stays missing (NaN);
  MCF-12 decides when a missing point is an error.
- Any other bad value stops the load with an error that names the file and the
  line (line 1 is the header).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED = ["Issue_Key", "Type", "Resolution_Date", "Story_Point"]
NO_VALUE = {"", "NULL"}
DATE_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}(?:[ T].*)?")


class LoadError(ValueError):
    """The CSV file cannot be used."""


@dataclass(frozen=True)
class LoadReport:
    file: str
    rows_read: int
    rows_no_date: int

    @property
    def rows_kept(self) -> int:
        return self.rows_read - self.rows_no_date


def _line(index: int) -> int:
    """CSV line number of a data row (line 1 is the header)."""
    return int(index) + 2


def load_issues(path: str | Path) -> tuple[pd.DataFrame, LoadReport]:
    path = Path(path)
    name = path.name
    if not path.is_file():
        raise LoadError(f"{name}: file not found")
    try:
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    except pd.errors.EmptyDataError as exc:
        raise LoadError(f"{name}: empty file") from exc
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise LoadError(f"{name}: not a readable CSV file: {exc}") from exc

    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        raise LoadError(f"{name}: missing column(s): {', '.join(missing)}")
    if raw.empty:
        raise LoadError(f"{name}: no rows")

    raw = raw[REQUIRED]
    resolution = raw["Resolution_Date"].str.strip()
    has_date = ~resolution.isin(NO_VALUE)

    # Dates: the text must look like YYYY-MM-DD..., and the day must exist.
    dated = resolution[has_date]
    shape_ok = dated.str.fullmatch(DATE_TEXT)
    day = pd.to_datetime(dated.str[:10], format="%Y-%m-%d", errors="coerce")
    bad_date = ~shape_ok | day.isna()
    if bad_date.any():
        i = bad_date.idxmax()
        raise LoadError(f"{name}, line {_line(i)}: bad Resolution_Date {dated[i]!r}")

    # Story points: a decimal number, or empty / NULL (kept as missing).
    points_text = raw["Story_Point"].str.strip()
    blank = points_text.isin(NO_VALUE)
    points = pd.to_numeric(points_text.where(~blank), errors="coerce")
    bad_point = ~blank & points.isna()
    if bad_point.any():
        i = bad_point.idxmax()
        raise LoadError(f"{name}, line {_line(i)}: bad Story_Point {points_text[i]!r}")

    issues = pd.DataFrame(
        {
            "issue_key": raw.loc[has_date, "Issue_Key"],
            "type": raw.loc[has_date, "Type"],
            "done_day": day.dt.date,
            "story_point": points[has_date].astype(float),
        }
    ).reset_index(drop=True)
    report = LoadReport(file=name, rows_read=len(raw), rows_no_date=int((~has_date).sum()))
    return issues, report
