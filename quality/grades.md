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
