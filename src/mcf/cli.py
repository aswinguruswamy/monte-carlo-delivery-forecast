"""Command line: `mcf forecast FILE --backlog N` (MCF-16, D25, D28).

Exit codes: 0 = dates printed; 1 = data error or no forecast; 2 = bad command
line. Every number and date comes from code; nothing here is AI text.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import date, timedelta

import numpy as np

from mcf.data.load import LoadError, LoadReport, load_issues
from mcf.data.types import (
    BUG,
    D04_KIND,
    NOT_COUNTED,
    VALUE,
    IssueTypeError,
    TypeSummary,
    sort_types,
)
from mcf.explain.check import explain_checked
from mcf.explain.client import urllib_transport
from mcf.forecast.montecarlo import (
    RUNS,
    SEED,
    MonteCarloError,
    dates_from_days,
    simulate_days,
)
from mcf.forecast.throughput import ThroughputError, counts_from_ordinals, done_ordinals, window
from mcf.forecast.velocity import VelocityError, velocity_date, window_velocity
from mcf.result import ForecastFacts, report_number, report_percent

TRANSPORT = urllib_transport  # replaced by a fake in tests (NFR8)


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
    fc.add_argument(
        "--explain",
        action="store_true",
        help="add a short explanation: Claude picks approved sentences that fit this forecast "
        "(needs ANTHROPIC_API_KEY; D33.1). If the reply is not a valid choice, or the call "
        "fails, only the plain report is shown",
    )
    return parser


def _percent(value: float) -> str:
    return f"{round(value * 100)}%"


def _num(value: float) -> str:
    return f"{value:.1f}" if value >= 0.1 else f"{value:.3g}"


def _items(count: int) -> str:
    return f"{count} value item" + ("" if count == 1 else "s")


def compute(args: argparse.Namespace) -> ForecastFacts:
    """Calculate the numbers and dates of the forecast (no text from the data)."""
    return _compute_with_load(args)[0]


def _compute_with_load(args: argparse.Namespace) -> tuple[ForecastFacts, LoadReport]:
    facts, load, _ = compute_full(args)
    return facts, load


def compute_full(
    args: argparse.Namespace,
) -> tuple[ForecastFacts, LoadReport, np.ndarray]:
    """Return the facts, the load report and the simulated days of each run (for a chart)."""
    issues, load = load_issues(args.file, open_items=True)
    unknown = sorted({ty for ty in load.open_types if ty not in D04_KIND})
    if unknown:
        raise IssueTypeError(
            f"{load.file}: unknown issue type {unknown[0]!r} on an open row. "
            "Add it to D04 with a new decision, or fix the data."
        )
    if issues.empty:
        raise LoadError(f"{load.file}: no done item (all rows are open or have no date)")
    issues, _ = sort_types(issues, load.file, points_required=False)
    ordinals = done_ordinals(issues)

    if args.as_of is not None:
        t = args.as_of
    else:  # the last done day of any item (value, bug or epic)
        t = max(issues["done_day"])

    try:
        start, end = window(t)
    except OverflowError:  # MCF-29: day t is in the first 83 days of year 1
        first = date.min + timedelta(days=83)  # 0001-03-25: the first day t that works
        raise ThroughputError(
            f"no forecast from {t}: the 84-day history window starts before {date.min}. "
            f"Use --as-of {first} or later."
        ) from None
    counts = counts_from_ordinals(ordinals, start, end)
    if not counts.any():
        raise MonteCarloError(
            f"no forecast: no value item was done from {start} to {end}; use another --as-of"
        )
    rng = np.random.Generator(np.random.PCG64(args.seed))
    days = simulate_days(counts, args.backlog, rng)
    dates = dates_from_days(t, days)

    # MCF-32 (D43): velocity uses the value items that have a story point.
    no_point = (issues["kind"] == VALUE) & issues["story_point"].isna()
    in_history = issues["done_day"].map(lambda d: start <= d <= end).astype(bool)
    items_no_points = int((no_point & in_history).sum())
    velocity = window_velocity(issues[~no_point], t)
    if velocity == 0:  # no value item in the history has a story point
        v_date = velocity_per_sprint = points_needed = None
    else:
        if args.backlog_points is not None:
            points = args.backlog_points
        else:
            mean_points = velocity * 6 / int(counts.sum())
            points = mean_points * args.backlog
        v_date = velocity_date(t, velocity, points)
        velocity_per_sprint = report_number(float(velocity))
        points_needed = report_number(float(points))

    in_window = issues["done_day"].map(lambda d: start <= d <= end)
    kinds = issues.loc[in_window, "kind"]
    bug_share = TypeSummary(
        value=int((kinds == VALUE).sum()),
        bug=int((kinds == BUG).sum()),
        not_counted=int((kinds == NOT_COUNTED).sum()),
    ).bug_share
    return (
        ForecastFacts(
            t=t,
            backlog=args.backlog,
            window_start=start,
            window_end=end,
            items_done=int(counts.sum()),
            mc50=dates[50],
            mc85=dates[85],
            mc95=dates[95],
            runs=RUNS,
            velocity_date=v_date,
            velocity_per_sprint=velocity_per_sprint,
            points_needed=points_needed,
            points_estimated=args.backlog_points is None,
            open_items=load.rows_open,
            rows_no_date=load.rows_no_date,
            bug_share_percent=None if bug_share is None else report_percent(bug_share),
            items_no_points=items_no_points,
        ),
        load,
        days,
    )


def forecast(args: argparse.Namespace) -> str:
    return render(_compute_with_load(args)[0], args)


NO_VELOCITY = "Not available: needs story points"


def _velocity_line(f: ForecastFacts, points_note: str, points_given: bool) -> str:
    if f.velocity_date is None:
        unused = "; --backlog-points not used" if points_given else ""
        return f"Velocity: {NO_VELOCITY} in the history{unused}"
    return (
        f"Velocity: {f.velocity_date} ({_num(f.velocity_per_sprint)} points per 2 weeks; "
        f"{_num(f.points_needed)} points needed, {points_note})"
    )


def render(f: ForecastFacts, args: argparse.Namespace) -> str:
    t_note = "--as-of" if args.as_of is not None else "last done day in the file"
    points_note = "estimated" if f.points_estimated else "given"
    share = f"{f.bug_share_percent}%" if f.bug_share_percent is not None else "n/a"
    lines = [
        f"Forecast: the next {f.backlog} value items",
        f"From {f.t} ({t_note})",
        f"History: {f.window_start} to {f.window_end} (84 days), {_items(f.items_done)} done",
        "",
        f"Monte Carlo ({f.runs:,} runs, seed {args.seed}):",
        *(f"  {p}%: {d}" for p, d in ((50, f.mc50), (85, f.mc85), (95, f.mc95))),
        "  The 50% date is not certain: half of the runs finish later.",
        "",
        _velocity_line(f, points_note, getattr(args, "backlog_points", None) is not None),
        *(
            [
                f"Value items with no story points ({f.window_start} to {f.window_end}): "
                f"{f.items_no_points}"
            ]
            if f.items_no_points
            else []
        ),
        "",
        f"Open items skipped: {f.open_items}",
        f"Rows with no date (NULL): {f.rows_no_date}",
        f"Bug share ({f.window_start} to {f.window_end}): {share}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        facts = _compute_with_load(args)[0]
        print(render(facts, args))
        if getattr(args, "explain", False):
            text, reason = explain_checked(facts, transport=TRANSPORT)
            if text is not None:
                print(f"\nExplanation (AI-selected, approved sentences):\n{text}")
            else:
                print(f"\nAI explanation not shown: {reason}")
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
