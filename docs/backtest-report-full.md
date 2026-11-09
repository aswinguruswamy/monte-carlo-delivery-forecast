# Back-test report — full TAWOS data (v2) next to the extract (v1)

The v2 back-test runs the **unchanged ADR 0002 method** on the full TAWOS Issue table, with the data rules of ADR 0003 (D54, D54.1, D54.2), fixed before any v2 run (R2). v1 used an extract with only pointed issues resolved as completed (R13).

## Summary

| Success measure | v1: extract | v2: full data | Pass rule |
| --- | --- | --- | --- |
| 1. Calibration of the 85% date | 69.0% **FAIL** | 75.0% **PASS** | 75–95% |
| 2. Median absolute error, Monte Carlo 50% vs velocity | 34 d vs 36 d **PASS** | 14 d vs 90 d **PASS** | Monte Carlo smaller |
| Cases scored | 7,692 | 22,619 | — |
| Projects | 29 | 39 | — |
| Cases with no forecast | 903 (10.5%) | 536 (2.3%) | counted, not scored |

v2 measure 2 uses the 12,632 cases with a velocity date (of 22,619 scored cases): a case has no velocity date when no value item in its 84-day window has story points, or when the date would be after year 9999 (D54.2). Measure 1 uses all scored cases.

Measure 1 passes on the full data, but its bootstrap 95% interval (73.0% to 77.1%) crosses the 75% edge of the band, so the result is not robust.

Each result is published as it is (R3). A Monte Carlo date is a probability, not a promise: the 50% date is not certain.

## Side by side

| Number | v1: extract | v2: full data | Done = completed only (information) |
| --- | --- | --- | --- |
| Calibration of the 50% date | 51.6% | 54.8% | 54.8% |
| Calibration of the 85% date | 69.0% | 75.0% | 73.5% |
| Calibration of the 95% date | 76.2% | 83.0% | 81.4% |
| Calibration 85%, no-forecast cases as misses | 61.7% | 73.3% | 72.1% |
| Mean of the per-project calibrations (85%) | 67.7% | 73.6% | 72.3% |
| Median error, Monte Carlo 50% | 34 d | 14 d | 19 d |
| Median error, velocity | 36 d | 90 d | 83 d |
| Mean error, Monte Carlo 50% | 201.7 d | 81.4 d | 96.9 d |
| Mean error, velocity | 259.0 d | 497.1 d | 505.4 d |
| Bias, Monte Carlo 50% (negative = early) | +83.1 d | +22.3 d | +30.3 d |
| Bias, velocity (negative = early) | +139.7 d | +469.5 d | +468.3 d |
| Cases scored | 7,692 | 22,619 | 21,789 |
| Measure 2 cases | 7,692 | 12,632 | 11,485 |
| Measure 1 | **FAIL** | **PASS** | **FAIL** |
| Measure 2 | **PASS** | **PASS** | **PASS** |
| Bootstrap 95% interval, calibration 85% | 66.5% to 71.6% | 73.0% to 77.1% | 71.6% to 75.5% |
| Bootstrap 95% interval, error difference (velocity − MC; > 0 = MC better) | 0 to 6 days | 40 to 140 days | 33 to 120 days |

Done = completed only counts only the resolutions Fixed, Done, Complete, Completed, Implemented, Deployed and Resolved (ADR 0003 decision 1, information only).

## Fully pointed cases (information)

