"""Load an issue CSV and check it (D02, ADR 0002 Data rules).

Rules:
- Required columns: Issue_Key, Type, Resolution_Date, Story_Point. Other columns
  are ignored. A duplicate column name is an error.
- Each row must have as many fields as the header. Blank lines are skipped.
- Only a Resolution_Date that is exactly the text "NULL" means "no date". That
  row is removed and counted (ADR 0002 rule 3). Any other value must be a date.
- Open-items mode (D25, CLI only, `open_items=True`): an empty Resolution_Date
  means "open, not done". That row is removed and counted; its Story_Point is
  still checked, and its Type is listed in `open_types` for the caller to check.
  The back-test never uses this mode.
- The done day is the first 10 characters of Resolution_Date (YYYY-MM-DD). There
  is no time zone conversion (ADR 0002 rule 5).
- Story_Point is a decimal number above 0. An empty or "NULL" value stays missing
  (NaN); MCF-12 decides when a missing point is an error.
- Jira export (D42, user-file mode only): the loader also accepts the Jira column
  names in `ALIASES` (any letter case) and the Jira dates "03/Nov/26 4:35 PM",
  "03/Nov/2026 4:35 PM" and "03/Nov/26". The time is ignored, as for ISO dates.
  Two story point columns are allowed; the row takes the value that is not empty,
  and 2 different values are an error. Repeated columns that the loader does not
  use (for example "Sprint") are ignored. A used column that shows 2 times, or our
  name together with a Jira name for the same column, is an error. The loader
  never reads the other columns, so names and titles never load (RAID C2). The
  back-test path keeps the strict rules above (ADR 0002).
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
JIRA_DATE = re.compile(
    r"(\d{1,2})/([A-Za-z]{3})/(\d{2}|\d{4})(?:\s+(\d{1,2}):(\d{2})\s*([AaPp][Mm]))?", re.ASCII
)
MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )
}
# User-file mode only (D42): the column names we accept, in lower case.
ALIASES = {
    "Issue_Key": ("issue_key", "issue key"),
    "Type": ("type", "issue type"),
    "Resolution_Date": ("resolution_date", "resolved"),
    "Story_Point": (
        "story_point",
        "story points",
        "story point estimate",
        "custom field (story points)",
        "custom field (story point estimate)",
    ),
}
JIRA_HINT = "A Jira export needs the columns Issue key, Issue Type, Resolved and Story Points."
DATE_HINT = "Use YYYY-MM-DD or the Jira form 03/Nov/26 4:35 PM."


class LoadError(ValueError):
    """The CSV file cannot be used."""


@dataclass(frozen=True)
class LoadReport:
    file: str
    rows_read: int
    rows_no_date: int
    rows_open: int = 0
    open_types: tuple[str, ...] = ()

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


def _jira_day(text: str) -> date | None:
    """A Jira export date, or ISO; None if the text is neither (user-file mode only)."""
    text = text.strip()
    day = _done_day(text)
    if day is not None:
        return day
    m = JIRA_DATE.fullmatch(text)
    if not m or m[2].lower() not in MONTHS:
        return None
    if m[4] is not None and not (1 <= int(m[4]) <= 12 and int(m[5]) <= 59):
        return None
    year = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
    try:
        return date(year, MONTHS[m[2].lower()], int(m[1]))
    except ValueError:
        return None


def column_indexes(header: list[str], *, user_file: bool) -> dict[str, list[int]]:
    """The header position(s) of each required column, or a LoadError message.

    Strict (back-test) mode: our exact names, one position each. User-file mode
    (D42): our names or the Jira names, any letter case; Story_Point may have more
    than one column with different names.
    """
    if not user_file:
        dupes = sorted({c for c in header if header.count(c) > 1})
        if dupes:
            raise ValueError(f"duplicate column(s): {', '.join(dupes)}")
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise ValueError(f"missing column(s): {', '.join(missing)}")
        return {c: [header.index(c)] for c in REQUIRED}

    names = [c.strip().lower() for c in header]
    found: dict[str, list[int]] = {}
    missing = []
    for field in REQUIRED:
        idx = [i for i, n in enumerate(names) if n in ALIASES[field]]
        if not idx:
            missing.append(field)
            continue
        used = [names[i] for i in idx]
        dupes = sorted({header[i] for i in idx if used.count(names[i]) > 1})
        if dupes:
            raise ValueError(f"duplicate column(s): {', '.join(dupes)}")
        if len(idx) > 1 and field != "Story_Point":
            shown = ", ".join(repr(header[i]) for i in idx)
            raise ValueError(f"{len(idx)} columns for {field}: {shown}. Keep one.")
        found[field] = idx
    if missing:
        raise ValueError(f"missing column(s): {', '.join(missing)}. {JIRA_HINT}")
    return found


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


def _row_point(row: list[str], idx: list[int], name: str, line: int) -> float:
    """The row's story point: the one value that is not empty, or NaN."""
    values = []
    for i in idx:
        value = _story_point(row[i])
        if value is None:
            raise LoadError(f"{name}, line {line}: bad Story_Point {row[i]!r}")
        if not math.isnan(value):
            values.append(value)
    if len(set(values)) > 1:
        raise LoadError(
            f"{name}, line {line}: 2 different story points ({', '.join(map(str, values))}). "
            "Keep one story point column, or make the values the same."
        )
    return values[0] if values else math.nan


def load_issues(path: str | Path, *, open_items: bool = False) -> tuple[pd.DataFrame, LoadReport]:
    path = Path(path)
    name = path.name
    if path.exists() and not path.is_file():
        raise LoadError(f"{path}: not a file")
    if not path.is_file():
        raise LoadError(f"{name}: file not found")

    keys, types, days, points = [], [], [], []
    rows_read = rows_no_date = rows_open = 0
    open_types: list[str] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh, strict=True)
            header = next(reader, None)
            if header is None:
                raise LoadError(f"{name}: empty file")
            try:
                cols = column_indexes(header, user_file=open_items)
            except ValueError as exc:
                raise LoadError(f"{name}: {exc}") from None
            col = {c: i[0] for c, i in cols.items()}
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
                if open_items and resolution == "":
                    _row_point(row, cols["Story_Point"], name, line)  # still checked (D25)
                    rows_open += 1
                    open_types.append(row[col["Type"]])
                    continue
                day = _jira_day(resolution) if open_items else _done_day(resolution)
                if day is None:
                    hint = f" in column {header[col['Resolution_Date']]!r}. {DATE_HINT}"
                    raise LoadError(
                        f"{name}, line {line}: bad Resolution_Date {resolution!r}"
                        + (hint if open_items else "")
                    )
                point = _row_point(row, cols["Story_Point"], name, line)
                keys.append(row[col["Issue_Key"]])
                types.append(row[col["Type"]])
                days.append(day)
                points.append(point)
    except UnicodeDecodeError as exc:
        raise LoadError(f"{name}: not UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise LoadError(f"{name}: cannot read the file: {exc}") from exc
    except csv.Error as exc:
        raise LoadError(f"{name}, line {reader.line_num}: not a readable CSV file: {exc}") from exc

    if rows_read == 0:
        raise LoadError(f"{name}: no rows")
    report = LoadReport(
        file=name,
        rows_read=rows_read,
        rows_no_date=rows_no_date,
        rows_open=rows_open,
        open_types=tuple(open_types),
    )
    issues = pd.DataFrame(
        {"issue_key": keys, "type": types, "done_day": days, "story_point": points},
        columns=["issue_key", "type", "done_day", "story_point"],
    ).astype({"issue_key": object, "type": object, "done_day": object, "story_point": float})
    return issues, report
