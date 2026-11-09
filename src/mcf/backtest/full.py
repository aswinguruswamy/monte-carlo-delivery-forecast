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
from fractions import Fraction
from pathlib import Path

import numpy as np

from mcf.backtest.metrics import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    NO_FORECAST_FLAG,
    calibration_passes,
    error_passes,
)
from mcf.backtest.run import SIZES, _after, _all_dates, _points_needed
from mcf.data.types import BUG, D04_KIND, NOT_COUNTED, VALUE
from mcf.forecast.montecarlo import RUNS, case_generator, forecast_dates
from mcf.forecast.throughput import counts_from_ordinals, window
from mcf.forecast.velocity import SPRINTS, VelocityTooFar, velocity_date

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


@dataclass(frozen=True)
class FullCase:
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
    fully_pointed: bool


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
    summary = FullSummary(project=project, p=p, value_items_done=int(ordinals.size))
    cases: list[FullCase] = []
    for n in sizes:
        all_dates = _all_dates(ordinals)
        ts = [t for t in all_dates if ordinals.size - _after(ordinals, t) >= n]
        summary.cases[n] = len(ts)
        summary.short_dates[n] = len(all_dates) - len(ts)
        summary.no_forecast[n] = 0
        summary.no_velocity[n] = 0
        summary.no_pointed_item[n] = 0
        summary.velocity_too_far[n] = 0
        for t in ts:
            start = _after(ordinals, t)
            actual = date.fromordinal(int(ordinals[start + n - 1]))
            last_day = ordinals[start + n - 1]
            needed_pts = np.concatenate([points[start : start + n], points[ordinals == last_day]])
            fully_pointed = not np.isnan(needed_pts).any()
            first, last = window(t)
            counts = counts_from_ordinals(ordinals, first, last)
            if not counts.any():
                summary.no_forecast[n] += 1
                cases.append(
                    FullCase(project, p, t, n, True, None, None, None, None, actual, fully_pointed)
                )
                continue
            mc = forecast_dates(t, counts, n, case_generator(p, t, n), runs=runs)
            in_window = (ordinals >= first.toordinal()) & (ordinals <= last.toordinal())
            pointed = points[in_window]
            pointed = pointed[~np.isnan(pointed)]
            v = None
            if not pointed.size:
                summary.no_pointed_item[n] += 1
            else:
                filled = np.where(np.isnan(points), pointed.mean(), points)
                needed = _points_needed(ordinals, filled, t, n, "mean")
                try:
                    v = velocity_date(t, float(pointed.sum()) / SPRINTS, needed)
                except VelocityTooFar:  # D54.2; any other velocity error stops the run
                    summary.velocity_too_far[n] += 1
            if v is None:
                summary.no_velocity[n] += 1
            cases.append(
                FullCase(project, p, t, n, False, mc[50], mc[85], mc[95], v, actual, fully_pointed)
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


def _days(a: date, b: date) -> int:
    return (a - b).days


def _group(cases: list[FullCase]) -> dict:
    """Measure 1 on every forecast case; measure 2 (both methods) on the velocity cases."""
    scored = [c for c in cases if not c.no_forecast]
    with_v = [c for c in scored if c.velocity is not None]
    row: dict = {
        "cases": len(scored),
        "no_forecast_cases": len(cases) - len(scored),
        "measure_2_cases": len(with_v),
    }
    if scored:
        row["calibration_50"] = float(np.mean([c.actual <= c.mc50 for c in scored]))
        row["calibration_85"] = float(np.mean([c.actual <= c.mc85 for c in scored]))
        row["calibration_95"] = float(np.mean([c.actual <= c.mc95 for c in scored]))
    if with_v:
        mc = np.array([_days(c.mc50, c.actual) for c in with_v], dtype=float)
        v = np.array([_days(c.velocity, c.actual) for c in with_v], dtype=float)
        row.update(
            median_error_mc50=float(np.median(np.abs(mc))),
            median_error_velocity=float(np.median(np.abs(v))),
            mean_error_mc50=float(np.abs(mc).mean()),
            mean_error_velocity=float(np.abs(v).mean()),
            bias_mc50=float(mc.mean()),
            bias_velocity=float(v.mean()),
        )
    return row


def _bootstrap(groups: dict[str, list[FullCase]]) -> dict:
    """As ADR 0002 and D30: whole projects resampled; measure 2 on the velocity cases."""
    per = []
    for cases in groups.values():
        scored = [c for c in cases if not c.no_forecast]
        if scored:
            hit = np.array([c.actual <= c.mc85 for c in scored], dtype=bool)
            with_v = [c for c in scored if c.velocity is not None]
            mc = np.array([abs(_days(c.mc50, c.actual)) for c in with_v], dtype=float)
            v = np.array([abs(_days(c.velocity, c.actual)) for c in with_v], dtype=float)
            per.append((hit, mc, v))
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    calib = np.empty(BOOTSTRAP_RESAMPLES)
    diff = np.full(BOOTSTRAP_RESAMPLES, np.nan)
    for i in range(BOOTSTRAP_RESAMPLES):
        pick = rng.integers(0, len(per), size=len(per))
        calib[i] = np.concatenate([per[j][0] for j in pick]).mean()
        mc = np.concatenate([per[j][1] for j in pick])
        if mc.size:
            diff[i] = np.median(np.concatenate([per[j][2] for j in pick])) - np.median(mc)
    ok = diff[~np.isnan(diff)]
    return {
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "projects": len(per),
        "calibration_85_95ci": [float(x) for x in np.quantile(calib, [0.025, 0.975])],
        "median_error_difference_95ci": (
            [float(x) for x in np.quantile(ok, [0.025, 0.975])] if ok.size else None
        ),
        "median_error_difference_resamples": int(ok.size),
        "median_error_difference_meaning": "velocity median - Monte Carlo median; > 0 = MC better",
    }


def full_metrics(cases: list[FullCase], summaries: list[FullSummary]) -> dict:
    """The ADR 0002 report items, with measure 2 on the cases with a velocity date (ADR 0003)."""
    scored = [c for c in cases if not c.no_forecast]
    if not scored:
        raise FullBacktestError("no forecast case")
    summary = _group(cases)
    hits = sum(c.actual <= c.mc85 for c in scored)
    share = Fraction(summary["no_forecast_cases"], len(cases))
    summary["calibration_85_no_forecast_as_miss"] = hits / len(cases)
    summary["no_forecast_share"] = float(share)
    summary["no_forecast_over_10_percent"] = share > NO_FORECAST_FLAG
    summary["measure_1_pass"] = calibration_passes(Fraction(hits, len(scored)))
    summary["measure_2_pass"] = (
        error_passes(summary["median_error_mc50"], summary["median_error_velocity"])
        if summary["measure_2_cases"]
        else None
    )
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
    rates = [r["calibration_85"] for r in by_project.values() if "calibration_85" in r]
    summary["mean_project_calibration_85"] = float(np.mean(rates))
    return {
        "summary": summary,
        "by_n": {str(n): _group([c for c in cases if c.n == n]) for n in SIZES},
        "by_project": by_project,
        "pointed_only": _group([c for c in cases if c.fully_pointed]),
        "bootstrap": _bootstrap(groups),
    }


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
    "fully_pointed",
]


def write_cases(cases: Iterable[FullCase], path: Path) -> None:
    """One row per case. No issue rows (D08)."""
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(CASE_COLUMNS)
        for c in cases:
            w.writerow(
                [c.project, c.p, c.t, c.n, int(c.no_forecast)]
                + ["" if d is None else d for d in (c.mc50, c.mc85, c.mc95, c.velocity)]
                + [c.actual, int(c.fully_pointed)]
            )


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
