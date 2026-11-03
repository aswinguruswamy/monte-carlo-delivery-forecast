"""Send the explanation prompt to the Claude Messages API (MCF-21; proposed D32).

No new dependency: HTTP with the standard library. The transport is a plain
function, so tests pass a fake and never call the paid API (NFR8). The API key
comes from ANTHROPIC_API_KEY (or the caller) and never appears in an error.
"""

from __future__ import annotations

import json
import os
import urllib.error
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


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect, so the key header never goes to another URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_OPENER = urllib.request.build_opener(NoRedirect)


def urllib_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with _OPENER.open(request, timeout=timeout) as response:
        return response.read()


def _body(facts: ForecastFacts, model: str | None) -> bytes:
    prompt = build_prompt(facts)
    return json.dumps(
        {
            "model": model or os.environ.get("MCF_MODEL") or DEFAULT_MODEL,
            "max_tokens": MAX_TOKENS,
            "system": prompt["system"],
            "messages": prompt["messages"],
        }
    ).encode()


def _send(
    body: bytes, api_key: str | None, transport: Transport, timeout: float
) -> tuple[bytes | None, str | None]:
    """Return (reply, None) or (None, error text). The key stays in this frame only."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None, "no API key: set ANTHROPIC_API_KEY"
    headers = {
        "x-api-key": key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }
    try:
        return transport(API_URL, headers, body, timeout), None
    except urllib.error.HTTPError as exc:
        return None, f"the API call failed: HTTP {exc.code}"
    except Exception as exc:  # network error or timeout
        return None, f"the API call failed: {type(exc).__name__}"


def _text(raw: bytes) -> tuple[str | None, str | None]:
    try:
        reply = json.loads(raw)
        stop = reply.get("stop_reason")
        blocks = [b for b in reply["content"] if b.get("type") == "text"]
        text = "".join(b["text"] for b in blocks).strip()
    except (ValueError, KeyError, TypeError, AttributeError):
        return None, "the API reply could not be read"
    if stop not in ("end_turn", "stop_sequence"):
        return None, "the reply did not stop normally"
    if not text:
        return None, "the API reply has no text"
    return text, None


def explain(
    facts: ForecastFacts,
    *,
    transport: Transport = urllib_transport,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float = TIMEOUT_SECONDS,
) -> str:
    """Return Claude's explanation, or raise ExplainError (never with the key in it).

    The key comes from ANTHROPIC_API_KEY. The api_key argument is for tests and
    for a caller that already holds the key (D32).
    """
    body = _body(facts, model)
    raw, error = _send(body, api_key, transport, timeout)
    del api_key
    if error is None:
        text, error = _text(raw)
        if error is None:
            return text
    raise ExplainError(error)
