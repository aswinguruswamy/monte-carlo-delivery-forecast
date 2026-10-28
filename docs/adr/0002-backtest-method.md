# ADR 0002: Back-test method

**Status:** Accepted by the PM on 2026-10-28 (gate G4, D21; amended by D21.1 on 2026-10-28, before any back-test run) · **Ticket:** MCF-8
**Builds on:** D04 (value items), D05 (velocity baseline), D06 (TAWOS extract, all 29 projects, as recorded), D07 (75–95% band), D08 (no data in the repo), R2 (method before results)

## Context
We claim that the Monte Carlo 85% date is calibrated, and that Monte Carlo is more accurate than velocity. A back-test checks these claims on past data: we go back to a date in the past, forecast from the data known on that date, and compare the forecast with what really happened.
We fix every choice in this ADR **before the first back-test run**, so that nobody can change the method after seeing the results.

## Data rules
1. Source: the 29 CSV files in `Dataset/RQ2 and RQ3` of SOLAR-group/SPvsDevelopmentEffort at commit `e8ae43b`. The download script checks each file with a checksum (D08).
2. Columns used: `Issue_Key`, `Type`, `Resolution_Date`, `Story_Point`. One file is one project. Projects are numbered 0 to 28 in the alphabetical order of the file names.
3. Remove only the rows where `Resolution_Date` is the text `NULL` (19 rows: APIKIT 1, DM 2, JSWCLOUD 5, MDL 11) (D06). No other row is removed, corrected or smoothed.
4. An item is **done** on the calendar day of its `Resolution_Date`, whatever its `Status` or `Resolution` (this includes the statuses Won't Fix, Invalid, In Progress, Accepted and Automation), as recorded (D06).
5. The calendar day is the first 10 characters of `Resolution_Date` (`YYYY-MM-DD`). There is no time zone conversion.
6. Issue types follow D04: value items count; bugs do not count; epics do not count. An unknown type stops the run with an error.
7. `Story_Point` is read as a decimal number (values such as 1.5 occur). A value item with no story point stops the run with an error. There is no silent default.

## Forecast question
On a **forecast date** *t*, the question is: **"When will the next *N* value items be done?"**
- The forecast is made at the **end of day *t***. Items done on day *t* are history. The first possible target day is *t* + 1.
- The **actual date** is the day when the *N*-th value item done after day *t* was resolved. Items done on the same day are counted together.
- One case = one project, one forecast date, one backlog size.

## Forecast dates
- The first forecast date of a project is its first value-item resolution day **+ 83 days**, so that the first window holds 84 days that start on that resolution day.
- After that, a forecast date every 14 days (one sprint).
- The last forecast date is the last one for which at least *N* value items are done after it.
- All 29 projects are used (D06). A project with no case for a size *N* is listed in the report (for example, CONFSERVER has no case for *N* = 50).

## Backlog sizes
*N* = **10, 25 and 50** value items. Each size is reported apart, and all sizes together with equal weight for each case.

## History window
The **84 days from day *t* − 83 to day *t*** (12 weeks, 6 sprints). Both methods use the same window, so the comparison is fair. Days with 0 items stay in.

## Runs and seed
- **Runs:** 10,000 for each case.
- **Seed:** 20261028.
- Each case uses its own random stream: `numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence([20261028, p, t.toordinal(), N])))`, where *p* is the project number (Data rules 2). So each case can be run again alone and give the same result.

## Monte Carlo method
1. Take the 84 daily counts of done value items in the window.
2. In one run, pick days at random from these counts (with replacement) and add them up, day by day. If the total reaches *N* on the *k*-th day picked, the run's result is *k* (*k* ≥ 1).
3. After 10,000 runs, the *p*% result is the smallest *k* such that at least *p*% of the runs are ≤ *k* (numpy `quantile` with `method="inverted_cdf"`). This rounds **up** to a whole day. The **50%, 85% and 95% dates** are *t* + that *k* in days.

## Velocity method
1. Sprint *s* (*s* = 1 to 6) covers days *t* − 83 + 14(*s* − 1) to *t* − 70 + 14(*s* − 1). **Velocity** = (the sum of the story points of value items done in the 84-day window) ÷ 6. A sprint with 0 points counts as 0.
2. **Points needed** = the sum of the story points of the next *N* value items (the items that were really done next, with their points as recorded).
3. The velocity date = *t* + (points needed ÷ velocity) × 14 days, rounded **up** to a whole day. There is no rounding to the end of a sprint, so the baseline is not made late on purpose.
4. **Note:** step 2 uses information after *t* (which items were done next, and their final points). This helps velocity. So a Monte Carlo win on measure 2 is a conservative result; a Monte Carlo loss tells less.

## Metrics
1. **Calibration (success measure 1):** the share of cases in which the actual date is on or before the Monte Carlo 85% date. The 50% and 95% shares are also reported, for information.
2. **Error (success measure 2):** for each case, the absolute error in days, |forecast date − actual date|, for the Monte Carlo 50% date and for the velocity date. The main number is the **median** absolute error of each method. The mean error and the signed bias (early or late) are also reported.
3. The pass metrics use **all cases together** (every project, every *N*).
4. For information only, also reported: the metrics for each project and each *N*; the **mean of the per-project calibrations**; and a **95% interval** from a bootstrap that picks whole projects at random (2,000 resamples, seed 20261028), for the calibration and for the difference between the two median errors. Cases are not independent (windows 14 days apart share 70 of 84 days), so the interval shows how sure the result is.

## Pass rules
- **Measure 1 passes** if the calibration is from **75% to 95%**, both ends included (D07).
- **Measure 2 passes** if the Monte Carlo median absolute error is **smaller** than the velocity median absolute error, on the same cases. Equal medians mean measure 2 fails.
- Pass and fail use the numbers from all cases together, not the bootstrap interval.
- A failed measure is published as it is (R3, D06). We do not tune the method to pass.

## Cases with no forecast
- A case has no forecast when its 84-day window has 0 done value items. Then Monte Carlo has no days to pick, and velocity is 0. No story point in the data is 0 or less, so the two methods always lose the same cases.
- These cases are **counted and reported** for each project. They are left out of the pass metrics, because the tool shows an error to the user, not a date.
- For information, the calibration is also reported with these cases counted as **misses**.
- The report also counts the dates that are not forecast dates because fewer than *N* value items were done after them.
- If more than 10% of all cases have no forecast, the report says so in its summary.

## What is reported
1. The summary: both measures, pass or fail, and the number of cases.
2. One row for each of the 29 projects: number of cases, calibration, the median error of each method, and the cases with no forecast.
3. One row for each *N*.
4. The information-only numbers in Metrics 4 and in Cases with no forecast.
5. The limits: only issues with story points (I1, R5); 2-week periods instead of real sprints (A2); every resolved item counted as done, whatever its status (Data rules 4); velocity uses the real future items' points (Velocity method 4).
6. Only summary numbers are published. No issue rows (D08).

## Change rule
After the PM accepts this ADR, a change to any rule above needs a new decision (Dxx.1, D14) with the reason. If a change comes after any result was seen, the report shows the result before the change and the result after it. A test stores a checksum of this file, so any change shows in CI.

## Options considered
| Choice | Options | Chosen | Reason |
|---|---|---|---|
| Forecast question | Next *N* items done; the open backlog on date *t* | Next *N* items | The open backlog changes as new items come in. "Next *N* done" has one clear actual date. |
| Backlog sizes | One size; 10, 25, 50 | 10, 25, 50 | Shows short and long forecasts. |
| History window | All history; last 84 days; last 182 days | 84 days | Recent speed matters more. Same as 6 sprints for velocity. |
| Metric weighting | All cases together; mean of the projects | All cases together (mean of the projects also reported) | One simple number. Each project is still shown apart. |
| Cases with no forecast | Leave out and report; count as a miss | Leave out and report (as a miss also reported) | The tool gives an error, not a date. The count is public. |
| Velocity rounding | Exact days; end of the sprint | Exact days | Fair to the baseline. |
| Velocity scope | Real points of the next *N* items done; mean points per item in the window × *N* | Real points of the next *N* items | A real team knows the points of its backlog. It helps velocity, so it is stated as a limit. |
| Uncertainty | None; bootstrap by project | Bootstrap by project, information only | Cases overlap, so a plain count overstates how sure we are. |
