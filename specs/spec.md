# Spec: MCF v2 – Charter-date chance, thin-history warning, SRG function

Version: 1.2.1 | Status: **APPROVED by Aswin Guruswamy, 2026-11-22** (1.1 = demo decision; 1.2 = screenshots in place of a video, Aswin 2026-11-23; 1.2.1 = audit text fixes) | Date: 2026-11-22
Tool: MCF | MoSCoW: Must (R3: Should) | Source: `specs/requirements.md` v1.4, `clarify/MCF-clarify-log.md`, MCF v1.2.0 code (`forecast/montecarlo.py`, `forecast/throughput.py`, `result.py`, `cli.py`, `web/logic.py`, `web/content/how_accurate.md`, `docs/method.md`, ADR 0002, read 2026-11-22)

Requirement IDs `MCF-Rn.m` belong to R1–R11 and N1–N7 on the requirements page (v1.4 numbering).
Sources: `R`/`N` = requirements page; `MCF-x.y` = MCF clarify log; `SH-x.y` = shared clarify log; `v1` = existing MCF code or ADR; `proposal` = Claude's proposal, confirmed only by approval of this spec.

**v2 does not change the forecast method.** Window, runs, seed and percentiles stay as in v1 (ADR 0002).

## 1. Problem
A PM must say when the work will be done, and often whether the team will make the charter date. MCF v1 gives 50/85/95% dates, but it cannot answer "will we make the charter date?", it does not warn when the history is thin, and SRG cannot call it.

## 2. Goal and non-goals
- **Goal:** add the charter-date chance, a thin-history warning and one function for SRG, with small quality fixes – and no change to the forecast method.
- **Non-goals:** "how many by a date", gap and pace warnings, a young-team rule, live Jira, several teams, visitors' own AI key, a forecast log (requirements page §8).

## 3. Users and scenarios
| User | Scenario | Today | After |
|---|---|---|---|
| PM | Sponsor asks "will we make 15 Dec?" | Gives the 85% date and hopes | "62% chance to finish by 15 Dec" |
| PM | Team finished only 12 tickets in 12 weeks | Dates look as sure as any others | Warning above the dates |
| SRG | Needs a finish date per team | Not possible | Calls the MCF function |

## 4. Definitions (v1 unless marked)
| Term | Meaning | Source |
|---|---|---|
| Value item | An item whose type MCF counts (13 types; not bugs or epics). | v1 (D04.2) |
| Day t | The forecast date. Default: the last done day in the file. | v1 (D28) |
| Backlog N | Value items still to do; a whole number of 1 or more. | v1 |
| Window | The 84 calendar days from t − 83 to t. Days with 0 items stay in, also days before the first item. | v1 (ADR 0002) |
| Run | Pick a day of the window at random (with replacement) and add its count; repeat until the total reaches N. k = days picked. 10,000 runs; seed 20261028 by default (v1 draw order). | v1 |
| p% date | t + the smallest k such that at least p% of runs have k or fewer days (inverted-CDF percentile). | v1 |
| Chance by date D | 100 × (runs with t + k ≤ D) ÷ 10,000, **rounded down** to a whole percent. "100%" only when every run finishes by D; "under 1%" when some, but fewer than 1%, do. | R1, proposal |
| Date text | Command line: ISO (2026-12-21). Page: v1 page format (`long_date`, "Dec. 21, 2026"). | v1 |

