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
