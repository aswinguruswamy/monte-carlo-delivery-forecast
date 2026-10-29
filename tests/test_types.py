"""MCF-12 acceptance checks: sort issue types as D04 says (ADR 0002 Data rules 6-7)."""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from mcf.data.load import load_issues
from mcf.data.types import BUG, NOT_COUNTED, VALUE, IssueTypeError, sort_types

D04_VALUE = [
    "Story", "Task", "Improvement", "New Feature", "Suggestion", "Enhancement Request",
    "Sub-task", "Technical task", "Documentation", "Technical Debt", "Wish", "Question",
]  # fmt: skip
D04_BUG = ["Bug", "Build Failure", "Problem Ticket", "Incident"]
D04_NOT_COUNTED = ["Epic"]
DATA = Path(__file__).resolve().parents[1] / "data"


def issues(types: list[str], points: list[float] | None = None) -> pd.DataFrame:
    n = len(types)
    return pd.DataFrame(
        {
            "issue_key": [f"P-{i}" for i in range(n)],
            "type": types,
            "done_day": [date(2020, 1, 1)] * n,
            "story_point": points if points is not None else [1.0] * n,
        }
    )


@pytest.mark.parametrize(
    "type_name, kind",
    [(t, VALUE) for t in D04_VALUE]
    + [(t, BUG) for t in D04_BUG]
    + [(t, NOT_COUNTED) for t in D04_NOT_COUNTED],
)
def test_each_of_the_17_types_maps_as_in_d04(type_name, kind):
    sorted_, _ = sort_types(issues([type_name]), file="P.csv")
    assert sorted_["kind"].iloc[0] == kind


def test_the_map_has_exactly_17_types():
    from mcf.data.types import D04_KIND

    assert len(D04_KIND) == 17
    assert set(D04_KIND) == set(D04_VALUE + D04_BUG + D04_NOT_COUNTED)


@pytest.mark.parametrize("unknown", ["Spike", "story", "Story ", "", "Sub-Task"])
def test_unknown_type_stops_with_an_error_that_names_it(unknown):
    with pytest.raises(IssueTypeError, match=rf"P\.csv: unknown issue type {unknown!r} \(1 row"):
        sort_types(issues(["Story", unknown]), file="P.csv")


def test_bug_share_shows():
    _, summary = sort_types(issues(["Story", "Story", "Story", "Bug", "Epic"]), file="P.csv")
    assert (summary.value, summary.bug, summary.not_counted) == (3, 1, 1)
    # Bug share = bugs / (value + bugs): epics are containers, not work items (D04).
    assert summary.bug_share == pytest.approx(0.25)


def test_bug_share_is_none_when_there_is_no_work_item():
    # "0% bugs" would look like a real result; None means "no work items".
    _, summary = sort_types(issues(["Epic"]), file="P.csv")
    assert summary.bug_share is None


def test_empty_table_gives_zero_counts_and_no_bug_share():
    sorted_, summary = sort_types(issues([]), file="P.csv")
    assert len(sorted_) == 0 and "kind" in sorted_.columns
    assert (summary.value, summary.bug, summary.not_counted, summary.bug_share) == (0, 0, 0, None)


def test_value_item_with_no_story_point_stops_with_an_error():
    with pytest.raises(IssueTypeError, match=r"P\.csv: value item P-1 \(Task\) has no story point"):
        sort_types(issues(["Story", "Task"], [2.0, math.nan]), file="P.csv")


def test_bug_or_epic_with_no_story_point_is_fine():
    sorted_, _ = sort_types(issues(["Bug", "Epic"], [math.nan, math.nan]), file="P.csv")
    assert list(sorted_["kind"]) == [BUG, NOT_COUNTED]


def test_input_rows_are_not_changed_or_dropped():
    df = issues(["Story", "Bug", "Epic"])
    sorted_, _ = sort_types(df, file="P.csv")
    assert len(sorted_) == 3
    assert list(sorted_.columns) == ["issue_key", "type", "done_day", "story_point", "kind"]
    assert "kind" not in df.columns  # the input table is not changed


TAWOS_FILES = sorted(DATA.glob("*.csv")) if DATA.is_dir() else []


@pytest.mark.skipif(len(TAWOS_FILES) != 29, reason="TAWOS data not downloaded")
def test_tawos_types_are_all_known_and_value_items_have_points():
    seen: set[str] = set()
    for p in TAWOS_FILES:
        df, _ = load_issues(p)
        sort_types(df, file=p.name)  # raises on an unknown type or a missing point
        seen |= set(df["type"])
    assert seen == set(D04_VALUE + D04_BUG + D04_NOT_COUNTED)


# --- review findings ---------------------------------------------------------


@pytest.mark.parametrize("blank", [None, math.nan])
def test_blank_type_is_a_clear_unknown_type_error(blank):
    with pytest.raises(
        IssueTypeError, match=r"P\.csv: unknown issue type (None|nan) \(1 row\(s\)\)"
    ):
        sort_types(issues(["Story", blank]), file="P.csv")


def test_other_unknown_types_are_counted_with_blanks():
    with pytest.raises(IssueTypeError, match=r"'Spike' \(2 row\(s\); 1 other unknown type\(s\)\)"):
        sort_types(issues(["Spike", "Spike", None]), file="P.csv")


@pytest.mark.parametrize("missing", [pd.NA, None, math.nan])
def test_any_missing_point_on_a_value_item_is_a_clear_error(missing):
    df = issues(["Story", "Task"]).astype({"story_point": object})
    df.loc[1, "story_point"] = missing
    with pytest.raises(IssueTypeError, match=r"value item P-1 \(Task\) has no story point"):
        sort_types(df, file="P.csv")
