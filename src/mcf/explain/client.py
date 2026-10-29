"""Send the explanation prompt to the Claude Messages API (MCF-21; proposed D32).

No new dependency: HTTP with the standard library. The transport is a plain
function, so tests pass a fake and never call the paid API (NFR8). The API key
comes from ANTHROPIC_API_KEY (or the caller) and never appears in an error.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable

from mcf.explain.prompt import build_prompt
from mcf.result import ForecastFacts

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-haiku-5-5"
MAX_TOKENS = 400
TIMEOUT_SECONDS = 30.0

Transport = Callable[[str, dict[str, str], bytes, float], bytes]


class ExplainError(RuntimeError):
    """No explanation could be made. The caller shows the plain report (NFR5)."""


def urllib_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def explain(
    facts: ForecastFacts,
    *,
    transport: Transport = urllib_transport,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float = TIMEOUT_SECONDS,
) -> str:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ExplainError("no API key: set ANTHROPIC_API_KEY")
    prompt = build_prompt(facts)
    body = json.dumps(
        {
            "model": model or os.environ.get("MCF_MODEL") or DEFAULT_MODEL,
            "max_tokens": MAX_TOKENS,
            "system": prompt["system"],
            "messages": prompt["messages"],
        }
    ).encode()
    headers = {
        "x-api-key": key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }
    try:
        raw = transport(API_URL, headers, body, timeout)
    except Exception as exc:  # network, HTTP or timeout error
        raise ExplainError(f"the API call failed: {type(exc).__name__}") from None
    try:
        reply = json.loads(raw)
        blocks = [b for b in reply["content"] if b.get("type") == "text"]
        text = "".join(b["text"] for b in blocks).strip()
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ExplainError("the API reply could not be read") from None
    if not text:
        raise ExplainError("the API reply has no text")
    return text
