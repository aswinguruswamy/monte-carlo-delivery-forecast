"""MCF-42 checks: a full dark theme (D48.1). Light mode keeps the v1.1 colours.

The page follows the device (System) and the menu's Light / Dark switch. The CSS uses
light-dark(<light>, <dark>), which follows Streamlit's color-scheme on stApp.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from mcf.web import logic

ROOT = Path(__file__).resolve().parents[1]
PAIR = re.compile(r"light-dark\((#[0-9a-f]{6}),(#[0-9a-f]{6})\)")
# Review MCF-42: also 3-digit hex and rgb() colours, so no colour escapes the pair check.
HEX = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b|rgba?\(")

# The approved design (canvas MainDark, 2026-11-09), light -> dark.
APPROVED = {
    "#f5f6f8": "#0f1115",
    "#ffffff": "#1a1d23",
    "#31333f": "#e6e8ee",
    "#5f6370": "#a3a9b6",
    "#2f6db5": "#79b0ff",
    "#9a5a0c": "#f2b05e",
    "#b8322f": "#ff8a80",
    "#1a7f37": "#5bd47a",
    "#fff8ee": "#2a2216",
    "#f0faf3": "#16261b",
    "#878c98": "#6b7280",
    "#7d1d14": "#ffb4ab",  # error text: not in the canvas; light on the dark error box
    "#0054a3": "#8cc4ff",  # info text (Streamlit's light colour); review MCF-42
}


def _luminance(colour: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _all_html() -> str:
    from test_layout import facts  # the same made-up forecast as the layout tests

    return logic.page_css() + logic.cards_html(facts())


def test_the_config_has_both_themes_and_no_fixed_base():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())
    assert "base" not in cfg["theme"]  # a fixed base removes the switch (D48)
    dark = cfg["theme"]["dark"]
    assert dark["backgroundColor"] == "#0f1115"
    assert dark["secondaryBackgroundColor"] == "#232730"
    assert dark["textColor"] == "#e6e8ee"
    # Review MCF-42: light mode keeps Streamlit's light colours (v1.1).
    assert cfg["theme"]["light"] == {"backgroundColor": "#ffffff", "textColor": "#31333f"}


def test_every_page_colour_has_a_dark_pair_from_the_design():
    text = _all_html()
    pairs = PAIR.findall(text)
    assert pairs, "no light-dark() colours"
    for light, dark in pairs:
        assert APPROVED.get(light) == dark, (light, dark)
    left = PAIR.sub("", text)
    assert not HEX.findall(left), f"colours with no dark pair: {set(HEX.findall(left))}"


def test_light_mode_keeps_the_v1_1_colours():
    """Only the dark side is new: taking the light side gives the v1.1.0 CSS back."""
    css = PAIR.sub(r"\1", logic.page_css())
    assert '[data-testid="stCaptionContainer"]{color:#5f6370;opacity:1}' in css
    assert '[data-testid="stAlertContentError"]{color:#7d1d14}' in css
    assert "background:#f5f6f8" in css and "background:#ffffff" in css


def test_dark_text_colours_have_4_5_to_1_on_the_dark_boxes():
    for text in ("#e6e8ee", "#a3a9b6"):
        for back in ("#0f1115", "#1a1d23", "#232730", "#2a2216", "#16261b"):
            assert contrast(text, back) >= 4.5, (text, back)


def test_inner_borders_are_3_to_1_in_both_themes():
    """The canvas review: darker in light mode, a little lighter in dark mode."""
    assert contrast("#878c98", "#ffffff") >= 3
    assert contrast("#6b7280", "#1a1d23") >= 3
    css = logic.page_css()
    assert "light-dark(#878c98,#6b7280)" in css


def test_chart_lines_pass_3_to_1_in_both_themes():
    """Altair draws the lines, so CSS cannot switch them: one set for both (D48.1)."""
    assert set(logic.CHART_COLORS) == {"p50", "p85", "p95", "velocity"}
    for colour in logic.CHART_COLORS.values():
        assert contrast(colour, "#ffffff") >= 3, colour
        assert contrast(colour, "#1a1d23") >= 3, colour
    assert logic.CHART_COLORS == {
        "p50": "#3d7fcd",
        "p85": "#ab7119",
        "p95": "#d25350",
        "velocity": "#1d903e",
    }


def test_the_chart_marker_table_uses_the_chart_colours():
    from test_layout import facts

    marks = logic.marker_table(facts())
    assert set(marks["color"]) <= set(logic.CHART_COLORS.values())


# --- Review MCF-42 ---------------------------------------------------------------------------


def _blend(top: str, alpha: float, under: str) -> str:
    a = [int(top[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(under[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(
        f"{round(alpha * x + (1 - alpha) * y):02x}" for x, y in zip(a, b, strict=True)
    )


def test_the_info_text_is_readable_on_the_dark_section_box():
    """High contrast for "AI explanation not shown" inside a section: it was 4.30:1."""
    css = logic.page_css()
    assert '[data-testid="stAlertContentInfo"]{color:light-dark(#0054a3,#8cc4ff)}' in css
    box = _blend("#3d9df3", 0.2, "#1a1d23")  # Streamlit's dark info box on the section box
    assert contrast("#8cc4ff", box) >= 4.5
    assert contrast("#0054a3", _blend("#1c83ff", 0.1, "#ffffff")) >= 4.5  # light unchanged


def test_the_input_border_uses_streamlit_1_66_test_ids():
    """The baseweb selectors matched nothing; these are the elements that draw the border."""
    css = logic.page_css()
    for testid in ("stTextInputRootElement", "stNumberInputContainer", "stDateInputField"):
        assert f'[data-testid="{testid}"]' in css
    assert "data-baseweb" not in css
    # A theme switch left the border between the 2 colours: Streamlit's border fade stopped.
    assert (
        '[data-testid="stDateInputField"]{border-color:light-dark(#878c98,#6b7280);'
        "transition:none}" in css
    )
