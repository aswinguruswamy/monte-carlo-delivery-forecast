# Quality grades — MCF

Log of the quality-gate grades (pm-toolkit quality-gate skill). Newest last.

## Ticket MCF-7 — 2026-10-28 — grader: builder pre-check (judgement items 8–10 also covered by the separate-session independent review)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira transition and brief at 20:33Z; first commit 4dabf73 at 20:35Z | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-7-repo-and-ci`; 4 commits, each "MCF-7: …"; LICENSE/NOTICE kept on the MCF-9 branch | — |
| 3 | CI green on the PR | ✅ | PR #1 head 9133793: 3 of 3 jobs success | — |
| 4 | PR adds tests | ✅ | `tests/test_repo_hygiene.py`, `tests/regressions/test_ci_gitleaks_permissions.py` (21 tests) | — |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D18 logged (v5). D19 and D20 are proposed and named as such in the PR | Log D19 and D20 after the PM decides in Review |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | PR #1 comment: "Changes required" → all findings fixed in 9133793 | — |
| 8 | Each acceptance criterion met, with a test | ✅ | AC1 YAML-parsed CI tests; AC2 every step fails on non-zero exit (merge blocking deferred, D18); AC3 Dependabot test; AC4 dataset rule tests incl. the review's bypass cases | — |
| 9 | README and rule pages match | ✅ | README dev steps match `pyproject.toml`; ADR 0001 matches CI; CLAUDE.md unchanged and still true | — |
| 10 | Workflow steps followed | 🟡 | Brief, In Progress, one branch, review, fixes with a regression test first (L2). Tests were run red before the code, but test and code are in one commit (4dabf73), so the order is not visible in Git | From MCF-10: commit the failing tests first, then the code |

Result: pass — no ❌. Ready for Review.
Repeated failures: none (first grade).

## Ticket MCF-9 — 2026-10-28 — grader: builder pre-check (judgement items 8–10 also covered by the separate-session independent review)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira transition and brief at 20:37Z; first commit authored 20:38Z | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-9-licence-files`; commits "MCF-9: …" hold LICENSE, NOTICE, tests, this log entry | — |
| 3 | CI green on the PR | ✅ | PR #2 head 7836c83: 3 of 3 jobs success (rechecked after this commit) | — |
| 4 | PR adds tests | ✅ | `tests/test_licence_files.py` (3 tests) | — |
| 5 | Each decision ID in the PR is in the Decision Log | n/a | No decision named | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | PR #2 comment: "Approve with changes" → all findings fixed | — |
| 8 | Each acceptance criterion met, with a test | ✅ | AC1 SHA-256 of LICENSE; AC2 NOTICE owner, no-dataset sentence, TAWOS citation; AC3 tests run in CI | — |
| 9 | README and rule pages match | ✅ | No README change needed; NOTICE makes no claim about files that do not exist | — |
| 10 | Workflow steps followed | 🟡 | Same as MCF-7 item 10: tests run red first, but in one commit with the files | From MCF-10: commit the failing tests first |

Result: pass — no ❌. Ready for Review.
Repeated failures: item 10 also partly met in MCF-7 (same session, same cause; not a second failure after a fix). Prevention rule already set for MCF-10.

## Ticket MCF-8 — 2026-10-28 — grader: builder pre-check (judgement items also covered by the separate-session independent review)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira transition and brief at 22:49Z; first commit ae3d38d after it | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-8-backtest-adr`; each commit "MCF-8: …" | — |
| 3 | CI green on the PR | ✅ | PR #9 head checked before merge | — |
| 4 | PR adds tests | ✅ | `tests/test_adr_backtest.py` (exact rules, approval gate, SHA-256 lock); the failing test was committed first (ae3d38d) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D21 (struck through) and D21.1 in the Decision Log v8 | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | PR #9 comment: "Changes required" → fixed as D21.1 | — |
| 8 | Each acceptance criterion met | ✅ | AC1 exact-rule tests; AC2 PM approval date in the status line, before any back-test commit; AC3 approval gate test | — |
| 9 | README and rule pages match | ✅ | CLAUDE.md "Method before results" matches ADR 0002 | — |
| 10 | Workflow steps followed | 🟡 | The PM approval was asked for while the independent review was still running; the PM approved D21 before the 3 blockers were known, and D21.1 was needed | Lesson L3: finish the independent review before asking the PM for approval |

Result: pass — no ❌.
Repeated failures: item 10 partly met in MCF-7, MCF-9 and MCF-8, each time for a different cause. The tests-first cause is fixed (MCF-8 committed the failing test first). New cause → L3.

