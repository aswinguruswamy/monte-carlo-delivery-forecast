# Monte Carlo Delivery Forecast (MCF)

Forecast delivery dates at 50%, 85% and 95% confidence from a team's past throughput, and prove the accuracy with a back-test on real public data.

**Status:** in development (MVP). The full README comes in MCF-25.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

## Forecast from your own CSV

```bash
mcf forecast team.csv --backlog 40
```

The CSV needs the columns `Issue_Key`, `Type`, `Resolution_Date` and `Story_Point`. An empty `Resolution_Date` means an open item: it is skipped and counted (D25). Options (D28): `--as-of YYYY-MM-DD` (day t, default: the last done day in the file; items done after it are not used), `--backlog-points P` (for the velocity date; default: an estimate), `--seed S`. Run `mcf forecast --help` for details. The 50% date is not certain: half of the runs finish later.

## Get the data

```bash
python -m mcf.data.download --dest data
```

This gets the 29 TAWOS files (47,205 rows) at a fixed commit and checks each file with SHA-256. The data is not stored in this repository (D08). If a file does not match, the script stops.

Copy `.env.example` to `.env` for local secrets. Never commit `.env`.

## Project documents

Confluence space MCF: Charter, Decision Log, RAID Log, Test Plan, Scope, Estimate and Backlog.
