"""Back-test run (ADR 0002, accepted as D21.1; MCF-17).

For each project, forecast date t and backlog size N, this makes one case: the
Monte Carlo 50/85/95% dates, the velocity date and the actual date. Metrics are
MCF-18. Only the window t-83..t feeds the Monte Carlo and velocity speed; the
points needed of the next N items come from after t by ADR design (Velocity
method 4).

`tie_rule` (proposed D29) says which points count when the N-th item's day
holds more items than needed: "row" = file row order; "mean" = the mean points
of that day's items x the number needed. It has no default: the PM decides.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from mcf.data.load import LoadReport, load_issues
from mcf.data.types import VALUE, sort_types
from mcf.forecast.montecarlo import RUNS, case_generator, forecast_dates
from mcf.forecast.throughput import counts_from_ordinals, done_ordinals, window
from mcf.forecast.velocity import velocity_date, window_velocity

SIZES = (10, 25, 50)
STEP_DAYS = 14
FIRST_OFFSET_DAYS = 83
TIE_RULES = ("row", "mean")
SUMMARY_COLUMNS = [
    "project",
    "p",
    "rows_read",
    "rows_no_date",
    "n",
    "cases",
    "no_forecast",
    "short_dates",
]
CASE_COLUMNS = [
    "project",
    "p",
    "t",
    "n",
    "no_forecast",
    "mc50",
    "mc85",
    "mc95",
    "velocity",
    "actual",
]


class BacktestError(ValueError):
    """The back-test cannot run on this input."""


@dataclass(frozen=True)
class Case:
    project: str
    p: int
    t: date
    n: int
    no_forecast: bool
    mc50: date | None
    mc85: date | None
    mc95: date | None
    velocity: date | None
    actual: date


@dataclass
class ProjectSummary:
    """Per project and size N: cases, no-forecast cases, and short dates.

    Short dates are dates on the 14-day sequence, up to the project's last value
    day, that are not forecast dates because fewer than N value items were done
    after them (ADR 0002, Cases with no forecast).
    """

    project: str
    p: int
    load: LoadReport | None = None
    cases: dict[int, int] = field(default_factory=dict)
    no_forecast: dict[int, int] = field(default_factory=dict)
    short_dates: dict[int, int] = field(default_factory=dict)


def _value_items(issues: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Value-item done days (ordinals) and points, in day order, then file order.

    The sort must be stable: the "row" tie rule depends on file order within a day.
    """
    ordinals = done_ordinals(issues)
    points = issues.loc[issues["kind"] == VALUE, "story_point"].to_numpy(dtype=float)
    order = np.argsort(ordinals, kind="stable")
    return ordinals[order], points[order]


def _all_dates(ordinals: np.ndarray) -> list[date]:
    """Every date on the 14-day sequence from first value day + 83 to the last value day."""
    if ordinals.size == 0:
        return []
    first = date.fromordinal(int(ordinals[0])) + timedelta(days=FIRST_OFFSET_DAYS)
    last = date.fromordinal(int(ordinals[-1]))
    dates, t = [], first
    while t <= last:
        dates.append(t)
        t += timedelta(days=STEP_DAYS)
    return dates


def _after(ordinals: np.ndarray, t: date) -> int:
    """Index of the first value item done after day t."""
    return int(np.searchsorted(ordinals, t.toordinal(), side="right"))


def forecast_dates_for(issues: pd.DataFrame, n: int) -> list[date]:
    """The forecast dates of a project for backlog size n (ADR: Forecast dates)."""
    ordinals, _ = _value_items(issues)
    return [t for t in _all_dates(ordinals) if ordinals.size - _after(ordinals, t) >= n]


def actual_date(issues: pd.DataFrame, t: date, n: int) -> date:
    """The day of the n-th value item done after day t."""
    ordinals, _ = _value_items(issues)
    start = _after(ordinals, t)
    if ordinals.size - start < n:
        raise BacktestError(f"fewer than {n} value items are done after {t}")
    return date.fromordinal(int(ordinals[start + n - 1]))


def points_needed(issues: pd.DataFrame, t: date, n: int, tie_rule: str) -> float:
    """The story points of the next n value items done after day t (proposed D29)."""
    return _points_needed(*_value_items(issues), t, n, tie_rule)


def _points_needed(
    ordinals: np.ndarray, points: np.ndarray, t: date, n: int, tie_rule: str
) -> float:
    if tie_rule not in TIE_RULES:
        raise BacktestError(f"unknown tie rule {tie_rule!r}; use one of {TIE_RULES}")
    start = _after(ordinals, t)
    if ordinals.size - start < n:
        raise BacktestError(f"fewer than {n} value items are done after {t}")
    if tie_rule == "row":
        return float(points[start : start + n].sum())
    last_day = ordinals[start + n - 1]
    before = points[start : start + n][ordinals[start : start + n] < last_day]
    same_day = points[ordinals == last_day]
    return float(before.sum() + same_day.mean() * (n - before.size))


