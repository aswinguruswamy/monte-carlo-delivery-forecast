# Changelog

All notable changes are in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-06

First public release.

### Added
- **Command line:** `mcf forecast FILE --backlog N` gives the Monte Carlo 50%, 85% and 95% dates and the velocity date from a team's CSV export (10,000 runs, 84-day history, fixed seed). Open items are skipped and counted (D25). Options: `--as-of`, `--backlog-points`, `--seed` (D28).
- **AI explanation** (`--explain`, and on the web page): Claude picks 3 to 6 sentences from a PM-approved bank of 15 (D33.1). Code writes every number and date. A reply that is not a valid choice, or an API failure, shows only the plain report. Needs `ANTHROPIC_API_KEY`.
- **Web page** (Streamlit, `streamlit run streamlit_app.py`): the made-up sample file or an upload, the 3 dates and the velocity date, a chart of the simulated finish dates, the AI explanation when a key is set (off by default, one call for each forecast).
- **Back-test** on 29 TAWOS projects (ADR 0002, fixed before the first run): report in `docs/backtest-report.md`, summary numbers in `results/metrics.json`.
- **Back-test review** script and skill (`python -m mcf.backtest.review`).
- **AI evaluation set** (10 cases × 3 runs), run by hand in GitHub Actions (D35).
- Data download script with checksums (no data in the repository, D08); README, method page, CITATION.cff, NOTICE; demo guide and video script (`docs/demo.md`).

### Fixed (before the release)
- A date near year 1 gave a stack trace in the command line (MCF-29).
- The web chart gave a raw error when a simulated run ended after 9999-12-31 (MCF-30).

### Back-test result (published as it is, R3)
- **Measure 1 — FAIL:** the 85% date was correct in 69.0% of 7,692 cases; the pass band is 75–95%. The 85% date was too early in 31.0% of cases.
- **Measure 2 — PASS:** median error 34 days (Monte Carlo 50% date) vs 36 days (velocity). The lead is small and not robust: the 95% interval of the difference is 0 to 6 days.
- 903 of 8,595 cases (10.5%) have no forecast (no item done in the 84-day window).

### Known limits
- The 50% date is not certain: up to half of the runs finish later.
- The 85% date was too early in about a third of the back-test cases (measure 1). Use the 95% date when a late finish costs a lot.
- The data holds only issues with story points that were resolved as completed. Teams with many unestimated items may behave differently. 29 open-source projects; the result may not hold for other teams.
- Velocity uses 2-week periods from day t, not real sprints. In the back-test, velocity uses the real points of the next N items, which helps velocity.
- Monte Carlo assumes that the past 84 days are a fair sample of the next weeks.
- The public demo has no API key, so the AI explanation is off there (D39).
- The sample file on the web page needs a repository checkout (editable install).
