# Changelog

All notable changes are in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-11-08

A clearer web page for sponsors and Jira exports with no editing. The forecast method and the back-test are unchanged.

### Added
- **Jira exports work as they are** (MCF-31, D42): the Jira column names (`Issue key`, `Issue Type`, `Resolved`, `Story Points` / `Story point estimate`, also as `Custom field (…)`) and Jira date formats are read, and repeated columns that the tool does not use are ignored. No name or title column is read.
- **Story points are optional** (MCF-32, D43): with no points, the 50%, 85% and 95% dates show and the velocity date shows "Not available"; with some points, the page and the command line show how many items have none.
- **"Subtask"** is a value type (MCF-38, D04.2), the Jira Cloud name for "Sub-task".
- **Help sidebar** on the web page (MCF-33, MCF-35, MCF-40): what you need, the steps, which date to use (P50, P85, P95), what to be careful of, and privacy. The steps say "Give the 85% date (P85) to your sponsor or client."
- **"How this forecast works"** on the page (MCF-36): the Monte Carlo steps, and the back-test result with its warning in the title ("the 85% date was too early about 1 in 3 times").
- **Footer** with the source code, the back-test report, the TAWOS citation and the version (MCF-36). The README starts with a "Try it" link to the live page.

### Changed
- **Plain labels** (MCF-33, MCF-35, D41, D46): "50% / 85% / 95% chance of completion" and "Velocity date"; dates written out; a typed backlog number from 1 to 10,000 (a thousands comma is accepted); card colours match the chart lines; the chart shows the year when the dates cross into a new year; "Message to sponsor" line.
- **Privacy:** error messages on the page do not show Jira issue keys (MCF-31).
- **Cards show only the label and the date** (MCF-34, MCF-40, D45, D49). "Needs story points" stays when there is no velocity date. The 85% card is highlighted, with hidden text for screen readers.
- **Layout** (MCF-37, MCF-41, D50): a grey page with 4 numbered white sections. The sections can close and are open when the page loads. Each section has a hidden heading for screen readers.
- **Light theme only** (MCF-39, D48): the page no longer follows a dark-mode setting, so the new white boxes stay readable on a phone in dark mode.
- **AI explanation:** no AI line on a page with no key (MCF-35). The prompt is version 5 (MCF-32): with no velocity date, no velocity or points sentence is offered.
- **Demo video script** follows the v1.1 page and checks the version in the footer (MCF-43).

### Fixed
- Texts below 4.5:1 contrast: the captions (MCF-37); the empty date field, the file size, the error message and the upload hint (MCF-39, MCF-41). The manual browser check (`scripts/browser_check.py`) now tests the contrast of all visible text, also in dark mode.
- A Jira Cloud export with "Subtask" rows stopped with an unknown-type error (MCF-38).

### Back-test result (unchanged since 1.0.0)
- **Measure 1 — FAIL:** the 85% date was correct in 69.0% of 7,692 cases; the pass band is 75–95%.
- **Measure 2 — PASS:** median error 34 days (Monte Carlo 50% date) vs 36 days (velocity).

### AI evaluation (measure 3), prompt version 5
- **To run before the tag** (MCF-44): the manual evaluation workflow, 10 cases × 3 runs.

### Known limits
- All known limits of 1.0.0 still apply: the 50% date is not certain; the 85% date was too early in about a third of the back-test cases; the back-test data holds only estimated, completed issues of 29 open-source projects.
- The page is light only; a dark theme is planned (MCF-42).
- After an error (for example a bad backlog number), closed sections come back open.
- The 20-second user test was small (a few developers, with a short explanation; D51).

## [1.0.0] - 2026-11-03

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

### AI evaluation (measure 3)
- **PASS** on 2026-11-03 (claude-haiku-5-5, prompt version 4): 10 cases × 3 runs; 30 of 30 replies were a valid choice of approved sentences; 0 wrong numbers or dates; 0 API errors; the instruction hidden in the file name and issue keys never reached the prompt (3 of 3 runs passed).

### Known limits
- The 50% date is not certain: up to half of the runs finish later.
- The 85% date was too early in about a third of the back-test cases (measure 1). Use the 95% date when a late finish costs a lot.
- The data holds only issues with story points that were resolved as completed. Teams with many unestimated items may behave differently. 29 open-source projects; the result may not hold for other teams.
- Velocity uses 2-week periods from day t, not real sprints. In the back-test, velocity uses the real points of the next N items, which helps velocity.
- Monte Carlo assumes that the past 84 days are a fair sample of the next weeks.
- The public demo has no API key, so the AI explanation is off there (D39).
- The sample file on the web page needs a repository checkout (editable install).

[1.1.0]: https://github.com/aswinguruswamy/monte-carlo-delivery-forecast/releases/tag/v1.1.0
[1.0.0]: https://github.com/aswinguruswamy/monte-carlo-delivery-forecast/releases/tag/v1.0.0
