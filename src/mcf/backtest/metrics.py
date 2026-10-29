"""Back-test metrics (ADR 0002 Metrics, Pass rules, Cases with no forecast; D07).

- Calibration p% = share of forecast cases with actual date <= the Monte Carlo
  p% date. Measure 1 passes if 75% <= calibration of the 85% date <= 95% (D07),
  compared on exact counts.
- Error = |forecast date - actual date| in days, for the Monte Carlo 50% date
  and the velocity date. Measure 2 passes only if the Monte Carlo median is
  smaller than the velocity median; equal medians fail.
- Bias = mean of (forecast - actual) in days; negative = early.
- Pass metrics use all forecast cases together. No-forecast cases are counted
  and reported, not scored. Rows for N = 10, 25 and 50 always appear; with the
  project summaries, every project appears, with its short-date counts.
- Information only: the mean of per-project calibrations (projects with at
  least one forecast case); calibration with no-forecast cases counted as
  misses; a bootstrap that picks whole projects (2,000 resamples, seed
  20261028). Details the ADR does not set (proposed D30): only projects with
  at least one forecast case are resampled; the generator is
  numpy.random.default_rng(20261028); the 95% interval is the 2.5% and 97.5%
  quantiles (numpy default method); the median difference is velocity - Monte
  Carlo (> 0 = Monte Carlo better).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from datetime import date
from fractions import Fraction
from pathlib import Path

import numpy as np

from mcf.backtest.run import CASE_COLUMNS, SIZES, SUMMARY_COLUMNS, Case, ProjectSummary

BAND = (Fraction(75, 100), Fraction(95, 100))
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261028
NO_FORECAST_FLAG = Fraction(10, 100)
_RATE_KEYS = (
    "calibration_50",
    "calibration_85",
    "calibration_95",
    "median_error_mc50",
    "median_error_velocity",
    "mean_error_mc50",
    "mean_error_velocity",
    "bias_mc50",
    "bias_velocity",
)


class MetricsError(ValueError):
    """Metrics cannot be calculated from this input."""


def calibration_passes(calibration_85: float | Fraction) -> bool:
    return BAND[0] <= Fraction(calibration_85) <= BAND[1]


def error_passes(median_mc50: float, median_velocity: float) -> bool:
    return median_mc50 < median_velocity


def _days(a: date, b: date) -> int:
    return (a - b).days


def check_case(c: Case) -> None:
    dates = (c.mc50, c.mc85, c.mc95, c.velocity)
    where = f"case {c.project} {c.t} N={c.n}"
    if c.n not in SIZES:
        raise MetricsError(f"{where}: N must be one of {SIZES}")
    if c.actual <= c.t:
        raise MetricsError(f"{where}: the actual date must be after t")
    if c.no_forecast and any(d is not None for d in dates):
        raise MetricsError(f"{where}: a no-forecast case must have no forecast date")
    if not c.no_forecast and any(d is None for d in dates):
        raise MetricsError(f"{where}: a forecast case needs all 4 forecast dates")


def _arrays(cases: Sequence[Case]) -> dict[str, np.ndarray]:
    return {
        "hit50": np.array([c.actual <= c.mc50 for c in cases], dtype=bool),
        "hit85": np.array([c.actual <= c.mc85 for c in cases], dtype=bool),
        "hit95": np.array([c.actual <= c.mc95 for c in cases], dtype=bool),
        "signed_mc": np.array([_days(c.mc50, c.actual) for c in cases], dtype=float),
        "signed_v": np.array([_days(c.velocity, c.actual) for c in cases], dtype=float),
    }


def _group(cases: Sequence[Case]) -> dict:
    scored = [c for c in cases if not c.no_forecast]
    row: dict = {"cases": len(scored), "no_forecast_cases": len(cases) - len(scored)}
    if not scored:
        return {**row, **dict.fromkeys(_RATE_KEYS)}
    a = _arrays(scored)
    row.update(
        calibration_50=float(a["hit50"].mean()),
        calibration_85=float(a["hit85"].mean()),
        calibration_95=float(a["hit95"].mean()),
        median_error_mc50=float(np.median(np.abs(a["signed_mc"]))),
        median_error_velocity=float(np.median(np.abs(a["signed_v"]))),
        mean_error_mc50=float(np.abs(a["signed_mc"]).mean()),
        mean_error_velocity=float(np.abs(a["signed_v"]).mean()),
        bias_mc50=float(a["signed_mc"].mean()),
        bias_velocity=float(a["signed_v"].mean()),
    )
    return row


def _bootstrap(groups: dict[str, list[Case]]) -> dict:
    per = []
    for cases in groups.values():
        scored = [c for c in cases if not c.no_forecast]
        if scored:
            a = _arrays(scored)
            per.append((a["hit85"], np.abs(a["signed_mc"]), np.abs(a["signed_v"])))
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    calib = np.empty(BOOTSTRAP_RESAMPLES)
    diff = np.empty(BOOTSTRAP_RESAMPLES)
    for i in range(BOOTSTRAP_RESAMPLES):
        pick = rng.integers(0, len(per), size=len(per))
        calib[i] = np.concatenate([per[j][0] for j in pick]).mean()
        diff[i] = np.median(np.concatenate([per[j][2] for j in pick])) - np.median(
            np.concatenate([per[j][1] for j in pick])
        )
    return {
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "projects": len(per),
        "calibration_85_95ci": [float(x) for x in np.quantile(calib, [0.025, 0.975])],
        "median_error_difference_95ci": [float(x) for x in np.quantile(diff, [0.025, 0.975])],
        "median_error_difference_meaning": "velocity median - Monte Carlo median; > 0 = MC better",
    }


def compute_metrics(
    cases: Iterable[Case], summaries: Sequence[ProjectSummary] | None = None
) -> dict:
    cases = list(cases)
    if not cases:
        raise MetricsError("no cases")
    numbers: dict[str, int] = {}
    for c in cases:
        check_case(c)
        if numbers.setdefault(c.project, c.p) != c.p:
            raise MetricsError(f"project {c.project} has two numbers: {numbers[c.project]}, {c.p}")
    if summaries is not None:
        known = {s.project: s.p for s in summaries}
        for name, p in numbers.items():
            if known.get(name) != p:
                raise MetricsError(f"project {name} (p={p}) is not in the project summaries")
    scored = [c for c in cases if not c.no_forecast]
    if not scored:
        raise MetricsError("no forecast case: every case has no forecast")

    summary = _group(cases)
    hits = sum(c.actual <= c.mc85 for c in scored)
    share = Fraction(summary["no_forecast_cases"], len(cases))
    summary["calibration_85_no_forecast_as_miss"] = hits / len(cases)
    summary["no_forecast_share"] = float(share)
    summary["no_forecast_over_10_percent"] = share > NO_FORECAST_FLAG
    summary["measure_1_pass"] = calibration_passes(Fraction(hits, len(scored)))
    summary["measure_2_pass"] = error_passes(
        summary["median_error_mc50"], summary["median_error_velocity"]
    )

    by_n = {str(n): _group([c for c in cases if c.n == n]) for n in SIZES}

    groups: dict[str, list[Case]] = {}
    order = (
        [(s.p, s.project) for s in summaries]
        if summaries is not None
        else sorted({(c.p, c.project) for c in cases})
    )
    for _, name in sorted(order):
        groups[name] = []
    for c in cases:
        groups[c.project].append(c)
    by_project = {}
    for name, cs in groups.items():
        p = numbers.get(name, next((q for q, n in order if n == name), None))
        by_project[name] = {"p": p, **_group(cs)}
    if summaries is not None:
        for s in summaries:
            by_project[s.project]["short_dates"] = {str(n): s.short_dates.get(n, 0) for n in SIZES}
            by_project[s.project]["cases_by_n"] = {str(n): s.cases.get(n, 0) for n in SIZES}
        summary["no_case_sizes"] = [
            [s.project, n]
            for s in sorted(summaries, key=lambda s: s.p)
            for n in SIZES
            if s.cases.get(n, 0) == 0
        ]
        summary["short_dates"] = {
            str(n): sum(s.short_dates.get(n, 0) for s in summaries) for n in SIZES
        }
    summary["projects"] = len(by_project)
    rates = [r["calibration_85"] for r in by_project.values() if r["calibration_85"] is not None]
    summary["mean_project_calibration_85"] = float(np.mean(rates))

    return {
        "summary": summary,
        "by_n": by_n,
        "by_project": by_project,
        "bootstrap": _bootstrap(groups),
    }


def _read(path: str | Path, columns: list[str]) -> list[tuple[int, dict]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != columns:
            raise MetricsError(f"{path}: expected column(s) {columns}, got {reader.fieldnames}")
        return [(reader.line_num, row) for row in reader]


def load_cases(path: str | Path) -> list[Case]:
    """Read and check a cases.csv written by `write_cases`."""

    def day(text: str) -> date | None:
        return date.fromisoformat(text) if text else None

    cases = []
    for line, row in _read(path, CASE_COLUMNS):
        try:
            if row["no_forecast"] not in ("0", "1"):
                raise MetricsError(f"no_forecast must be 0 or 1, got {row['no_forecast']!r}")
            c = Case(
                project=row["project"],
                p=int(row["p"]),
                t=date.fromisoformat(row["t"]),
                n=int(row["n"]),
                no_forecast=row["no_forecast"] == "1",
                mc50=day(row["mc50"]),
                mc85=day(row["mc85"]),
                mc95=day(row["mc95"]),
                velocity=day(row["velocity"]),
                actual=date.fromisoformat(row["actual"]),
            )
            check_case(c)
        except (ValueError, TypeError) as exc:
            raise MetricsError(f"{path}, line {line}: {exc}") from exc
        cases.append(c)
    return cases


def load_summaries(path: str | Path) -> list[ProjectSummary]:
    """Read a projects.csv written by `write_summaries`."""
    out: dict[str, ProjectSummary] = {}
    for line, row in _read(path, SUMMARY_COLUMNS):
        try:
            s = out.setdefault(row["project"], ProjectSummary(row["project"], int(row["p"])))
            n = int(row["n"])
            s.cases[n] = int(row["cases"])
            s.no_forecast[n] = int(row["no_forecast"])
            s.short_dates[n] = int(row["short_dates"])
        except ValueError as exc:
            raise MetricsError(f"{path}, line {line}: {exc}") from exc
    return list(out.values())


def write_metrics(metrics: dict, path: str | Path) -> None:
    text = json.dumps(metrics, indent=2, sort_keys=True, allow_nan=False)
    Path(path).write_text(text + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="python -m mcf.backtest.metrics", description="Back-test metrics (ADR 0002)."
    )
    parser.add_argument("--cases", required=True, type=Path, help="cases.csv from mcf.backtest")
    parser.add_argument("--projects", type=Path, help="projects.csv from mcf.backtest")
    parser.add_argument("--out", required=True, type=Path, help="metrics.json to write")
    args = parser.parse_args(argv)
    try:
        summaries = load_summaries(args.projects) if args.projects else None
        metrics = compute_metrics(load_cases(args.cases), summaries)
    except (MetricsError, OSError) as exc:
        print(f"mcf.backtest.metrics: error: {exc}", file=sys.stderr)
        return 1
    write_metrics(metrics, args.out)
    s = metrics["summary"]
    m1 = "PASS" if s["measure_1_pass"] else "FAIL"
    m2 = "PASS" if s["measure_2_pass"] else "FAIL"
    print(f"Cases scored: {s['cases']}; no forecast: {s['no_forecast_cases']}")
    print(f"Measure 1 (85% calibration {s['calibration_85']:.1%}, band 75-95%): {m1}")
    print(
        f"Measure 2 (median error MC {s['median_error_mc50']:.1f} d vs velocity "
        f"{s['median_error_velocity']:.1f} d): {m2}"
    )
    if s["no_forecast_over_10_percent"]:
        print(f"Note: more than 10% of cases have no forecast ({s['no_forecast_share']:.1%}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
