"""The MCF web page (MCF-24, D01).

Run: streamlit run streamlit_app.py   (needs: pip install -e ".[web]")

All numbers come from the same code as the CLI (mcf.web.logic). The page shows
no issue keys or file names (RAID C2). The AI explanation (D33.1) needs
ANTHROPIC_API_KEY; without it, the page shows the plain forecast.
"""

from __future__ import annotations

import os

import altair as alt
import streamlit as st

from mcf.forecast.montecarlo import SEED
from mcf.web import logic

SAMPLE = "Sample file (made-up data)"
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
    bars = (
        alt.Chart(hist)
        .mark_bar(color="#8fa8c8")
        .encode(
            x=alt.X("finish_date:T", title="Finish date"),
            y=alt.Y("runs:Q", title="Simulated runs"),
            tooltip=[alt.Tooltip("finish_date:T", title="Date"), "runs:Q"],
        )
    )
    rules = (
        alt.Chart(marks)
        .mark_rule(strokeWidth=2)
        .encode(
            x="date:T",
            color=alt.Color(
                "label:N",
                title=None,
                scale=alt.Scale(
                    domain=["50%", "85%", "95%", "Velocity"],
                    range=["#2f6db5", "#d08a1f", "#b8322f", "#555555"],
                ),
            ),
            strokeDash=alt.condition(
                alt.datum.label == "Velocity", alt.value([6, 4]), alt.value([1, 0])
            ),
            tooltip=[alt.Tooltip("label:N", title="Line"), alt.Tooltip("date:T", title="Date")],
        )
    )
    return (bars + rules).properties(height=320)


def main() -> None:
    st.set_page_config(page_title="Monte Carlo Delivery Forecast", layout="centered")
    st.title("Monte Carlo Delivery Forecast")
    st.markdown(
        "When will the next **N value items** be done? The page gives the dates at "
        "**50%, 85% and 95%** from many simulated runs of the team's recent daily pace, "
        "and the usual **velocity** date."
    )

    sample = logic.sample_bytes()
    sources = [SAMPLE, UPLOAD] if sample is not None else [UPLOAD]
    source = st.radio("Data", sources, key="source", horizontal=True)
    data: bytes | None = sample if source == SAMPLE else None
    if source == UPLOAD:
        uploaded = st.file_uploader(
            "CSV with the columns Issue_Key, Type, Resolution_Date, Story_Point",
            type=["csv"],
            key="upload",
        )
        if uploaded is not None:
            data = uploaded.getvalue()

    backlog = st.number_input(
        "Backlog: value items still to do", min_value=1, value=40, step=1, key="backlog"
    )
    with st.expander("More options"):
        points_given = st.toggle("I know the backlog story points", key="points_given")
        backlog_points = None
        if points_given:
            backlog_points = st.number_input(
                "Backlog story points", min_value=0.1, value=100.0, key="backlog_points"
            )
        as_of = st.date_input(
            "Forecast date (empty: the last done day in the file)", value=None, key="as_of"
        )
        seed = st.number_input("Random seed", min_value=0, value=SEED, step=1, key="seed")

    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    explain = st.toggle(
        "Add an AI explanation (Claude picks approved sentences)",
        value=False,  # off by default: each new forecast is one paid call
        disabled=not has_key,
        key="explain",
    )
    if not has_key:
        st.caption("AI explanation off: set ANTHROPIC_API_KEY on the server to turn it on.")

    if data is None:
        st.info("Upload a CSV file to see the forecast.")
        return

    try:
        result = logic.forecast_from_bytes(
            data,
            backlog=int(backlog),
            backlog_points=None if backlog_points is None else float(backlog_points),
            as_of=as_of,
            seed=int(seed),
        )
    except logic.WebError as exc:
        st.error(logic.plain(str(exc)))  # text from the file shows as plain text
        return

    f = result.facts
    st.subheader(f"Forecast for the next {f.backlog} value items, from {f.t}")
    top, bottom = st.columns(2), st.columns(2)  # 2 x 2, so a full date fits
    top[0].metric("50% date", str(f.mc50))
    top[1].metric("85% date", str(f.mc85))
    bottom[0].metric("95% date", str(f.mc95))
    if f.velocity_date is None:
        bottom[1].metric("Velocity date", "Not available", help="Needs story points.")
        bottom[1].caption("Not available: needs story points")
    else:
        bottom[1].metric("Velocity date", str(f.velocity_date))
    if f.items_no_points:
        st.caption(
            f"{f.items_no_points} value items done between {f.window_start} and "
            f"{f.window_end} have no story points. The velocity date leaves them out."
        )
    st.markdown("**The 50% date is not certain: half of the runs finish later.**")
    st.altair_chart(_chart(result), width="stretch")
    left_out = not_drawn_text(logic.runs_not_drawn(result))
    if left_out:
        st.caption(left_out)
    st.caption(
        f"{f.runs:,} simulated runs from {f.items_done} value items done between "
        f"{f.window_start} and {f.window_end}. Bars: runs that finish on each date. "
        "Lines: the 50%, 85% and 95% dates and the velocity date."
    )

    if explain:
        try:
            text = _explanation(f)
        except _NoText as exc:
            st.info(f"AI explanation not shown: {exc}")
        else:
            st.markdown("#### Explanation")
            st.markdown(text)
            st.caption("AI-selected, approved sentences (D33.1). Code wrote every date above.")

    with st.expander("Full report"):
        st.code(result.report, language=None)


if __name__ == "__main__":
    main()
