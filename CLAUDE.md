# Rules for Claude — Monte Carlo Delivery Forecast (MCF)

Project documents: v1 – Confluence space MCF (Charter, Decision Log, RAID Log, Test Plan), read-only from v2. v2 – `specs/` in this repo.

## Method before results
1. Write the back-test method in an ADR and get PM approval before the first back-test run (risk R2).
2. Never change the method, the data selection, or the pass band (75–95%, D07) after seeing results. A change needs a new decision (Dxx.1) and the reason.
3. First test (v1): use all 29 TAWOS projects as recorded (D06); remove only the 19 rows with no date. The latest test uses the full TAWOS data, 39 projects (ADR 0003).
4. Before a change to the forecast method (window, runs, percentiles, counted types): write a decision record (ADR), re-run the 39-project test on the full TAWOS data, and publish the result before and after. MCF v2 does not change the method (v2 spec R9.1).

## Tests
1. Write or change the tests first, then the code.
2. No test calls a real paid API. Use fakes. (The AI evaluation workflow is not a test: it runs by hand and on a pull request that changes `src/mcf/explain/`, MCF v2 spec R8.1.)
3. Each bug becomes a regression test before the fix.
4. Monte Carlo tests use a fixed random seed.
5. The back-test never uses data after the forecast date.

## Data
1. Never commit dataset files. Use the download script with commit e8ae43b and checksums (D08).
2. Count value items only (D04). An unknown issue type is an error, never a silent default.
3. Never try to trace issues back to individual contributors (dataset author, RAID C2). Load no names or titles.

## AI explanation
1. Code calculates every number and date. Claude only explains them.
2. A script checks that every number and date in the AI text exists in the result. On failure, drop the AI text and show the plain report.
3. Never describe the 50% date as certain.

## Workflow
v2 (from 2026-11-23, Aswin's decision SH-5.3): **one pull request per task**, named with its task number (M1, M2, …) from `specs/` and the plan; an independent review of each PR; merge when CI passes; Aswin approves Done once, at release. Decisions go in the spec and plan with a version line. No Jira or Confluence writes.

Never delete a decision (D14 still holds). In v2, change a decision with a new version line and a change-log row in the spec or plan; the old text stays in the change log and in git history.

v1 (for history): the pm-toolkit ticket workflow with Jira, and the Confluence Decision Log.

## Shared rules (v2)
The rules for MCF, SRG and RAID are in [CONTRIBUTING.md](CONTRIBUTING.md). The approved v2 specs are in `specs/`.
