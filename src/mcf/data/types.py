"""Sort issue types into value, bug and not counted (D04, ADR 0002 Data rules 6-7).

Only value items count in throughput and velocity. Bugs show as a share only.
Epics are containers and do not count. Type names are matched exactly, as
recorded. An unknown type is an error, never a silent default.

Story points are checked for presence only. `load_issues` already rejects
points that are not finite or not above 0, so pass only tables from it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

VALUE = "value"
BUG = "bug"
NOT_COUNTED = "not counted"

D04_KIND = {
    **dict.fromkeys(
        [
            "Story",
            "Task",
            "Improvement",
            "New Feature",
            "Suggestion",
            "Enhancement Request",
            "Sub-task",
            "Technical task",
            "Documentation",
            "Technical Debt",
            "Wish",
            "Question",
        ],
        VALUE,
    ),
    **dict.fromkeys(["Bug", "Build Failure", "Problem Ticket", "Incident"], BUG),
    "Epic": NOT_COUNTED,
}


class IssueTypeError(ValueError):
    """An issue type or a value item cannot be used."""


@dataclass(frozen=True)
class TypeSummary:
    value: int
    bug: int
    not_counted: int

    @property
    def bug_share(self) -> float | None:
        """Bugs as a share of work items (value + bugs). Epics are not work items.

        None when there is no work item, so a report does not show a false "0%".
        """
        work = self.value + self.bug
        return self.bug / work if work else None


def sort_types(issues: pd.DataFrame, file: str) -> tuple[pd.DataFrame, TypeSummary]:
    """Return a copy of the issues with a `kind` column, and a summary."""
    kind = issues["type"].map(D04_KIND)
    unknown = issues.loc[kind.isna(), "type"]
    if not unknown.empty:
        counts = unknown.value_counts(dropna=False, sort=False)
        first = unknown.iloc[0]
        count = int(counts[first]) if first in counts.index else int(unknown.isna().sum())
        others = len(counts) - 1
        more = f"; {others} other unknown type(s)" if others else ""
        raise IssueTypeError(
            f"{file}: unknown issue type {first!r} ({count} row(s){more}). "
            "Add it to D04 with a new decision, or fix the data."
        )

    value_rows = issues[kind == VALUE]
    no_point = value_rows["story_point"].isna()
    if no_point.any():
        row = value_rows[no_point].iloc[0]
        raise IssueTypeError(
            f"{file}: value item {row['issue_key']} ({row['type']}) has no story point"
        )

    sorted_ = issues.assign(kind=kind)
    summary = TypeSummary(
        value=int((kind == VALUE).sum()),
        bug=int((kind == BUG).sum()),
        not_counted=int((kind == NOT_COUNTED).sum()),
    )
    return sorted_, summary
