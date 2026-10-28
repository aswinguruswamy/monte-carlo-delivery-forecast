# ADR 0001: Stack for MCF

**Status:** Accepted by the PM on 2026-10-28 (D20) · **Date:** 2026-10-28 · **Ticket:** MCF-7
**Builds on:** D01 (command-line MVP, Streamlit page in v1), D02 (CSV input), D19 (licence policy)

## Context
MCF is a solo portfolio project. The PM must be able to read and run the code. The MVP is a command-line tool (D01). v1 adds a Streamlit page and a Claude explanation. The data is a CSV file (D02).

## Decision
Versions resolved on 2026-10-28 with a fresh install.

| Part | Choice | Python 3.11 | Python 3.12 |
|---|---|---|---|
| Language | Python | Python 3.11 | Python 3.12 |
| Calculation | numpy (requires >=2.0) | 2.4.6 | 2.5.4 |
| Data loading | pandas (requires >=2.2) | 3.1.0 | 3.1.0 |
| Tests | pytest (>=8.0) | 9.2.0 | 9.2.0 |
| Style | ruff, lint and format (>=0.6) | 0.17.3 | 0.17.3 |
| Dependency scan | pip-audit (>=2.7) | 2.10.1 | 2.10.1 |
| Licence scan | pip-licenses (pinned ==5.5.5) | 5.5.5 | 5.5.5 |
| CI test helper | pyyaml (>=6.0) | 6.0.3 | 6.0.3 |
| Secret scan | gitleaks-action, pinned by commit | v3.0.0 | v3.0.0 |
| Build | hatchling (>=1.25) | — | — |
| Web page (v1) | Streamlit | added in MCF-24 | added in MCF-24 |
| AI explanation (v1) | anthropic SDK | added in MCF-21 | added in MCF-21 |

**No lock file.** CI installs the newest versions that meet the ranges on each run. The Python 3.11 and 3.12 jobs can therefore get different numpy versions. Dependabot reports new versions weekly. A lock file or a constraints file is added before the release (MCF-27), so the release build can be repeated.

**Licence policy (D19).** CI fails if a runtime dependency has a strong copyleft licence (GPL or AGPL, matched by exact name). LGPL and permissive licences are allowed. Development tools are not scanned, because they are not shipped.

## Options considered
Python with Streamlit; Next.js on Vercel; an offline HTML file; command line only (see D01).

## Consequences
- Same stack as KAN and SRG, so the PM can run it.
- The MVP has 2 direct runtime dependencies (numpy, pandas). Streamlit and the anthropic SDK come in v1.
- Branch protection is not enforced while the repository is private (D18). CI still runs on each pull request, and the PM approves each merge in chat.
