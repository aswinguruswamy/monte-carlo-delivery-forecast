"""The logic of the web page (MCF-24, D01), without Streamlit.

The page uses the same calculation as the CLI (`mcf.cli.compute_full`), so the
page and the CLI always give the same dates. Errors become a WebError with a
clear message: no stack trace, no temporary path. The page shows no issue keys
or file names (RAID C2).
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import logging
import re
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from mcf import __version__
from mcf.cli import compute_full, render
from mcf.data.load import LoadError, column_indexes
from mcf.data.types import IssueTypeError
from mcf.explain.check import explain_checked
from mcf.explain.client import Transport, urllib_transport
from mcf.forecast.montecarlo import RUNS, SEED, MonteCarloError
from mcf.forecast.throughput import WINDOW_DAYS, ThroughputError
from mcf.forecast.velocity import VelocityError
from mcf.result import ForecastFacts
from mcf.web.backtest_facts import BACKTEST

TRANSPORT: Transport = urllib_transport  # replaced by a fake in tests (NFR8)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # also set in .streamlit/config.toml
SAMPLE_FILE = Path(__file__).resolve().parents[3] / "examples" / "sample_team.csv"
_TMP_NAME = "upload.csv"
_KNOWN = (LoadError, IssueTypeError, ThroughputError, MonteCarloError, VelocityError)
_UNKNOWN = (
    "The file could not be read. Use a UTF-8 CSV file with the columns "
    "Issue_Key, Type and Resolution_Date (Story_Point is optional), or a Jira export."
)


_LOG = logging.getLogger(__name__)
_OUT_OF_RANGE = "The file cannot be used: a date is too early or too late to forecast from."
# CLI words that mean nothing on the page -> page words
_PAGE_WORDS = (
    ("use another --as-of", "choose another forecast date"),
    ("Use --as-of ", "Choose a forecast date of "),
    (
        "Add it to D04 with a new decision, or fix the data.",
        "Use a known issue type (for example Story, Task, Bug), or fix the data.",
    ),
)
_NOT_UTF8 = re.compile(r"not UTF-8 text: .*")
_MARKDOWN = re.compile(r"([\\`*_{}\[\]()<>#+!|~])")


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


def plain(text: str) -> str:
    """Escape Markdown, so text from the file shows as plain text on the page."""
    return _MARKDOWN.sub(r"\\\1", text)


def _keys(data: bytes) -> set[str]:
    """The issue keys in the file (best effort), to keep them out of messages (RAID C2)."""
    try:
        rows = csv.reader(io.StringIO(data.decode("utf-8-sig", errors="replace")))
        header = next(rows, [])
        col = column_indexes(header, user_file=True)["Issue_Key"][0]
        return {r[col] for r in rows if len(r) > col and r[col].strip()}
    except (ValueError, csv.Error):
        return set()


def _clean(message: str, keys: set[str]) -> str:
    for prefix in (f"{_TMP_NAME}, ", f"{_TMP_NAME}: "):
        message = message.replace(prefix, "")
    message = message.replace(_TMP_NAME, "the file")
    for cli, page in _PAGE_WORDS:
        message = message.replace(cli, page)
    message = _NOT_UTF8.sub("the file is not UTF-8 text. Save the file as CSV UTF-8.", message)
    for key in sorted(keys, key=len, reverse=True):
        message = message.replace(key, "an item")
    return message


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
            facts, _, days = compute_full(args)
        except _KNOWN as exc:
            message = _clean(str(exc), _keys(data))
            raise WebError(f"The file cannot be used: {message}") from None
        except OverflowError:
            _LOG.exception("date out of range")
            raise WebError(_OUT_OF_RANGE) from None
        except Exception:  # never show a stack trace or internal detail on the page
            _LOG.exception("unexpected error in the forecast")  # server log only
            raise WebError(_UNKNOWN) from None
    return WebForecast(facts=facts, report=render(facts, args), finish_days=days)


def _last_day(result: WebForecast) -> int:
    """The largest number of days after day t that is still a calendar date."""
    return (date.max - result.facts.t).days


def runs_not_drawn(result: WebForecast) -> int:
    """Runs that end after 9999-12-31: the chart leaves them out (MCF-30)."""
    return int((result.finish_days > _last_day(result)).sum())


def chart_table(result: WebForecast) -> pd.DataFrame:
    """Number of simulated runs that finish on each date (up to 9999-12-31)."""
    finish = result.finish_days[result.finish_days <= _last_day(result)]
    days, runs = np.unique(finish, return_counts=True)
    t = result.facts.t
    return pd.DataFrame(
        {
            "finish_date": [t + timedelta(days=int(d)) for d in days],
            "runs": runs.astype(int),
        }
    )


def marker_table(facts: ForecastFacts) -> pd.DataFrame:
    """The chart lines, in the card colours (MCF-33). No velocity line without a date (MCF-32).

    MCF-37: when the velocity date is the 50% date, the 2 lines sit side by side
    (`offset` in px), so both show.
    """
    same = facts.velocity_date is not None and facts.velocity_date == facts.mc50
    marks = [
        ("50% chance", facts.mc50, COLORS["p50"], -3 if same else 0),
        ("85% chance", facts.mc85, COLORS["p85"], 0),
        ("95% chance", facts.mc95, COLORS["p95"], 0),
    ]
    if facts.velocity_date is not None:
        marks.append(("Velocity", facts.velocity_date, COLORS["velocity"], 3 if same else 0))
    return pd.DataFrame(marks, columns=["label", "date", "color", "offset"])


# --- MCF-33 (D41): plain-language page text ------------------------------------------------

# Text colours on white; each has 4.5:1 contrast or more (WCAG AA, tested).
COLORS = {
    "p50": "#2f6db5",
    "p85": "#9a5a0c",
    "p95": "#b8322f",
    "velocity": "#1a7f37",
    "muted": "#5f6370",
    "ink": "#31333f",
}
MAX_BACKLOG = 10_000
BACKLOG_ERROR = "Type a whole number from 1 to 10,000."
BACKLOG_HELP = "Type any whole number from 1 to 10,000."
INTRO = (
    "Upload your team's finished work items, or try the sample file. See the dates with "
    "a 50%, 85% and 95% chance of completion, from your team's real pace (throughput)."
)
NOT_CERTAIN = "The 50% date is not certain: half of the time the work finishes later."
CHART_CAPTION = (
    "Each bar: how often the work finished on that day in {runs:,} tries "
    '(Monte Carlo simulation, see "How this forecast works").'
)
SAMPLE_LABEL = "Sample file (example team, not real data)"
REPORT_LABEL = "Full report (technical)"
REPORT_DESCRIPTION = "The same forecast as plain text, as the command line prints it."
# MCF-35: a plain explanation under each option in "More options".
OPTION_HELP = {
    "backlog_points": "For the velocity date. Off: the tool estimates them.",
    "as_of": "Empty: the day the last item in your file was finished.",
    "seed": "Use the same number to get the same dates again.",
}
PHONE_HELP = "Help: tap » at the top left."
SIDEBAR = """\
### How to use this page

