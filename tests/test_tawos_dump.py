"""MCF-28 checks: the streaming reader of the TAWOS SQL dump.

The reader returns only the allowed columns (ADR 0003 rule 2, C2): no title, description,
URL, issue key, names or user IDs. The fixture is a made-up mini dump.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcf.data.tawos_dump import ISSUE_COLUMNS, DumpError, read_table, sha256_of

MINI = Path(__file__).resolve().parent / "fixtures" / "tawos_mini.sql"


def test_issue_rows_hold_only_the_allowed_columns():
    rows = list(read_table(MINI, "Issue", ISSUE_COLUMNS))
    assert ISSUE_COLUMNS == (
        "ID",
        "Type",
        "Status",
        "Resolution",
        "Resolution_Date",
        "Story_Point",
        "Project_ID",
    )
    assert rows == [
        (1, "Story", "Closed", "Fixed", "2026-01-05 10:00:00", 3.0, 1),
        (2, "Bug", "Closed", "Won't Fix", "2026-01-06 11:00:00", None, 1),
        (3, "Sub-task", "Open", None, None, 1.5, 2),
        (4, "Epic", "Resolved", "Done", "2026-02-01 00:00:00", 8.0, 2),
    ]


def test_no_title_description_key_or_user_id_comes_out():
    text = repr(list(read_table(MINI, "Issue", ISSUE_COLUMNS)))
    for secret in ("Secret title", "quote", "AA-1", "BB-1", "77", "fake", "Project A"):
        assert secret not in text


def test_text_with_brackets_commas_and_quotes_does_not_split_a_row():
    rows = list(read_table(MINI, "Issue", ("ID",)))
    assert [r[0] for r in rows] == [1, 2, 3, 4]  # "x),(5,'fake'" is one text value


def test_project_keys_are_read():
    assert list(read_table(MINI, "Project", ("ID", "Project_Key"))) == [(1, "AA"), (2, "BB")]


def test_an_unknown_column_is_an_error():
    with pytest.raises(DumpError, match="no column 'Sprint'"):
        list(read_table(MINI, "Issue", ("ID", "Sprint")))


def test_a_missing_table_is_an_error():
    with pytest.raises(DumpError, match="no table 'Comment'"):
        list(read_table(MINI, "Comment", ("ID",)))


def test_a_row_with_the_wrong_number_of_values_is_an_error(tmp_path):
    bad = MINI.read_text().replace(",3,77,1),(2,", ",3,77),(2,")
    p = tmp_path / "bad.sql"
    p.write_text(bad)
    with pytest.raises(DumpError, match="row has 10 values, the table has 11 columns"):
        list(read_table(p, "Issue", ISSUE_COLUMNS))


def test_sha256_of_a_file(tmp_path):
    p = tmp_path / "x"
    p.write_bytes(b"abc")
    assert sha256_of(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_inventory_gives_counts_only():
    """ADR 0003 rules 3 and 6: types, resolutions and counts per project, before any run."""
    from mcf.data.tawos_dump import inventory

    inv = inventory(MINI)
    assert inv["types"] == {"Story": 1, "Bug": 1, "Sub-task": 1, "Epic": 1}
    assert inv["resolutions"] == {"Fixed": 1, "Won't Fix": 1, "(none)": 1, "Done": 1}
    assert inv["projects"] == {
        "AA": {"issues": 2, "resolved": 2, "with_points": 1},
        "BB": {"issues": 2, "resolved": 1, "with_points": 2},
    }
    assert inv["issues"] == 4
    assert "Secret" not in repr(inv) and "AA-1" not in repr(inv)


def test_export_writes_the_allowed_columns_only(tmp_path):
    """ADR 0003: the small file for the run holds no ID, key, title, text or user ID."""
    from mcf.data.tawos_dump import export_csv

    out = tmp_path / "issues.csv"
    assert export_csv(MINI, out) == 4
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "Project_Key,Type,Status,Resolution,Resolution_Date,Story_Point"
    assert lines[1:] == [
        "AA,Story,Closed,Fixed,2026-01-05 10:00:00,3.0",
        "AA,Bug,Closed,Won't Fix,2026-01-06 11:00:00,",
        "BB,Sub-task,Open,,,1.5",
        "BB,Epic,Resolved,Done,2026-02-01 00:00:00,8.0",
    ]
    text = out.read_text()
    for secret in ("Secret", "AA-1", "quote", "77", "Project A"):
        assert secret not in text
