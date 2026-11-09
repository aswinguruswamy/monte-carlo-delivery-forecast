# ADR 0003: Data rules for the back-test on the full TAWOS dataset

**Status:** Accepted by the PM on 2026-11-09 (D54), **before any v2 back-test run** (R2) · **Ticket:** MCF-28 · **Deciders:** the PM · **Decision Log:** D54
**Builds on:** ADR 0002 (method, unchanged), D04.2 (value types), D06 (all projects, as recorded), D08 (no data in the repo), D23 (v2 keeps the method; only the data rules change), R2 (method before results), C2 (no tracing of contributors)

## Context
The v1 back-test used an extract of TAWOS: only issues with story points, and only issues resolved as completed (dataset author, 2026-10-29; R13). That filter can make the forecast look better or worse than on real team data. D23 asks for a second back-test on the **full TAWOS Issue table**, with the **ADR 0002 method unchanged**, and a report that puts the two results side by side.
Only the data rules change. They must be fixed here, and approved, **before any v2 run**.

## Data rules
1. **Source:** the TAWOS MySQL dump `TAWOS.sql` from figshare article 19085834, as downloaded by the PM on 2026-11-09: **4,313,856,480 bytes, SHA-256 `97dc0deaaa02ac75017d2b9cbe0765ac3377b5d7c10f9f88bc62de838f34badd`**. Its README says **"V. 1.0"**; the TAWOS GitHub page names version 1.1 at DOI 10.5522/04/21308124, which the build session cannot reach. The report states the version used. The file stays outside the repository; every run checks the SHA-256 (D08).
2. **Table and columns:** from `Issue` only `ID`, `Type`, `Status`, `Resolution`, `Resolution_Date`, `Story_Point`, `Project_ID`; from `Project` only `ID`, `Project_Key`. **No other column is kept**: not `Issue_Key`, `URL`, `Title`, the description columns, or any creator, assignee or reporter ID (C2). The reader (`mcf.data.tawos_dump`) skips them as it reads.
3. **Projects:** all **39** projects in the `Issue` table, as recorded (like D06); 458,232 issues, 352,632 with a resolution date. A project is numbered by the alphabetical order of its key. A project with too little history has no cases; it is listed in the report.
4. **Done:** see Decision 1 below.
5. **Calendar day:** the first 10 characters of the resolution date (`YYYY-MM-DD`), with no time-zone conversion (as ADR 0002 rule 5).
6. **Types:** D04.2, plus the 7 types below that the extract does not have. Any other type stops the run with an error.

| Type (issues) | Rule (PM, D54) | Reason |
|---|---|---|
| Support Request (2,368) | value | Like "Question", which D04 counts. |
| Test Task (336), Test (17), Investigation (22) | value | Work items like "Task". |
| Milestone (44), Release (4) | not counted | Containers, like "Epic". |
| Public Security Vulnerability (1) | bug | A defect. |
7. **Story points:** a decimal number; empty means "no story point". Monte Carlo does not use them. For velocity, see Decision 2.

## Decision 1: which resolved issues are "done"
| Option | What counts as done | Pros | Cons | Exit plan |
|---|---|---|---|---|
| **A (recommended)** | Every issue with a resolution date, whatever its `Resolution` (same as ADR 0002 rule 4) | The same rule as v1, so the comparison shows only the effect of the extract's filter. Simple, no judgement per project. | Counts Won't Fix, Duplicate and similar as done, which can make the pace look faster. | Report B as information too. |
| B | Only resolutions that mean "completed" (for example Fixed, Done, Resolved, Complete), mapped per project from the `Resolution` values | Closer to "work delivered". | A mapping per project is a judgement; it is fixed before the run, but it is a second change at the same time as the data. | Report A as information. |