Cases where each of the next N value items (with the items of the N-th item's day) has story points, so the velocity date uses no estimated points (ADR 0003 decision 2).

| Cases | Calibration 85% | Median error MC 50% | Median error velocity |
| --- | --- | --- | --- |
| 531 | 74.0% | 8 d | 10 d |

## v2 results by backlog size

| N | Cases scored | Calibration 85% | Measure 2 cases | Median error MC 50% | Median error velocity | No forecast | Short dates |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 7,793 | 77.6% | 4,388 | 8 d | 41 d | 189 | 389 |
| 25 | 7,570 | 74.6% | 4,243 | 15 d | 94 d | 182 | 619 |
| 50 | 7,256 | 72.8% | 4,001 | 26 d | 194 d | 165 | 950 |

## v2 results by project

| Project | Cases scored | Calibration 85% | Measure 2 cases | Median error MC 50% | Median error velocity | No forecast |
| --- | --- | --- | --- | --- | --- | --- |
| ALOY | 477 | 65.2% | 349 | 158 d | 223 d | 10 |
| APIKIT | 402 | 63.4% | 330 | 101 d | 122.5 d | 54 |
| APSTUD | 276 | 60.9% | 201 | 47 d | 58 d | 42 |
| BAM | 1,098 | 76.7% | 490 | 8 d | 247 d | 0 |
| BE | 253 | 77.5% | 181 | 29 d | 68 d | 12 |
| CLI | 268 | 69.0% | 266 | 86 d | 173 d | 26 |
| CLOV | 681 | 70.6% | 345 | 72 d | 179 d | 240 |
| COMPASS | 155 | 63.2% | 152 | 12 d | 17 d | 0 |
| CONFCLOUD | 435 | 77.7% | 120 | 21.5 d | 1967.5 d | 0 |
| CONFSERVER | 1,268 | 74.9% | 332 | 11 d | 964 d | 0 |
| CWD | 999 | 71.8% | 195 | 23 d | 749 d | 0 |
| CXX | 495 | 73.5% | 186 | 25 d | 349 d | 0 |
| DAEMON | 232 | 75.9% | 212 | 186.5 d | 292 d | 14 |
| DATACASS | 530 | 74.5% | 408 | 54 d | 377.5 d | 6 |
| DM | 501 | 76.0% | 501 | 2 d | 2 d | 0 |
| DNN | 331 | 59.8% | 331 | 13 d | 33 d | 0 |
| DURACLOUD | 659 | 65.4% | 596 | 101.5 d | 133.5 d | 41 |
| EVG | 403 | 86.1% | 304 | 2 d | 4 d | 0 |
| FAB | 307 | 77.5% | 307 | 2 d | 110 d | 0 |
| FE | 924 | 71.8% | 382 | 38 d | 906 d | 0 |
| INDY | 47 | 61.7% | 47 | 14 d | 13 d | 0 |
| IS | 190 | 75.3% | 190 | 13.5 d | 14 d | 0 |
| JAVA | 876 | 78.4% | 348 | 12 d | 263.5 d | 0 |
| JRACLOUD | 257 | 75.1% | 135 | 27 d | 380 d | 0 |
| JRASERVER | 1,265 | 75.1% | 306 | 13 d | 141.5 d | 0 |
| JSWCLOUD | 932 | 76.4% | 384 | 7 d | 254.5 d | 57 |
| JSWSERVER | 933 | 77.8% | 423 | 7 d | 301 d | 1 |
| MDL | 1,091 | 85.5% | 440 | 3 d | 91.5 d | 0 |
| MESOS | 686 | 79.0% | 476 | 8 d | 24 d | 0 |
| MULE | 1,256 | 77.0% | 560 | 13 d | 35 d | 3 |
| MXNET | 57 | 75.4% | 48 | 17 d | 291 d | 0 |
| NEXUS | 949 | 72.8% | 740 | 22 d | 192.5 d | 0 |
| SERVER | 885 | 90.2% | 228 | 1 d | 60 d | 0 |
| STL | 188 | 73.9% | 152 | 10.5 d | 8.5 d | 27 |
| TIDOC | 631 | 74.0% | 427 | 18 d | 33 d | 0 |
| TIMOB | 719 | 74.1% | 662 | 8 d | 29 d | 0 |
| TISTUD | 584 | 69.5% | 574 | 21 d | 30.5 d | 3 |
| USERGRID | 187 | 72.2% | 112 | 12 d | 19 d | 0 |
| XD | 192 | 76.0% | 192 | 4 d | 4 d | 0 |

## Data read (ADR 0003 report item 3)

| Project | Issues read | No resolution date | Not a value item | Value items done | 0 points (D54.1) | Over 100 points (D54.2) |
| --- | --- | --- | --- | --- | --- | --- |
| ALOY | 1,519 | 213 | 599 | 707 | 7 | 0 |
| APIKIT | 886 | 37 | 476 | 373 | 3 | 0 |
| APSTUD | 8,135 | 2,002 | 4,999 | 1,134 | 7 | 0 |
| BAM | 14,252 | 2,033 | 5,664 | 6,555 | 8 | 0 |
| BE | 802 | 63 | 162 | 577 | 1 | 0 |
| CLI | 645 | 70 | 376 | 199 | 8 | 0 |
| CLOV | 1,501 | 0 | 531 | 970 | 3 | 0 |
| COMPASS | 1,791 | 341 | 605 | 845 | 0 | 0 |
| CONFCLOUD | 23,409 | 18,162 | 4,457 | 790 | 0 | 0 |
| CONFSERVER | 42,324 | 6,056 | 22,351 | 13,917 | 5 | 0 |
| CWD | 4,311 | 986 | 1,641 | 1,684 | 1 | 0 |
| CXX | 2,032 | 262 | 496 | 1,274 | 12 | 0 |
| DAEMON | 313 | 30 | 124 | 159 | 0 | 0 |
| DATACASS | 798 | 35 | 161 | 602 | 21 | 1 |
| DM | 26,506 | 3,936 | 4,275 | 18,295 | 482 | 2 |
| DNN | 10,060 | 2,495 | 5,251 | 2,314 | 3 | 0 |
| DURACLOUD | 1,125 | 212 | 326 | 587 | 5 | 0 |
| EVG | 10,299 | 1,015 | 4,196 | 5,088 | 240 | 0 |
| FAB | 13,682 | 840 | 3,646 | 9,196 | 9 | 0 |
| FE | 5,533 | 918 | 2,773 | 1,842 | 19 | 0 |
| INDY | 2,321 | 357 | 834 | 1,130 | 3 | 0 |
| IS | 1,531 | 238 | 392 | 901 | 12 | 0 |
| JAVA | 3,560 | 114 | 1,063 | 2,383 | 0 | 0 |
| JRACLOUD | 25,669 | 19,871 | 4,990 | 808 | 0 | 1 |
| JRASERVER | 44,165 | 8,950 | 16,261 | 18,954 | 0 | 0 |
| JSWCLOUD | 11,702 | 4,151 | 3,171 | 4,380 | 21 | 0 |
| JSWSERVER | 12,862 | 2,038 | 5,290 | 5,534 | 21 | 0 |
| MDL | 66,741 | 14,492 | 33,601 | 18,648 | 18 | 2 |
| MESOS | 10,157 | 3,066 | 3,758 | 3,333 | 1 | 0 |
| MULE | 11,816 | 524 | 5,411 | 5,881 | 225 | 0 |
| MXNET | 1,404 | 1,093 | 91 | 220 | 0 | 0 |
| NEXUS | 9,912 | 879 | 5,574 | 3,459 | 4 | 0 |
| SERVER | 48,663 | 4,829 | 21,453 | 22,381 | 23 | 0 |
| STL | 1,663 | 506 | 234 | 923 | 13 | 0 |
| TIDOC | 3,059 | 285 | 1,261 | 1,513 | 7 | 0 |
| TIMOB | 22,059 | 2,485 | 14,497 | 5,077 | 72 | 9 |
| TISTUD | 5,979 | 827 | 3,173 | 1,979 | 56 | 0 |
| USERGRID | 1,339 | 528 | 253 | 558 | 1 | 0 |
| XD | 3,707 | 661 | 525 | 2,521 | 76 | 1 |
| **All** | 458,232 | 105,600 | 184,941 | 167,691 | 1,387 | 16 |

Forecast cases with no velocity date: 9,987 with no pointed item in the window, 0 with a date after year 9999 (D54.2).

## Limits

- Only 14% of the issues have story points, so most v2 velocity dates use estimated points for part of the backlog (ADR 0003 decision 2): the mean points of the pointed value items in the window.
- D54.1: a story point of 0 counts as no story point (1,387 done value items). D54.2: large story points are used as recorded (141 values above 100 in the file, the largest 26,710,114; 16 of them on done value items); one such item can decide the velocity of every window it is in.
- The velocity errors on the full data rest mostly on estimated points. On the 531 fully pointed cases the two methods are close (see Fully pointed cases), so the large measure 2 margin shows how velocity behaves with sparse estimates, not that velocity fails on well-estimated work.
- Done = any resolution date, so Won't Fix, Duplicate and similar count as done (about 4 in 10 resolutions). The completed-only view shows the effect.
- Velocity uses 2-week periods counted from day t, not the teams' real sprints (A2), and the real points of the next N items where they exist (ADR 0002 limit).
- Case selection uses knowledge of the future: a forecast date exists only when at least N value items were done after it (ADR 0002 design). Cases 14 days apart share 70 of 84 window days.
- The dump's README says version 1.0; the TAWOS GitHub page names version 1.1 (doi 10.5522/04/21308124). This report uses the file named under Data.

## Data and method

- Data: `TAWOS.sql` from figshare 19085834 (README "V. 1.0", SHA-256 97dc0dea…f34badd), read without a database by `mcf.data.tawos_dump`. Only the allowed columns were kept (C2); the export with 458,232 rows has SHA-256 `393566e2d08fc4404ac7ecb77d9ac06e633b185677ec18d61167f3dce9644ea6` (`src/mcf/data/tawos_full_manifest.json`). Neither file is in the repository (D08).
- Method: ADR 0002 unchanged; data rules ADR 0003 (D54, D54.1, D54.2). 10,000 runs per case, seed 20261028, one random stream per case.
- The data is subject to the TAWOS terms of use (research purposes only): https://github.com/SOLAR-group/TAWOS. Do not try to trace issues back to individual contributors. Only summary numbers are published, no issue rows.
- Cite: Tawosi, Al-Subaihin, Moussa, Sarro. A Versatile Dataset of Agile Open Source Software Projects. MSR 2022. https://doi.org/10.1145/3524842.3528029 — dataset doi 10.5522/04/21308124.

## Reproduce

```bash
python -m mcf.backtest.full --data tawos-issues-allowed.csv --out results-full
python -m mcf.backtest.full_report --v1 results/metrics.json \
    --v2 results-full --commit <commit> --out docs/backtest-report-full.md
```

- Code commit of the run: `500df2a (run), report: see the commit of this file`
- `cases-full-any.csv` SHA-256: `cd324ec90bd1ccbe8e6d637649b05d3def0713ddc2ee84240fe0861c15a047ed`
- `cases-full-completed.csv` SHA-256: `0c62bb388e9d343a8daa01130d1b66595202fd2830f3df9a09305783f1ef6b36`
