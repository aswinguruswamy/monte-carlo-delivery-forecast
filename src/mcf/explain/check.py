"""Check the AI text before anyone sees it (MCF-22; R4, NFR4, NFR5; CLAUDE.md AI rules).

The check fails closed: when in doubt, the AI text is dropped and only the
plain report is shown.

- Every date must be a result date. A Monte Carlo date next to "N% date" (or
  "median") must be the N% date, so swapped percentiles fail.
- Every other number, in digits, must be a result value, or a method number in
  its place (50/85/95 with %, 84 days, 6 sprints, 2 weeks, 14 days).
- Number words, fractions, signs, relative dates and weekday names fail.
- Certainty words fail anywhere in the text (only "not certain", "no
  guarantee" and similar negations are allowed).
- Control and direction characters fail.
"""

from __future__ import annotations

import re
from dataclasses import fields
from datetime import date

from mcf.explain.client import ExplainError, Transport, explain, urllib_transport
from mcf.result import ForecastFacts

REASON_NUMBER = "a number or date in it is not in the result"
REASON_CERTAIN = "it describes a date as certain"
REASON_TEXT = "it holds text that cannot be checked"

# Method numbers and the words that must follow them.
METHOD_CONTEXT = {
    50.0: r"(%|\s?percent|th\b)",
    85.0: r"(%|\s?percent|th\b)",
    95.0: r"(%|\s?percent|th\b)",
    84.0: r"[\s-]?days?\b",
    14.0: r"[\s-]?days?\b",
    6.0: r"\s(two-week\s|2-week\s)?(sprints?|periods?)\b",
    2.0: r"[\s-]?weeks?\b",
}

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
_ORD = r"(?:st|nd|rd|th)?"
_DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), ("y", "m", "d")),
    (
        re.compile(rf"\b(\d{{1,2}}){_ORD}\s+of\s+{_MONTH}(?:,?\s+(\d{{4}}))?\b", re.I),
        ("d", "M", "y"),
    ),
    (re.compile(rf"\b{_MONTH}\s+(\d{{1,2}}){_ORD}(?:,?\s+(\d{{4}}))?\b", re.I), ("M", "d", "y")),
    (re.compile(rf"\b(\d{{1,2}}){_ORD}\s+{_MONTH}(?:,?\s+(\d{{4}}))?\b", re.I), ("d", "M", "y")),
]
_NUMBER = re.compile(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")
_SIGNED = re.compile(r"(?<![\w])[-+−]\s?\d")
_FRACTION = re.compile(r"\d\s*/\s*\d")
_NUMBER_WORDS = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundred|thousand|million|dozen|half|quarter|twice|double|triple|first|"
    r"second|third|fourth|fifth|tenth)\b",
    re.I,
)
_HALF_OF_RUNS = re.compile(r"\bhalf of the (simulated )?runs\b", re.I)
_RELATIVE = re.compile(
    r"\b(today|tomorrow|yesterday|tonight|weekend|monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|(next|last|this|coming)\s+(week|month|year|sprint|quarter))\b",
    re.I,
)
_DOUBLE_NEGATIVE = re.compile(r"\bnot\s+(un\w+|im\w+)", re.I)
_NEGATED = re.compile(
    r"\b(not\s+(a\s+|an\s+)?(certain|certainty|guarantee[ds]?|promise|sure)|"
    r"no\s+(guarantee|promise|certainty))\b",
    re.I,
)
_CERTAIN = re.compile(
    r"\b(will|won'?t|shall|going to|certain(ly)?|guarantee[ds]?|definite(ly)?|for sure|sure|"
    r"assure[ds]?|no doubt|count on|promise[ds]?|lock|expect(s|ed)?|commit(s|ted)?)\b",
    re.I,
)
_PERCENTILE = re.compile(r"\b(50|85|95)\s*(?:%|-?\s?percent|th\b)|\b(median)\b", re.I)
_SENTENCE = re.compile(r"(?<=[.!?;:])\s+|\n+")
_BAD_CHARS = re.compile(r"[\x00-\x09\x0b-\x1f\x7f​-‏‪-‮⁦-⁩]")


