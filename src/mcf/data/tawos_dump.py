"""Read rows from the full TAWOS MySQL dump without a database (MCF-28, ADR 0003).

The dump (`TAWOS.sql`, about 4.3 GB) is read line by line. Only the columns that the
caller names come out; every other value (titles, descriptions, URLs, issue keys, user
IDs) is skipped as it is read and never kept (ADR 0003 rule 2, C2).

Standard library only, so it runs where the data is (Python 3.10 or later).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from pathlib import Path

# ADR 0003 rule 2: the only Issue columns the v2 back-test may load.
ISSUE_COLUMNS = (
    "ID",
    "Type",
    "Status",
    "Resolution",
    "Resolution_Date",
    "Story_Point",
    "Project_ID",
)
PROJECT_COLUMNS = ("ID", "Project_Key")

_CREATE = re.compile(r"^CREATE TABLE `([^`]+)` \(")
_COLUMN = re.compile(r"^\s+`([^`]+)` (\w+)")
_TOKEN = re.compile(r"'((?:[^'\\]|\\.)*)'|(NULL)|([-+0-9.eE]+)|(\()|(\))|(,)|(;)", re.S)
_ESCAPES = {"0": "\0", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a", "b": "\b"}
_INT_TYPES = {"int", "tinyint", "smallint", "mediumint", "bigint"}
_FLOAT_TYPES = {"double", "float", "decimal"}


class DumpError(ValueError):
    """The dump is not in the expected shape."""


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), text, flags=re.S)


def _convert(token: re.Match, sql_type: str):
    if token.group(2):
        return None
    if token.group(1) is not None:
        return _unescape(token.group(1))
    number = token.group(3)
    if sql_type in _INT_TYPES:
        return int(number)
    if sql_type in _FLOAT_TYPES:
        return float(number)
    return number


def _schema(path: Path, table: str) -> list[tuple[str, str]]:
    columns: list[tuple[str, str]] = []
    inside = False
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not inside:
                m = _CREATE.match(line)
                inside = bool(m and m.group(1) == table)
                continue
            col = _COLUMN.match(line)
            if not col:
                return columns
            columns.append((col.group(1), col.group(2).lower()))
    raise DumpError(f"no table '{table}' in the dump")


def read_table(path: Path, table: str, wanted: tuple[str, ...]) -> Iterator[tuple]:
    """Yield one tuple per row of `table`, holding only the `wanted` columns, in that order."""
    schema = _schema(Path(path), table)
    names = [name for name, _ in schema]
    for name in wanted:
        if name not in names:
            raise DumpError(f"no column '{name}' in table '{table}'")
    keep = [(names.index(name), schema[names.index(name)][1]) for name in wanted]
    start = f"INSERT INTO `{table}` "
    prefix = f"{start}VALUES "
    width = len(schema)
    with Path(path).open(encoding="utf-8", errors="replace") as fh:
        for number, line in enumerate(fh, 1):
            if not line.startswith(start):
                continue
            if not line.startswith(prefix):
                raise DumpError(f"line {number}: unexpected INSERT form for table '{table}'")
            row: list[re.Match] | None = None
            ended = False
            for token in _TOKEN.finditer(line, len(prefix)):
                if token.group(4):
                    row = []
                elif token.group(5):
                    if row is None or len(row) != width:
                        got = 0 if row is None else len(row)
                        raise DumpError(f"row has {got} values, the table has {width} columns")
                    yield tuple(_convert(row[i], kind) for i, kind in keep)
                    row = None
                elif token.group(7):
                    ended = True
                elif token.group(6):
                    continue
                elif row is not None:
                    row.append(token)
            # Review MCF-28: a split, cut-off or broken line must not lose rows silently.
            if row is not None or not ended:
                raise DumpError(f"line {number}: the INSERT does not end with ';'")


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    """The SHA-256 of a file, read in chunks (ADR 0003 rule 1)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def inventory(path: Path) -> dict:
    """Counts only, for ADR 0003 rules 3 and 6: no dates, no back-test results."""
    keys = dict(read_table(path, "Project", PROJECT_COLUMNS))
    types: dict[str, int] = {}
    resolutions: dict[str, int] = {}
    projects: dict[str, dict[str, int]] = {}
    total = 0
    for _id, kind, _status, resolution, done, points, project in read_table(
        path, "Issue", ISSUE_COLUMNS
    ):
        total += 1
        types[kind or "(none)"] = types.get(kind or "(none)", 0) + 1
        name = resolution or "(none)"
        resolutions[name] = resolutions.get(name, 0) + 1
        p = projects.setdefault(
            keys.get(project, f"(project {project})"),
            {"issues": 0, "resolved": 0, "with_points": 0},
        )
        p["issues"] += 1
        p["resolved"] += done is not None
        p["with_points"] += points is not None
    return {"issues": total, "types": types, "resolutions": resolutions, "projects": projects}


EXPORT_HEADER = ("Project_Key", "Type", "Status", "Resolution", "Resolution_Date", "Story_Point")


def export_csv(path: Path, out: Path, expected_rows: int | None = None) -> int:
    """Write the allowed columns only, one row per issue (ADR 0003); return the row count.

    The issue ID is dropped too: the run needs only the project, the type, the
    resolution, the resolution date and the story points. With `expected_rows`
    (458,232 for TAWOS V. 1.0), a different count is an error.
    """
    import csv

    keys = dict(read_table(path, "Project", PROJECT_COLUMNS))
    count = 0
    with Path(out).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(EXPORT_HEADER)
        for _id, kind, status, resolution, done, points, project in read_table(
            path, "Issue", ISSUE_COLUMNS
        ):
            if project not in keys:
                raise DumpError(f"unknown Project_ID {project} in table 'Issue'")
            writer.writerow([keys[project], kind, status, resolution, done, points])
            count += 1
    if expected_rows is not None and count != expected_rows:
        raise DumpError(f"the export has {count} rows, expected {expected_rows}")
    return count