## Ticket MCF-10 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the separate-session independent review and re-review)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira transition and brief at 22:58Z on Oct 28; first commit 523d881 after it | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-10-download-data`; each commit "MCF-10: …"; the `.gitignore` fix is needed by this ticket's code | — |
| 3 | CI green on the PR | ✅ | PR #10: af7796c green; final head rechecked before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_download.py`, `tests/conftest.py`, `tests/regressions/test_gitignore_data_folder.py`, checksum rule in `tests/test_repo_hygiene.py`; failing tests committed first (523d881, 2a807fa, and the re-review tests) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D06, D08 only (existing) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Review "Changes required" (2 blockers, 5 should-fix) → re-review "Approve", all 7 fixed; 2 re-review notes also fixed | — |
| 8 | Each acceptance criterion met | ✅ | AC1 manifest 29 files, 47,205 rows, full SHA; real run OK. AC2 changed, missing or bad-local file leaves nothing (tests). AC3 type/size + checksum rules, both unit-tested. AC4 network blocked in every test | — |
| 9 | README and rule pages match | ✅ | README "Get the data" added | — |
| 10 | Workflow steps followed | ✅ | Brief, In Progress, tests first, review finished before the approval request (L3 applied) | — |

Result: pass — no ❌. First full pass at the ticket point.
Repeated failures: none. Trend: item 10 partly met in MCF-7, MCF-9, MCF-8 → met in MCF-10 after L3.

## Ticket MCF-11 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the separate-session review and re-review)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira transition and brief at 03:54Z; first commit 5989a60 after it | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-11-load-csv`; each commit "MCF-11: …"; ruff `src` setting needed for this ticket's imports | — |
| 3 | CI green on the PR | ✅ | 2eae686 green; final head rechecked before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_load.py` (35 tests); failing tests committed first three times (5989a60, fd1ae06, and the re-review tests) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | No new decision; follows ADR 0002 (D21.1) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Review "Approve with changes" (1 blocker: empty dates removed against ADR rule 3) → re-review "Approve with changes" → fixed | — |
| 8 | Each acceptance criterion met | ✅ | AC1 errors name the file and the real line (multi-line, blank lines, ragged rows, unclosed quote). AC2 TAWOS 47,205 read, 19 no date (local run). AC3 100k rows in 0.2 s. AC4 made-up data; TAWOS test skipped in CI | — |
| 9 | README and rule pages match | ✅ | Loader rules match ADR 0002 Data rules 3–5 and 7 | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review finished before the approval request (L3) | — |

Result: pass — no ❌.
Note for the PM: the ADR rule (only NULL = no date) makes open items with an empty resolution date an error. Real Jira exports contain open items → decide in MCF-16 (CLI).

## Ticket MCF-12 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the separate-session review)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira transition and brief at 04:17Z; first commit 3c1797b after it | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-12-sort-types`; each commit "MCF-12: …" | — |
| 3 | CI green on the PR | ✅ | 384e35a green; final head rechecked before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_types.py` (40 tests); failing tests committed first twice | — |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D04 only. The bug-share formula (bugs ÷ (value + bugs)) is a reading of D04 that is not yet on record | PM to approve D04.1 at Review |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | "Approve with changes", no blockers; 3 code items fixed; 1 decision item for the PM | — |
| 8 | Each acceptance criterion met | ✅ | AC1 17 types exact; AC2 unknown type error (incl. blank); AC3 bug share; AC4 missing point on a value item; AC5 TAWOS local check passed | — |
| 9 | README and rule pages match | ✅ | Code matches D04 and ADR 0002 Data rules 6–7 | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review finished before the approval request | — |

Result: pass — no ❌. Item 5 closes when the PM decides D04.1.

## Ticket MCF-13 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the separate-session review)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira transition and brief at 04:39Z; first commit 96430d3 after it | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-13-throughput`; each commit "MCF-13: …" | — |
| 3 | CI green on the PR | ✅ | cfe4cab green; final head rechecked before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_throughput.py` (22 tests); failing tests committed first twice | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D04.1 (logged) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | 🟡 | "Approve with changes", no blockers; 4 items fixed. The reviewer is a separate subagent with its own context, but it runs inside the builder's session | PM to decide if a subagent counts as independent (pm-toolkit rule) |
| 8 | Each acceptance criterion met | ✅ | AC1 hand calculation; AC2 zero days kept; AC3 only value (unknown kind = error); AC4 window t−83..t tested at both ends; AC5 start > end error | — |
| 9 | README and rule pages match | ✅ | Matches ADR 0002 History window and Monte Carlo step 1 | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review finished before the approval request | — |

Result: pass — no ❌. Item 7 also applies to MCF-7 to MCF-12 (same review set-up).

## Ticket MCF-14 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief posted before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-14-velocity`; each commit "MCF-14: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_velocity.py` (36 tests) + 2 throughput regressions; failing tests committed first, twice (build and review fixes) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D04.1, D05, D21.1 (all logged) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Changes required", 2 blockers (datetime t shifted the window; tolerance untested) and 3 should-fix items — all fixed with regression tests | — |
| 8 | Each acceptance criterion met | ✅ | AC1 hand calculation; AC2 window t−83..t at both ends; AC3 value items only; AC4 round up, float-safe (420-day case); AC5 velocity 0 = no-forecast error | — |
| 9 | README and rule pages match | ✅ | Matches ADR 0002 Velocity method 1 and 3, and Cases with no forecast | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review finished before the approval request; no back-test run | — |

