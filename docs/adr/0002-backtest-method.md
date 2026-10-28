# ADR 0002: Back-test method

**Status:** Proposed — for PM approval at gate G4 · **Date:** 2026-10-28 · **Ticket:** MCF-8
**Builds on:** D04 (value items), D05 (velocity baseline), D06 (TAWOS extract, all 29 projects, as recorded), D07 (75–95% band), D08 (no data in the repo), R2 (method before results)

## Context
We claim that the Monte Carlo 85% date is calibrated, and that Monte Carlo is more accurate than velocity. A back-test checks these claims on past data: we go back to a date in the past, forecast from the data known on that date, and compare the forecast with what really happened.
We fix every choice in this ADR **before the first back-test run**, so that nobody can change the method after seeing the results.

## Data rules
1. Source: the 29 CSV files in `Dataset/RQ2 and RQ3` of SOLAR-group/SPvsDevelopmentEffort at commit `e8ae43b`. The download script checks each file with a checksum (D08).
2. Columns used: `Issue_Key`, `Type`, `Resolution_Date`, `Story_Point`. One file is one project.
3. Remove only the 19 rows with no date (D06). No other row is removed, corrected or smoothed.
4. An item is **done** on the calendar day of its `Resolution_Date`, as recorded. Every resolution counts, including "Won't Fix" and "Invalid" (D06, as recorded).
5. Issue types follow D04: value items count; bugs do not count; epics do not count. An unknown type stops the run with an error.
6. A value item with no story point stops the run with an error. There is no silent default.

## Forecast question
On a **forecast date** *t*, the question is: **"When will the next *N* value items be done?"**
- The forecast uses only items done on or before *t*.
- The **actual date** is the day when the *N*-th value item done after *t* was resolved.
- One case = one project, one forecast date, one backlog size.

## Forecast dates
- The first forecast date of a project is its first value-item resolution date plus the history window (84 days).
- After that, a forecast date every 14 days (one sprint).
- The last forecast date is the last one for which at least *N* value items are done after it.
- All 29 projects are used (D06). A project with no valid forecast date gives no case, and the report lists it.

## Backlog sizes
*N* = **10, 25 and 50** value items. Each size is reported apart and all sizes together.

## History window
The **84 days (12 weeks, 6 sprints) up to and including *t***. Both methods use the same window, so the comparison is fair. Days with 0 items stay in.

## Runs and seed
- **Runs:** 10,000 for each case.
- **Seed:** 20261028. Each case gets its own random stream from the seed, the project, the forecast date and *N*, so each case can be run again alone with the same result.

## Monte Carlo method
1. Take the 84 daily counts of done value items in the window.
2. In one run, pick days at random from these counts (with replacement) and add them up, day by day, until the total reaches *N*. The number of days picked is the run's result.
3. After 10,000 runs, the **50%, 85% and 95% dates** are *t* plus the 50th, 85th and 95th percentile of the results. A percentile is rounded **up** to a whole day (no interpolation).

## Velocity method
1. Split the window into 6 sprints of 14 days. Velocity = the mean story points of value items done in each sprint.
2. Points needed = the sum of the story points of the next *N* value items (the items that were really done next).
3. The velocity date = *t* + (points needed ÷ velocity) × 14 days, rounded up to a whole day. No rounding to the end of a sprint, so the baseline is not made late on purpose.

## Metrics
1. **Calibration (success measure 1):** the share of cases in which the actual date is on or before the Monte Carlo 85% date. The 50% and 95% shares are also reported, for information.
2. **Error (success measure 2):** for each case, the absolute error in days, |forecast date − actual date|, for the Monte Carlo 50% date and for the velocity date. The main number is the **median** absolute error of each method. The mean error and the signed bias (early or late) are also reported.
3. All metrics are calculated on **all cases together** (every project, every *N*). They are also shown for each project and for each *N*, for information.

## Pass rules
- **Measure 1 passes** if the calibration is from **75% to 95%**, both ends included (D07).
- **Measure 2 passes** if the Monte Carlo median absolute error is **smaller** than the velocity median absolute error, on the same cases.
- A failed measure is published as it is (R3, D06). We do not tune the method to pass.

## Cases with no forecast
- Monte Carlo cannot forecast when all 84 days in the window have 0 done value items. Velocity cannot forecast when the window has 0 story points.
- These cases are **counted and reported** for each method and each project. They are left out of the metrics, because the tool shows an error to the user, not a date.
- Measure 2 uses only the cases in which **both** methods give a date.
- If more than 10% of all cases have no forecast, the report says so in its summary.

## What is reported
1. The summary: both measures, pass or fail, and the number of cases.
2. One row for each of the 29 projects: number of cases, calibration, the median error of each method, and the cases with no forecast.
3. One row for each *N*.
4. The limits: only issues with story points (I1, R5), 2-week periods instead of real sprints (A2), and resolutions such as "Won't Fix" counted as done.
5. Only summary numbers are published. No issue rows (D08).

## Change rule
After the PM accepts this ADR, a change to any rule above needs a new decision (Dxx.1, D14) with the reason. If a change comes after any result was seen, the report shows the result before the change and the result after it.

## Options considered
| Choice | Options | Chosen | Reason |
|---|---|---|---|
| Forecast question | Next *N* items done; the open backlog on date *t* | Next *N* items | The open backlog changes as new items come in. "Next *N* done" has one clear actual date. |
| Backlog sizes | One size; 10, 25, 50 | 10, 25, 50 | Shows short and long forecasts. |
| History window | All history; last 84 days; last 182 days | 84 days | Recent speed matters more. Same as 6 sprints for velocity. |
| Metric weighting | All cases together; mean of the projects | All cases together | One simple number. Each project is still shown apart. |
| Cases with no forecast | Leave out and report; count as a miss | Leave out and report | The tool gives an error, not a date. The count is public. |
| Velocity rounding | Exact days; end of the sprint | Exact days | Fair to the baseline. |
