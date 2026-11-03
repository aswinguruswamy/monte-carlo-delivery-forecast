"""Check the AI text before anyone sees it (MCF-22, D33; R4, NFR4, NFR5; CLAUDE.md AI rules).

D33: the AI text must hold no number or date at all; code writes them in the
report. The check fails closed: any of these drops the whole AI text, and only
the plain report is shown.

- a character outside plain ASCII (apart from a few quote marks and dashes), or
  a control character;
- a digit, apart from the labels 50%, 85% and 95%;
- a month or weekday name, a relative date, or a number word;
- a certainty word (only "not certain", "no guarantee" and similar negations at
  the end of a clause are allowed), or the word "velocity".
"""

from __future__ import annotations

import re

from mcf.explain.client import ExplainError, Transport, explain, urllib_transport
from mcf.result import ForecastFacts

REASON_NUMBER = "a number or date in it is not in the result"
REASON_CERTAIN = "it describes a date as certain"
REASON_TEXT = "it holds text that cannot be checked"

_ALLOWED_CHARS = re.compile(r"[\x20-\x7e\n‘’“”–—]*")
_LABEL = re.compile(r"(?<![\w.,%-])(50|85|95)%(?![\w.,%])")
_DIGIT = re.compile(r"\d")
_WORDS = re.compile(
    r"\b("
    # months and weekdays
    r"january|february|march|april|may|june|july|august|september|october|november|"
    r"december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday|weekend|"
    # relative dates
    r"today|tomorrow|yesterday|tonight|fortnight|(next|last|this|coming)\s+(week|month|year|"
    r"sprint|quarter)|a\s+(day|week|month|year)\s+(before|after|later|earlier)|"
    # number words
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundred|thousand|million|billion|dozen|half|quarter|twice|double|"
    r"triple|first|second|third|fourth|fifth|tenth|percent|percentile"
    r")\b",
    re.I,
)
_HALF_OF_RUNS = re.compile(r"\bhalf of the (simulated )?runs\b", re.I)
_NEGATED = re.compile(
    r"\b(not|no)\s+(a\s+|an\s+)?(certain|guarantee[ds]?|promise|commitment)(?=\s*[.,;:!)]|\s*$)",
    re.I,
)
_CERTAIN = re.compile(
    r"\b(will|won'?t|shall|going\s+to|certain\w*|uncertain\w*|guarantee\w*|definite\w*|"
    r"for\s+sure|sure|assur\w*|no\s+doubt|count\s+on|promis\w*|lock\w*|set\s+in\s+stone|"
    r"bank\s+on|firm|inevitabl\w*|fail\w*|safe\s+bet|given|on\s+track|deliver\w*|ship\w*|"
    r"expect\w*|commit|commits|committed|velocity)\b",
    re.I,
)


def check_text(text: str, facts: ForecastFacts) -> list[str]:
    """Return the problems as fixed reasons; an empty list means the text may be shown.

    `facts` is not used: the AI text must not hold any result value (D33).
    """
    if not text.strip() or not _ALLOWED_CHARS.fullmatch(text):
        return [REASON_TEXT]
    problems: list[str] = []
    rest = _LABEL.sub(" ", text)
    if _DIGIT.search(rest) or _WORDS.search(_HALF_OF_RUNS.sub(" ", rest)):
        problems.append(REASON_NUMBER)
    if _CERTAIN.search(_NEGATED.sub(" ", text)):
        problems.append(REASON_CERTAIN)
    return problems


def explain_checked(
    facts: ForecastFacts,
    *,
    transport: Transport = urllib_transport,
    api_key: str | None = None,
    model: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (checked AI text, None), or (None, a fixed reason that never quotes the text)."""
    try:
        text = explain(facts, transport=transport, api_key=api_key, model=model)
    except ExplainError as exc:
        return None, str(exc)
    problems = check_text(text, facts)
    if problems:
        return None, problems[0]
    return text, None
