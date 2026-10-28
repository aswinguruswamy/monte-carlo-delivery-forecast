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

Copy `.env.example` to `.env` for local secrets. Never commit `.env`.

## Project documents

Confluence space MCF: Charter, Decision Log, RAID Log, Test Plan, Scope, Estimate and Backlog.
