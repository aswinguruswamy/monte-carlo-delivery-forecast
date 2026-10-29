"""Command line: `mcf forecast FILE --backlog N` (MCF-16, D25, D28).

Exit codes: 0 = dates printed; 1 = data error or no forecast; 2 = bad command
line. Every number and date comes from code; nothing here is AI text.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import date

import numpy as np

from mcf.data.load import LoadError, load_issues
from mcf.data.types import IssueTypeError, sort_types
from mcf.forecast.montecarlo import (
    PERCENTILES,
    RUNS,
    SEED,
    MonteCarloError,
    forecast_dates,
)
from mcf.forecast.throughput import ThroughputError, counts_from_ordinals, done_ordinals, window
from mcf.forecast.velocity import VelocityError, velocity_date, window_velocity


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a whole number, got {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be 1 or more, got {value}")
    return value


def _seed(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a whole number, got {text!r}") from None
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more, got {value}")
    return value


def _points(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a number, got {text!r}") from None
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"must be a number above 0, got {text!r}")
    return value


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a date YYYY-MM-DD, got {text!r}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcf", description="Monte Carlo delivery forecast.")
    commands = parser.add_subparsers(dest="command", required=True)
    fc = commands.add_parser(
        "forecast",
        help="forecast when the next N value items will be done",
        description=(
            "Forecast when the next N value items will be done, from the items done in "
            "the 84 days up to day t. Prints the Monte Carlo 50%%, 85%% and 95%% dates "
            "and the velocity date."
        ),
    )
    fc.add_argument(
        "file",
        metavar="FILE",
        help="CSV with columns Issue_Key, Type, Resolution_Date, Story_Point. "
        "An empty Resolution_Date means an open item (skipped and counted).",
    )
    fc.add_argument(
        "--backlog",
        required=True,
        type=_positive_int,
        metavar="N",
        help="number of value items still to do (1 or more)",
    )
    fc.add_argument(
        "--as-of",
        type=_day,
        metavar="YYYY-MM-DD",
        help="day t, the forecast date (default: the last done day in the file); "
        "items done after it are not used",
    )
    fc.add_argument(
        "--backlog-points",
        type=_points,
        metavar="P",
        help="story points of the backlog, for the velocity date (default: estimate = "
        "mean points per value item in the window x N)",
    )
    fc.add_argument(
        "--seed",
        type=_seed,
        default=SEED,
        metavar="S",
        help=f"random seed, for repeatable dates (default: {SEED})",
    )
    return parser


def _percent(value: float) -> str:
    return f"{round(value * 100)}%"


def forecast(args: argparse.Namespace) -> str:
    issues, load = load_issues(args.file, open_items=True)
    if issues.empty:
        raise LoadError(f"{load.file}: no done item (all rows are open or have no date)")
    issues, types = sort_types(issues, load.file)
    ordinals = done_ordinals(issues)

    if args.as_of is not None:
        t, t_note = args.as_of, "--as-of"
    else:  # the last done day of any item (value, bug or epic)
        t, t_note = max(issues["done_day"]), "last done day in the file"

    start, end = window(t)
    counts = counts_from_ordinals(ordinals, start, end)
    if not counts.any():
        raise MonteCarloError(
            f"no forecast: no value item was done from {start} to {end}; use another --as-of"
        )
    rng = np.random.Generator(np.random.PCG64(args.seed))
    dates = forecast_dates(t, counts, args.backlog, rng)

    velocity = window_velocity(issues, t)
    if args.backlog_points is not None:
        points, points_note = args.backlog_points, "given"
    else:
        mean_points = velocity * 6 / int(counts.sum())
        points, points_note = mean_points * args.backlog, "estimated"
    v_date = velocity_date(t, velocity, points)

    bug_share = types.bug_share
    lines = [
        f"Forecast: the next {args.backlog} value items",
        f"From {t} ({t_note})",
        f"History: {start} to {end} (84 days), {int(counts.sum())} value items done",
        "",
        f"Monte Carlo ({RUNS:,} runs, seed {args.seed}):",
        *(f"  {p}%: {dates[p]}" for p in PERCENTILES),
        "  The 50% date is not certain: half of the runs finish later.",
        "",
        f"Velocity: {v_date} ({velocity:.1f} points per 2 weeks; "
        f"{points:.1f} points needed, {points_note})",
        "",
        f"Open items skipped: {load.rows_open}",
        f"Rows with no date (NULL): {load.rows_no_date}",
        f"Bug share: {_percent(bug_share) if bug_share is not None else 'n/a'}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        print(forecast(args))
    except (
        LoadError,
        IssueTypeError,
        ThroughputError,
        MonteCarloError,
        VelocityError,
    ) as exc:
        print(f"mcf: error: {exc}", file=sys.stderr)
        return 1
    return 0