Result: pass — no ❌.

## Ticket MCF-15 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief posted before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-15-montecarlo`; each commit "MCF-15: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_montecarlo.py` (41 tests, fixed seeds); failing tests committed first, twice (build and review fixes) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D04.1, D05, D21.1 (all logged) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Approve with changes", no blockers; 4 should-fix and 3 nice-to-have items fixed with regression tests | — |
| 8 | Each acceptance criterion met | ✅ | AC1 constant 5/day, N=50 → 10 days; AC2 k ≥ 1; AC3 inverted CDF; AC4 50% ≤ 85% ≤ 95%; AC5 all-zero = no-forecast error; AC6 ADR seed stream; NFR1 worst case 10.7 s (reviewer) | — |
| 9 | README and rule pages match | ✅ | Matches ADR 0002 Monte Carlo method 1–3 and the Back-test seed rule | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review finished before the approval request; no back-test run | — |

Result: pass — no ❌.

## Ticket MCF-16 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief posted before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-16-cli`; each commit "MCF-16: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_cli.py` (34 tests), load and Monte Carlo regressions; failing tests committed first, twice | — |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D25 logged; D28 (CLI defaults) proposed, not yet logged | PM to decide D28 at Review |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Changes required", 1 blocker (bug share used data after t) and 5 should-fix items — all fixed with regression tests | — |
| 8 | Each acceptance criterion met | ✅ | AC1 dates and exit 0; AC2 clear errors, exit 1 or 2 (incl. OS errors, date overflow); AC3 --help; D25 both paths; NFR1 100,000 rows end to end ≈ 1 s | — |
| 9 | README and rule pages match | ✅ | README usage section; D25 wording (empty date only) | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review finished before the approval request; no back-test run | — |

Result: pass — no ❌. Item 5 closes when the PM decides D28.

## Ticket MCF-17 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief posted before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-17-backtest`; each commit "MCF-17: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_backtest_run.py` (26 tests, synthetic data); failing tests committed first, three times | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D21.1, D29 (logged before the first run), D08 | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Changes required", 2 blockers (tests that could not catch a velocity leak or an unstable sort) and 5 should-fix items — all fixed with regression tests | — |
| 8 | Each acceptance criterion met | ✅ | AC1 ADR rules each tested; AC2 no data after t in the forecasts (window tests); AC3 two full runs, byte-identical outputs (cases.csv SHA-256 1608fda9…) | — |
| 9 | README and rule pages match | ✅ | ADR 0002 + D29; method fixed before the first run (R2) | — |
| 10 | Workflow steps followed | ✅ | D29 decided before the first run; no metrics computed (MCF-18) | — |

Result: pass — no ❌.

## Ticket MCF-18 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief posted before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-18-metrics`; each commit "MCF-18: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_backtest_metrics.py` (43 tests, hand-made cases); failing tests committed first, three times | — |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D07, D21.1 logged; D30 (bootstrap details) proposed | PM to decide D30 at Review |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Approve with changes", no blockers; 7 should-fix and 4 nice-to-have items fixed with regression tests | — |
| 8 | Each acceptance criterion met | ✅ | AC1 hand calculation; AC2 band edges 75% and 95% pass, 74.99% and 95.01% fail (exact counts) | — |
| 9 | README and rule pages match | ✅ | ADR 0002 Metrics, Pass rules, What is reported | — |
| 10 | Workflow steps followed | ✅ | No metrics computed on the real cases (waits for D30) | — |

Result: pass — no ❌. Item 5 closes when the PM decides D30.

