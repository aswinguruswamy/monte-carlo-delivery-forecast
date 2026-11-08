"""The MCF web page (MCF-24, D01).

Run: streamlit run streamlit_app.py   (needs: pip install -e ".[web]")

All numbers come from the same code as the CLI (mcf.web.logic). The page shows
no issue keys or file names (RAID C2). The AI explanation (D33.1) needs
ANTHROPIC_API_KEY; without it, the page shows the plain forecast.
"""

from __future__ import annotations

import html
import os

import altair as alt
import streamlit as st

from mcf.forecast.montecarlo import SEED
from mcf.web import logic

SAMPLE = logic.SAMPLE_LABEL
UPLOAD = "Upload a CSV file"


def not_drawn_text(count: int) -> str | None:
    """The caption for runs that end after 9999-12-31 (MCF-30), or None."""
    if count == 0:
        return None
    if count == 1:
        return "The chart does not show 1 run that ends after 9999-12-31."
    return f"The chart does not show {count:,} runs that end after 9999-12-31."


class _NoText(Exception):
    """No approved text. Not cached, so a later rerun can try again."""


@st.cache_data(show_spinner="Asking Claude...", max_entries=256, ttl=24 * 3600)
def _explanation(facts) -> str:
    """One paid call for each forecast: the result is cached by the facts."""
    text, reason = logic.ai_explanation(facts)
    if text is None:
        raise _NoText(reason)
    return text


def _chart(result: logic.WebForecast) -> alt.LayerChart:
    hist = logic.chart_table(result)
    marks = logic.marker_table(result.facts)
    date_axis = alt.Axis(
        format=logic.axis_format(result.facts), labelAngle=0, title="Finish date", tickCount=6
    )
    bars = (
        alt.Chart(hist)
        .mark_bar(color="#c3d0e2")
        .encode(
            x=alt.X("finish_date:T", axis=date_axis),
            y=alt.Y("runs:Q", title="Simulated runs"),
            tooltip=[alt.Tooltip("finish_date:T", title="Date", format="%b %-d, %Y"), "runs:Q"],
        )
    )
    scale = alt.Scale(domain=list(marks["label"]), range=list(marks["color"]))
    layers = []
    for row in marks.itertuples():  # one layer per line, so 2 lines on 1 day sit side by side
        layers.append(
            alt.Chart(marks[marks["label"] == row.label])
            .mark_rule(strokeWidth=3, xOffset=int(row.offset))
            .encode(
                x="date:T",
                color=alt.Color(
                    "label:N",
                    title=None,
                    scale=scale,
                    legend=alt.Legend(orient="bottom", columns=2),  # all 4 fit on a phone
                ),
                strokeDash=alt.value([6, 4] if row.label == "Velocity" else [1, 0]),
                tooltip=[
                    alt.Tooltip("label:N", title="Line"),
                    alt.Tooltip("date:T", title="Date", format="%b %-d, %Y"),
                ],
            )
        )
    rules = alt.layer(*layers)
    return (bars + rules).properties(height=300)


def _sidebar() -> None:
    with st.sidebar:  # first in reading order; fixed on the left (MCF-33, #15)
        st.markdown(logic.SIDEBAR)


