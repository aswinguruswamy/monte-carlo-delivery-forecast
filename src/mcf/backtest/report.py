"""Back-test report in Markdown (ADR 0002 What is reported; R3, R5, I1; MCF-19).

Every number comes from metrics.json (MCF-18) and the run information. The
report states a failed measure as failed (R3) and publishes summary numbers
only, no issue rows (D08).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from mcf.backtest.run import SIZES

# Value items with a resolution date and a status other than a closed status, in the
# TAWOS extract (checked against the data by tests/test_backtest_report.py when the
# data is present; CI has no data, so the separate-chat re-run also checks it).
STATUS_COUNTS = {
    "Won't Fix": 853,
    "Invalid": 335,
    "In Progress": 1,
    "Accepted": 1,
}
TABLE_HEAD = (
    "| Cases scored | Calibration 85% | Median error MC 50% | Median error velocity | No forecast "
    "| Short dates |"
)
REQUIRED_INFO = ("code_commit", "cases_sha256", "projects_sha256", "rows_read", "rows_no_date")


class ReportError(ValueError):
    """The report cannot be made from this input."""


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def _d(x: float | None) -> str:
    return "—" if x is None else f"{x:g} d"


def _d1(x: float | None) -> str:
    return "—" if x is None else f"{x:+.1f} d"


def _ok(flag: bool) -> str:
    return "**PASS**" if flag else "**FAIL**"


def render_report(metrics: dict, info: dict) -> str:
    missing = [k for k in REQUIRED_INFO if k not in info]
    if missing:
        raise ReportError(f"run information is missing: {', '.join(missing)}")
    s = metrics["summary"]
    if "short_dates" not in s:
        raise ReportError(
            "metrics were made without projects.csv (--projects); short dates missing"
        )
    boot = metrics["bootstrap"]
    total = s["cases"] + s["no_forecast_cases"]
    both = s["measure_1_pass"] and s["measure_2_pass"]

    lines: list[str] = []
    add = lines.append
    add("# Back-test report — Monte Carlo vs velocity (v1, TAWOS extract)")
    add("")
    add("## Summary")
    add("")
    add("| Success measure | Result | Pass rule | Pass or fail |")
    add("| --- | --- | --- | --- |")
    add(
        f"| 1. Calibration of the 85% date | {_pct(s['calibration_85'])} | 75–95% "
        f"| {_ok(s['measure_1_pass'])} |"
    )
    add(
        f"| 2. Median absolute error, Monte Carlo 50% vs velocity | "
        f"{_d(s['median_error_mc50'])} vs {_d(s['median_error_velocity'])} | "
        f"Monte Carlo smaller | {_ok(s['measure_2_pass'])} |"
    )
    add("")
    add(
        f"Cases scored: {s['cases']:,} from {s['projects']} projects "
        f"(N = 10, 25, 50). Cases with no forecast: {s['no_forecast_cases']:,} of {total:,} "
        f"({s['no_forecast_share']:.1%}); they are counted, not scored."
    )
    if not both:
        failed = [
            name for name, ok in (("1", s["measure_1_pass"]), ("2", s["measure_2_pass"])) if not ok
        ]
        add("")
        add(
            f"Success measure {' and '.join(failed)} did not pass. The result is published as it "
            "is (R3)."
        )
    add("")
    add(
        f"The 85% date was too early in {1 - s['calibration_85']:.1%} of the scored cases. "
        "The method was fixed before the first run and was not changed after it (R2). D29 and "
        "D30 completed two details that the ADR did not set: D29 came before the run, and D30 "
        "came before the metrics."
    )
    lo, hi = boot["median_error_difference_95ci"]
    if s["measure_2_pass"] and lo <= 0:
        add("")
        add(
            f"Measure 2 passes on all cases together, but the bootstrap 95% interval of the "
            f"error difference ({lo:g} to {hi:g} days) includes 0, so the advantage is not robust."
        )
    if s["no_forecast_over_10_percent"]:
        add("")
        add(
            f"More than 10% of cases have no forecast ({s['no_forecast_share']:.1%}): in these "
            "cases the 84-day window held no done value item, so neither method gives a date."
        )
    add("")
    add("A Monte Carlo date is a probability, not a promise: the 50% date is not certain.")

    add("")
    add("## Results by backlog size")
    add("")
    add("| N " + TABLE_HEAD)
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for n in SIZES:
        r = metrics["by_n"][str(n)]
        add(
            f"| {n} | {r['cases']:,} | {_pct(r['calibration_85'])} | {_d(r['median_error_mc50'])} "
            f"| {_d(r['median_error_velocity'])} | {r['no_forecast_cases']:,} "
            f"| {s['short_dates'][str(n)]:,} |"
        )
    add("")
    add("Short dates: dates on the 14-day sequence with fewer than N value items done after them.")
    no_case = s.get("no_case_sizes", [])
    listed = ", ".join(f"{name} (N = {n})" for name, n in no_case) if no_case else "none"
    add("")
    add(f"Projects with no case for a size N: {listed}.")

    add("")
    add("## Results by project")
    add("")
    add("| Project " + TABLE_HEAD)
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for name, r in metrics["by_project"].items():
        short = sum(r.get("short_dates", {}).values())
        add(
            f"| {name} | {r['cases']:,} | {_pct(r['calibration_85'])} "
            f"| {_d(r['median_error_mc50'])} | {_d(r['median_error_velocity'])} "
            f"| {r['no_forecast_cases']:,} | {short:,} |"
        )
    add("")
    add("All sizes together. A project with 0 cases has no rate (—).")

    add("")
    add("## Information only")
    add("")
    add("These numbers help to read the result. They are not used for pass or fail.")
    add("")
    add("| Number | Value |")
    add("| --- | --- |")
    add(
        f"| Mean of the per-project calibrations (85%) | {_pct(s['mean_project_calibration_85'])} |"
    )
    add(
        f"| Calibration with no-forecast cases as misses (85%) "
        f"| {_pct(s['calibration_85_no_forecast_as_miss'])} |"
    )
    clo, chi = boot["calibration_85_95ci"]
    add(f"| Bootstrap 95% interval of the calibration (85%) | {_pct(clo)} to {_pct(chi)} |")
    add(
        f"| Bootstrap 95% interval of the error difference (velocity − Monte Carlo; > 0 = "
        f"Monte Carlo better) | {lo:g} to {hi:g} days |"
    )
    add(f"| Calibration of the 50% date | {_pct(s['calibration_50'])} |")
    add(f"| Calibration of the 95% date | {_pct(s['calibration_95'])} |")
    add(
        f"| Mean absolute error, Monte Carlo 50% / velocity | {s['mean_error_mc50']:.1f} d / "
        f"{s['mean_error_velocity']:.1f} d |"
    )
    add(
        f"| Bias (forecast − actual; negative = early), Monte Carlo 50% / velocity | "
        f"{_d1(s['bias_mc50'])} / {_d1(s['bias_velocity'])} |"
    )
    add("")
    add(
        f"The bootstrap picks whole projects ({boot['resamples']:,} resamples, seed "
        f"{boot['seed']}, {boot['projects']} projects with a forecast case; D30). Cases 14 days "
        "apart share most of their history, so a plain case count overstates how sure the "
        "result is."
    )

    add("")
    add("## Limits")
    add("")
    add(
        "- The data holds only issues with story points, and only issues resolved as completed "
        "(dataset author, 2026-10-29; R13, R5, I1). Teams with many unestimated items may behave "
        "differently. A v2 back-test on the full TAWOS data is planned (D23)."
    )
    add("- Velocity uses 2-week periods counted from day t, not the teams' real sprints (A2).")
    other = ", ".join(f"{k} ({v:,})" for k, v in STATUS_COUNTS.items())
    add(
        "- Every resolved item counts as done on its resolution day, whatever its status (D21.1). "
        "This does not contradict the first limit: every Resolution value in the extract is a "
        f"completed value, but there are value items with another status: {other} (RAID C5)."
    )
    if s["measure_2_pass"]:
        verdict = "this Monte Carlo win on measure 2 is conservative"
        if lo <= 0:
            verdict += f"; it is also small and not robust (interval {lo:g} to {hi:g} days)"
    else:
        verdict = "a Monte Carlo loss on measure 2 tells less"
    add(
        "- Velocity uses the real points of the next N items, known only after day t. This helps "
        f"velocity, so {verdict}."
    )
    add(
        "- Case selection: a forecast date exists only when at least N value items were done "
        "after it, so the set of cases uses knowledge of the future (ADR 0002 design)."
    )
    add("- Same-day ties in velocity points use the mean of that day's items (D29).")
    add("- Cases overlap: windows 14 days apart share 70 of 84 days.")
    add("- 29 open-source projects; the result may not hold for other teams.")

    add("")
    add("## Data and method")
    add("")
    add(
        f"- Data: TAWOS extract (SOLAR-group/SPvsDevelopmentEffort, Dataset/RQ2 and RQ3, commit "
        f"e8ae43b), 29 projects, {info['rows_read']:,} rows read, {info['rows_no_date']} rows "
        "with no resolution date removed (D06). Each file is checked with SHA-256."
    )
    add(
        "- Method: ADR 0002 (accepted as D21.1 before any run), D29 and D30. 10,000 runs per case, "
        "seed 20261028, one random stream per case."
    )
    add(
        "- The data is subject to the TAWOS terms of use: https://github.com/SOLAR-group/TAWOS. "
        "Do not try to trace issues back to individual contributors. Only summary numbers are "
        "published, no issue rows (D08)."
    )
    add(
        "- Cite: Tawosi, Al-Subaihin, Moussa, Sarro. A Versatile Dataset of Agile Open Source "
        "Software Projects. MSR 2022. https://doi.org/10.1145/3524842.3528029 — and Tawosi, "
        "Moussa, Sarro. On the Relationship Between Story Points and Development Effort in Agile "
        "Open-Source Software. ESEM 2022. https://doi.org/10.1145/3544902.3546238"
    )
    add("")
    add("## Reproduce")
    add("")
    add("```bash")
    add('pip install -e ".[dev]"')
    add("python -m mcf.data.download --dest data")
    add("python -m mcf.backtest --data data --out results")
    add("python -m mcf.backtest.metrics --cases results/cases.csv \\")
    add("    --projects results/projects.csv --out results/metrics.json")
    add("python -m mcf.backtest.report --results results --commit <commit> \\")
    add("    --out docs/backtest-report.md")
    add("```")
    add("")
    add(f"- Code commit of the run: `{info['code_commit']}`")
    add(f"- `cases.csv` SHA-256: `{info['cases_sha256']}`")
    add(f"- `projects.csv` SHA-256: `{info['projects_sha256']}`")
    add("")
    return "\n".join(lines)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mcf.backtest.report", description=__doc__)
    parser.add_argument(
        "--results",
        required=True,
        type=Path,
        help="folder with cases.csv, projects.csv and metrics.json",
    )
    parser.add_argument("--commit", required=True, help="code commit of the back-test run")
    parser.add_argument("--out", required=True, type=Path, help="report file to write (.md)")
    args = parser.parse_args(argv)
    try:
        metrics = json.loads((args.results / "metrics.json").read_text(encoding="utf-8"))
        with (args.results / "projects.csv").open(newline="", encoding="utf-8") as fh:
            by_project = {
                row["project"]: (int(row["rows_read"]), int(row["rows_no_date"]))
                for row in csv.DictReader(fh)
            }
        info = {
            "code_commit": args.commit,
            "cases_sha256": _sha(args.results / "cases.csv"),
            "projects_sha256": _sha(args.results / "projects.csv"),
            "rows_read": sum(r for r, _ in by_project.values()),
            "rows_no_date": sum(n for _, n in by_project.values()),
        }
        text = render_report(metrics, info)
    except (ReportError, OSError, ValueError, KeyError) as exc:
        print(f"mcf.backtest.report: error: {exc}", file=sys.stderr)
        return 1
    args.out.write_text(text, encoding="utf-8")
    print(f"report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