## Ticket MCF-19 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the separate-chat review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-19-report`; each commit "MCF-19: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_backtest_report.py` (27 tests); failing tests committed first, three times | — |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D21.1, D23, D29, D30 logged; D31 (AC2 record) proposed | PM to decide D31 at Review |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Separate chat (D24): "Changes required" (2 blockers, 7 should-fix) → fixed; re-check "Approve with changes", no blockers, 4 should-fix → fixed. Re-run byte-identical. | — |
| 8 | Each acceptance criterion met | ✅ | AC1 summary, 29 project rows, limits; AC2 data:validate-data run in the re-check ("Share with noted caveats"), logged in MCF-19 | — |
| 9 | README and rule pages match | ✅ | ADR 0002 What is reported; RAID Log v6 (R2, R3, R13, C5) | — |
| 10 | Workflow steps followed | ✅ | Method fixed before results; failed measure published as failed (R3) | — |

Result: pass — no ❌. Item 5 closes when the PM decides D31.

## Ticket MCF-25 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-25-readme`; each commit "MCF-25: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_docs.py` (13 tests); failing tests committed first, twice | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D04.1, D08, D21.1, D25, D28, D29, D30 (logged) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Approve with changes", no blockers; 6 should-fix and 6 nice-to-have items fixed; CITATION.cff validated with cffconvert | — |
| 8 | Each acceptance criterion met | ✅ | AC1 install, use, method, limits, results, handover; AC2 CITATION.cff cites MSR and ESEM 2022 (CI test) | — |
| 9 | README and rule pages match | ✅ | README numbers tested against results/metrics.json; author conditions C2–C4 met | — |
| 10 | Workflow steps followed | ✅ | Brief with tool check (L8), tests first, review before approval | — |

Result: pass — no ❌.

## Ticket MCF-21 — 2026-10-29 — grader: builder pre-check (judgement items also covered by the subagent review and re-check, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-21-explain`; each commit "MCF-21: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_explain.py` (39 tests) + CLI fixture made from main; failing tests committed first, three times | — |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | NFR3, NFR8, C2 covered; D32 (stdlib HTTP, model, key) proposed | PM to decide D32 at Review |
| 6 | AI ticket evaluation | ✅ | AI checklist in the review: data minimisation (only report numbers and dates), injection rule, secret handling (no redirects, key out of errors and frames), stop reason, prompt version. Evaluation set is MCF-23 | — |
| 7 | Independent review with a verdict | ✅ | Review: "Request changes", 2 blockers (key leak by redirect; Claude had to round numbers) + 6 should-fix → fixed; re-check: "Approve", live redirect probe and 21-case CLI byte comparison | — |
| 8 | Each acceptance criterion met | ✅ | AC1 prompt holds only counts and dates (secret-key test); AC2 no test calls the paid API (fake transport, socket block) | — |
| 9 | README and rule pages match | ✅ | CLAUDE.md AI rules 1 and 3 | — |
| 10 | Workflow steps followed | ✅ | Brief with tool check (L8), tests first, review and re-check before approval | — |

Result: pass — no ❌. Item 5 closes when the PM decides D32.

## Ticket MCF-22 — 2026-11-03 — grader: builder pre-check (judgement items also covered by four subagent reviews, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-22-check`; each commit "MCF-22: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_explain_check.py` (44 tests); failing tests committed first, five times | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D32, D33 (struck), D33.1 (logged) | — |
| 6 | AI ticket evaluation | ✅ | Three adversarial reviews (30, 47 of 135, 91 of 109 bypasses) led to D33.1: a closed ID check; the 4th review found no way to print non-bank text. Live-model evaluation is MCF-23 | — |
| 7 | Independent review with a verdict | ✅ | Four reviews; the last one: "Changes requested", 3 wording blockers + 4 should-fix items, all fixed with tests | — |
| 8 | Each acceptance criterion met | ✅ | A number in the reply → dropped (any free text is dropped); "will" → dropped; API failure → plain report (NFR5) | — |
| 9 | README and rule pages match | ✅ | README `--explain`; CLAUDE.md AI rules met by design | — |
| 10 | Workflow steps followed | ✅ | Design changes went to the PM (D33, D33.1). The PM approved the bank text at Review (2026-11-03) | — |

Result: pass — no ❌. Item 10 closed: the PM approved the bank text on 2026-11-03.

