"""Check Claude's reply before anyone sees it (MCF-22; D33.1; R4, NFR4, NFR5).

Claude must reply with JSON that holds only sentence IDs. The check is closed:
the reply must be exactly {"sentences": [ids]}, with 3 to 6 different IDs that
exist and apply to this forecast, and the mandatory "50% date is not certain"
sentence first. Code then prints the PM-approved text of those sentences. Any
other reply drops the AI text, and only the plain report shows.
"""

from __future__ import annotations

import json

from mcf.explain.bank import BANK, MANDATORY, applicable_ids
from mcf.explain.client import ExplainError, Transport, explain, urllib_transport
from mcf.explain.prompt import MAX_SENTENCES, MIN_SENTENCES
from mcf.result import ForecastFacts

REASON_TEXT = "the reply was not a valid choice of approved sentences"


def parse_selection(reply: str, facts: ForecastFacts) -> tuple[str | None, str | None]:
    """Return (rendered text, None), or (None, a fixed reason)."""
    try:
        data = json.loads(reply)
    except (ValueError, TypeError):
        return None, REASON_TEXT
    if not isinstance(data, dict) or set(data) != {"sentences"}:
        return None, REASON_TEXT
    ids = data["sentences"]
    allowed = set(applicable_ids(facts))
    if (
        not isinstance(ids, list)
        or not all(isinstance(i, str) for i in ids)
        or not MIN_SENTENCES <= len(ids) <= MAX_SENTENCES
        or len(set(ids)) != len(ids)
        or ids[0] != MANDATORY
        or not set(ids) <= allowed
    ):
        return None, REASON_TEXT
    return " ".join(BANK[i] for i in ids), None


def explain_checked(
    facts: ForecastFacts,
    *,
    transport: Transport = urllib_transport,
    api_key: str | None = None,
    model: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (approved text, None), or (None, a fixed reason that never quotes the reply)."""
    try:
        reply = explain(facts, transport=transport, api_key=api_key, model=model)
    except ExplainError as exc:
        return None, str(exc)
    return parse_selection(reply.strip(), facts)