## 5. Requirements (EARS)
| ID | Type | Requirement | Source |
|---|---|---|---|
| MCF-R1.1 | Optional | Where the user enters a charter date D, the MCF shall show "<x>% chance to finish by <D>" on the page and in the command-line output. | R1, MCF-0.2 |
| MCF-R1.2 | Unwanted | If D is on or before t, then the MCF shall show "The charter date must be after <t>." and no chance. | R1, proposal |
| MCF-R1.3 | Ubiquitous | The MCF shall compute the chance from the same 10,000 runs as the dates. | R1, N1 |
| MCF-R2.1 | Unwanted | If fewer than 30 value items are done in the window, then the MCF shall warn above the dates: "Only <n> items finished in the last 12 weeks. Treat the dates with care." | R2 |
| MCF-R2.2 | Ubiquitous | The MCF shall show the warning on the page, in the command-line output and in the function result. | R2, N3 |
| MCF-R3.1 | Ubiquitous | The MCF shall show in "How accurate" both results: first test (29 projects, 69.0%, missed the target) and latest test (39 projects, 75.0%, met the target), with the pass rule (75–95%, shown once); the page shows the shares as "69 of 100" and "75 of 100". | R3, v1 `how_accurate.md` |
| MCF-R4.1 | Ubiquitous | The MCF shall show "AI: <model> · prompt v<n>" below every AI explanation. | R4 |
| MCF-R5.1 | Ubiquitous | The README shall start with "Known limits", above "Install", and say that teams with less than 12 weeks of history get dates that are too late. | R5 |
| MCF-R6.1 | Ubiquitous | The MCF shall give one public function. In: daily counts for consecutive days ending on day t, t, N, seed (default 20261028), optional charter date. Out: 50/85/95% dates, chance by the charter date, the warning (or none). | R6, SH-3.3 |
| MCF-R6.2 | Ubiquitous | The function shall use the last 84 days of the counts; with fewer than 84 days, the missing earlier days count as 0 (as v1). | R6, v1 |
| MCF-R6.3 | Ubiquitous | The function shall return the same dates, chance and warning as the page and the command line for the same counts, t, N and seed. | R6, N1 |
| MCF-R6.4 | Unwanted | If N < 1, a count is below 0, or no count in the window is above 0, then the function shall raise an error with the v1 reason text, never a date. | R6, v1 |
| MCF-R6.5 | Ubiquitous | The function shall not choose ticket types; the caller passes the counts. | R6 |
| MCF-R7.1 | Ubiquitous | The existing tests and golden files shall stay; new tests cover the chance, the warning and the function, and property tests check: 50% ≤ 85% ≤ 95% date, N + 1 never gives an earlier date (same seed), same seed → same output. | R7, v1 |
| MCF-R8.1 | Event | When a pull request changes the prompt, the sentence list, the check or the model setting, CI shall run the AI evaluation (10 cases × 3 runs) and fail the check on FAIL. The evaluation check is not a required branch check, because it runs only on AI changes; a FAIL shows on the PR and the PR is not merged. | R8, v1 (`eval.yml`, today manual) |
| MCF-R9.1 | Ubiquitous | The contributing rules (CLAUDE.md of the repo) shall say: before a change to the forecast method, write a decision record, re-run the 39-project test, and publish before and after. | R9, v1 (ADR 0002 change rule) |
| MCF-R10.1 | State | While the app runs with no `ANTHROPIC_API_KEY`, the MCF shall show a saved AI explanation of the sample file, labelled "Saved example – the live explanation needs an API key." | R10, SH-4.4 |
| MCF-R11.1 | Ubiquitous | The README and the portfolio card shall show 3 screenshots of the page: the inputs with a charter date, the dates with the chance and the saved AI example, and the accuracy section. `scripts/take_screenshots.py` makes them again. | R11, SH-5.5 |

## 6. Acceptance criteria
Example A: t = 2026-12-01; 84 days of history, exactly 1 item done each day. Every run then needs exactly N days. Dates are command-line text; the page shows the same dates in the v1 page format.

| ID | Req | Given | When | Then | Test |
|---|---|---|---|---|---|
| AC1 | R6.3 | Example A, N = 20 | Forecast | 50/85/95% dates all 2026-12-21 | unit |
| AC2 | R1.1 | Example A, N = 20, charter 2026-12-21 | Forecast | "100% chance to finish by 2026-12-21" | unit |
| AC3 | R1.1 | Example A, N = 20, charter 2026-12-20 | Forecast | "0% chance to finish by 2026-12-20" | unit |
| AC4 | R1.1 | 9,960 of 10,000 runs by D | Chance | "99%" (rounded down) | unit |
| AC5 | R1.1 | 50 of 10,000 runs by D | Chance | "under 1%" | unit |
| AC6 | R1.2 | Example A, charter 2026-12-01 | Forecast | "The charter date must be after 2026-12-01." | unit |
| AC7 | R1.3 | Random history, fixed seed, charter = the 85% date | Forecast | Chance ≥ 85% | property |
| AC8 | R2.1 | Window with 29 items | Forecast | "Only 29 items finished in the last 12 weeks …" | unit (edge) |
| AC9 | R2.1 | Window with 30 items | Forecast | No warning | unit (edge) |
| AC10 | R2.2 | Window with 12 items | Page, command line, function | Same warning in all 3, above the dates | unit |
| AC11 | R3.1 | Page | "How accurate" opens | Both results with the pass rule | golden |
| AC12 | R4.1 | AI explanation on | Page | "AI: <model> · prompt v<n>" below the text | unit |
| AC13 | R5.1 | README | Docs test | First section after the title is "Known limits" and names the 12-week limit | unit |
| AC14 | R6.1, R6.3 | Sample CSV, N = 40, default seed | Function, page, command line | Same dates, chance and warning | unit |
| AC15 | R6.2 | Counts for 100 days | Function | Same output as with the last 84 days only | unit |
| AC16 | R6.2 | Counts for 31 days, 1 a day, N = 10 | Function | Same output as v1 with 53 zero days added before | unit |
| AC17 | R6.4 | Counts all 0 | Function | Error "no forecast: no value item was done in the history window" (v1 text) | unit |
| AC18 | R6.4 | N = 0 | Function | Error "N must be a whole number of 1 or more" | unit |
| AC19 | R7.1 | Random histories, N, seed | Property tests | All 3 properties hold | property |
| AC20 | R7.1 | Golden files | Test run | Updated files pass | golden |
| AC21 | R8.1 | PR changes the sentence list | CI | Eval job runs; FAIL fails the check | CI run log |
| AC22 | R9.1 | Repo CLAUDE.md | Docs test | Contains the method-change rule | unit |
| AC23 | N2 | Sample file, 10,000 runs | Timed test | Under 3 s | timed unit test (marked slow) |
| AC24 | R10.1 | No key set, sample file | Page | Saved explanation with the label; no API call made | unit (fake client asserts no call) |
| AC25 | R11.1 | README | Docs test | A "Screenshots" section links the 3 images, and the files exist | unit |