## Ticket MCF-20 — 2026-11-03 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-20-review-skill`; each commit "MCF-20: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | 🟡 | `tests/test_backtest_review.py` (25 tests), tests first twice; one commit (0d437ef) was pushed with a failing test and fixed in the next commit | Lesson L10 |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D06, D07, D13, D21.1, D29, D30 (logged) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Request changes", 3 blockers (band taken from the code, no 29-project check, tests ran against the wrong copy) + 3 should-fix — all fixed with tests | — |
| 8 | Each acceptance criterion met | ✅ | ADR rules (lock, order, fixed values), future data (3 named tests on the reviewed copy), the band (fixed 75–95%); each gap listed | — |
| 9 | README and rule pages match | ✅ | SKILL.md lists the ADR rules left to judgement | — |
| 10 | Workflow steps followed | ✅ | Brief with tool check (L8), review before approval | — |

Result: pass — no ❌.

## Ticket MCF-23 — 2026-11-03 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief (D35, tool check L8) before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-23-eval`; each commit "MCF-23: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_explain_eval.py` (41 tests, fakes only); failing tests committed first twice; the 2 planted bugs the review found now fail the tests (L6) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D33.1, D35 (logged) | — |
| 6 | AI ticket evaluation | ✅ | 10 fixed cases cover all 15 bank sentences and each condition value; repeat runs; injection case; prompt version recorded. Live run on `main` 2026-11-03: PASS, 30 of 30 format, 0 wrong numbers, 0 API errors (evidence on MCF-23) | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Approve with changes", 0 blockers, 4 should-fix — all fixed with tests; 4 of 6 nice-to-have done | — |
| 8 | Each acceptance criterion met | ✅ | AC1 and AC2 proved with fakes and with the live run (PASS, injection 3 of 3). AC2 "project name" = the file name and issue keys (the tool has no project-name field) | — |
| 9 | README and rule pages match | ✅ | README: live run is the manual workflow only; PASS / INCONCLUSIVE rules | — |
| 10 | Workflow steps followed | ✅ | Brief, decision D35 before the build, tests first, review before approval | — |

Result: pass — no ❌. Items 6 and 8 closed by the live run PASS (2026-11-03).

## Ticket MCF-24 — 2026-11-03 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief (tool check L8: webapp-testing skill not available) before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-24-streamlit`; each commit "MCF-24: …". The CLI date bug found in review went to a new ticket (MCF-29) | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review; CI installs `.[dev,web]`, the licence scan covers `.[web]` | — |
| 4 | PR adds tests | ✅ | `tests/test_web.py` + `tests/test_web_app.py` (49 tests, fake AI transport); failing tests committed first twice; planted bugs (seed, forecast date, AI toggle, 85/95 swap) now fail the tests or the browser check (L6) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D01, D08, D19, D33.1 (logged) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket (uses the MCF-22 explanation); the AI call is off by default and cached per forecast | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Approve with changes", 0 blockers, 6 should-fix — all fixed with tests; nice-to-have 7–10, 12–14 done; 11 in the README | — |
| 8 | Each acceptance criterion met | ✅ | AC1 and AC2: AppTest + browser check. AC3: the webapp-testing skill is not available; `scripts/browser_check.py` (Playwright, desktop + phone) 18 of 18 pass; the PM accepted it for AC3 (D36, 2026-11-03) | — |
| 9 | README and rule pages match | ✅ | README "Web page": start folder, what the page shows, AI off by default | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌. Item 8 closed by D36.

## Ticket MCF-29 — 2026-11-03 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-29-date-overflow`; each commit "MCF-29: …"; the web chart overflow went to a new ticket (MCF-30) | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | Regression test first (55a356b fails on the old code, reviewer checked); boundary test 0001-03-24 / 0001-03-25 | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D37 (logged) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Approve with changes", 0 blockers; 1 should-fix outside scope → MCF-30; message nice-to-have done with tests first | — |
| 8 | Each acceptance criterion met | ✅ | Clear `mcf: error:` and exit 1; no traceback (subprocess test); same text on the page in page words | — |
| 9 | README and rule pages match | n/a | No user-facing doc change | — |
| 10 | Workflow steps followed | ✅ | Brief, regression test first, review before approval | — |

Result: pass — no ❌.

## Ticket MCF-30 — 2026-11-03 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-30-chart-overflow`; each commit "MCF-30: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | Regression test first (00fabd0 fails with the real OverflowError, reviewer checked); boundary pinned after the review (a planted off-by-one got through before) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D38 | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Approve with changes", 0 blockers, 2 should-fix — both fixed with tests first | — |
| 8 | Each acceptance criterion met | ✅ | No raw error; the chart leaves out runs after 9999-12-31 and says how many; the dates do not change | — |
| 9 | README and rule pages match | n/a | No user-facing doc change | — |
| 10 | Workflow steps followed | ✅ | Brief, regression test first, review before approval | — |

Result: pass — no ❌.

