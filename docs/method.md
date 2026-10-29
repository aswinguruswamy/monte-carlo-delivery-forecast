# The method in plain words

This page explains how the tool makes its dates and how the back-test checks them. The exact rules are in [ADR 0002](adr/0002-backtest-method.md).

## The question

"When will the next N value items be done?" A value item is a story, task, improvement or similar (D04.1). Bugs and epics do not count.

## Monte Carlo

1. Count the value items done on each of the last **84 days** (12 weeks). Days with 0 items stay in.
2. One run: pick one of those 84 days at random, add its count, and repeat. When the total reaches N, the number of days picked is the result of that run.
3. Do **10,000 runs**. Sort the results.
4. The **50% date** is the day by which half of the runs are done. The **85% date** and the **95% date** work the same way.

The 50% date is **not certain**: half of the runs finish later. A later date with a higher percentage is the safer promise.

## Velocity (the usual method)

1. Add the story points of the value items done in the same 84 days, and divide by 6 two-week periods. This is the velocity: points per sprint.
2. Date = backlog points ÷ velocity × 14 days, rounded up to a whole day.

## The back-test

1. For each of 29 real projects, go back to a past date t (every 14 days).
2. Use only the data known on day t to make both forecasts, for N = 10, 25 and 50.
3. Find the real date when the N-th item was done.
4. Compare.

**Two success measures, fixed before the first run:**

- **Measure 1 (calibration):** the 85% date must be correct (the real date is on or before it) in **75% to 95%** of cases. Below 75% means the 85% date is too early too often. Above 95% means it is too late to be useful.
- **Measure 2 (accuracy):** the **median** error in days of the Monte Carlo 50% date must be smaller than the median error of the velocity date.

A case with no item done in its 84 days has no forecast. It is counted and reported, not scored.

## Why the rules were fixed first

If the method changes after the results are known, it is easy to tune it until it passes. So the method, the data and the pass rules were written down and approved before the first run (ADR 0002, D21.1). Two details that the ADR did not set were decided before the results they affect (D29, D30). The v1 result is published as it is, also the failed measure: see [backtest-report.md](backtest-report.md).
