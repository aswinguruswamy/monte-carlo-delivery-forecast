# Monte Carlo Delivery Forecast (MCF)

Forecast when the next N work items will be done, as dates at 50%, 85% and 95% confidence, from a team's past throughput. The tool also gives the usual velocity date, and a back-test on 29 real open-source projects compares the two methods.

**Status:** package version 0.0.1; v1 in development. The MVP (command line and back-test) is complete. The full v1.0.0 release follows the release check (MCF-27).

## Install

Python 3.11 or 3.12.

```bash
git clone https://github.com/aswinguruswamy/monte-carlo-delivery-forecast.git
cd monte-carlo-delivery-forecast
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Use

```bash
mcf forecast team.csv --backlog 40
```

The CSV needs the columns `Issue_Key`, `Type`, `Resolution_Date` and `Story_Point`. An empty `Resolution_Date` means an open item: it is skipped and counted (D25). Options (D28):

- `--backlog N` (required): the number of value items still to do.
- `--as-of YYYY-MM-DD`: day t, the forecast date. Default: the last done day in the file. Items done after day t are not used.
- `--backlog-points P`: story points of the backlog, for the velocity date. Default: an estimate (mean points per value item in the window × N), labelled "estimated".
- `--seed S`: random seed, default 20261028. The same file and seed give the same dates.
- `--explain`: add a short explanation. Claude picks sentences from a PM-approved list that fit this forecast (needs `ANTHROPIC_API_KEY`; model from `MCF_MODEL`, D32, D33.1). The sentences hold no numbers or dates; code writes those. If the reply is not a valid choice, or the call fails, only the plain report shows.

**AI evaluation (MCF-23, D35):** the live evaluation runs only by hand in GitHub Actions: Actions → "AI evaluation (manual)" → Run workflow (on `main`). It uses the repository secret `ANTHROPIC_API_KEY` and calls the paid API. It sends 10 fixed cases (one with an instruction hidden in the file name and issue keys) 3 times each to Claude. **PASS** needs all of these: every answered reply is a valid choice of approved sentences, the shown text has no wrong number or date, the hidden instruction never reaches the prompt, and no API call fails after one retry. If calls fail but nothing else fails, the result is **INCONCLUSIVE**: run it again. The result is in the job summary and the `eval-result` artifact. The tests use fakes only; the script (`python -m mcf.explain.eval`) is not for local live runs (D35).

Run `mcf forecast --help` for details. The output gives the Monte Carlo 50%, 85% and 95% dates and the velocity date. **The 50% date is not certain: half of the runs finish later.**

## Web page

```bash
pip install -e ".[web]"
streamlit run streamlit_app.py
```

Start it from the repository root: the settings in `.streamlit/config.toml` (uploads of 10 MB at most, no usage data sent to Streamlit, no Deploy button) apply only there.

Use the made-up sample file ([examples/sample_team.csv](examples/sample_team.csv), in a repository checkout only) or upload your own CSV (same columns as above). Enter the backlog and see the 50%, 85% and 95% dates, the velocity date, and a chart of the simulated finish dates. The page uses the same code as `mcf forecast`, so the dates are the same. A bad file shows a clear error. The forecast and the report show no issue keys or file names (the upload box shows the name of your own file). The AI explanation needs `ANTHROPIC_API_KEY` on the server. It is off until you turn it on, and the page asks Claude only once for each forecast.

## How it works

- **Monte Carlo:** take the daily count of finished value items in the last 84 days. In one run, pick days from that history at random and add them up until the backlog is done. Do 10,000 runs. The 85% date is the day by which 85% of the runs are done.
- **Velocity (the usual method):** story points done in the last 84 days ÷ 6 two-week periods = points per sprint. Date = backlog points ÷ velocity × 14 days, rounded up to a whole day.
- **Back-test:** go back to many past dates, forecast from the data known on each date, and compare with what really happened.

The full method in plain words is in [docs/method.md](docs/method.md). The exact rules are in [ADR 0002](docs/adr/0002-backtest-method.md), fixed before the first run.

## Results

Back-test of v1 on the TAWOS extract: 29 projects, N = 10, 25 and 50 items, **7,692** scored cases.

| Success measure | Result | Pass rule | Pass or fail |
| --- | --- | --- | --- |
| 1. The 85% date is correct in 75–95% of cases | 69.0% | 75–95% | **FAIL** |
| 2. Median error: Monte Carlo 50% date vs velocity date | 34 days vs 36 days | Monte Carlo smaller | **PASS** |

Measure 1 did not pass: the 85% date was too early in 31.0% of cases. Measure 2 passes, but the lead is small and not robust (the 95% interval of the difference is 0 to 6 days). 903 of 8,595 cases (10.5%) have no forecast because no item was done in their 84-day window. The method was not changed after the results. Full report, with one row for each project: [docs/backtest-report.md](docs/backtest-report.md).

## Limits

- The data holds only issues with story points, and only issues resolved as completed. Teams with many unestimated items may behave differently.
- Every resolved item counts as done on its resolution day, whatever its status. Every Resolution value is a completed value, but some value items have another status: Won't Fix (853), Invalid (335), In Progress (1), Accepted (1).
- Case selection: a forecast date exists only when at least N value items were done after it, so the set of cases uses knowledge of the future (by design).
- When several items were done on the same day as the N-th item, velocity uses the mean points of that day's items (D29).
- Velocity uses 2-week periods counted from day t, not the teams' real sprints.
- In the back-test, velocity uses the real points of the next N items, which a team would not know exactly. This helps velocity.
- The back-test cases overlap (dates 14 days apart share most of their history).
- 29 open-source projects; the result may not hold for other teams.
- Monte Carlo assumes that the past 84 days are a fair sample of the next weeks.

## Data

The back-test uses the TAWOS dataset extract (SOLAR-group/SPvsDevelopmentEffort, `Dataset/RQ2 and RQ3`, commit `e8ae43b`). **The data is subject to the TAWOS terms of use: https://github.com/SOLAR-group/TAWOS.** This repository holds no data files (D08). Get the data with:

```bash
python -m mcf.data.download --dest data
```

This gets the 29 files (47,205 rows) and checks each file with SHA-256. If a file does not match, the script stops. **Do not try to trace issues back to individual contributors.** The tool loads no names or titles, and only summary numbers are published.

Re-run the back-test (about 7 minutes, measured on 2026-10-29: two runs of 406 s and 429 s):

```bash
python -m mcf.backtest --data data --out results
python -m mcf.backtest.metrics --cases results/cases.csv --projects results/projects.csv --out results/metrics.json
python -m mcf.backtest.report --results results --commit <commit> --out docs/backtest-report.md
```

## Cite

See [CITATION.cff](CITATION.cff). If you use the data, cite:

- Tawosi, Al-Subaihin, Moussa, Sarro. *A Versatile Dataset of Agile Open Source Software Projects.* MSR 2022. https://doi.org/10.1145/3524842.3528029
- Tawosi, Moussa, Sarro. *On the Relationship Between Story Points and Development Effort in Agile Open-Source Software.* ESEM 2022. https://doi.org/10.1145/3544902.3546238

## Handover

- **Rules for changes:** [CLAUDE.md](CLAUDE.md) (method before results, tests first, no data files, AI explanation rules).
- **Decisions and risks:** Confluence space MCF (Decision Log, RAID Log, Test Plan). Each decision has an ID (Dxx); a changed decision keeps the old row, struck through (D14).
- **Quality:** CI runs style, tests on Python 3.11 and 3.12, a secret scan, a dependency scan and a licence scan on each pull request. Grades per ticket: `quality/grades.md`.
- **To change the back-test method:** write a new decision and a before-and-after report first (ADR 0002 Change rule). A test locks the ADR text.
- Copy `.env.example` to `.env` for local secrets. Never commit `.env`.

## Licence

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
