"""v2 back-test on the full TAWOS data (MCF-28, ADR 0003, D54).

Only the data rules change. The ADR 0002 method is the v1 code itself: the same
history window, Monte Carlo runs and seed stream, velocity date, and "mean" tie rule
(D29). The input is the allowed-columns file made from the dump by
`mcf.data.tawos_dump.export_csv` (no keys, titles or user IDs); it stays outside
the repository (D08).

ADR 0003 decisions:
1. Done = any resolution date ("any"); "completed" (the 7 values in COMPLETED) is
   run too, for information.
2. Missing story points: velocity uses the pointed value items in the window; the
   points needed use the real points and, for an item with none, the mean points per
   pointed value item in the window. No pointed item in the window: no velocity date.
   Measure 2 compares the methods on the cases with a velocity date; the cases whose
   next N items all have points are reported too, for information.

Pre-run review decisions (PM, 2026-11-09, before any v2 result):
- D54.1: a story point of 0 is "no story point" (ADR 0002 accepts only points above 0).
- D54.2: large story points are used as recorded (like D06). A velocity date that cannot
  be a calendar date (after year 9999) is counted as "too far", apart from the cases with
  no pointed item in the window.
"""

from __future__ import annotations

import csv
import hashlib
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np

from mcf.backtest import metrics, run
from mcf.backtest.run import SIZES, FullCase, run_cases
from mcf.data.types import BUG, D04_KIND, NOT_COUNTED, VALUE
from mcf.forecast.montecarlo import RUNS

# ADR 0003 rule 6 (D54): the types of the full table that the extract does not have.
EXTRA_KIND = {
    **dict.fromkeys(["Support Request", "Test Task", "Test", "Investigation"], VALUE),
    **dict.fromkeys(["Milestone", "Release"], NOT_COUNTED),
    "Public Security Vulnerability": BUG,
}
FULL_KIND = {**D04_KIND, **EXTRA_KIND}

# ADR 0003 decision 1, information only: the resolutions that mean "completed".
COMPLETED = frozenset(
    {"Fixed", "Done", "Complete", "Completed", "Implemented", "Deployed", "Resolved"}
)
DONE_RULES = ("any", "completed")

# The allowed-columns file made on 2026-11-09 from TAWOS.sql (SHA-256 97dc0dea…34badd).
EXPORT_SHA256 = "393566e2d08fc4404ac7ecb77d9ac06e633b185677ec18d61167f3dce9644ea6"
COLUMNS = ("Project_Key", "Type", "Status", "Resolution", "Resolution_Date", "Story_Point")


class FullBacktestError(ValueError):
    """The v2 back-test cannot run on this input."""


@dataclass
class FullSummary:
    project: str
    p: int
    value_items_done: int = 0
    cases: dict[int, int] = field(default_factory=dict)
    no_forecast: dict[int, int] = field(default_factory=dict)
    no_velocity: dict[int, int] = field(default_factory=dict)
    no_pointed_item: dict[int, int] = field(default_factory=dict)
    velocity_too_far: dict[int, int] = field(default_factory=dict)
    short_dates: dict[int, int] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)


COUNT_KEYS = (
    "issues_read",
    "no_resolution_date",
    "not_value_item",
    "not_completed",
    "value_items_done",
    "zero_points",
    "over_100_points",
)


def _point(text: str) -> float:
    """D54.1: empty or 0 is "no story point" (NaN); other values as recorded (D54.2)."""
    if not text:
        return math.nan
    value = float(text)
    if not math.isfinite(value) or value < 0:
        raise FullBacktestError(f"bad story point {text!r}")
    return math.nan if value == 0 else value