def run_project(
    issues: pd.DataFrame,
    project: str,
    p: int,
    *,
    tie_rule: str,
    sizes: Iterable[int] = SIZES,
    runs: int = RUNS,
) -> tuple[list[Case], ProjectSummary]:
    if tie_rule not in TIE_RULES:
        raise BacktestError(f"unknown tie rule {tie_rule!r}; use one of {TIE_RULES}")
    ordinals, points = _value_items(issues)
    summary = ProjectSummary(project=project, p=p)
    cases: list[Case] = []
    velocities: dict[date, float] = {}
    for n in sizes:
        all_dates = _all_dates(ordinals)
        ts = [t for t in all_dates if ordinals.size - _after(ordinals, t) >= n]
        summary.cases[n] = len(ts)
        summary.short_dates[n] = len(all_dates) - len(ts)
        summary.no_forecast[n] = 0
        for t in ts:
            start = _after(ordinals, t)
            actual = date.fromordinal(int(ordinals[start + n - 1]))
            counts = counts_from_ordinals(ordinals, *window(t))
            if not counts.any():
                summary.no_forecast[n] += 1
                cases.append(Case(project, p, t, n, True, None, None, None, None, actual))
                continue
            mc = forecast_dates(t, counts, n, case_generator(p, t, n), runs=runs)
            if t not in velocities:
                velocities[t] = window_velocity(issues, t)
            needed = _points_needed(ordinals, points, t, n, tie_rule)
            v = velocity_date(t, velocities[t], needed)
            cases.append(Case(project, p, t, n, False, mc[50], mc[85], mc[95], v, actual))
    return cases, summary


def check_files(files: list[Path], manifest: dict) -> None:
    """The CSV files must be exactly the manifest files, with matching SHA-256 (D08)."""
    expected = {e["name"]: e["sha256"] for e in manifest["files"]}
    found = {f.name: f for f in files}
    extra = sorted(set(found) - set(expected))
    missing = sorted(set(expected) - set(found))
    if extra or missing:
        raise BacktestError(
            f"data files do not match the manifest: extra {extra}, missing {missing}"
        )
    for name, sha in expected.items():
        if hashlib.sha256(found[name].read_bytes()).hexdigest() != sha:
            raise BacktestError(f"{name}: checksum does not match the manifest")


def run_backtest(
    data_dir: str | Path,
    *,
    tie_rule: str,
    sizes: Iterable[int] = SIZES,
    runs: int = RUNS,
    manifest: dict | None = None,
) -> tuple[list[Case], list[ProjectSummary]]:
    """Run every CSV file in data_dir; projects are numbered in alphabetical file order.

    With a manifest, the files must be exactly the manifest files (ADR Data rules 1).
    """
    files = sorted(Path(data_dir).glob("*.csv"), key=lambda f: f.name)
    if not files:
        raise BacktestError(f"no CSV files in {data_dir}")
    if manifest is not None:
        check_files(files, manifest)
    sizes = tuple(sizes)
    all_cases: list[Case] = []
    summaries: list[ProjectSummary] = []
    for p, path in enumerate(files):
        issues, load = load_issues(path)
        issues, _ = sort_types(issues, path.name)
        cases, summary = run_project(
            issues, path.stem, p, tie_rule=tie_rule, sizes=sizes, runs=runs
        )
        summary.load = load
        all_cases += cases
        summaries.append(summary)
    return all_cases, summaries


def write_cases(cases: Iterable[Case], path: str | Path) -> None:
    """Write one row per case. No issue rows (D08)."""
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(CASE_COLUMNS)
        for c in cases:
            writer.writerow(
                [
                    c.project,
                    c.p,
                    c.t,
                    c.n,
                    int(c.no_forecast),
                    *("" if d is None else d for d in (c.mc50, c.mc85, c.mc95, c.velocity)),
                    c.actual,
                ]
            )


def write_summaries(summaries: Iterable[ProjectSummary], path: str | Path) -> None:
    """Write one row per project and size N, including sizes with 0 cases."""
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(SUMMARY_COLUMNS)
        for s in summaries:
            rows_read = s.load.rows_read if s.load else ""
            no_date = s.load.rows_no_date if s.load else ""
            for n in s.cases:
                writer.writerow(
                    [
                        s.project,
                        s.p,
                        rows_read,
                        no_date,
                        n,
                        s.cases[n],
                        s.no_forecast[n],
                        s.short_dates[n],
                    ]
                )