**Fact from the file:** of all resolutions, about **6 in 10** are completed-like (Fixed 160,857; Done 43,256; Complete 7,149; Completed 1,378; Implemented 111; Deployed 102; Resolved 44). The rest are Won't Fix (40,816), Duplicate (33,166), Won't Do (15,709), Timed out (11,648), Cannot Reproduce (10,917) and 45 other values. So A counts many items that delivered nothing, and **"Suggestion" (96,370 issues) is a value type** in D04.

**Decided (PM, D54): A** for the pass metrics (it is what the tool does with a user's own Jira export, and it isolates the extract's filter); B **for information only**, with "completed" = the 7 values above. Because the difference may be large, B is shown next to A in the summary, not only in an appendix.

## Decision 2: items with no story points (velocity only)
| Option | Velocity rule | Pros | Cons | Exit plan |
|---|---|---|---|---|
| **A (recommended)** | Velocity = points of the done value items **that have points** in the window ÷ 6. Points needed = the real points of the next *N* items; for an item with no points, the mean points per pointed value item in the window (the D28 / D44 rule of the tool). No pointed item in the window → no velocity date for that case. | The same rule as the tool that users run (D43, D44). Uses all cases. | Velocity gets estimated points for part of the backlog. | — |
| B | A velocity case only when all next *N* items have points | No estimate. | Removes many cases, so measure 2 compares on a small, selected set. | — |

**Fact from the file:** only **65,427 of 458,232 issues (14%)** have story points; 5 projects have most of them (DM 20,664; EVG 5,402; TIMOB 4,665; MULE 4,170; XD 3,705). So with A, the velocity date of most cases rests mainly on estimated points, and with B most cases have no velocity date.

**Measure 2 compares the two methods on the same cases:** the cases where velocity has a date. Monte Carlo is scored on all cases for measure 1. **Decided (PM, D54): A**, and the report also gives measure 2 on the cases where all next *N* items have points (B), for information.

## Change rule
As ADR 0002: after acceptance, a change needs a new decision (Dxx.1, D14) with the reason; a change after any v2 result was seen shows the result before and after the change. A test stores a checksum of this file.

## Unchanged (ADR 0002)
Forecast question, forecast dates, *N* = 10, 25, 50, the 84-day window, 10,000 runs, the seed and the random stream (with the project number from rule 3), the Monte Carlo and velocity methods, the metrics, the pass rules (75–95%, D07), the cases with no forecast, and the change rule.

## What is reported
1. The v1 (extract) and v2 (full) results side by side: calibration, both median errors, pass or fail, cases, projects.
2. The information-only results of Decision 1 B.
3. The number of issues read, removed (no resolution date), and left out (not a value item), for each project.
4. Only summary numbers. No issue rows (D08).

## Consequences
- **New code:** a streaming reader for the `INSERT` rows of the `Issue` table in the SQL dump (no MySQL install), with tests on a small made-up dump; a manifest with the file's SHA-256; a `--full` option for the back-test; a side-by-side report.
- **Tests:** the reader loads only the allowed columns; an unknown type stops the run; the checksum check; the velocity rule of Decision 2; a fixed seed.
- **Run:** the dump stays on the PM's Mac. The reader makes a small file with the allowed columns only (about 458,000 rows, no keys, titles or user IDs), which is copied into the build session for the run. The Mac sandbox stops any job after 45 seconds, so the run cannot happen there.
- **Documents:** README cites the DOI; `docs/backtest-report-full.md`; CHANGELOG; Decision Log D54.
- **Risk:** the results may differ a lot from v1. They are published as they are (R3).

## Sources checked
- TAWOS README, GitHub SOLAR-group/TAWOS (read 2026-11-09): version 1.1, MySQL 8.0.22 dump, DOI 10.5522/04/21308124, `Issue` columns, Apache 2.0, "research purposes only", no tracing of individuals.
- figshare article 19085834 "The TAWOS dataset" (search result, 2026-11-09). Not opened from the build session (blocked).
- The downloaded file itself (2026-11-09): its README, the `CREATE TABLE` statements, and counts only (types, resolutions, issues per project). No dates were summarised and no forecast was made.