def _read(path: str | Path, done_rule: str) -> tuple[dict[str, tuple], dict[str, dict]]:
    if done_rule not in DONE_RULES:
        raise FullBacktestError(f"unknown done rule {done_rule!r}; use one of {DONE_RULES}")
    days: dict[str, list[int]] = {}
    pts: dict[str, list[float]] = {}
    counts: dict[str, dict[str, int]] = {}
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        if tuple(next(reader, ())) != COLUMNS:
            raise FullBacktestError(f"the file must have the columns {', '.join(COLUMNS)}")
        for line, (project, kind, _status, resolution, done, point) in enumerate(reader, 2):
            if kind not in FULL_KIND:
                raise FullBacktestError(f"line {line}: unknown issue type {kind!r} (ADR 0003)")
            days.setdefault(project, [])
            pts.setdefault(project, [])
            n = counts.setdefault(project, dict.fromkeys(COUNT_KEYS, 0))
            n["issues_read"] += 1
            if not done:
                n["no_resolution_date"] += 1
                continue
            if FULL_KIND[kind] != VALUE:
                n["not_value_item"] += 1
                continue
            if done_rule == "completed" and resolution not in COMPLETED:
                n["not_completed"] += 1
                continue
            try:
                value = _point(point)
            except (ValueError, FullBacktestError) as exc:
                raise FullBacktestError(f"line {line}: bad story point {point!r}") from exc
            n["value_items_done"] += 1
            n["zero_points"] += point != "" and float(point) == 0
            n["over_100_points"] += bool(value > 100)
            days[project].append(date.fromisoformat(done[:10]).toordinal())
            pts[project].append(value)
    out = {}
    for project in sorted(days):
        d = np.array(days[project], dtype=np.int64)
        order = np.argsort(d, kind="stable")
        out[project] = (d[order], np.array(pts[project], dtype=float)[order])
    return out, {project: counts[project] for project in sorted(counts)}


def project_counts(path: str | Path, done_rule: str = "any") -> dict[str, dict[str, int]]:
    """ADR 0003 report item 3: issues read, removed and left out, per project."""
    return _read(path, done_rule)[1]


def load_projects(path: str | Path, done_rule: str = "any") -> dict[str, tuple]:
    """Per project (alphabetical): the done days (ordinals) and points of its value items.

    Points are NaN where an item has none (empty or 0, D54.1). Items are in day order,
    then file order.
    """
    return _read(path, done_rule)[0]


def run_project_full(
    ordinals: np.ndarray,
    points: np.ndarray,
    project: str,
    p: int,
    *,
    sizes: Iterable[int] = SIZES,
    runs: int = RUNS,
) -> tuple[list[FullCase], FullSummary]:
    """The v2 back-test of one project: the shared case loop with the ADR 0003 rules."""
    cases, counts = run_cases(
        ordinals,
        points,
        project,
        p,
        tie_rule="mean",
        sizes=sizes,
        runs=runs,
        velocity_for=None,
        too_far_raises=False,
    )
    no_velocity = {n: counts.no_pointed_item[n] + counts.velocity_too_far[n] for n in counts.cases}
    summary = FullSummary(
        project=project,
        p=p,
        value_items_done=int(ordinals.size),
        cases=counts.cases,
        no_forecast=counts.no_forecast,
        no_velocity=no_velocity,
        no_pointed_item=counts.no_pointed_item,
        velocity_too_far=counts.velocity_too_far,
        short_dates=counts.short_dates,
    )
    return cases, summary


def run_full(
    path: str | Path,
    *,
    done_rule: str = "any",
    sizes: Iterable[int] = SIZES,
    runs: int = RUNS,
    expected_sha256: str | None = None,
) -> tuple[list[FullCase], list[FullSummary]]:
    """Run every project of the allowed-columns file (ADR 0003 rule 3)."""
    if expected_sha256 is not None:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected_sha256:
            raise FullBacktestError("the input file's checksum does not match (ADR 0003 rule 1)")
    sizes = tuple(sizes)
    cases: list[FullCase] = []
    summaries: list[FullSummary] = []
    projects, counts = _read(path, done_rule)
    for p, (project, (ordinals, points)) in enumerate(projects.items()):
        c, s = run_project_full(ordinals, points, project, p, sizes=sizes, runs=runs)
        s.counts = counts[project]
        cases += c
        summaries.append(s)
    return cases, summaries


