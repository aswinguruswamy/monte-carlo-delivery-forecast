"""MCF-22 acceptance checks for the D33 design (R4, NFR4, NFR5; CLAUDE.md AI rules).

D33: code writes every number and date. Claude writes a short plain paragraph that
holds no digit (only the labels 50%, 85% and 95%), no date, no month or weekday,
no number word and no certainty word. The check rejects anything else.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from mcf.explain.check import (
    REASON_CERTAIN,
    REASON_NUMBER,
    REASON_TEXT,
    check_text,
    explain_checked,
)
from mcf.result import ForecastFacts

T = date(2020, 6, 30)


def facts(**over) -> ForecastFacts:
    base = dict(
        t=T,
        backlog=40,
        window_start=T - timedelta(days=83),
        window_end=T,
        items_done=120,
        mc50=date(2020, 7, 20),
        mc85=date(2020, 7, 28),
        mc95=date(2020, 8, 2),
        runs=10_000,
        velocity_date=date(2020, 7, 25),
        velocity_per_sprint=31.5,
        points_needed=80.0,
        points_estimated=True,
        open_items=3,
        rows_no_date=1,
        bug_share_percent=21,
    )
    base.update(over)
    return ForecastFacts(**base)


GOOD = [
    "The 50% date is the middle result: half of the simulated runs finish later, so it is "
    "not certain. The 85% date gives more room and is a safer date to share with a sponsor. "
    "The 95% date is the cautious choice when a miss would be costly.",
    "Treat the 50% date as a coin toss, not a commitment. Plan on the 85% date. Use the 95% "
    "date when the cost of being late is high.",
    "Each date comes from many simulated runs of the team's recent pace. Later dates hold more "
    "of those runs, so they carry less risk.",
    "The median (50%) date is not a guarantee.",
    "Share a range, not a single day: the 85% and 95% dates show how much room to keep.",
]


@pytest.mark.parametrize("text", GOOD)
def test_good_explanations_pass(text):
    assert check_text(text, facts()) == []


@pytest.mark.parametrize(
    "text",
    [
        # any digit apart from the three labels
        "The team needs 41 items.",
        "The 85% date is 2020-07-29.",
        "About 22% of items were bugs.",
        "It used 10,000 runs.",
        "Release v9 is planned.",
        "It used 1e9 runs.",
        "The 50.0% date is the middle one.",
        "The 50 % date is the middle one.",
        "P50 is the middle one.",
        "Velocity is -31.5 points.",
        "About 1/2 of the runs finish later.",
        "The 85% date is in the 3rd week.",
        "The work takes 10:30 hours.",
        # dates without digits
        "The 85% date is in late July.",
        "Delivery is on Monday.",
        "Delivery is next week.",
        "Delivery is tomorrow.",
        "It ends in a fortnight.",
        "The 95% date is in early September.",
        # number words
        "The team needs forty-one items.",
        "It takes three weeks.",
        "A dozen items remain.",
        "Look at all three dates.",
        # certainty, synonyms, negation tricks
        "The 50% date will happen.",
        "The team is going to finish on the 50% date.",
        "Expect delivery on the 50% date.",
        "You can count on the 50% date.",
        "The 50% date is assured.",
        "No doubt about the 50% date.",
        "The 50% date won't slip.",
        "The 50% date is set in stone.",
        "The 50% date is locked in.",
        "Bank on the 50% date.",
        "It is a firm date.",
        "It is inevitable.",
        "It can't fail.",
        "It is a safe bet.",
        "It is pretty much a given.",
        "It is never uncertain.",
        "There is no uncertainty.",
        "It is not without certainty.",
        "It is not uncertain.",
        "The team is on track for the 50% date.",
        "The 50% date is the delivery date.",
        "The work ships on the 50% date.",
        "The 50% date is not guaranteed to slip.",
        "There is no guarantee the work takes longer than the 50% date.",
        "It is not certain that the work slips past the 50% date.",
        "We promise the 50% date.",
        "The 50% date shall hold.",
        "It is definitely the 50% date.",
        # velocity is described by code, not by Claude
        "The velocity date is later than the 95% date.",
        # characters that cannot be checked
        "The team wіll finish.",  # Cyrillic і
        "This is сertain.",  # Cyrillic с
        "The 85% date is ready.\x1b[A\x1b[K",
        "The 85 % date.",
        "Ｔhe date.",
        "",
        "   ",
    ],
)
def test_bad_texts_fail(text):
    assert check_text(text, facts()), repr(text)


def test_reasons_are_fixed_text():
    assert check_text("It needs 41 items.", facts())[0] == REASON_NUMBER
    assert check_text("The 50% date will happen.", facts())[0] == REASON_CERTAIN
    assert check_text("Wіll.", facts())[0] == REASON_TEXT


# --- the safe path (NFR5) -----------------------------------------------------


def transport(text: str | None = None, error: Exception | None = None):
    def send(url, headers, body, timeout):
        if error is not None:
            raise error
        return json.dumps(
            {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}
        ).encode()

    return send


def test_good_text_is_returned():
    text, reason = explain_checked(facts(), transport=transport(GOOD[0]), api_key="k")
    assert text == GOOD[0] and reason is None


def test_text_with_a_number_is_dropped_with_a_fixed_reason():
    text, reason = explain_checked(facts(), transport=transport("It needs 41 items."), api_key="k")
    assert text is None and reason == REASON_NUMBER


def test_api_failure_gives_no_text_and_a_reason():
    text, reason = explain_checked(facts(), transport=transport(error=OSError("x")), api_key="k")
    assert text is None and "API call failed" in reason


def test_missing_key_gives_no_text_and_a_reason(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, reason = explain_checked(facts(), transport=transport(GOOD[0]))
    assert text is None and "ANTHROPIC_API_KEY" in reason


def test_a_cut_reply_reason_is_fixed_text():
    def cut(url, headers, body, timeout):
        return json.dumps(
            {"content": [{"type": "text", "text": "x"}], "stop_reason": "<b>odd</b>"}
        ).encode()

    text, reason = explain_checked(facts(), transport=cut, api_key="k")
    assert text is None and "odd" not in reason


# --- CLI --explain --------------------------------------------------------------

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cli_team.csv"
EXPECTED = (Path(__file__).resolve().parent / "fixtures" / "cli_team_expected.txt").read_text()


def run_cli(capsys, monkeypatch, reply):
    import mcf.cli as cli

    monkeypatch.setattr(cli, "TRANSPORT", reply)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    code = cli.main(["forecast", str(FIXTURE), "--backlog", "30", "--explain"])
    return code, capsys.readouterr().out


def test_cli_without_explain_makes_no_call_and_prints_the_plain_report(capsys, monkeypatch):
    import mcf.cli as cli

    def boom(*a, **k):
        raise AssertionError("no API call without --explain")

    monkeypatch.setattr(cli, "TRANSPORT", boom)
    assert cli.main(["forecast", str(FIXTURE), "--backlog", "30"]) == 0
    assert capsys.readouterr().out == EXPECTED


def test_cli_adds_checked_text(capsys, monkeypatch):
    code, out = run_cli(capsys, monkeypatch, transport(GOOD[1]))
    assert code == 0
    assert out.startswith(EXPECTED)
    assert "Explanation (AI, checked):" in out and GOOD[1] in out


def test_cli_drops_bad_text_and_keeps_the_plain_report(capsys, monkeypatch):
    code, out = run_cli(capsys, monkeypatch, transport("It will be done by 2020-07-20."))
    assert code == 0
    assert out.startswith(EXPECTED)
    assert "will be done" not in out
    assert f"AI explanation not shown: {REASON_NUMBER}" in out


def test_cli_api_failure_keeps_the_plain_report(capsys, monkeypatch):
    code, out = run_cli(capsys, monkeypatch, transport(error=TimeoutError()))
    assert code == 0
    assert out.startswith(EXPECTED)
    assert "AI explanation not shown: the API call failed" in out


def test_cli_computes_the_forecast_once(capsys, monkeypatch):
    import mcf.cli as cli

    calls = []
    real = cli._compute_with_load

    def counting(args):
        calls.append(1)
        return real(args)

    monkeypatch.setattr(cli, "_compute_with_load", counting)
    run_cli(capsys, monkeypatch, transport(GOOD[0]))
    assert len(calls) == 1


def test_prompt_states_the_check_rules():
    from mcf.explain.prompt import PROMPT_VERSION, build_prompt

    system = build_prompt(facts())["system"].lower()
    assert PROMPT_VERSION == "3"
    for words in ("digit", "date", "month", "number word", "will", "certain", "velocity"):
        assert words in system, words
