"""Check the AI text before anyone sees it (MCF-22; R4, NFR4, NFR5; CLAUDE.md AI rules).

Every date in the text must be one of the result's dates. Every other number
must be a result value or a fixed method number. A sentence about the 50% date
must not sound certain. Any problem drops the whole AI text; the plain report
is always shown.
"""

from __future__ import annotations

import re
from dataclasses import fields
from datetime import date

from mcf.explain.client import ExplainError, Transport, explain, urllib_transport
from mcf.result import ForecastFacts

# Numbers that belong to the method, not to one result: the percentiles, the
# 84-day window, 6 periods of 2 weeks (14 days).
METHOD_NUMBERS = {50.0, 85.0, 95.0, 84.0, 6.0, 2.0, 14.0}

_MONTHS = {
    name: i
    for i, names in enumerate(
        [
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sept", "sep"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        ],
        start=1,
    )
    for name in names
}
_MONTH = "(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"
_DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), ("y", "m", "d")),
    (
        re.compile(rf"\b{_MONTH}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b", re.I),
        ("M", "d", "y"),
    ),
    (
        re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MONTH}(?:,?\s+(\d{{4}}))?\b", re.I),
        ("d", "M", "y"),
    ),
]
_NUMBER = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")
_SENTENCE = re.compile(r"(?<=[.!?;])\s+")
_CERTAIN = re.compile(
    r"\b(will|certain|certainly|guarantee[sd]?|definitely|for sure|sure to)\b", re.I
)
_NEGATED = re.compile(
    r"\b(not|no|never)\s+(a\s+)?(certain|certainty|guarantee[sd]?|definite|sure)\b", re.I
)
_FIFTY = re.compile(r"\b50\s?%|\bmedian\b", re.I)


def _fact_dates(facts: ForecastFacts) -> set[date]:
    return {getattr(facts, f.name) for f in fields(facts) if type(getattr(facts, f.name)) is date}


def _fact_numbers(facts: ForecastFacts) -> set[float]:
    out = set(METHOD_NUMBERS)
    for f in fields(facts):
        v = getattr(facts, f.name)
        if type(v) in (int, float):
            out.add(float(v))
    return out


def _find_dates(text: str) -> tuple[list[tuple[int | None, int, int, str]], str]:
    """Return the dates found (year may be None) and the text with them blanked out."""
    found = []
    for pattern, order in _DATE_PATTERNS:

        def take(m: re.Match, order=order) -> str:
            parts = dict(zip(order, m.groups(), strict=True))
            month = _MONTHS[parts["M"].lower()] if "M" in parts else int(parts["m"])
            year = int(parts["y"]) if parts.get("y") else None
            found.append((year, month, int(parts["d"]), m.group(0)))
            return " " * len(m.group(0))

        text = pattern.sub(take, text)
    return found, text


def _date_ok(year: int | None, month: int, day: int, allowed: set[date]) -> bool:
    return any(
        d.month == month and d.day == day and (year is None or d.year == year) for d in allowed
    )


def check_text(text: str, facts: ForecastFacts) -> list[str]:
    """Return the problems in the AI text; an empty list means it may be shown."""
    if not text.strip():
        return ["the AI text is empty"]
    problems: list[str] = []
    allowed_dates = _fact_dates(facts)
    dates, rest = _find_dates(text)
    for year, month, day, raw in dates:
        if not _date_ok(year, month, day, allowed_dates):
            problems.append(f"date {raw!r} is not in the result")
    allowed_numbers = _fact_numbers(facts)
    for raw in _NUMBER.findall(rest):
        if float(raw.replace(",", "")) not in allowed_numbers:
            problems.append(f"number {raw} is not in the result")

    mc50 = facts.mc50
    for number, sentence in enumerate(_SENTENCE.split(text), start=1):
        sentence_dates, _ = _find_dates(sentence)
        about_50 = _FIFTY.search(sentence) or any(
            _date_ok(y, m, d, {mc50}) and not _date_ok(y, m, d, {facts.mc85, facts.mc95})
            for y, m, d, _ in sentence_dates
        )
        if about_50 and _CERTAIN.search(_NEGATED.sub(" ", sentence)):
            problems.append(f"sentence {number} describes the 50% date as certain")
    return problems


def explain_checked(
    facts: ForecastFacts,
    *,
    transport: Transport = urllib_transport,
    api_key: str | None = None,
    model: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (checked AI text, None), or (None, the reason the AI text is not shown)."""
    try:
        text = explain(facts, transport=transport, api_key=api_key, model=model)
    except ExplainError as exc:
        return None, str(exc)
    problems = check_text(text, facts)
    if problems:
        return None, problems[0]
    return text, None
