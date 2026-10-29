"""Run the back-test: `python -m mcf.backtest --data data --out results`.

The data must be exactly the 29 manifest files with matching SHA-256 (D08). The
same-day tie rule is "mean" (D29). Writes cases.csv and projects.csv. No issue rows.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcf.backtest.run import TIE_RULES, BacktestError, run_backtest, write_cases, write_summaries
from mcf.data.download import load_manifest
from mcf.data.load import LoadError
from mcf.data.types import IssueTypeError
from mcf.forecast.montecarlo import RUNS, MonteCarloError
from mcf.forecast.throughput import ThroughputError
from mcf.forecast.velocity import VelocityError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mcf.backtest", description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="folder with the TAWOS CSV files")
    parser.add_argument("--out", required=True, type=Path, help="folder for the result files")
    parser.add_argument(
        "--tie-rule", default="mean", choices=TIE_RULES, help="same-day tie rule (D29: mean)"
    )
    parser.add_argument("--runs", type=int, default=RUNS, help=f"runs per case (ADR: {RUNS})")
    args = parser.parse_args(argv)
    try:
        cases, summaries = run_backtest(
            args.data, tie_rule=args.tie_rule, runs=args.runs, manifest=load_manifest()
        )
    except (
        BacktestError,
        LoadError,
        IssueTypeError,
        ThroughputError,
        MonteCarloError,
        VelocityError,
    ) as exc:
        print(f"mcf.backtest: error: {exc}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    write_cases(cases, args.out / "cases.csv")
    write_summaries(summaries, args.out / "projects.csv")
    print(f"{len(cases)} cases from {len(summaries)} projects written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
