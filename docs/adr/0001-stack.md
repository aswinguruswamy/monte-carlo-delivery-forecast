# ADR 0001: Stack for MCF

**Status:** Accepted (D01) · **Date:** 2026-10-28 · **Ticket:** MCF-7

## Context
MCF is a solo portfolio project. The PM must be able to read and run the code. The MVP is a command-line tool (D01). v1 adds a Streamlit page and a Claude explanation. The data is a CSV file (D02).

## Decision
| Part | Choice | Version (2026-10-28) |
|---|---|---|
| Language | Python | 3.11 and 3.12 in CI (NFR9) |
| Calculation | numpy | 2.5.4 (requires >=2.0) |
| Data loading | pandas | 3.1.0 (requires >=2.2) |
| Tests | pytest | 9.2.0 |
| Style | ruff (lint and format) | 0.17.3 |
| Dependency scan | pip-audit | 2.10.1 |
| Licence scan | pip-licenses | latest |
| Secret scan | gitleaks-action | v3.0.0 (pinned by commit) |
| Web page (v1) | Streamlit | 1.66.1 (added in MCF-24) |
| AI explanation (v1) | anthropic SDK | 2.3.0 (added in MCF-21) |
| Build | hatchling | >=1.25 |

## Options considered
Python with Streamlit; Next.js on Vercel; an offline HTML file; command line only (see D01).

## Consequences
- Same stack as KAN and SRG, so the PM can run it.
- Streamlit and the anthropic SDK are added only in v1, so the MVP has 2 runtime dependencies.
- Branch protection is not enforced while the repository is private (D18). CI still runs on each pull request.
