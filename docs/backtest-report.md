# Back-test report — Monte Carlo vs velocity (v1, TAWOS extract)

## Summary

| Success measure | Result | Pass rule | Pass or fail |
| --- | --- | --- | --- |
| 1. Calibration of the 85% date | 69.0% | 75–95% | **FAIL** |
| 2. Median absolute error, Monte Carlo 50% vs velocity | 34 d vs 36 d | Monte Carlo smaller | **PASS** |

Cases scored: 7,692 from 29 projects (N = 10, 25, 50). Cases with no forecast: 903 of 8,595 (10.5%); they are counted, not scored.

Success measure 1 did not pass. The result is published as it is; the method was fixed before the first run and was not changed after it (R2, R3).

Measure 2 passes on all cases together, but the bootstrap 95% interval of the error difference (0 to 6 days) includes 0, so the advantage is not robust.

More than 10% of cases have no forecast (10.5%): in these cases the 84-day window held no done value item, so neither method gives a date.

A Monte Carlo date is a probability, not a promise: the 50% date is not certain.

## Results by backlog size

| N | Cases | Calibration 85% | Median error MC 50% | Median error velocity | No forecast | Short dates |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 2,871 | 71.1% | 19 d | 20 d | 432 | 685 |
| 25 | 2,536 | 68.1% | 36 d | 41 d | 253 | 1,199 |
| 50 | 2,285 | 67.3% | 63 d | 66 d | 218 | 1,485 |

Short dates: dates on the 14-day sequence with fewer than N value items done after them.

## Results by project

| Project | Cases | Calibration 85% | Median error MC 50% | Median error velocity | No forecast | Short dates |
| --- | --- | --- | --- | --- | --- | --- |
| APIKIT | 284 | 60.6% | 231.5 d | 161 d | 153 | 109 |
| APSTUD | 103 | 61.2% | 38 d | 78 d | 1 | 73 |
| BAM | 220 | 63.2% | 74 d | 55.5 d | 0 | 488 |
| BE | 105 | 60.0% | 40 d | 49 d | 0 | 78 |
| CLOV | 196 | 70.9% | 109 d | 185.5 d | 0 | 158 |
| COMPASS | 105 | 60.0% | 15 d | 14 d | 0 | 78 |
| CONFSERVER | 95 | 42.1% | 607 d | 845 d | 92 | 404 |
| CXX | 76 | 71.1% | 97 d | 220 d | 2 | 222 |
| DAEMON | 188 | 70.2% | 195.5 d | 299.5 d | 34 | 99 |
| DM | 501 | 79.6% | 2 d | 2 d | 0 | 0 |
| DNN | 317 | 67.5% | 50 d | 58 d | 0 | 25 |
| DURACLOUD | 468 | 65.8% | 112 d | 127.5 d | 40 | 221 |
| EVG | 265 | 84.9% | 3 d | 4 d | 15 | 20 |
| FAB | 263 | 73.4% | 85 d | 71 d | 0 | 34 |
| INDY | 47 | 70.2% | 8 d | 12 d | 0 | 16 |
| IS | 184 | 66.8% | 15 d | 12 d | 0 | 26 |
| JSWCLOUD | 163 | 61.3% | 78 d | 71 d | 136 | 238 |
| JSWSERVER | 161 | 64.6% | 50 d | 50 d | 61 | 315 |
| MDL | 387 | 70.0% | 76 d | 63 d | 150 | 21 |
| MESOS | 440 | 71.1% | 19 d | 21 d | 1 | 45 |
| MULE | 437 | 76.0% | 18 d | 17 d | 0 | 139 |
| NEXUS | 583 | 68.6% | 146 d | 175 d | 93 | 128 |
| SERVER | 182 | 72.5% | 16 d | 19 d | 0 | 16 |
| STL | 101 | 75.2% | 8 d | 6 d | 8 | 47 |
| TIDOC | 402 | 68.4% | 27.5 d | 31.5 d | 111 | 33 |
| TIMOB | 640 | 68.3% | 30 d | 31 d | 6 | 17 |
| TISTUD | 533 | 62.7% | 35 d | 41 d | 0 | 166 |
| USERGRID | 56 | 64.3% | 14 d | 14 d | 0 | 52 |
| XD | 190 | 71.6% | 5 d | 4.5 d | 0 | 101 |

All sizes together. A project with 0 cases has no rate (—).

## Information only

These numbers help to read the result. They are not used for pass or fail.

| Number | Value |
| --- | --- |
| Mean of the per-project calibrations (85%) | 67.7% |
| Calibration with no-forecast cases as misses (85%) | 61.7% |
| Bootstrap 95% interval of the calibration (85%) | 66.5% to 71.6% |
| Bootstrap 95% interval of the error difference (velocity − Monte Carlo; > 0 = Monte Carlo better) | 0 to 6 days |
| Calibration of the 50% date | 51.6% |
| Calibration of the 95% date | 76.2% |
| Mean absolute error, Monte Carlo 50% / velocity | 201.7 d / 259.0 d |
| Bias (forecast − actual; negative = early), Monte Carlo 50% / velocity | +83.1 d / +139.7 d |

The bootstrap picks whole projects (2,000 resamples, seed 20261028, 29 projects with a forecast case; D30). Cases 14 days apart share most of their history, so a plain case count overstates how sure the result is.

## Limits

- The data holds only issues with story points, and only issues resolved as completed (dataset author, 2026-10-29; R13, R5, I1). Teams with many unestimated items may behave differently. A v2 back-test on the full TAWOS data is planned (D23).
- Velocity uses 2-week periods counted from day t, not the teams' real sprints (A2).
- Every resolved item counts as done on its resolution day, whatever its status (D21.1).
- Velocity uses the real points of the next N items, known only after day t. This helps velocity; a Monte Carlo win on measure 2 is therefore conservative.
- Same-day ties in velocity points use the mean of that day's items (D29).
- Cases overlap: windows 14 days apart share 70 of 84 days.
- 29 open-source projects; the result may not hold for other teams.

## Data and method

- Data: TAWOS extract (SOLAR-group/SPvsDevelopmentEffort, Dataset/RQ2 and RQ3, commit e8ae43b), 29 projects, 47,205 rows read, 19 rows with no resolution date removed (D06). Each file is checked with SHA-256.
- Method: ADR 0002 (accepted as D21.1 before any run), D29 and D30. 10,000 runs per case, seed 20261028, one random stream per case.
- The data is subject to the TAWOS terms of use: https://github.com/SOLAR-group/TAWOS. Do not try to trace issues back to individual contributors. Only summary numbers are published, no issue rows (D08).
- Cite: Tawosi, Al-Subaihin, Moussa, Sarro. A Versatile Dataset of Agile Open Source Software Projects. MSR 2022. https://doi.org/10.1145/3524842.3528029 — and Tawosi, Moussa, Sarro. On the Relationship Between Story Points and Development Effort in Agile Open-Source Software. ESEM 2022. https://doi.org/10.1145/3544902.3546238

## Reproduce

```bash
python -m mcf.data.download --dest data
python -m mcf.backtest --data data --out results
python -m mcf.backtest.metrics --cases results/cases.csv \
    --projects results/projects.csv --out results/metrics.json
```

- Code commit of the run: `007e4ab (run), aebb32d (metrics)`
- `cases.csv` SHA-256: `1608fda91e3fb42e27ea340cfea6ba97a9ac668da9e2b123c02e78b76b2025e7`
- `projects.csv` SHA-256: `5830cbb859758633d983f78227d1af9ad3b2a7385bdc5dc6a27c7b058ce19ad6`
