"""MCF-31 checks: a Jira CSV export works for a user's own file (D42).

The back-test path keeps its strict rules (ADR 0002): only the user-file mode
(`open_items=True`, used by the CLI and the page) reads Jira names and dates.
The fixture is made-up data in the shape of a Jira Cloud export.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import pytest

from mcf.cli import main
from mcf.data.load import LoadError, load_issues

ROOT = Path(__file__).resolve().parents[1]
JIRA = ROOT / "tests" / "fixtures" / "jira_export.csv"
OURS = "Issue_Key,Type,Resolution_Date,Story_Point\n"


def jira_as_ours(tmp_path: Path) -> Path:
    """The same data as the Jira fixture, in our 4-column format with ISO dates."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Issue_Key", "Type", "Resolution_Date", "Story_Point"])
    with JIRA.open(newline="", encoding="utf-8") as fh:
        rows = csv.reader(fh)
        head = next(rows)
        for r in rows:
            row = dict(zip(head, r, strict=False))
            resolved = r[head.index("Resolved")]
            day = "" if not resolved else _iso(resolved)
            pts = r[11] or r[12]
            w.writerow([row["Issue key"], row["Issue Type"], day, pts])
    p = tmp_path / "ours.csv"
    p.write_text(out.getvalue(), encoding="utf-8")
    return p


def _iso(text: str) -> str:
    from datetime import datetime

    return datetime.strptime(text, "%d/%b/%y %I:%M %p").date().isoformat()


def write(tmp_path: Path, text: str, name: str = "team.csv") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# --- AC1: a Jira export works with no editing --------------------------------------------


def test_jira_export_gives_the_same_forecast_as_our_format(tmp_path, capsys):
    assert main(["forecast", str(JIRA), "--backlog", "30"]) == 0
    jira_out = capsys.readouterr().out
    assert main(["forecast", str(jira_as_ours(tmp_path)), "--backlog", "30"]) == 0
    ours_out = capsys.readouterr().out
    assert jira_out == ours_out
    assert "Open items skipped: 4" in jira_out


def test_the_web_page_logic_reads_a_jira_export():
    from mcf.web.logic import forecast_from_bytes

    result = forecast_from_bytes(JIRA.read_bytes(), backlog=30)
    assert result.facts.open_items == 4


# --- AC2: Jira column names -------------------------------------------------------------------


@pytest.mark.parametrize(
    "key, kind, done, points",
    [
        ("Issue key", "Issue Type", "Resolved", "Story Points"),
        ("Issue key", "Issue Type", "Resolved", "Story point estimate"),
        ("Issue key", "Issue Type", "Resolved", "Custom field (Story Points)"),
        ("Issue key", "Issue Type", "Resolved", "Custom field (Story point estimate)"),
        ("issue key", "issue type", "resolved", "story points"),  # any letter case
    ],
)
def test_jira_column_names_map_to_ours(tmp_path, key, kind, done, points):
    p = write(tmp_path, f"{key},{kind},{done},{points}\nA-1,Story,2026-09-30,3\n")
    issues, _ = load_issues(p, open_items=True)
    assert issues.loc[0, "issue_key"] == "A-1"
    assert issues.loc[0, "story_point"] == 3.0


def test_no_name_or_title_column_is_read():
    issues, _ = load_issues(JIRA, open_items=True)
    assert list(issues.columns) == ["issue_key", "type", "done_day", "story_point"]
    text = issues.to_string()
    assert "Person" not in text and "Made-up item" not in text


def test_points_come_from_whichever_story_point_column_has_a_value():
    issues, _ = load_issues(JIRA, open_items=True)
    stories = issues[issues["type"] == "Story"]
    assert stories["story_point"].notna().all()


def test_two_story_point_columns_with_different_values_are_an_error(tmp_path):
    p = write(
        tmp_path,
        "Issue key,Issue Type,Resolved,Story Points,Story point estimate\n"
        "A-1,Story,2026-09-30,3,5\n",
    )
    with pytest.raises(LoadError, match="line 2: 2 different story points"):
        load_issues(p, open_items=True)


