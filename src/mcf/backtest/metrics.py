"""Back-test metrics (ADR 0002 Metrics, Pass rules, Cases with no forecast; D07).

- Calibration p% = share of forecast cases with actual date <= the Monte Carlo
  p% date. Measure 1 passes if 75% <= calibration of the 85% date <= 95% (D07).
- Error = |forecast date - actual date| in days, for the Monte Carlo 50% date
  and the velocity date. Measure 2 passes only if the Monte Carlo median is
  smaller than the velocity median; equal medians fail.
- Bias = mean of (forecast - actual) in days; negative = early.
- Pass metrics use all forecast cases together. No-forecast cases are counted
  and reported, not scored.
- Information only: per N and per project rows; the mean of per-project
  calibrations (projects with at least one forecast case); calibration with
  no-forecast cases counted as misses; a bootstrap that picks whole projects
  (2,000 resamples, seed 20261028). Implementation details of the bootstrap,
  not set in the ADR: the generator is numpy.random.default_rng(20261028), and
  the 95% interval is the 2.5% and 97.5% quantiles (numpy default method).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path

import numpy as np

from mcf.backtest.run import CASE_COLUMNS, Case

BAND = (0.75, 0.95)
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261028
NO_FORECAST_FLAG = 0.10


class MetricsError(ValueError):
    """Metrics cannot be calculated from this input."""


def calibration_passes(calibration_85: float) -> bool:
    return BAND[0] <= calibration_85 <= BAND[1]


def error_passes(median_mc50: float, median_velocity: float) -> bool:
    return median_mc50 < median_velocity


def _days(a: date, b: date) -> int:
    return (a - b).days


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
    no_forecast = len(cases) - len(scored)
    row: dict = {"cases": len(scored), "no_forecast_cases": no_forecast}
    if not scored:
        for key in (
            "calibration_50",
            "calibration_85",
            "calibration_95",
            "median_error_mc50",
            "median_error_velocity",
            "mean_error_mc50",
            "mean_error_velocity",
            "bias_mc50",
            "bias_velocity",
        ):
            row[key] = None
        return row
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


def _bootstrap(by_project: dict[str, list[Case]]) -> dict:
    per = []
    for cases in by_project.values():
        scored = [c for c in cases if not c.no_forecast]
        if scored:
            a = _arrays(scored)
            per.append((a["hit85"], np.abs(a["signed_mc"]), np.abs(a["signed_v"])))
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    calib = np.empty(BOOTSTRAP_RESAMPLES)
    diff = np.empty(BOOTSTRAP_RESAMPLES)
    for i in range(BOOTSTRAP_RESAMPLES):
        pick = rng.integers(0, len(per), size=len(per))
        hits = np.concatenate([per[j][0] for j in pick])
        mc = np.concatenate([per[j][1] for j in pick])
        v = np.concatenate([per[j][2] for j in pick])
        calib[i] = hits.mean()
        diff[i] = np.median(v) - np.median(mc)
    return {
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "projects": len(per),
        "calibration_85_95ci": [float(x) for x in np.quantile(calib, [0.025, 0.975])],
        "median_error_difference_95ci": [float(x) for x in np.quantile(diff, [0.025, 0.975])],
        "median_error_difference_meaning": "velocity median - Monte Carlo median; > 0 = MC better",
    }


def compute_metrics(cases: Iterable[Case]) -> dict:
    cases = list(cases)
    if not cases:
        raise MetricsError("no cases")
    scored = [c for c in cases if not c.no_forecast]
    if not scored:
        raise MetricsError("no forecast case: every case has no forecast")

    summary = _group(cases)
    hits = sum(c.actual <= c.mc85 for c in scored)
    summary["calibration_85_no_forecast_as_miss"] = hits / len(cases)
    summary["no_forecast_share"] = summary["no_forecast_cases"] / len(cases)
    summary["no_forecast_over_10_percent"] = summary["no_forecast_share"] > NO_FORECAST_FLAG
    summary["measure_1_pass"] = calibration_passes(summary["calibration_85"])
    summary["measure_2_pass"] = error_passes(
        summary["median_error_mc50"], summary["median_error_velocity"]
    )

    by_n: dict[str, dict] = {}
    for n in sorted({c.n for c in cases}):
        by_n[str(n)] = _group([c for c in cases if c.n == n])

    groups: dict[str, list[Case]] = {}
    for c in sorted(cases, key=lambda c: (c.p, c.project)):
        groups.setdefault(c.project, []).append(c)
    by_project = {name: {"p": cs[0].p, **_group(cs)} for name, cs in groups.items()}
    rates = [r["calibration_85"] for r in by_project.values() if r["calibration_85"] is not None]
    summary["mean_project_calibration_85"] = float(np.mean(rates))

    return {
        "summary": summary,
        "by_n": by_n,
        "by_project": by_project,
        "bootstrap": _bootstrap(groups),
    }


def load_cases(path: str | Path) -> list[Case]:
    """Read a cases.csv written by `write_cases`."""
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != CASE_COLUMNS:
            raise MetricsError(
                f"{path}: expected column(s) {CASE_COLUMNS}, got {reader.fieldnames}"
            )

        def day(text: str) -> date | None:
            return date.fromisoformat(text) if text else None

        cases = []
        for row in reader:
            cases.append(
                Case(
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
            )
    return cases


def write_metrics(metrics: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