## Ticket MCF-26 — 2026-11-03 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-26-demo`; each commit "MCF-26: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_demo.py` (10 tests); failing tests committed first twice; the review's blocker reproduced and fixed (clean install 10 → 18 of 18) | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D01, A5; D39 (no key on the public demo, PM 2026-11-03) | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Request changes", 1 blocker (sample file missing on Cloud) + 3 should-fix — all fixed with tests first | — |
| 8 | Each acceptance criterion met | 🟡 | AC2 (video): done, 18.8 s, 0.2 MB. AC1: ready, but the PM must deploy; then the browser check runs on the live URL | PM deploys |
| 9 | README and rule pages match | ✅ | README links `docs/demo.md` | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌. Item 5 closed by D39. Item 8 closes after the deploy and the live check.

## Ticket MCF-27 — 2026-11-03 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief (release-readiness skill loaded) before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-27-release`; each commit "MCF-27: …" | — |
| 3 | CI green on the PR | ✅ | Final head checked green before Review (5 jobs incl. the clean-install job on 3.11 and 3.12) | — |
| 4 | PR adds tests | ✅ | `tests/test_release.py` (9 tests); failing tests committed first twice | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D18, D20, D26, D39; R3 | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent: "Approve with changes", 0 blockers, 2 should-fix — fixed (demo lock) or put in the G8 steps (release-day date); gitleaks on all 143 commits: no leaks; pip-audit: none | — |
| 8 | Each acceptance criterion met | 🟡 | AC1: version 1.0.0 everywhere; clean install on 3.11 and 3.12 in CI; tag check ready. AC2 and the tag need the PM's go (G8) | PM go |
| 9 | README and rule pages match | ✅ | README status, CHANGELOG, CITATION, demo guide | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌. Item 8 closes at the G8 go: tag, release, public repository.

## Ticket MCF-31 — 2026-11-04 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-31-jira-export`; each commit "MCF-31: …" | — |
| 3 | CI green on the PR | ✅ | PR #30 head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_jira_export.py` (42 tests) and a made-up 133-row fixture; failing tests committed first twice | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D42, D25, ADR 0002, RAID C2 | — |
| 6 | AI ticket evaluation | n/a | Not an AI ticket | — |
| 7 | Independent review with a verdict | ✅ | Subagent grade B+, 0 blockers, 1 major (our point name plus a Jira one), 3 minor, 2 nits — all fixed or pinned with tests first; back-test loader compared old vs new on 77 inputs: no difference; 5 planted bugs caught | — |
| 8 | Each acceptance criterion met | ✅ | Jira names, Jira dates, repeated columns, point columns, no names or titles, back-test unchanged | — |
| 9 | README and rule pages match | ✅ | README data section and the loader docstring | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌. Open point for the PM: `Subtask` vs `Sub-task` (D04.1).

## Ticket MCF-32 — 2026-11-04 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-32-optional-points` (on top of MCF-31); each commit "MCF-32: …" | — |
| 3 | CI green on the PR | ✅ | PR head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_optional_points.py` (25 tests) and a page AppTest; failing tests committed first twice | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D43, D33.1 (no new sentence), ADR 0002 | — |
| 6 | AI ticket evaluation | 🟡 | Prompt version 4 → 5: the template is the same; "velocity" and "points" may now be "none". The 10 eval cases are unchanged. No eval case without points yet | PM decides |
| 7 | Independent review with a verdict | ✅ | Subagent grade B, 0 blockers, 1 major, 4 minor, 2 nits — 6 fixed with tests first; the major (points needed with partial points) is kept by design, see the PR | PM decides |
| 8 | Each acceptance criterion met | ✅ | No points: 3 dates and "Not available: needs story points"; some points: count shown on the CLI and page; back-test unchanged | — |
| 9 | README and rule pages match | ✅ | Loader docstring | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌. Items 6 and 7 have a PM choice in the approval.

## Ticket MCF-33 — 2026-11-04 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-33-page-redesign` (on top of MCF-32); each commit "MCF-33: …" | — |
| 3 | CI green on the PR | ✅ | PR head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_web_redesign.py` and new AppTests; browser check updated (20 of 20, desktop and phone); failing tests committed first twice | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D41, D43, D33.1 | — |
| 6 | AI ticket evaluation | n/a | No AI change | — |
| 7 | Independent review with a verdict | ✅ | Subagent grade B−, 0 blockers, 3 major (contrast 4.47:1 on the safer card, demo script wait text, phone legend), 6 minor, 3 nits — all majors and minors fixed with tests first | — |
| 8 | Each acceptance criterion met | 🟡 | Sidebar, labels, typed backlog, colours, date axis, accessibility: done. The 20-second test with 3–5 people is the PM's step | PM runs the 20-second test |
| 9 | README and rule pages match | ✅ | `docs/demo.md` (v1.0.0 video kept as is) | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌. Item 8 closes after the PM's 20-second test.

## Ticket MCF-34 — 2026-11-04 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-34-velocity-help`; each commit "MCF-34: …" | — |
| 3 | CI green on the PR | ✅ | PR head checked green before Review | — |
| 4 | PR adds tests | ✅ | 3 new or changed tests in `tests/test_web_redesign.py`; failing tests committed first | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D45 (changes part of D41), D43 | — |
| 6 | AI ticket evaluation | n/a | No AI change | — |
| 7 | Independent review with a verdict | ✅ | Subagent grade A−, no blocker; 1 minor (help text not tied to the expander label) fixed with a test; 1 minor was already covered (`test_no_sentence_repeats_between_the_sidebar_and_the_page`) | — |
| 8 | Each acceptance criterion met | ✅ | Card shows label and date only; "Not available / Needs story points" kept; help line explains pace and estimated points; CLI unchanged; browser check 20 of 20 | — |
| 9 | README and rule pages match | ✅ | No doc names the removed text | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌.