def _fact_dates(facts: ForecastFacts) -> set[date]:
    return {getattr(facts, f.name) for f in fields(facts) if type(getattr(facts, f.name)) is date}


def _fact_numbers(facts: ForecastFacts) -> set[float]:
    return {
        float(getattr(facts, f.name))
        for f in fields(facts)
        if type(getattr(facts, f.name)) in (int, float)
    }


def _find_dates(text: str) -> tuple[list[tuple[int | None, int, int, int]], str]:
    """Return (year or None, month, day, position) for each date, and the text without them."""
    found = []
    for pattern, order in _DATE_PATTERNS:

        def take(m: re.Match, order=order) -> str:
            parts = dict(zip(order, m.groups(), strict=True))
            month = _MONTHS[parts["M"].lower()] if "M" in parts else int(parts["m"])
            year = int(parts["y"]) if parts.get("y") else None
            found.append((year, month, int(parts["d"]), m.start()))
            return " " * len(m.group(0))

        text = pattern.sub(take, text)
    return found, text


def _matches(year: int | None, month: int, day: int, d: date) -> bool:
    return d.month == month and d.day == day and (year is None or d.year == year)


def check_text(text: str, facts: ForecastFacts) -> list[str]:
    """Return the problems in the AI text; an empty list means it may be shown."""
    if not text.strip():
        return ["text: the AI text is empty"]
    problems: list[str] = []
    if _BAD_CHARS.search(text):
        problems.append("text: control or direction characters")

    # Dates: each must be a result date; Monte Carlo dates must match their percentile.
    allowed_dates = _fact_dates(facts)
    mc = {"50": facts.mc50, "85": facts.mc85, "95": facts.mc95, "median": facts.mc50}
    for sentence in _SENTENCE.split(text):
        dates, _ = _find_dates(sentence)
        marks = [
            (m.start(), (m.group(1) or m.group(2)).lower()) for m in _PERCENTILE.finditer(sentence)
        ]
        for year, month, day, pos in dates:
            if not any(_matches(year, month, day, d) for d in allowed_dates):
                problems.append(f"date: {month:02d}-{day:02d} is not in the result")
                continue
            is_mc = any(_matches(year, month, day, d) for d in mc.values())
            if not is_mc or not marks:
                continue
            before = [m for m in marks if m[0] < pos]
            label = (before[-1] if before else min(marks, key=lambda m: m[0] - pos))[1]
            if not _matches(year, month, day, mc[label]):
                problems.append(f"date: a date does not belong to the {label} label")

    # Numbers in digits.
    _, rest = _find_dates(text)
    allowed = _fact_numbers(facts)
    for m in _NUMBER.finditer(rest):
        value = float(m.group(1).replace(",", ""))
        if value in allowed:
            continue
        context = METHOD_CONTEXT.get(value)
        if context and re.match(context, rest[m.end() :], re.I):
            continue
        problems.append("number: a number is not in the result")
    if _SIGNED.search(rest) or _FRACTION.search(rest):
        problems.append("number: a signed number or a fraction")
    if _NUMBER_WORDS.search(_HALF_OF_RUNS.sub(" ", text)):
        problems.append("number: a number written as a word")
    if _RELATIVE.search(text):
        problems.append("date: a relative date or a weekday")

    # Certainty: fail closed on the whole text.
    plain = _NEGATED.sub(" ", _DOUBLE_NEGATIVE.sub(" certain ", text))
    if _CERTAIN.search(plain):
        problems.append("certain: the text uses a certainty word")
    return problems


def _reason(problem: str) -> str:
    kind = problem.split(":", 1)[0]
    return {"certain": REASON_CERTAIN, "text": REASON_TEXT}.get(kind, REASON_NUMBER)


def explain_checked(
    facts: ForecastFacts,
    *,
    transport: Transport = urllib_transport,
    api_key: str | None = None,
    model: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (checked AI text, None), or (None, a fixed reason).

    The reason never quotes the AI text, so a dropped wrong date is never shown.
    """
    try:
        text = explain(facts, transport=transport, api_key=api_key, model=model)
    except ExplainError as exc:
        return None, str(exc)
    problems = check_text(text, facts)
    if problems:
        return None, _reason(problems[0])
    return text, None
