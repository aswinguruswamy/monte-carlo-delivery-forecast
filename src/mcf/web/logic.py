"""The logic of the web page (MCF-24, D01), without Streamlit.

The page uses the same calculation as the CLI (`mcf.cli._compute_full`), so the
page and the CLI always give the same dates. Errors become a WebError with a
clear message: no stack trace, no temporary path. The page shows no issue keys
or file names (RAID C2).
"""

from __future__ import annotations

import argparse
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from mcf.cli import _compute_full, render
from mcf.data.load import LoadError
from mcf.data.types import IssueTypeError
from mcf.explain.check import explain_checked
from mcf.explain.client import Transport, urllib_transport
from mcf.forecast.montecarlo import SEED, MonteCarloError
from mcf.forecast.throughput import ThroughputError
from mcf.forecast.velocity import VelocityError
from mcf.result import ForecastFacts

TRANSPORT: Transport = urllib_transport  # replaced by a fake in tests (NFR8)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # also set in .streamlit/config.toml
SAMPLE_FILE = Path(__file__).resolve().parents[3] / "examples" / "sample_team.csv"
_TMP_NAME = "upload.csv"
_KNOWN = (LoadError, IssueTypeError, ThroughputError, MonteCarloError, VelocityError)
_UNKNOWN = (
    "The file could not be read. Use a UTF-8 CSV file with the columns "
    "Issue_Key, Type, Resolution_Date and Story_Point."
)


class WebError(ValueError):
    """A clear message for the page user."""


@dataclass(frozen=True)
class WebForecast:
    facts: ForecastFacts
    report: str
    finish_days: np.ndarray  # days after day t, one value per simulated run


def sample_bytes() -> bytes | None:
    """The made-up sample file, or None when the package runs without the repository."""
    return SAMPLE_FILE.read_bytes() if SAMPLE_FILE.is_file() else None


def _clean(message: str) -> str:
    for prefix in (f"{_TMP_NAME}, ", f"{_TMP_NAME}: "):
        message = message.replace(prefix, "")
    return message.replace(_TMP_NAME, "the file")


def forecast_from_bytes(
    data: bytes,
    *,
    backlog: int,
    backlog_points: float | None = None,
    as_of: date | None = None,
    seed: int = SEED,
) -> WebForecast:
    if isinstance(backlog, bool) or not isinstance(backlog, int) or backlog < 1:
        raise WebError("The backlog must be a whole number of 1 or more.")
    if backlog_points is not None and not backlog_points > 0:
        raise WebError("The backlog points must be a number above 0.")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise WebError("The seed must be a whole number of 0 or more.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise WebError("The file is larger than 10 MB.")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / _TMP_NAME
        path.write_bytes(data)
        args = argparse.Namespace(
            file=str(path),
            backlog=backlog,
            backlog_points=backlog_points,
            as_of=as_of,
            seed=seed,
            explain=False,
        )
        try:
            facts, _, days = _compute_full(args)
        except _KNOWN as exc:
            raise WebError(f"The file cannot be used: {_clean(str(exc))}") from None
        except Exception:  # never show a stack trace or internal detail on the page
            raise WebError(_UNKNOWN) from None
    return WebForecast(facts=facts, report=render(facts, args), finish_days=days)


def chart_table(result: WebForecast) -> pd.DataFrame:
    """Number of simulated runs that finish on each date."""
    days, runs = np.unique(result.finish_days, return_counts=True)
    t = result.facts.t
    return pd.DataFrame(
        {
            "finish_date": [t + timedelta(days=int(d)) for d in days],
            "runs": runs.astype(int),
        }
    )


def marker_table(facts: ForecastFacts) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "label": ["50%", "85%", "95%", "Velocity"],
            "date": [facts.mc50, facts.mc85, facts.mc95, facts.velocity_date],
        }
    )


def ai_explanation(facts: ForecastFacts) -> tuple[str | None, str | None]:
    """(approved text, None) or (None, a fixed reason). Never raises (NFR5)."""
    return explain_checked(facts, transport=TRANSPORT)
