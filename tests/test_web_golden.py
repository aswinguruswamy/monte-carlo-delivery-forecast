"""MCF-47: the page text, CSS and colours stay byte-for-byte the same after the move.

The golden file was made from the code before the move (commit d82d9b5) with
``python tests/test_web_golden.py --write``. It holds code-made text only: no dataset
rows (D08) and no issue keys (C2). The package version is written as ``<version>``, so a
release does not change the file. Do not write it again in a refactor ticket; a wording
change writes it again from the new code, with PM approval.
"""

import json
import re
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

import pytest

from mcf import __version__
from mcf.web import logic

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "web_golden" / "page_strings.json"
CONTENT_FILES = (
    "sidebar.md",
    "how_dates_are_made.md",
    "how_accurate.md",
    "footer.md",
    "page.css",
    "colors.json",
)


def page_strings() -> dict[str, str]:
    """Every fixed string the page sends, and the strings made for the sample forecast."""
    out: dict[str, str] = {
        "SIDEBAR": logic.SIDEBAR,
        "page_css": logic.page_css(),
        "phone_help_html": logic.phone_help_html(),
        "INTRO": logic.INTRO,
        "NOT_CERTAIN": logic.NOT_CERTAIN,
        "CHART_CAPTION": logic.CHART_CAPTION,
        "SAMPLE_LABEL": logic.SAMPLE_LABEL,
        "REPORT_LABEL": logic.REPORT_LABEL,
        "REPORT_DESCRIPTION": logic.REPORT_DESCRIPTION,
        "BACKLOG_HELP": logic.BACKLOG_HELP,
        "BACKLOG_ERROR": logic.BACKLOG_ERROR,
        "PHONE_HELP": logic.PHONE_HELP,
        "OPTION_HELP": json.dumps(logic.OPTION_HELP, sort_keys=True),
        "COLORS": json.dumps(logic.COLORS),
        "DARK": json.dumps(logic.DARK),
        "CHART_COLORS": json.dumps(logic.CHART_COLORS),
        "INPUTS_SECTION": repr(logic.INPUTS_SECTION),
        "HOW_IT_WORKS_HEADING": logic.HOW_IT_WORKS_HEADING,
        "how_it_works": repr(logic.how_it_works()),
        "footer_markdown": logic.footer_markdown().replace(
            f"Version {__version__}", "Version <version>"
        ),
    }
    for backlog, as_of in ((40, None), (40, date(2026, 8, 15)), (2000, None)):
        tag = f"sample-{backlog}-{as_of}"
        try:
            facts = logic.forecast_from_bytes(
                logic.sample_bytes() or b"", backlog=backlog, as_of=as_of
            ).facts
        except logic.WebError as exc:
            out[f"{tag}-error"] = str(exc)
            continue
        out[f"{tag}-cards"] = repr(logic.cards(facts))
        out[f"{tag}-cards_html"] = logic.cards_html(facts)
        out[f"{tag}-result_heading"] = logic.result_heading(facts)
        out[f"{tag}-sections"] = repr(logic.sections(facts))
        out[f"{tag}-from_line"] = logic.from_line(facts, as_of_given=as_of is not None)
        out[f"{tag}-history_line"] = logic.history_line(facts)
        out[f"{tag}-message_line"] = logic.message_line(facts)
        out[f"{tag}-no_points_line"] = repr(logic.no_points_line(facts))
        out[f"{tag}-same_day_note"] = repr(logic.same_day_note(facts))
        out[f"{tag}-axis_format"] = logic.axis_format(facts)
        out[f"{tag}-marker_table"] = logic.marker_table(facts).to_csv(index=False)
    return out


def test_the_page_strings_are_byte_for_byte_the_same_as_before_the_move():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    now = page_strings()
    assert sorted(now) == sorted(golden)
    for key, text in golden.items():
        assert now[key].encode("utf-8") == text.encode("utf-8"), key


def test_the_golden_file_covers_a_forecast_and_the_fixed_text():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert "sample-40-None-cards_html" in golden
    assert "light-dark(" in golden["page_css"]
    assert "### How to use this page" in golden["SIDEBAR"]


@pytest.mark.parametrize("name", CONTENT_FILES)
def test_each_content_file_is_in_the_source_package(name):
    assert (ROOT / "src" / "mcf" / "web" / "content" / name).is_file()


def test_the_content_files_have_no_stray_dollar_sign():
    """string.Template fields are $name; any other $ would break the fill."""
    for name in CONTENT_FILES:
        text = (ROOT / "src" / "mcf" / "web" / "content" / name).read_text(encoding="utf-8")
        assert not re.search(r"\$(?![A-Za-z_]\w*)", text), name


def test_each_dark_role_note_names_a_dark_colour():
    palette = json.loads((ROOT / "src" / "mcf" / "web" / "content" / "colors.json").read_text())
    assert set(palette["DARK_ROLES"]) <= set(palette["DARK"])


@pytest.mark.parametrize(
    "bad",
    [
        "/* a comment\non two lines */\nx{color:red}",  # comment over two lines
        "/* note */ x{color:red}",  # a rule after a comment on the same line
        "x{color:red} /* note */",  # a comment after a rule
        ".a\n.b{color:red}",  # a line break inside a selector
    ],
)
def test_the_css_loader_rejects_a_file_it_would_join_wrongly(bad):
    with pytest.raises(ValueError):
        logic.css_rules(bad)


def test_the_css_loader_keeps_rules_and_drops_full_comment_lines():
    text = "/* note */\n[a],\n[b]{color:red}\n.c{width:1px;\nheight:1px}"
    assert logic.css_rules(text) == "[a],[b]{color:red}.c{width:1px;height:1px}"


def test_the_built_wheel_contains_the_content_files(tmp_path):
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(ROOT), "--no-deps", "-q", "-w", str(tmp_path)],
        check=True,
    )
    (wheel,) = tmp_path.glob("mcf-*.whl")
    names = set(zipfile.ZipFile(wheel).namelist())
    for name in CONTENT_FILES:
        assert f"mcf/web/content/{name}" in names


if __name__ == "__main__" and sys.argv[1:] == ["--write"]:
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(
        json.dumps(page_strings(), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("wrote", GOLDEN)
