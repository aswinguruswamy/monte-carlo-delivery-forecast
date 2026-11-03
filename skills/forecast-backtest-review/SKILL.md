---
name: forecast-backtest-review
description: Review a Monte Carlo forecast back-test report (MCF) before the PM approves it. Use when a back-test report, its metrics or its method changes, or when the PM asks for a back-test review.
---

# Forecast back-test review

Use this skill to review `docs/backtest-report.md` and `results/metrics.json` in the MCF repository. You are the reviewer, not the builder. Find what is wrong. Report only; do not change files.

## Step 1 — machine checks

Run in the repository root:

```bash
python -m mcf.backtest.review --repo .
```

The script checks: the ADR 0002 lock, the ADR before the first back-test code (git), the pass rules (75–95% band, D07; Monte Carlo median error smaller than velocity, a tie fails), the report against a fresh render of the metrics, a failed measure shown as FAIL, the required sections, one row for each project, sizes with no case, and the "no data after day t" tests. Copy each `GAP` line into your result.

## Step 2 — re-run (when time allows)

Download the data and run the back-test again. Compare the SHA-256 values in the report (about 7 minutes):

```bash
python -m mcf.data.download --dest data
python -m mcf.backtest --data data --out results
python -m mcf.backtest.metrics --cases results/cases.csv --projects results/projects.csv --out results/metrics.json
```

## Step 3 — judgement checks (a script cannot make these)

1. **Method before results:** read the Decision Log. Was each method detail decided before the results it affects? D29 (same-day tie rule) must be before the first run; D30 (bootstrap details) must be before the metrics. Any later change needs a new decision and a before-and-after report (ADR 0002 Change rule).
2. **Overclaim:** look for words that overclaim, that is, claim more than the numbers show ("proves", "always", "reliable", a win that the bootstrap interval does not support). A small, non-robust lead must be called small.
3. **Limits:** the extract (story points only, resolved as completed), 2-week periods, velocity's future points, overlapping cases, case selection.
4. **Data terms:** TAWOS terms of use, no tracing to individual contributors, citations, no issue rows.
5. **The 50% date** is never described as certain.

## Output

Give your result in this block, so that the PM can copy it:

```
===== REVIEW RESULT START =====
REVIEW: back-test report — commit <short SHA>
VERDICT: Approve | Approve with changes | Changes required
GAPS (machine): <each GAP line, or "none">
BLOCKERS: <numbered, file:line, exact fix — or "none">
SHOULD FIX: <numbered — or "none">
JUDGEMENT CHECKS: <check> — Met | Not met — <evidence>   (one line each)
NOTES: at most 5 lines
===== REVIEW RESULT END =====
```