# --- AC3: Jira date formats -------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, day",
    [
        ("03/Nov/26 4:35 PM", date(2026, 11, 3)),
        ("3/Nov/26 4:35 AM", date(2026, 11, 3)),
        ("03/Nov/2026 4:35 PM", date(2026, 11, 3)),
        ("03/nov/26 4:35 pm", date(2026, 11, 3)),
        ("03/Nov/26", date(2026, 11, 3)),
        ("2026-11-03 16:35", date(2026, 11, 3)),
        ("2026-11-03", date(2026, 11, 3)),
    ],
)
def test_jira_and_iso_dates_are_read(tmp_path, text, day):
    p = write(tmp_path, f"Issue key,Issue Type,Resolved,Story Points\nA-1,Story,{text},3\n")
    issues, _ = load_issues(p, open_items=True)
    assert issues.loc[0, "done_day"] == day


@pytest.mark.parametrize(
    "text", ["11/03/2026", "Nov 3 2026", "31/Feb/26 1:00 PM", "03/Nov/26 13:00 PM"]
)
def test_other_dates_are_a_clear_error_with_the_line(tmp_path, text):
    p = write(tmp_path, f"Issue key,Issue Type,Resolved,Story Points\nA-1,Story,{text},3\n")
    with pytest.raises(LoadError, match=r"line 2: bad Resolution_Date .* Use YYYY-MM-DD"):
        load_issues(p, open_items=True)


# --- AC4: repeated columns ----------------------------------------------------------------------


def test_repeated_columns_we_do_not_use_are_ignored():
    issues, report = load_issues(JIRA, open_items=True)
    assert report.rows_read == 133


def test_a_repeated_column_we_use_is_still_an_error(tmp_path):
    p = write(
        tmp_path,
        "Issue key,Issue Type,Resolved,Resolved,Story Points\nA-1,Story,2026-09-30,2026-09-30,3\n",
    )
    with pytest.raises(LoadError, match="duplicate column"):
        load_issues(p, open_items=True)


def test_our_name_and_a_jira_name_for_the_same_column_is_an_error(tmp_path):
    p = write(
        tmp_path,
        "Issue_Key,Issue key,Type,Resolution_Date,Story_Point\nA-1,A-1,Story,2026-09-30,3\n",
    )
    with pytest.raises(LoadError, match="2 columns for Issue_Key"):
        load_issues(p, open_items=True)


# --- AC5: the back-test path does not change (ADR 0002) ---------------------------------------


def test_the_back_test_loader_still_refuses_jira_names(tmp_path):
    p = write(tmp_path, "Issue key,Issue Type,Resolved,Story Points\nA-1,Story,2026-09-30,3\n")
    with pytest.raises(LoadError, match="missing column"):
        load_issues(p)


def test_the_back_test_loader_still_refuses_jira_dates(tmp_path):
    p = write(tmp_path, OURS + "A-1,Story,03/Nov/26 4:35 PM,3\n")
    with pytest.raises(LoadError, match="bad Resolution_Date"):
        load_issues(p)


def test_the_back_test_loader_still_refuses_any_repeated_column(tmp_path):
    p = write(
        tmp_path,
        "Issue_Key,Type,Resolution_Date,Story_Point,Sprint,Sprint\nA-1,Story,2026-09-30,3,x,y\n",
    )
    with pytest.raises(LoadError, match="duplicate column"):
        load_issues(p)


def test_the_page_hides_jira_issue_keys_in_messages():
    from mcf.web import logic

    keys = logic._keys(JIRA.read_bytes())
    assert "DEMO-101" in keys and len(keys) == 133


def test_the_fixture_is_small_and_made_up():
    text = JIRA.read_text(encoding="utf-8")
    assert JIRA.stat().st_size < 100 * 1024
    assert "DEMO-" in text and "Made-up item" in text