## 7. Non-functional requirements
| ID | Area | Requirement | Check |
|---|---|---|---|
| N1 | Same result | Same counts, inputs and seed → same dates, chance and warning. | AC14, AC19 |
| N2 | Speed | A forecast (10,000 runs) in under 3 s. | AC23 |
| N3 | Honesty | Warning on all 3 surfaces; "half of the runs finish later" under the 50% date (v1). | AC10 |
| N4 | Accuracy | Method unchanged; the published 75.0% result stays valid. | AC1, AC16 (v1 behaviour kept) |
| N5 | Privacy | Reads only 4 columns; no names or titles reach the AI (v1). | v1 tests |
| N6 | Cost | Free demo; AI explanation < US$0.01; AI evaluation run < US$0.50. | eval job summary |
| N7 | Plain language | Warning and errors in simple English (texts above). | review |

## 8. Constitution check
| Principle | How this spec complies |
|---|---|
| P1 Code writes the facts | Dates, chance and warning come from code; the AI only picks approved sentences (v1). |
| P2 Verify before you show | v1 check of the AI reply stays (MCF-22). |
| P3 Fail loudly | R1.2, R6.4; warning R2. |
| P4 Time and source | Day t and the window shown (v1); model and prompt version (R4.1). |
| P5 Least data to the AI | 4 columns only (v1). |
| P6 Secrets | API key only in `.env` or repository secrets (v1). |
| P7 Prove before you claim | Method unchanged; method-change rule (R9.1). |
| P8 Same input, same output | Fixed seed (v1), R6.3. |
| P9–P12 | One spec; smallest change to v1; plain language; shared CI. |

## 9. Edge cases
- N below 1 → v1 error (R6.4).
- Charter date far in the future → chance up to 100%.
- Young team (less than 12 weeks) → v1 behaviour, usually the warning, and the README limit. SRG does not ask for a forecast before 12 weeks.
- Throughput too low (no result within 100,000 days) → v1 error stays.

## 10. Out of scope
How many by a date · gap and pace warnings · young-team rule · accuracy test at every release · live Jira · several teams · visitors' own AI key · forecast log · velocity from real sprints · other trackers.

## 11. Clarify checklist
- [x] Actors and triggers · [x] Inputs · [x] Outputs · [x] Rules have a source · [x] Errors · [x] Edge cases · [x] Data to the AI (v1, 4 columns) · [x] Freshness (day t shown) · [x] ACs testable · [x] Dependencies (SRG uses R6) · [x] Cost

## 12. Proposals to confirm by approval
Charter-date error text (R1.2) · chance rounded down (§4) · CI eval fails the PR check (R8.1).

## Grades
- **Independent review of v0.1** (separate session): 1 blocker, 7 should-fix, 4 nits; all numbers correct. Fixed in v0.2.
- **v0.3** applies Aswin's trims (requirements v1.2). Most v0.2 fixes were for parts that are now cut (young-team test, count method, gap and pace edges). The remaining fixes stay: function input (R6.1–R6.2), N < 1 (R6.4), chance rounding (§4), date text (§4), v1 error text (AC17), edge tests (AC8, AC9).
- **Builder pre-check of v0.3:** Completeness ✅ (R1–R9, N1–N7 mapped) · Testability ✅ (AC per requirement; 24 of 25 in code, AC21 by the live evaluation) · Conflicts ✅ (no method change; SRG asks only after 12 weeks) · Traceability ✅.

## 13. Change log
| Version | Date | Change | Approved by |
|---|---|---|---|
| 0.1 | 2026-11-22 | First draft from requirements v1.1 and the v1 code | – |
| 0.2 | 2026-11-22 | Independent review fixes (12 findings) | – |
| 0.3 | 2026-11-22 | Trimmed to requirements v1.2 (Aswin's cuts) | – |
| 1.0 | 2026-11-22 | Approved as is, including the §12 proposals | Aswin Guruswamy |
| 1.1 | 2026-11-22 | Keyless demo with a saved AI example; video (requirements v1.3) | Aswin Guruswamy (SH-4.4) |
| 1.2 | 2026-11-23 | R11.1, AC25: 3 README screenshots in place of a video (requirements v1.4) | Aswin Guruswamy (SH-5.5) |
| 1.2.1 | 2026-11-23 | Audit text fixes, no scope change: source path, R1–R11 range, R3.1 wording matches the page, R8.1 note on the required checks, grade count | Claude (admin fix, CLAUDE.md §5) |
