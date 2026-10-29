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

## Get the data

```bash
python -m mcf.data.download --dest data
```

This gets the 29 TAWOS files (47,205 rows) at a fixed commit and checks each file with SHA-256. The data is not stored in this repository (D08). If a file does not match, the script stops.

Copy `.env.example` to `.env` for local secrets. Never commit `.env`.

## Project documents

Confluence space MCF: Charter, Decision Log, RAID Log, Test Plan, Scope, Estimate and Backlog.
