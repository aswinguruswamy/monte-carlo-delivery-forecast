# Changelog

All notable changes are in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-11-09

A dark theme for the web page, and a second back-test on the full TAWOS data. The forecast method, the tool's velocity rule and the AI prompt are unchanged.

### Added
- **Dark theme** (MCF-42, D48.1): the page follows the device and the menu's System / Light / Dark switch, with dark colours from the approved design. Light mode keeps the 1.1.0 colours, except darker input and inner borders (3:1) and new chart line colours: one set that is readable in both themes, so the lines no longer match the card colours exactly (D41). The browser check tests both themes and a manual switch (46 checks).
- **v2 back-test on the full TAWOS data** (MCF-28, ADR 0003, D54, D54.1, D54.2): a reader for the TAWOS SQL dump that keeps only the allowed columns (`mcf.data.tawos_dump`; no keys, titles or user IDs), the v2 run (`mcf.backtest.full`) with the unchanged ADR 0002 method, and a side-by-side report (`docs/backtest-report-full.md`, summary numbers in `results/metrics-full.json`). The README cites the dataset DOI. Neither the dump nor the export is in the repository (D08).

- **Dev container settings** for GitHub Codespaces (`.devcontainer/devcontainer.json`, added by the PM).

### Changed
- The manual AI evaluation workflow uploads its result with `actions/upload-artifact` 7.0.2 (PR #34, D47).
- The page no longer forces the light theme (replaces "Light theme only" of 1.1.0, D48).
- The repository check for data files allows the dev container settings file (`.devcontainer/devcontainer.json`).

### Fixed
- The info text ("AI explanation not shown") was 4.30:1 on a dark section box; it is now readable in both themes (MCF-42).
- The browser check could fail by chance when Streamlit dimmed old elements during a rerun; it now waits until no element is stale (MCF-42).

### Back-test results (published as they are, R3)
- **v1, TAWOS extract (unchanged since 1.0.0):** measure 1 **FAIL**, the 85% date was correct in 69.0% of 7,692 cases (pass band 75–95%); measure 2 **PASS**, 34 days vs 36 days.
- **v2, full TAWOS data (new):** 39 projects, 22,619 scored cases. Measure 1 **PASS** at 75.0% (16,974 of 22,619), but **not robust**: its bootstrap 95% interval (73.0% to 77.1%) crosses the 75% edge. With "done = completed only" (information) it is 73.5% (**FAIL**). Measure 2 **PASS**, 14 days vs 90 days on 12,632 cases, but see the D54.3 limit below. Full report: `docs/backtest-report-full.md`.

### AI evaluation (measure 3), prompt version 5 (unchanged)
- **PASS** on 2026-11-09 (claude-haiku-5-5; 1 manual run on the merged code of this release, with upload-artifact 7.0.2): 10 cases × 3 runs; 30 of 30 replies were a valid choice of approved sentences; 0 wrong numbers or dates; 0 API errors; the injection case passed 3 of 3 runs.

### Known limits
- All known limits of 1.0.0 and 1.1.0 still apply, except "light only": the 50% date is not certain; on the extract the 85% date was too early in about a third of the cases.
- v2 counts every resolved issue as done, also Won't Fix, Duplicate and similar (about 4 in 10 resolutions). The v2 measure 1 pass depends on this rule: with completed only, it fails.
- **D54.3:** the v2 velocity rule (ADR 0003) takes the pace from the items with story points only, but counts all N items as work, so its date is late when few items have points. The tool divides by all items (D44). Most of the v2 measure 2 margin comes from this rule, so it does not test the velocity rule that users run. On the 524 fully pointed cases with a velocity date: 8 days vs 10 days.
- Only 14% of the full TAWOS issues have story points; large story points are used as recorded (D54.2).
- The page in the app still shows only the v1 back-test result and its warning, and its footer links only to the v1 report.
- No new demo video for 1.2.0 (D55): the v1.1.0 video shows the light page and "Version 1.1.0".
- Browsers without CSS `light-dark()` (Chrome before 123, Safari before 17.5, Firefox before 120) show Streamlit's own colours, not the page colours.
- Some of Streamlit's own parts are below 3:1 (radio circle, focus ring, next-month days in the date picker).

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
- **PASS** on 2026-11-08 (claude-haiku-5-5, prompt version 5; 2 manual runs, both PASS): 10 cases × 3 runs; 30 of 30 replies were a valid choice of approved sentences; 0 wrong numbers or dates; 0 API errors; the instruction hidden in the file name and issue keys never reached the prompt (3 of 3 runs passed).

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

[1.2.0]: https://github.com/aswinguruswamy/monte-carlo-delivery-forecast/releases/tag/v1.2.0
[1.1.0]: https://github.com/aswinguruswamy/monte-carlo-delivery-forecast/releases/tag/v1.1.0
[1.0.0]: https://github.com/aswinguruswamy/monte-carlo-delivery-forecast/releases/tag/v1.0.0
