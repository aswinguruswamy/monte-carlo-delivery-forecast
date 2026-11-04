"""The numbers and dates of one forecast (MCF-21).

Code calculates every value here (CLAUDE.md AI rule 1). The values are stored
as the printed report shows them (rounded), so Claude has nothing to calculate
and the MCF-22 check can find each number in the report. Only exact numbers,
booleans and dates are allowed: no text from the data (issue keys, types,
project or file names) can reach the AI prompt (NFR3, RAID C2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from datetime import date


def report_number(value: float) -> float:
    """Round a decimal as the report prints it: 1 decimal, or 3 significant digits below 0.1."""
    return float(f"{value:.1f}" if value >= 0.1 else f"{value:.3g}")


def report_percent(share: float) -> int:
    return round(share * 100)


_TYPES = {
    "t": date,
    "backlog": int,
    "window_start": date,
    "window_end": date,
    "items_done": int,
    "mc50": date,
    "mc85": date,
    "mc95": date,
    "runs": int,
    "velocity_date": date,
    "velocity_per_sprint": float,
    "points_needed": float,
    "points_estimated": bool,
    "open_items": int,
    "rows_no_date": int,
    "bug_share_percent": int,
    "items_no_points": int,
}
# MCF-32 (D43): with no story points in the history, there is no velocity date.
VELOCITY_FIELDS = ("velocity_date", "velocity_per_sprint", "points_needed")
NULLABLE = {"bug_share_percent", *VELOCITY_FIELDS}


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
    velocity_date: date | None
    velocity_per_sprint: float | None
    points_needed: float | None
    points_estimated: bool
    open_items: int
    rows_no_date: int
    bug_share_percent: int | None
    items_no_points: int = 0  # value items in the history window with no story point

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if value is None and f.name in NULLABLE:
                continue
            expected = _TYPES[f.name]
            if type(value) is not expected:  # exact type: no bool for int, no subclasses
                raise TypeError(f"{f.name}: expected {expected.__name__}, got {value!r}")
            if expected is float and not math.isfinite(value):
                raise ValueError(f"{f.name}: must be finite, got {value!r}")
            if expected in (int, float) and value < 0:
                raise ValueError(f"{f.name}: must be 0 or more, got {value!r}")
        if len({getattr(self, n) is None for n in VELOCITY_FIELDS}) > 1:
            raise ValueError(f"{', '.join(VELOCITY_FIELDS)} must be all set or all None")
        if self.backlog < 1 or self.runs < 1:
            raise ValueError("backlog and runs must be 1 or more")
        if self.bug_share_percent is not None and self.bug_share_percent > 100:
            raise ValueError("bug_share_percent must be at most 100")
        if not self.mc50 <= self.mc85 <= self.mc95:
            raise ValueError("the dates must be in order: 50% <= 85% <= 95%")
        if not self.window_start <= self.window_end == self.t:
            raise ValueError("the window must end on day t")
