"""The numbers and dates of one forecast (MCF-21).

Code calculates every value here (CLAUDE.md AI rule 1). Only numbers, booleans,
None and dates are allowed, so no text from the data (issue keys, types,
project or file names) can reach the AI prompt (NFR3, RAID C2).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime


@dataclass(frozen=True)
class ForecastFacts:
    t: date
    backlog: int
    window_start: date
    window_end: date
    items_done: int
    mc50: date
    mc85: date
    mc95: date
    runs: int
    velocity_date: date
    velocity_per_sprint: float
    points_needed: float
    points_estimated: bool
    open_items: int
    rows_no_date: int
    bug_share: float | None

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if value is None and f.name == "bug_share":
                continue
            if isinstance(value, datetime) or isinstance(value, str):
                raise TypeError(f"{f.name}: text and datetimes are not allowed, got {value!r}")
            if not isinstance(value, (date, int, float, bool)):
                raise TypeError(f"{f.name}: only numbers, booleans and dates, got {value!r}")
