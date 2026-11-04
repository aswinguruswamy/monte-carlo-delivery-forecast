"""MCF-32 checks: a team without story points can use the tool (D43).

User-file path only (CLI and page). The Monte Carlo dates need only the done
days. The velocity date needs story points; with none in the 84-day history it
is "Not available: needs story points". The back-test path (ADR 0002) keeps the
rule that every value item has a story point.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from mcf.cli import main
from mcf.data.load import LoadError, load_issues
from mcf.data.types import IssueTypeError, sort_types
from mcf.explain.bank import applicable_ids, qualities
from mcf.explain.prompt import build_prompt
from mcf.result import ForecastFacts

T = date(2026, 9, 30)
NOT_AVAILABLE = "Not available: needs story points"


def rows(points: list[str], *, header: str = "Issue_Key,Type,Resolution_Date,Story_Point") -> str:
    """One Story a day, ending on T, with the given point text."""
    lines = [header]
    n = len(points)
    for i, p in enumerate(points):
        day = T - timedelta(days=n - 1 - i)
        cells = [f"A-{i + 1}", "Story", day.isoformat()]
        if "Story_Point" in header:
            cells.append(p)
        lines.append(",".join(cells))
    return "\n".join(lines) + "\n"


def write(tmp_path: Path, text: str, name: str = "team.csv") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def run(capsys, *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


# --- AC1: no story points at all ------------------------------------------------------------


def test_no_point_column_gives_the_monte_carlo_dates(tmp_path, capsys):
    p = write(tmp_path, rows(["x"] * 40, header="Issue_Key,Type,Resolution_Date"))
    code, out, err = run(capsys, "forecast", str(p), "--backlog", "10")
    assert code == 0, err
    assert "  50%: 2026-" in out and "  95%: 2026-" in out
    assert f"Velocity: {NOT_AVAILABLE}" in out


def test_empty_points_give_the_same_result_as_no_column(tmp_path, capsys):
    a = write(tmp_path, rows([""] * 40), name="a.csv")
    b = write(tmp_path, rows(["x"] * 40, header="Issue_Key,Type,Resolution_Date"), name="b.csv")
    _, out_a, _ = run(capsys, "forecast", str(a), "--backlog", "10")
    _, out_b, _ = run(capsys, "forecast", str(b), "--backlog", "10")
    assert out_a == out_b
    assert "Value items with no story points (2026-07-09 to 2026-09-30): 40" in out_a


def test_no_points_and_given_backlog_points_is_still_not_available(tmp_path, capsys):
    p = write(tmp_path, rows([""] * 40))
    code, out, _ = run(capsys, "forecast", str(p), "--backlog", "10", "--backlog-points", "50")
    assert code == 0
    assert f"Velocity: {NOT_AVAILABLE} in the history; --backlog-points not used" in out


def test_the_not_available_line_names_the_history(tmp_path, capsys):
    p = write(tmp_path, rows([""] * 40))
    _, out, _ = run(capsys, "forecast", str(p), "--backlog", "10")
    assert f"Velocity: {NOT_AVAILABLE} in the history\n" in out


def test_the_no_points_count_includes_both_window_ends(tmp_path, capsys):
    # 3 items with no points: the day before the window, its first day, its last day (T).
    start = T - timedelta(days=83)
    lines = ["Issue_Key,Type,Resolution_Date,Story_Point"]
    lines += [f"A-{i},Story,{d},2" for i, d in enumerate([start, T], 1)]
    lines += [f"B-{i},Story,{d}," for i, d in enumerate([start - timedelta(days=1), start, T], 1)]
    lines += ["C-1,Bug,2026-09-01,", "C-2,Story,,"]  # a bug and an open item are not counted
    p = write(tmp_path, "\n".join(lines) + "\n")
    _, out, err = run(capsys, "forecast", str(p), "--backlog", "10")
    assert "Value items with no story points (2026-07-09 to 2026-09-30): 2" in out, err


def test_one_item_with_no_points_is_singular(tmp_path, capsys):
    p = write(tmp_path, rows(["2"] * 39 + [""]))
    _, out, _ = run(capsys, "forecast", str(p), "--backlog", "10")
    assert "Value items with no story points (2026-07-09 to 2026-09-30): 1" in out
    from mcf.web import logic

    f = logic.forecast_from_bytes(rows(["2"] * 39 + [""]).encode(), backlog=10).facts
    assert logic.no_points_line(f).startswith("1 work item done between")  # MCF-33 words


def test_points_only_outside_the_history_window_is_not_available(tmp_path, capsys):
    p = write(tmp_path, rows(["3"] * 10 + [""] * 84))  # the 10 with points are older
    code, out, _ = run(capsys, "forecast", str(p), "--backlog", "10")
    assert code == 0
    assert f"Velocity: {NOT_AVAILABLE}" in out


def test_the_page_logic_gives_dates_with_no_points():
    from mcf.web import logic

    data = rows([""] * 40).encode()
    result = logic.forecast_from_bytes(data, backlog=10)
    f = result.facts
    assert f.mc50 <= f.mc85 <= f.mc95
    assert f.velocity_date is None and f.items_no_points == 40
    assert logic.marker_table(f)["label"].tolist() == ["50/50 (P50)", "Safer (P85)", "Safest (P95)"]


# --- AC2: some story points ------------------------------------------------------------------


def test_some_points_velocity_uses_them_and_counts_the_rest(tmp_path, capsys):
    p = write(tmp_path, rows(["2", ""] * 20))
    code, out, _ = run(capsys, "forecast", str(p), "--backlog", "10")
    assert code == 0
    # 20 items x 2 points in 6 sprints = 6.7 points per 2 weeks
    assert "Velocity: 2026-" in out and "(6.7 points per 2 weeks;" in out
    assert "Value items with no story points (2026-07-09 to 2026-09-30): 20" in out


def test_all_points_shows_no_count_line(tmp_path, capsys):
    p = write(tmp_path, rows(["2"] * 40))
    _, out, _ = run(capsys, "forecast", str(p), "--backlog", "10")
    assert "no story points" not in out


def test_a_bad_point_is_still_an_error(tmp_path, capsys):
    p = write(tmp_path, rows(["2", "x"]))
    code, _, err = run(capsys, "forecast", str(p), "--backlog", "10")
    assert code == 1 and "bad Story_Point" in err


# --- AI explanation: no velocity sentence without a velocity date -----------------------------


def facts(**kw) -> ForecastFacts:
    base = dict(
        t=T,
        backlog=10,
        window_start=T - timedelta(days=83),
        window_end=T,
        items_done=40,
        mc50=T + timedelta(days=10),
        mc85=T + timedelta(days=14),
        mc95=T + timedelta(days=17),
        runs=10_000,
        velocity_date=None,
        velocity_per_sprint=None,
        points_needed=None,
        points_estimated=True,
        open_items=0,
        rows_no_date=0,
        bug_share_percent=None,
        items_no_points=40,
    )
    base.update(kw)
    return ForecastFacts(**base)


def test_no_velocity_date_offers_no_velocity_or_points_sentence():
    f = facts()
    assert qualities(f)["velocity"] == "none"
    ids = applicable_ids(f)
    assert not [i for i in ids if i.startswith("velocity") or i == "points_estimated"]
    options = build_prompt(f)["messages"][0]["content"].split("Sentences you can choose:")[1]
    assert "velocity" not in options.lower()


@pytest.mark.parametrize(
    "kw",
    [
        {"velocity_date": T + timedelta(days=12)},  # a date with no velocity numbers
        {"velocity_per_sprint": 3.0},
        {"points_needed": 30.0},
    ],
)
def test_velocity_fields_are_all_set_or_all_none(kw):
    with pytest.raises(ValueError, match="all set or all None"):
        facts(**kw)


def test_items_no_points_is_a_whole_number_of_0_or_more():
    with pytest.raises(ValueError):
        facts(items_no_points=-1)
    with pytest.raises(TypeError):
        facts(items_no_points=1.0)


def test_items_no_points_is_required_and_at_most_items_done():
    with pytest.raises(ValueError, match="items_no_points"):
        facts(items_no_points=41)
    base = facts().__dict__ | {}
    del base["items_no_points"]
    with pytest.raises(TypeError):
        ForecastFacts(**base)


def test_a_velocity_date_needs_a_velocity_above_0():
    with pytest.raises(ValueError, match="velocity_per_sprint"):
        facts(velocity_date=T + timedelta(days=9), velocity_per_sprint=0.0, points_needed=3.0)


def test_the_prompt_version_is_5_for_the_none_qualities():
    from mcf.explain.check import parse_selection
    from mcf.explain.prompt import PROMPT_VERSION

    assert PROMPT_VERSION == "5"
    reply = '{"sentences": ["fifty_not_certain", "share_85", "velocity_50_85"]}'
    text, reason = parse_selection(reply, facts())
    assert text is None and reason  # a velocity sentence is refused with no velocity date


def test_the_page_says_nothing_about_a_velocity_date_it_does_not_have():
    from mcf.web import logic

    f = logic.forecast_from_bytes(rows([""] * 40).encode(), backlog=10).facts
    assert "velocity date" not in logic.no_points_line(f).lower()


# --- AC3: the back-test path does not change (ADR 0002) ----------------------------------------


def test_the_back_test_loader_still_needs_the_point_column(tmp_path):
    p = write(tmp_path, rows(["x"] * 3, header="Issue_Key,Type,Resolution_Date"))
    with pytest.raises(LoadError, match="missing column"):
        load_issues(p)


def test_the_back_test_type_check_still_needs_a_point_on_each_value_item(tmp_path):
    issues, _ = load_issues(write(tmp_path, rows(["2", ""])))
    with pytest.raises(IssueTypeError, match="has no story point"):
        sort_types(issues, "team.csv")