## Ticket MCF-35 — 2026-11-04 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-35-plain-wording`; each commit "MCF-35: …" | — |
| 3 | CI green on the PR | ✅ | PR head checked green before Review | — |
| 4 | PR adds tests | ✅ | New and changed tests in `tests/test_web_redesign.py` and `tests/test_web_app.py`; failing tests committed first twice; browser check 20 of 20 | — |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D41, D44, D45 logged. **D46** ("chance of completion" back on the page) is decided at this approval | PM decides D46 |
| 6 | AI ticket evaluation | n/a | No AI change (the sentence bank is not touched) | — |
| 7 | Independent review with a verdict | ✅ | Subagent grade B−, no blocker; weak AI-line test, "Empty" for a toggle, stale demo guide and demo script fixed with tests first; honesty point, bank wording and card layout go to the PM (see PR) | PM decides |
| 8 | Each acceptance criterion met | ✅ | All MCF-35 criteria; numbers and CLI unchanged | — |
| 9 | README and rule pages match | ✅ | `docs/demo.md` check name updated | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌. Item 5 closes with D46.

## Ticket MCF-36 — 2026-11-04 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-36-how-it-works`; each commit "MCF-36: …" | — |
| 3 | CI green on the PR | ✅ | PR head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_how_it_works.py` (21 tests) and an AppTest; failing tests committed first twice; browser check 20 of 20 | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D46 (warning on the page: closed by this ticket), R3 | — |
| 6 | AI ticket evaluation | n/a | No AI change | — |
| 7 | Independent review with a verdict | ✅ | Subagent grade B+, no blocker; typed "84 days" / "10,000" now from `WINDOW_DAYS` / `RUNS` (planted change was not caught before), 903 no-forecast cases added, "up to that date", "not bugs or epics" — all with tests first | — |
| 8 | Each acceptance criterion met | ✅ | Section with 2 parts, figures from tested facts, footer, chart caption, README "Try it" | — |
| 9 | README and rule pages match | ✅ | README "Try it" line | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌.

## Ticket MCF-37 — 2026-11-04 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-37-layout` (on top of MCF-36); each commit "MCF-37: …" | — |
| 3 | CI green on the PR | ✅ | PR head checked green before Review | — |
| 4 | PR adds tests | ✅ | `tests/test_layout.py` and a new browser-check step; failing tests committed first twice; browser check 22 of 22 | — |
| 5 | Each decision ID in the PR is in the Decision Log | ✅ | D41, D46 (layout only, no new decision) | — |
| 6 | AI ticket evaluation | n/a | No AI change | — |
| 7 | Independent review with a verdict | ✅ | Subagent grade C+, no blocker; caption contrast 3.7:1 → 5.9:1; a broken box selector passed every check → new browser step fails on it (planted again: caught); "touch" → "side by side"; section 2 order; Full report description | — |
| 8 | Each acceptance criterion met | ✅ | 4 numbered boxes plus Full report, grey page, history in section 2, cards stack on a phone, same-day lines and note, other states, fixed sidebar | — |
| 9 | README and rule pages match | ✅ | No doc names the old layout | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌.