def main() -> None:
    st.set_page_config(
        page_title="Monte Carlo Delivery Forecast",
        layout="centered",
        initial_sidebar_state="auto",  # open on a desktop, folded on a phone
    )
    _sidebar()
    st.markdown(logic.page_css(), unsafe_allow_html=True)  # fixed text only
    st.markdown(logic.phone_help_html(), unsafe_allow_html=True)  # fixed text only
    st.caption("MONTE CARLO DELIVERY FORECAST")
    st.title("When will your work be done?")
    st.markdown(logic.INTRO)

    with _section(logic.INPUTS_SECTION, 1):
        sample = logic.sample_bytes()
        sources = [SAMPLE, UPLOAD] if sample is not None else [UPLOAD]
        source = st.radio("Data", sources, key="source", horizontal=True)
        data: bytes | None = sample if source == SAMPLE else None
        if source == UPLOAD:
            uploaded = st.file_uploader(
                "CSV file (a Jira export works)", type=["csv"], key="upload"
            )
            if uploaded is not None:
                data = uploaded.getvalue()

        backlog_text = st.text_input(
            "How many work items are left? (backlog)", value="40", key="backlog"
        )
        st.caption(logic.BACKLOG_HELP)
        with st.expander("More options"):
            points_given = st.toggle("I know the story points left", key="points_given")
            st.caption(logic.OPTION_HELP["backlog_points"])
            backlog_points = None
            if points_given:
                backlog_points = st.number_input(
                    "Story points left", min_value=0.1, value=100.0, key="backlog_points"
                )
            as_of = st.date_input("Forecast from this date (as-of date)", value=None, key="as_of")
            st.caption(logic.OPTION_HELP["as_of"])
            seed = st.number_input(
                "Repeat number (random seed)", min_value=0, value=SEED, step=1, key="seed"
            )
            st.caption(logic.OPTION_HELP["seed"])

        explain = False
        if os.environ.get("ANTHROPIC_API_KEY"):
            explain = st.toggle(
                "Add an AI explanation (Claude picks approved sentences)",
                value=False,  # off by default: each new forecast is one paid call
                key="explain",
            )
        # PM 2026-11-04: no AI line on a page with no key.

    try:
        backlog = logic.parse_backlog(backlog_text)
    except logic.WebError as exc:
        st.error(str(exc))
        return
    if data is None:
        st.info("Upload a CSV file to see the forecast.")
        return

    try:
        result = logic.forecast_from_bytes(
            data,
            backlog=backlog,
            backlog_points=None if backlog_points is None else float(backlog_points),
            as_of=as_of,
            seed=int(seed),
        )
    except logic.WebError as exc:
        st.error(logic.plain(str(exc)))  # text from the file shows as plain text
        return

    f = result.facts
    _, result_section, chart_section, how_section = logic.sections(f)
    with _section(result_section, 2):
        st.caption(logic.from_line(f, as_of_given=as_of is not None))
        st.caption(logic.history_line(f))
        st.markdown(logic.cards_html(f), unsafe_allow_html=True)  # code-made text only
        st.markdown(f"**{logic.NOT_CERTAIN}**")
        st.markdown(logic.message_line(f))
        if logic.no_points_line(f):
            st.caption(logic.no_points_line(f))
        if explain:
            try:
                text = _explanation(f)
            except _NoText as exc:
                st.info(f"AI explanation not shown: {exc}")
            else:
                st.markdown("#### Explanation")
                st.markdown(text)
                st.caption("AI-selected, approved sentences (D33.1). Code wrote every date above.")

    with _section(chart_section, 3):
        st.altair_chart(_chart(result), width="stretch")
        left_out = not_drawn_text(logic.runs_not_drawn(result))
        if left_out:
            st.caption(left_out)
        if logic.same_day_note(f):
            st.caption(logic.same_day_note(f))

    with _section(how_section, 4):
        for part in logic.how_it_works():
            with st.expander(part.title):
                st.markdown(part.body)  # code-made text only

    with st.container(border=True):
        st.caption(logic.REPORT_DESCRIPTION)
        with st.expander(logic.REPORT_LABEL):
            st.code(result.report, language=None)

    st.divider()
    st.markdown(logic.footer_markdown())


def _section(section: logic.Section, number: int):
    """MCF-41: a numbered section the user can close; open when the page loads.

    The key gives the CSS class st-key-section-N (heading size, logic.page_css). With a
    key, Streamlit keeps the open or closed state when the page runs again.
    """
    # Review MCF-41: an expander label is not a heading, so screen readers that jump by
    # heading need a hidden h2 (code-made text only, escaped).
    st.markdown(
        f'<h2 class="mcf-sr-only">{html.escape(section.heading)}</h2>', unsafe_allow_html=True
    )
    box = st.expander(section.heading, expanded=True, key=f"section-{number}")
    box.caption(section.description)
    return box


if __name__ == "__main__":
    main()
