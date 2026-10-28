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