## Ticket MCF-38 — 2026-11-04 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-38-subtask`; each commit "MCF-38: …" | — |
| 3 | CI green on the PR | ✅ | PR head checked green before Review | — |
| 4 | PR adds tests | ✅ | Type, Jira export and TAWOS tests; failing tests committed first; the TAWOS check ran with the 29 downloaded files (no "Subtask" rows) | — |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D04.2 is logged at this approval (D04.1 struck through) | PM approves |
| 6 | AI ticket evaluation | n/a | No AI change | — |
| 7 | Independent review with a verdict | ✅ | Subagent grade A−, no blocker; not a back-test change after results (TAWOS has no "Subtask"); weak exit-code test made exact; stale "D04.1" in `throughput.py` fixed | — |
| 8 | Each acceptance criterion met | ✅ | "Subtask" is a value item on done and open rows; other spellings stay errors; back-test unchanged | — |
| 9 | README and rule pages match | ✅ | `docs/method.md` lists 13 value types | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌. Closes the MCF-31 open point "Subtask vs Sub-task".

## Ticket MCF-39 — 2026-11-07 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-39-light-theme`; each commit "MCF-39: …" | — |
| 3 | CI green on the PR | ✅ | PR #45 head checked green before Review | — |
| 4 | PR adds tests | 🟡 | Config, CSS and browser tests (dark-mode phone, contrast, theme switch, contrast self-test). The tests were run and failed before the fix, but were committed with the fix, not first | Commit failing tests first next time |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D48 is logged at this approval | PM approves |
| 6 | AI ticket evaluation | n/a | No AI change | — |
| 7 | Independent review with a verdict | ✅ | Subagent: no blocker; 1 Medium (contrast check missed see-through colours, 6 of 8 bad cases) and 5 Low, all fixed tests first; the stronger check found 3 real pale texts, fixed | — |
| 8 | Each acceptance criterion met | ✅ | Light theme, no switch, 4.5:1 in dark mode, browser check in dark mode, config test | — |
| 9 | README and rule pages match | ✅ | No doc names the dark theme | — |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌.

## Ticket MCF-40 — 2026-11-07 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-40-card-notes`; each commit "MCF-40: …" | — |
| 3 | CI green on the PR | ✅ | PR #46 head checked green before Review | — |
| 4 | PR adds tests | 🟡 | Card, HTML, help and browser tests; run and failed before the change, but committed with it | Commit failing tests first next time |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D49 is logged at this approval | PM approves |
| 6 | AI ticket evaluation | n/a | No AI change (the bank does not name the card notes) | — |
| 7 | Independent review with a verdict | ✅ | Subagent: 1 Medium (no on-page text said which date to share) and 3 Low, all fixed tests first | — |
| 8 | Each acceptance criterion met | ✅ | No notes except "Needs story points"; highlight kept; P50/P85/P95 and "give the 85% date" in the help | — |
| 9 | README and rule pages match | 🟡 | No repo doc names the notes; the design canvas is out of date for the cards (noted in the PR) | PM decides if the canvas is updated |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval | — |

Result: pass — no ❌.

## Ticket MCF-41 — 2026-11-07 — grader: builder pre-check (judgement items also covered by the subagent review, D24)

| # | Criterion | Grade | Evidence | Fix |
|---|---|---|---|---|
| 1 | In Progress before the first commit | ✅ | Jira In Progress and brief before the first commit | — |
| 2 | Branch and commits start with the key; only this ticket's work | ✅ | Branch `MCF-41-collapsible`; each commit "MCF-41: …" | — |
| 3 | CI green on the PR | ✅ | PR head checked green before Review | — |
| 4 | PR adds tests | 🟡 | AppTest (4 sections open, inner expanders inside, hidden headings) and browser checks (close and open, stays closed, label size); run and failed before the change, but committed with it | Commit failing tests first next time |
| 5 | Each decision ID in the PR is in the Decision Log | 🟡 | D50 is logged at this approval | PM approves |
| 6 | AI ticket evaluation | n/a | No AI change | — |
| 7 | Independent review with a verdict | ✅ | Subagent: no blocker; 2 Medium (screen-reader headings lost; the key untested) and 3 Low, fixed tests first; AC2 text change judged sound | — |
| 8 | Each acceptance criterion met | ✅ | Sections close and open, open on load, stay closed on a rerun, inner parts unchanged, D46 warning on load | — |
| 9 | README and rule pages match | 🟡 | No doc names the boxes; `scripts/record_demo.py` waits for headings that changed (the video is not recorded again, PM rule) | Update the demo script if the video is recorded again |
| 10 | Workflow steps followed | ✅ | Brief, tests first, review before approval; AC2 changed before the build and flagged for the PM | — |

Result: pass — no ❌.
