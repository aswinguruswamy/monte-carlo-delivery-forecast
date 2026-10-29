# Rules for Claude — Monte Carlo Delivery Forecast (MCF)

Project documents: Confluence space MCF (Charter, Decision Log, RAID Log, Test Plan).

## Method before results
1. Write the back-test method in an ADR and get PM approval before the first back-test run (risk R2).
2. Never change the method, the data selection, or the pass band (75–95%, D07) after seeing results. A change needs a new decision (Dxx.1) and the reason.
3. Use all 29 TAWOS projects as recorded (D06). Remove only the 19 rows with no date.

## Tests
1. Write or change the tests first, then the code.
2. No test calls a real paid API. Use fakes.
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
1. Follow the pm-toolkit ticket workflow: In Progress before the first commit, one ticket per branch, independent review, PM approval before Done.
2. Log each decision in the Decision Log. Never delete a decision; strike it through and add Dxx.1 below (D14).
