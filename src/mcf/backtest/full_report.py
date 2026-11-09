"""Side-by-side report: v1 back-test (TAWOS extract) and v2 (full TAWOS data) (MCF-28).

Every number comes from `results/metrics.json` (v1) and `metrics-full.json` (v2, ADR
0003). A failed measure is reported as failed (R3). Summary numbers only, no issue
rows (D08).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from mcf.backtest.report import _d, _d1, _ok, _pct
from mcf.backtest.run import SIZES

REQUIRED_INFO = (
    "code_commit",
    "export_sha256",
    "rows",
    "runs",
    "cases_any_sha256",
    "cases_completed_sha256",
)


class FullReportError(ValueError):
    """The report cannot be made from this input."""


def _m1(s: dict) -> str:
    return f"{_pct(s['calibration_85'])} {_ok(s['measure_1_pass'])}"


def _m2(s: dict) -> str:
    # v1 metrics have no "measure_2_cases": there every scored case has a velocity date.
    if not s.get("measure_2_cases", s.get("cases")):
        return "— (no case)"
    return (
        f"{_d(s['median_error_mc50'])} vs {_d(s['median_error_velocity'])} "
        f"{_ok(s['measure_2_pass'])}"
    )


def _ci(b: dict, key: str, fmt) -> str:
    v = b.get(key)
    return "—" if not v else f"{fmt(v[0])} to {fmt(v[1])}"


def _days_ci(b: dict, key: str) -> str:
    v = b.get(key)
    return "—" if not v else f"{round(v[0], 1):g} to {round(v[1], 1):g} days"


def _edge_note(s: dict, b: dict) -> str | None:
    """A measure 1 result whose bootstrap interval crosses a band edge is not robust."""
    ci = b.get("calibration_85_95ci")
    if not ci:
        return None
    for edge in (0.75, 0.95):
        if ci[0] < edge < ci[1]:
            word = "passes" if s["measure_1_pass"] else "fails"
            return (
                f"Measure 1 {word} on the full data, but its bootstrap 95% interval "
                f"({_pct(ci[0])} to {_pct(ci[1])}) crosses the {edge:.0%} edge of the band, "
                "so the result is not robust."
            )
    return None


def _n(x: int) -> str:
    return f"{x:,}"


def render_full_report(v1: dict, v2: dict, info: dict) -> str:
    missing = [k for k in REQUIRED_INFO if k not in info]
    if missing:
        raise FullReportError(f"run information is missing: {', '.join(missing)}")
    a, c, o = v2["any"]["summary"], v2["completed"]["summary"], v1["summary"]
    ba, bc, bo = v2["any"]["bootstrap"], v2["completed"]["bootstrap"], v1["bootstrap"]
    lines: list[str] = []
    add = lines.append

    add("# Back-test report — full TAWOS data (v2) next to the extract (v1)")
    add("")
    add(
        "The v2 back-test runs the **unchanged ADR 0002 method** on the full TAWOS Issue "
        "table, with the data rules of ADR 0003 (D54, D54.1, D54.2), fixed before any v2 run "
        "(R2). v1 used an extract with only pointed issues resolved as completed (R13)."
    )
    add("")
    add("## Summary")
    add("")
    add("| Success measure | v1: extract | v2: full data | Pass rule |")
    add("| --- | --- | --- | --- |")
    add(f"| 1. Calibration of the 85% date | {_m1(o)} | {_m1(a)} | 75–95% |")
    add(
        f"| 2. Median absolute error, Monte Carlo 50% vs velocity | {_m2(o)} | {_m2(a)} "
        "| Monte Carlo smaller |"
    )
    add(f"| Cases scored | {_n(o['cases'])} | {_n(a['cases'])} | — |")
    add(f"| Projects | {o['projects']} | {a['projects']} | — |")
    add(
        f"| Cases with no forecast | {_n(o['no_forecast_cases'])} "
        f"({_pct(o['no_forecast_share'])}) | {_n(a['no_forecast_cases'])} "
        f"({_pct(a['no_forecast_share'])}) | counted, not scored |"
    )
    add("")
    add(
        f"v2 measure 2 uses the {_n(a['measure_2_cases'])} cases with a velocity date "
        f"(of {_n(a['cases'])} scored cases): a case has no velocity date when no value item "
        "in its 84-day window has story points, or when the date would be after year 9999 "
        "(D54.2). Measure 1 uses all scored cases."
    )
    add("")
    note = _edge_note(a, ba)
    if note:
        add(note)
        add("")
    add(
        "Each result is published as it is (R3). A Monte Carlo date is a probability, not a "
        "promise: the 50% date is not certain."
    )
    add("")

    add("## Side by side")
    add("")
    add("| Number | v1: extract | v2: full data | Done = completed only (information) |")
    add("| --- | --- | --- | --- |")
    rows = [
        ("Calibration of the 50% date", "calibration_50", _pct),
        ("Calibration of the 85% date", "calibration_85", _pct),
        ("Calibration of the 95% date", "calibration_95", _pct),
        (
            "Calibration 85%, no-forecast cases as misses",
            "calibration_85_no_forecast_as_miss",
            _pct,
        ),
        ("Mean of the per-project calibrations (85%)", "mean_project_calibration_85", _pct),
        ("Median error, Monte Carlo 50%", "median_error_mc50", _d),
        ("Median error, velocity", "median_error_velocity", _d),
        ("Mean error, Monte Carlo 50%", "mean_error_mc50", lambda x: f"{x:.1f} d"),
        ("Mean error, velocity", "mean_error_velocity", lambda x: f"{x:.1f} d"),
        ("Bias, Monte Carlo 50% (negative = early)", "bias_mc50", _d1),
        ("Bias, velocity (negative = early)", "bias_velocity", _d1),
    ]
    for name, key, fmt in rows:
        cells = [fmt(s[key]) if s.get(key) is not None else "—" for s in (o, a, c)]
        add(f"| {name} | {' | '.join(cells)} |")
    add(f"| Cases scored | {_n(o['cases'])} | {_n(a['cases'])} | {_n(c['cases'])} |")
    add(
        f"| Measure 2 cases | {_n(o['cases'])} | {_n(a['measure_2_cases'])} "
        f"| {_n(c['measure_2_cases'])} |"
    )
    add(
        f"| Measure 1 | {_ok(o['measure_1_pass'])} | {_ok(a['measure_1_pass'])} "
        f"| {_ok(c['measure_1_pass'])} |"
    )
    m2 = [
        _ok(s["measure_2_pass"]) if s.get("measure_2_pass") is not None else "—" for s in (o, a, c)
    ]
    add(f"| Measure 2 | {' | '.join(m2)} |")
    add(
        f"| Bootstrap 95% interval, calibration 85% | {_ci(bo, 'calibration_85_95ci', _pct)} "
        f"| {_ci(ba, 'calibration_85_95ci', _pct)} | {_ci(bc, 'calibration_85_95ci', _pct)} |"
    )
    add(
        f"| Bootstrap 95% interval, error difference (velocity − MC; > 0 = MC better) "
        f"| {_days_ci(bo, 'median_error_difference_95ci')} "
        f"| {_days_ci(ba, 'median_error_difference_95ci')} "
        f"| {_days_ci(bc, 'median_error_difference_95ci')} |"
    )
    add("")
    add(
        "Done = completed only counts only the resolutions Fixed, Done, Complete, Completed, "
        "Implemented, Deployed and Resolved (ADR 0003 decision 1, information only)."
    )
    add("")

    p = v2["any"]["pointed_only"]
    add("## Fully pointed cases (information)")
    add("")
    add(
        "Cases where each of the next N value items (with the items of the N-th item's day) "
        "has story points, so the velocity date uses no estimated points (ADR 0003 "
        "decision 2)."
    )
    add("")
    add("| Cases | Calibration 85% | Median error MC 50% | Median error velocity |")
    add("| --- | --- | --- | --- |")
    add(
        f"| {_n(p['cases'])} | {_pct(p.get('calibration_85'))} | "
        f"{_d(p.get('median_error_mc50'))} | {_d(p.get('median_error_velocity'))} |"
    )
    add("")

    add("## v2 results by backlog size")
    add("")
    add(
        "| N | Cases scored | Calibration 85% | Measure 2 cases | Median error MC 50% "
        "| Median error velocity | No forecast | Short dates |"
    )
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for n in SIZES:
        r = v2["any"]["by_n"][str(n)]
        add(
            f"| {n} | {_n(r['cases'])} | {_pct(r.get('calibration_85'))} | "
            f"{_n(r['measure_2_cases'])} | {_d(r.get('median_error_mc50'))} | "
            f"{_d(r.get('median_error_velocity'))} | {_n(r['no_forecast_cases'])} | "
            f"{_n(a['short_dates'][str(n)])} |"
        )
    add("")

    add("## v2 results by project")
    add("")
    add(
        "| Project | Cases scored | Calibration 85% | Measure 2 cases | Median error MC 50% "
        "| Median error velocity | No forecast |"
    )
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for name, r in v2["any"]["by_project"].items():
        add(
            f"| {name} | {_n(r['cases'])} | {_pct(r.get('calibration_85'))} | "
            f"{_n(r['measure_2_cases'])} | {_d(r.get('median_error_mc50'))} | "
            f"{_d(r.get('median_error_velocity'))} | {_n(r['no_forecast_cases'])} |"
        )
    add("")
    if a.get("no_case_projects"):
        add(f"Projects with no case: {', '.join(a['no_case_projects'])}.")
        add("")

    add("## Data read (ADR 0003 report item 3)")
    add("")
    add(
        "| Project | Issues read | No resolution date | Not a value item | Value items done "
        "| 0 points (D54.1) | Over 100 points (D54.2) |"
    )
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for name, r in v2["any"]["by_project"].items():
        k = r["counts"]
        add(
            f"| {name} | {k['issues_read']:,} | {k['no_resolution_date']:,} | "
            f"{k['not_value_item']:,} | {k['value_items_done']:,} | {k['zero_points']:,} | "
            f"{k['over_100_points']:,} |"
        )
    t = a["counts"]
    add(
        f"| **All** | {t['issues_read']:,} | {t['no_resolution_date']:,} | "
        f"{t['not_value_item']:,} | {t['value_items_done']:,} | {t['zero_points']:,} | "
        f"{t['over_100_points']:,} |"
    )
    add("")
    nv = sum(a["no_pointed_item"].values())
    tf = sum(a["velocity_too_far"].values())
    add(
        f"Forecast cases with no velocity date: {nv:,} with no pointed item in the window, "
        f"{tf:,} with a date after year 9999 (D54.2)."
    )
    add("")

    add("## Limits")
    add("")
    add(
        "- Only 14% of the issues have story points, so most v2 velocity dates use estimated "
        "points for part of the backlog (ADR 0003 decision 2): the mean points of the pointed "
        "value items in the window."
    )
    add(
        "- D54.1: a story point of 0 counts as no story point "
        f"({a['counts']['zero_points']:,} done value items). D54.2: large story points are "
        "used as recorded (141 values above 100 in the file, the largest 26,710,114; "
        f"{a['counts']['over_100_points']:,} of them on done value items); one such item can "
        "decide the velocity of every window it is in."
    )
    add(
        "- The velocity errors on the full data rest mostly on estimated points. On the "
        f"{v2['any']['pointed_only']['cases']:,} fully pointed cases the two methods are "
        "close (see Fully pointed cases), so the large measure 2 margin shows how velocity "
        "behaves with sparse estimates, not that velocity fails on well-estimated work."
    )
    add(
        "- Done = any resolution date, so Won't Fix, Duplicate and similar count as done "
        "(about 4 in 10 resolutions). The completed-only view shows the effect."
    )
    add(
        "- Velocity uses 2-week periods counted from day t, not the teams' real sprints (A2), "
        "and the real points of the next N items where they exist (ADR 0002 limit)."
    )
    add(
        "- Case selection uses knowledge of the future: a forecast date exists only when at "
        "least N value items were done after it (ADR 0002 design). Cases 14 days apart "
        "share 70 of 84 window days."
    )
    add(
        "- The dump's README says version 1.0; the TAWOS GitHub page names version 1.1 "
        "(doi 10.5522/04/21308124). This report uses the file named under Data."
    )
    add("")

    add("## Data and method")
    add("")
    add(
        '- Data: `TAWOS.sql` from figshare 19085834 (README "V. 1.0", SHA-256 '
        "97dc0dea…f34badd), read without a database by `mcf.data.tawos_dump`. Only the "
        "allowed columns were kept (C2); the export with "
        f"{info['rows']:,} rows has SHA-256 `{info['export_sha256']}` "
        "(`src/mcf/data/tawos_full_manifest.json`). Neither file is in the repository (D08)."
    )
    add(
        f"- Method: ADR 0002 unchanged; data rules ADR 0003 (D54, D54.1, D54.2). "
        f"{info['runs']:,} runs per case, seed 20261028, one random stream per case."
    )
    add(
        "- The data is subject to the TAWOS terms of use (research purposes only): "
        "https://github.com/SOLAR-group/TAWOS. Do not try to trace issues back to individual "
        "contributors. Only summary numbers are published, no issue rows."
    )
    add(
        "- Cite: Tawosi, Al-Subaihin, Moussa, Sarro. A Versatile Dataset of Agile Open Source "
        "Software Projects. MSR 2022. https://doi.org/10.1145/3524842.3528029 — dataset "
        "doi 10.5522/04/21308124."
    )
    add("")
    add("## Reproduce")
    add("")
    add("```bash")
    add("python -m mcf.backtest.full --data tawos-issues-allowed.csv --out results-full")
    add("python -m mcf.backtest.full_report --v1 results/metrics.json \\")
    add("    --v2 results-full --commit <commit> --out docs/backtest-report-full.md")
    add("```")
    add("")
    add(f"- Code commit of the run: `{info['code_commit']}`")
    add(f"- `cases-full-any.csv` SHA-256: `{info['cases_any_sha256']}`")
    add(f"- `cases-full-completed.csv` SHA-256: `{info['cases_completed_sha256']}`")
    add("")
    return "\n".join(lines)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mcf.backtest.full_report", description=__doc__)
    parser.add_argument("--v1", required=True, type=Path, help="v1 metrics.json")
    parser.add_argument("--v2", required=True, type=Path, help="folder of the v2 run")
    parser.add_argument("--commit", required=True, help="code commit of the v2 run")
    parser.add_argument("--out", required=True, type=Path, help="report file to write (.md)")
    args = parser.parse_args(argv)
    try:
        v1 = json.loads(args.v1.read_text(encoding="utf-8"))
        full = json.loads((args.v2 / "metrics-full.json").read_text(encoding="utf-8"))
        info = {
            "code_commit": args.commit,
            "export_sha256": full["input"]["sha256"],
            "rows": full["input"]["rows"],
            "runs": full["input"]["runs"],
            "cases_any_sha256": _sha(args.v2 / "cases-full-any.csv"),
            "cases_completed_sha256": _sha(args.v2 / "cases-full-completed.csv"),
        }
        text = render_full_report(v1, full, info)
    except (FullReportError, OSError, ValueError, KeyError) as exc:
        print(f"mcf.backtest.full_report: error: {exc}", file=sys.stderr)
        return 1
    args.out.write_text(text, encoding="utf-8")
    print(f"report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
