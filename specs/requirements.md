# MCF v2 – Requirements

Version 1.3 · 2026-11-22 · Status: **APPROVED by Aswin Guruswamy, 2026-11-22** (v1.2 trims, v1.3 demo decision – all his, same day)
Note: the MCF benefits check on Dec 3, 2026 may add input.

---

## 1. What MCF v2 is

A free tool that answers **"When will it be done?"** from the team's real pace, not from a guess.
Give it your finished tickets (a Jira CSV export) and the number of tickets left. It gives three dates: 50%, 85% and 95% sure.
v2 adds one answer: **"Will we make the charter date?"** It warns you when the history is too thin to trust, and it gives SRG its finish dates.

**Pick one line for the README and the demo** (or write your own):
1. "Will we make the charter date? A free forecast that proves its own accuracy."
2. "When will it be done – with odds, not a guess."
3. "The free Monte Carlo forecast that tells you when not to trust it."

## 2. Who uses it, and the problem

**User:** a PM who must give a finish date, often with no budget for a paid Jira app.

**Problem:** most teams give one date from average velocity. That date is a guess with no odds. Paid Monte Carlo tools show a chart that does not explain itself, and none proves its own accuracy.

## 3. How a PM uses it

1. **Upload** a Jira CSV export of finished tickets (or use the sample file).
2. **Enter** the number of tickets left.
3. **Read the dates:** 50%, 85% and 95%, plus the usual velocity date for comparison.
4. **Enter the charter date** (optional). See the chance to finish by then, for example **"62% chance to finish by 15 Dec"**.
5. **Check the warning**, if any: "Only 12 tickets finished in the last 12 weeks – treat the dates with care."

## 4. What changes from v1

| | v1 (today) | v2 |
|---|---|---|
| Finish dates 50 / 85 / 95% | ✅ | ✅ same |
| Velocity date for comparison | ✅ | ✅ same |
| AI explanation from approved sentences | ✅ | ✅ same, plus model and prompt version shown |
| Chance to finish by a charter date | ❌ | **New** |
| Warning for too little history | ❌ | **New** |
| Accuracy shown in the app | First test only (29 projects) | **Updated:** latest test (39 projects) too |
| Finish dates for SRG | ❌ | **New** (SRG calls MCF code) |
| AI test | By hand | **Automatic** on each AI change |

## 5. Benefits

| For | Benefit |
|---|---|
| The PM | Answer **"will we make the charter date?"** with a number, not a feeling. |
| The PM | Know **when not to trust** the forecast, before the boss finds out. |
| The boss | Odds (50 / 85 / 95%) in place of one date that is always late. |
| SRG users | A finish date and a planned date beside each team. |
| Recruiters | A tool that **publishes its own accuracy** on 39 real projects, and shows PM thinking: odds, charter dates, data quality. |

## 6. What it does (functional requirements)

M = Must, S = Should.

| # | Requirement | Priority |
|---|---|---|
| R1 | Enter a charter (planned) date. Show the chance (%) to finish the remaining tickets by that date. | M |
| R2 | Warn when fewer than 30 tickets were finished in the last 12 weeks. | M |
| R3 | Show the latest accuracy result in the app (39 projects) beside the first one (29 projects). | S |
| R4 | Show the model and prompt version below the AI explanation. | M |
| R5 | Move "Known limits" to the top of the README. Add: teams with less than 12 weeks of history get dates that are too late. | M |
| R6 | Give SRG one stable function: daily finished-ticket counts + tickets left + seed → 50 / 85 / 95% dates, chance by a date, and the warning. Same results as the app for the same input. | M |
| R7 | Keep the existing automatic tests, and add tests for the new parts (chance, warning, SRG function). | M |
| R8 | Run the AI test automatically on each change to the prompt, the sentence list or the model. | M |
| R9 | Rule: before any future change to the forecast method, re-run the accuracy test on the 39 projects and publish before and after. | M |
| R10 | The public demo runs without an AI key: it shows a saved example of the AI explanation, labelled as a saved example. | M |
| R11 | Record a short video (2 minutes or less) of the v2 features; link it in the README and the portfolio. | M |

## 7. How well it must work (non-functional requirements)

| # | Area | Requirement |
|---|---|---|
| N1 | Same result | The same file, inputs and seed always give the same dates and %. |
| N2 | Speed | A forecast (10,000 runs) shows in under 3 seconds. |
| N3 | Honesty | The warning shows on the page, in the output and in the SRG result. The 50% date always says "half of the runs finish later". |
| N4 | Accuracy | v2 does not change the forecast method, so the published result (85% date right in 75.0% of cases, 39 projects) stays valid. |
| N5 | Privacy | MCF reads only 4 columns (key, type, resolved date, points). No names or titles. Code writes every number; the AI only picks approved sentences. |
| N6 | Cost | Free public demo. An AI explanation costs less than US$0.01. The automatic AI test costs less than US$0.50. |
| N7 | Plain language | Screens, warnings and errors use simple English. |

## 8. Not in v2 (later, if MCF becomes popular)

- "How many tickets by a date" (fixed date, flexible scope).
- Warnings for gaps (no tickets finished for 2+ weeks) and for a sudden change in pace.
- A special rule for teams younger than 12 weeks (needs a method change and a new accuracy test).
- Live Jira connection (CSV stays; SRG already reads Jira and passes the data).
- Several teams in one view (SRG does this).
- Visitors use their own AI key; a log of past forecasts; velocity from real sprints; other tools.

## 9. Sign-off

| | |
|---|---|
| Comments | v1.0: none. v1.2: trims below. |
| Decision | ☑ Approved ☐ Approved with changes ☐ Rejected |
| Signed | Aswin Guruswamy · 2026-11-22 (in chat) |
| Note | Positioning line not picked yet. |

## Change log
| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-11-22 | First draft, from the MCF analysis, the v1 README (v1.2.0), the v1 code and the SRG decisions |
| 1.0 | 2026-11-22 | Approved as is by Aswin. |
| 1.1 | 2026-11-22 | Fact fix: the v1 app already shows the 29-project test; R4 adds the 39-project result. |
| 1.2 | 2026-11-22 | Aswin's trims: cut "how many by a date", gap and pace warnings, young-team rule, accuracy test at every release (now: only before a method change). 11 → 9 requirements, all small. Requirements renumbered. |
| 1.3 | 2026-11-22 | Aswin: AI key only for the build (GitHub secret); public demo keyless with a saved AI example; a recorded video. R10, R11 added. |
