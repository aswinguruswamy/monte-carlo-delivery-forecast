"""The model and prompt version of an AI explanation (MCF v2 spec R4.1, shared item SH2).

Shown below every AI explanation, on the page and in the command line.
"""

from __future__ import annotations

import os

from mcf.explain.client import DEFAULT_MODEL
from mcf.explain.prompt import PROMPT_VERSION


def ai_run_line() -> str:
    model = os.environ.get("MCF_MODEL") or DEFAULT_MODEL  # the same rule as the client
    return f"AI: {model} · prompt v{PROMPT_VERSION}"