#### You need
A CSV file of your team's work items. A Jira export works with no changes.

To export from Jira: Filters › Export › CSV (all fields). The tool skips open items. \
The file can be up to 10 MB.

#### Steps
1. Choose the sample file (an example team) or upload your file.
2. Enter how many work items are left (backlog). Do not count bugs or epics.
3. Read the dates in the result.
4. Copy the message to your sponsor.

#### Which date to use
- **50% chance of completion:** use it to plan your own work.
- **85% chance of completion:** use it for the date you give a sponsor or client.
- **95% chance of completion:** use it when a late finish costs a lot.
- **Velocity date:** use it to compare with your sprint plan. It uses your team's average \
pace in story points. If you do not enter the story points left in More options, the tool \
estimates them.

#### Be careful
The dates assume your team keeps its recent pace (throughput).

The 85% date can be too early. See "How accurate is it?" on the page.

#### Privacy
The tool uses your file only for this forecast. It does not store the file or show issue keys.
"""

_MONTHS = (
    "Jan.", "Feb.", "March", "April", "May", "June",
    "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
)  # fmt: skip
_BACKLOG_TEXT = re.compile(r"[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+", re.ASCII)


def short_date(d: date) -> str:
    """A written-out date with no year: "Nov. 17" (page only; the CLI keeps ISO)."""
    return f"{_MONTHS[d.month - 1]} {d.day}"


def long_date(d: date) -> str:
    """A written-out date: "Nov. 17, 2026" (page only; the CLI keeps ISO)."""
    return f"{short_date(d)}, {d.year}"


def parse_backlog(text: str) -> int:
    """The typed backlog as a whole number from 1 to 10,000, or a WebError."""
    text = text.strip()
    if not _BACKLOG_TEXT.fullmatch(text):
        raise WebError(BACKLOG_ERROR)
    n = int(text.replace(",", ""))
    if not 1 <= n <= MAX_BACKLOG:
        raise WebError(BACKLOG_ERROR)
    return n


@dataclass(frozen=True)
class Card:
    label: str
    value: str
    notes: tuple[str, ...]
    color: str
    highlight: bool = False
    dashed: bool = False


def cards(facts: ForecastFacts) -> list[Card]:
    """The 4 date cards, in the order and colours of the chart lines."""
    if facts.velocity_date is None:
        v_value, v_note = "Not available", "Needs story points"
    else:  # MCF-34 (D45): pace and estimated points are explained in the help sidebar
        v_value, v_note = long_date(facts.velocity_date), "Uses story points"
    return [
        Card("50% chance of completion", long_date(facts.mc50), ("P50",), COLORS["p50"]),
        Card(
            "85% chance of completion",
            long_date(facts.mc85),
            ("P85 · Recommended to share", "If a delay costs a lot, use 95%."),
            COLORS["p85"],
            highlight=True,
        ),
        Card("95% chance of completion", long_date(facts.mc95), ("P95",), COLORS["p95"]),
        Card("Velocity date", v_value, (v_note,), COLORS["velocity"], dashed=True),
    ]


def card_background(c: Card) -> str:
    return "#fff8ee" if c.highlight else ("#f0faf3" if c.dashed else "#ffffff")


def _card_html(c: Card) -> str:
    e = html.escape
    style = "dashed" if c.dashed else "solid"
    width = 3 if c.highlight else 2
    back = card_background(c)
    note = "".join(f'<span class="mcf-card-note">{e(n)}</span>' for n in c.notes)
    return (
        f'<div class="mcf-card{" mcf-card-highlight" if c.highlight else ""}" '
        f'data-label="{e(c.label)}" style="border:{width}px {style} {c.color};'
        f"background:{back};border-radius:10px;padding:12px 14px;display:flex;"
        f'flex-direction:column;gap:2px;min-width:0">'
        f'<span class="mcf-card-label" style="font-size:0.85rem;font-weight:600;'
        f'color:{c.color}">{e(c.label)}</span>'
        f'<span class="mcf-card-value" style="font-size:1.2rem;font-weight:700;'
        f'color:{COLORS["ink"]};white-space:nowrap">{e(c.value)}</span>'
        f"{note}</div>"
    )


def cards_html(facts: ForecastFacts) -> str:
    """The cards as HTML. Only code-made text goes in (no text from the file)."""
    inner = "".join(_card_html(c) for c in cards(facts))
    return (
        '<div class="mcf-cards" style="display:grid;gap:10px;margin-bottom:16px;'
        'grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">'
        f"{inner}</div>"
        f"<style>.mcf-card-note{{font-size:0.82rem;color:{COLORS['muted']}}}"
        "@media (max-width: 640px){.mcf-cards{grid-template-columns:1fr !important}}</style>"
    )


def result_heading(facts: ForecastFacts) -> str:
    noun = "work item" if facts.backlog == 1 else "work items"
    return f"2. When the {facts.backlog:,} {noun} will be done"


# --- MCF-37: numbered sections in boxes ---------------------------------------------------


@dataclass(frozen=True)
class Section:
    heading: str
    description: str


INPUTS_SECTION = Section(
    "1. Your inputs", "Choose the work items to forecast from, and the work left."
)


def sections(facts: ForecastFacts) -> list[Section]:
    n = facts.backlog
    noun = "item" if n == 1 else "items"
    return [
        INPUTS_SECTION,
        Section(
            result_heading(facts),
            f"Each card shows the chance of completion of all {n:,} {noun} by that date.",
        ),
        Section(
            "3. All possible finish dates",
            CHART_CAPTION.format(runs=facts.runs) + " The lines show the dates above.",
        ),
        Section(
            "4. " + HOW_IT_WORKS_HEADING, "Open each part for the method and the test results."
        ),
    ]


def same_day_note(facts: ForecastFacts) -> str | None:
    if facts.velocity_date is not None and facts.velocity_date == facts.mc50:
        return (
            "The velocity date is the same day as the 50% date, so the two lines are drawn "
            "side by side."
        )
    return None


def page_css() -> str:
    """Grey page, white boxes (MCF-37). Fixed text only."""
    return (
        "<style>"
        '[data-testid="stAppViewContainer"],[data-testid="stMain"],'
        '[data-testid="stHeader"]{background:#f5f6f8}'
        # A bordered st.container is a stVerticalBlock inside a stLayoutWrapper (1.66).
        '[data-testid="stLayoutWrapper"]>[data-testid="stVerticalBlock"],'
        '[data-testid="stExpander"] details{background:#ffffff}'
        # Streamlit's caption is 60% opacity: 3.7:1 on white. This colour is 5.9:1.
        '[data-testid="stCaptionContainer"]{color:#5f6370;opacity:1}'
        "</style>"
    )


def from_line(facts: ForecastFacts, *, as_of_given: bool) -> str:
    why = "the date you chose" if as_of_given else "the day the last item in your file was finished"
    return f"Dates count from {long_date(facts.t)}, {why}."


def message_line(facts: ForecastFacts) -> str:
    """A ready-made sentence for the sponsor (MCF-35)."""
    fmt = short_date if facts.mc50.year == facts.mc85.year else long_date
    a, b = fmt(facts.mc50), fmt(facts.mc85)
    return f'Message to sponsor: "{a} to {b} (85% chance of completion by {b})."'


def history_line(facts: ForecastFacts) -> str:
    start = long_date(facts.window_start)
    if facts.window_start.year == facts.window_end.year:
        start = short_date(facts.window_start)
    noun = "work item" if facts.items_done == 1 else "work items"
    return (
        f"History used: {facts.items_done:,} {noun} (not bugs or epics) finished from {start} "
        f"to {long_date(facts.window_end)} (84 days)."
    )


def axis_format(facts: ForecastFacts) -> str:
    """The chart date format: add the year when the dates cross a year."""
    return "%b %-d" if facts.t.year == facts.mc95.year else "%b %-d, %Y"


def phone_help_html() -> str:
    """A help hint shown only on narrow screens, where the sidebar is folded."""
    return (
        f'<p class="mcf-phone-help" style="margin:0;font-size:0.9rem">{html.escape(PHONE_HELP)}</p>'
        "<style>@media (min-width: 641px) {.mcf-phone-help{display:none}}</style>"
    )


# --- MCF-36: "How this forecast works" and the footer ---------------------------------------

HOW_IT_WORKS_HEADING = "How this forecast works"
REPO_URL = "https://github.com/aswinguruswamy/monte-carlo-delivery-forecast"


@dataclass(frozen=True)
class Part:
    title: str
    body: str  # Markdown, code-made text only


def done_by_85_of_100() -> int:
    """Back-test: how many of 100 forecasts were done by the 85% date."""
    return round(BACKTEST.calibration_85 * 100)


def later_than_85_of_100() -> int:
    return 100 - done_by_85_of_100()


def about_one_in(per_100: int) -> str:
    """31 of 100 -> "about 1 in 3"."""
    return f"about 1 in {round(100 / per_100)}"


def how_it_works() -> list[Part]:
    """The 2 closed parts: how the dates are made, and how accurate they were."""
    later = about_one_in(later_than_85_of_100())
    monte_carlo = (
        "The tool does not use one average pace. It replays your team's real good days and "
        "bad days many times.\n\n"
        f"1. Count how many work items the team finished on each of the last {WINDOW_DAYS} "
        "days.\n"
        "2. Make one try: for each future day, pick one of those past days at random and use "
        "its count.\n"
        "3. Add the counts until all the work left is done. That day is the finish date of "
        "this try.\n"
        f"4. Do {RUNS:,} tries. Each try gives a different finish date.\n"
        "5. Sort the finish dates. The 50% date is the day by which half of the tries finish. "
        "The 85% and 95% dates work the same way.\n\n"
        "Story points are not needed for these dates. The velocity date uses story points, "
        "for comparison."
    )
    backtest = (
        f"We tested the tool on the history of {BACKTEST.projects} real open-source projects. "
        "A forecast is one prediction of when the next 10, 25 or 50 work items (not bugs or "
        "epics) will be done."
        "\n\n"
        "1. Pick a past date in a project. Use only the work done up to that date.\n"
        "2. Make the forecast.\n"
        "3. Compare it with the date the work was really done.\n\n"
        f"- **{BACKTEST.cases:,}** past forecasts checked "
        f"(**{BACKTEST.no_forecast:,}** more had too little history to forecast)\n"
        f"- **{done_by_85_of_100()} of 100** done by the 85% date (target: 75 to 95 of 100)\n"
        f"- **{later.capitalize()}** finished later than the 85% date\n\n"
        "So the 85% date is often too early. Use the 95% date when a late finish costs a lot. "
        "The result is published as it is, although it missed the target."
    )
    return [
        Part("How the dates are made (Monte Carlo)", monte_carlo),
        Part(
            f"How accurate is it? (back-test: the 85% date was too early {later} times)", backtest
        ),
    ]


def footer_markdown() -> str:
    return (
        "**About this project**\n\n"
        "Built by Aswin Guruswamy with Claude. Python and Streamlit. Open source (Apache 2.0)."
        "\n\n"
        f"Test data: TAWOS, {BACKTEST.projects} open-source projects "
        "(Tawosi et al., MSR 2022).\n\n"
        f"[Source code on GitHub]({REPO_URL}) · "
        f"[Full back-test report]({REPO_URL}/blob/main/docs/backtest-report.md)\n\n"
        f"Version {__version__}"
    )


def no_points_line(facts: ForecastFacts) -> str | None:
    """MCF-32: how many work items in the history have no story points."""
    n = facts.items_no_points
    if not n:
        return None
    noun, verb = ("work item", "has") if n == 1 else ("work items", "have")
    text = (
        f"{n} {noun} done between {long_date(facts.window_start)} and "
        f"{long_date(facts.window_end)} {verb} no story points."
    )
    if facts.velocity_date is not None:
        text += " The velocity date leaves them out."
    return text


def ai_explanation(facts: ForecastFacts) -> tuple[str | None, str | None]:
    """(approved text, None) or (None, a fixed reason). Never raises (NFR5)."""
    return explain_checked(facts, transport=TRANSPORT)
