"""MCF-22 acceptance checks: every number and date in the AI text is checked (R4, NFR4, NFR5)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from mcf.explain.check import check_text, explain_checked
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


GOOD = (
    "From 2020-06-30, the team has a 50% chance to finish the next 40 items by July 20, 2020. "
    "Half of the simulated runs finish later, so the 50% date is not certain. "
    "The 85% date is 28 July 2020 and the 95% date is Aug 2, 2020. "
    "Velocity, at 31.5 points per 2 weeks, gives 2020-07-25. "
    "The history covers 84 days with 120 items done, and 21% of work items were bugs."
)


def test_a_clean_text_passes():
    assert check_text(GOOD, facts()) == []


@pytest.mark.parametrize(
    "text, problem",
    [
        ("The 85% date is 2020-07-29.", "date"),  # one day off
        ("The 85% date is July 29, 2020.", "date"),
        ("The 85% date is 29 July 2020.", "date"),
        ("The team needs 41 items.", "number"),
        ("Velocity is 31.6 points per sprint.", "number"),
        ("About 22% were bugs.", "number"),
        ("That is 20 days from now.", "number"),  # not given; Claude calculated it
        ("It used 10,001 runs.", "number"),
        ("The 85% date is in mid-August.", None),  # no number: allowed
    ],
)
def test_numbers_and_dates_not_in_the_result_are_problems(text, problem):
    problems = check_text(text, facts())
    if problem is None:
        assert problems == []
    else:
        assert problems and problem in problems[0]


def test_allowed_numbers_with_commas_and_the_method_constants():
    text = "The 50%, 85% and 95% dates come from 10,000 runs over 84 days (6 sprints of 2 weeks)."
    assert check_text(text, facts()) == []


def test_a_month_day_date_without_year_must_match_a_fact_date():
    assert check_text("The 85% date is Jul 28.", facts()) == []
    assert check_text("The 85% date is Jul 27.", facts())


@pytest.mark.parametrize(
    "text",
    [
        "The work will be done on the 50% date, July 20, 2020.",
        "The 50% date is certain.",
        "You can definitely expect delivery by the 50% date.",
        "The 50% date of July 20, 2020 is guaranteed.",
        "The team will finish by July 20, 2020.",  # the 50% date without saying "50%"
    ],
)
def test_certainty_about_the_50_percent_date_fails(text):
    problems = check_text(text, facts())
    assert any("certain" in p for p in problems), problems


def test_negated_certainty_is_fine():
    assert check_text("The 50% date is not certain; it is not a guarantee.", facts()) == []


def test_certainty_words_fail_anywhere_in_the_text():
    """Fail closed (review of PR #22): a certainty word anywhere drops the text."""
    assert check_text("Half of the runs will finish after the 85% date of Jul 28.", facts())


def test_empty_text_is_a_problem():
    assert check_text("   ", facts())


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
    text, reason = explain_checked(facts(), transport=transport(GOOD), api_key="k")
    assert text == GOOD and reason is None


def test_text_with_a_wrong_number_is_dropped():
    text, reason = explain_checked(facts(), transport=transport("It needs 41 items."), api_key="k")
    assert text is None and "41" in reason


def test_api_failure_gives_no_text_and_a_reason():
    text, reason = explain_checked(facts(), transport=transport(error=OSError("x")), api_key="k")
    assert text is None and "API call failed" in reason


def test_missing_key_gives_no_text_and_a_reason(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, reason = explain_checked(facts(), transport=transport(GOOD))
    assert text is None and "ANTHROPIC_API_KEY" in reason


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
    good = "The 85% date is 2020-07-24, and the 50% date of 2020-07-20 is not certain."
    code, out = run_cli(capsys, monkeypatch, transport(good))
    assert code == 0
    assert out.startswith(EXPECTED)
    assert "Explanation (AI, checked):" in out and good in out


def test_cli_drops_bad_text_and_keeps_the_plain_report(capsys, monkeypatch):
    code, out = run_cli(capsys, monkeypatch, transport("It will be done by 2020-07-20."))
    assert code == 0
    assert out.startswith(EXPECTED)
    assert "will be done" not in out
    assert "AI explanation not shown:" in out


def test_cli_api_failure_keeps_the_plain_report(capsys, monkeypatch):
    code, out = run_cli(capsys, monkeypatch, transport(error=TimeoutError()))
    assert code == 0
    assert out.startswith(EXPECTED)
    assert "AI explanation not shown: the API call failed" in out


# --- review fixes (PR #22): adversarial texts must fail -----------------------


@pytest.mark.parametrize(
    "text",
    [
        # certainty in other words, or the 50% date under another name
        "The team is going to finish on July 20, 2020.",
        "Expect delivery on July 20, 2020.",
        "You can count on July 20, 2020.",
        "Delivery on July 20, 2020 is assured.",
        "No doubt: July 20, 2020.",
        "The 50% date won't slip.",
        "July 20, 2020 is a lock.",
        "It is not uncertain that the work ends on July 20, 2020.",
        "The 50-percent date is sure.",
        "The 50th percentile date shall hold.",
        "We promise July 20, 2020.",
        "e.g. the 50% date. It will happen.",
        "The 50% date is not certain. It will happen though.",
        # swapped percentiles
        "The 50% date is Jul 28.",
        "The 95% date is Jul 20.",
        "The median date is 2020-08-02.",
        # wrong numbers in other forms
        "The team needs forty-one items.",
        "It takes three weeks.",
        "A dozen items remain.",
        "The work ends on the 3rd of August.",
        "It used 1e9 runs.",
        "Release v9 is planned.",
        "Velocity is -31.5 points.",
        "About 1/2 of the runs finish later.",
        "Delivery is next week.",
        "Delivery is on Monday.",
        "Delivery is tomorrow.",
        # method numbers with the wrong meaning
        "There are 85 items left.",
        "The team ran 6 runs.",
        # terminal control characters
        "The 85% date is Jul 28.\x1b[A\x1b[K",
    ],
)
def test_adversarial_texts_fail(text):
    assert check_text(text, facts()), text


@pytest.mark.parametrize(
    "text",
    [
        "The 50% date is Jul 20 and the 85% date is Jul 28.",
        "July 28, 2020 is the 85% date; August 2, 2020 is the 95% date.",
        "The median (50%) date is 2020-07-20, which is not certain.",
        "The 50% date is not a guarantee: half of the runs finish later.",
    ],
)
def test_correct_bindings_pass(text):
    assert check_text(text, facts()) == [], check_text(text, facts())


def test_the_reason_line_never_repeats_the_ai_text():
    for bad in ("The 85% date is July 29, 2020.", "It needs 41 items.", "It will happen."):
        text, reason = explain_checked(facts(), transport=transport(bad), api_key="k")
        assert text is None
        assert "29" not in reason and "41" not in reason and "happen" not in reason
        assert reason in {
            "a number or date in it is not in the result",
            "it describes a date as certain",
            "it holds text that cannot be checked",
        }


def test_cli_computes_the_forecast_once(capsys, monkeypatch):
    import mcf.cli as cli

    calls = []
    real = cli._compute_with_load

    def counting(args):
        calls.append(1)
        return real(args)

    monkeypatch.setattr(cli, "_compute_with_load", counting)
    good = "The 85% date is 2020-07-24, and the 50% date of 2020-07-20 is not certain."
    run_cli(capsys, monkeypatch, transport(good))
    assert len(calls) == 1


def test_prompt_tells_the_model_the_check_rules():
    from mcf.explain.prompt import PROMPT_VERSION, build_prompt

    system = build_prompt(facts())["system"].lower()
    assert PROMPT_VERSION == "2"
    for words in ("digits", "will", "certain", "relative"):
        assert words in system, words
