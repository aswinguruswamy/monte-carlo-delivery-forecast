"""Load an issue CSV and check it (D02, ADR 0002 Data rules).

Rules:
- Required columns: Issue_Key, Type, Resolution_Date, Story_Point. Other columns
  are ignored. A duplicate column name is an error.
- Each row must have as many fields as the header. Blank lines are skipped.
- Only a Resolution_Date that is exactly the text "NULL" means "no date". That
  row is removed and counted (ADR 0002 rule 3). Any other value must be a date.
- Open-items mode (D25, CLI only, `open_items=True`): an empty or blank
  Resolution_Date means "open, not done". That row is removed and counted. The
  back-test never uses this mode.
- The done day is the first 10 characters of Resolution_Date (YYYY-MM-DD). There
  is no time zone conversion (ADR 0002 rule 5).
- Story_Point is a decimal number above 0. An empty or "NULL" value stays missing
  (NaN); MCF-12 decides when a missing point is an error.
- A bad value stops the load with an error that names the file and the real
  line in the file (line 1 is the header).
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

REQUIRED = ["Issue_Key", "Type", "Resolution_Date", "Story_Point"]
NO_DATE = "NULL"
NO_POINT = {"", "NULL"}
DATE_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}(?:[ T].*)?")
POINT_TEXT = re.compile(r"[0-9]+(?:\.[0-9]+)?|\.[0-9]+", re.ASCII)


class LoadError(ValueError):
    """The CSV file cannot be used."""


@dataclass(frozen=True)
class LoadReport:
    file: str
    rows_read: int
    rows_no_date: int
    rows_open: int = 0

    @property
    def rows_kept(self) -> int:
        return self.rows_read - self.rows_no_date - self.rows_open


def _done_day(text: str) -> date | None:
    if not DATE_TEXT.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _story_point(text: str) -> float | None:
    """Return the point value, NaN for no value, or None if the value is bad."""
    if text.strip() in NO_POINT:
        return math.nan
    if not POINT_TEXT.fullmatch(text.strip()):
        return None
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def load_issues(path: str | Path, open_items: bool = False) -> tuple[pd.DataFrame, LoadReport]:
    path = Path(path)
    name = path.name
    if not path.is_file():
        raise LoadError(f"{name}: file not found")

    keys, types, days, points = [], [], [], []
    rows_read = rows_no_date = rows_open = 0
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh, strict=True)
            header = next(reader, None)
            if header is None:
                raise LoadError(f"{name}: empty file")
            dupes = sorted({c for c in header if header.count(c) > 1})
            if dupes:
                raise LoadError(f"{name}: duplicate column(s): {', '.join(dupes)}")
            missing = [c for c in REQUIRED if c not in header]
            if missing:
                raise LoadError(f"{name}: missing column(s): {', '.join(missing)}")
            col = {c: header.index(c) for c in REQUIRED}
            width = len(header)

            for row in reader:
                line = reader.line_num  # real line of the row's last physical line
                if not row:
                    continue  # blank line
                if len(row) != width:
                    raise LoadError(
                        f"{name}, line {line}: expected {width} fields, found {len(row)}"
                    )
                rows_read += 1
                resolution = row[col["Resolution_Date"]]
                if resolution == NO_DATE:
                    rows_no_date += 1
                    continue
                if open_items and not resolution.strip():
                    rows_open += 1
                    continue
                day = _done_day(resolution)
                if day is None:
                    raise LoadError(f"{name}, line {line}: bad Resolution_Date {resolution!r}")
                point_text = row[col["Story_Point"]]
                point = _story_point(point_text)
                if point is None:
                    raise LoadError(f"{name}, line {line}: bad Story_Point {point_text!r}")
                keys.append(row[col["Issue_Key"]])
                types.append(row[col["Type"]])
                days.append(day)
                points.append(point)
    except UnicodeDecodeError as exc:
        raise LoadError(f"{name}: not UTF-8 text: {exc}") from exc
    except csv.Error as exc:
        raise LoadError(f"{name}, line {reader.line_num}: not a readable CSV file: {exc}") from exc

    if rows_read == 0:
        raise LoadError(f"{name}: no rows")
    report = LoadReport(
        file=name, rows_read=rows_read, rows_no_date=rows_no_date, rows_open=rows_open
    )
    issues = pd.DataFrame(
        {"issue_key": keys, "type": types, "done_day": days, "story_point": points},
        columns=["issue_key", "type", "done_day", "story_point"],
    ).astype({"issue_key": object, "type": object, "done_day": object, "story_point": float})
    return issues, report