def _group(cases: list[FullCase]) -> dict:
    return metrics.group(cases, velocity_cases=True)


def full_metrics(cases: list[FullCase], summaries: list[FullSummary]) -> dict:
    """The ADR 0002 report items, with measure 2 on the cases with a velocity date (ADR 0003)."""
    scored = [c for c in cases if not c.no_forecast]
    if not scored:
        raise FullBacktestError("no forecast case")
    summary = metrics.pass_summary(cases, _group(cases), velocity_cases=True)
    summary["projects"] = len(summaries)
    summary["projects_with_cases"] = len({c.project for c in cases})
    summary["value_items_done"] = sum(s.value_items_done for s in summaries)
    for key in ("short_dates", "no_pointed_item", "velocity_too_far"):
        summary[key] = {str(n): sum(getattr(s, key).get(n, 0) for s in summaries) for n in SIZES}
    summary["counts"] = {k: sum(s.counts.get(k, 0) for s in summaries) for k in COUNT_KEYS}

    groups = {s.project: [c for c in cases if c.project == s.project] for s in summaries}
    by_project = {}
    for s in summaries:
        by_project[s.project] = {
            "p": s.p,
            **_group(groups[s.project]),
            "cases_by_n": {str(n): s.cases.get(n, 0) for n in SIZES},
            "short_dates": {str(n): s.short_dates.get(n, 0) for n in SIZES},
            "no_pointed_item": {str(n): s.no_pointed_item.get(n, 0) for n in SIZES},
            "velocity_too_far": {str(n): s.velocity_too_far.get(n, 0) for n in SIZES},
            "counts": s.counts,
        }
    summary["no_case_projects"] = [s.project for s in summaries if not groups[s.project]]
    summary["mean_project_calibration_85"] = metrics.mean_calibration(by_project)
    return {
        "summary": summary,
        "by_n": {str(n): _group([c for c in cases if c.n == n]) for n in SIZES},
        "by_project": by_project,
        "pointed_only": _group([c for c in cases if c.fully_pointed]),
        "bootstrap": metrics.bootstrap(groups, velocity_cases=True),
    }


def write_cases(cases: Iterable[FullCase], path: Path) -> None:
    """One row per case, with the `fully_pointed` column. No issue rows (D08)."""
    run.write_cases(cases, path, fully_pointed=True)


def main(argv: list[str] | None = None) -> int:
    """`python -m mcf.backtest.full --data tawos-issues-allowed.csv --out results`."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(prog="python -m mcf.backtest.full", description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="the allowed-columns file")
    parser.add_argument("--out", required=True, type=Path, help="folder for the result files")
    parser.add_argument("--runs", type=int, default=RUNS, help=f"runs per case (ADR: {RUNS})")
    parser.add_argument(
        "--no-checksum", action="store_true", help="tests only: skip the ADR 0003 checksum"
    )
    args = parser.parse_args(argv)
    try:
        sha = hashlib.sha256(args.data.read_bytes()).hexdigest()
        if not args.no_checksum and sha != EXPORT_SHA256:
            raise FullBacktestError("the input file's checksum does not match (ADR 0003 rule 1)")
        rows = sum(1 for _ in args.data.open(encoding="utf-8")) - 1
        result: dict = {"input": {"sha256": sha, "rows": rows, "runs": args.runs}}
        args.out.mkdir(parents=True, exist_ok=True)
        for rule in DONE_RULES:
            cases, summaries = run_full(args.data, done_rule=rule, runs=args.runs)
            write_cases(cases, args.out / f"cases-full-{rule}.csv")
            result[rule] = full_metrics(cases, summaries)
    except (FullBacktestError, OSError, ValueError) as exc:
        print(f"mcf.backtest.full: error: {exc}", file=sys.stderr)
        return 1
    (args.out / "metrics-full.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"v2 back-test written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
