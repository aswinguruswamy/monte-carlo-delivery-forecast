"""MCF-22 acceptance checks for D33.1: Claude picks PM-approved sentences by ID (R4, NFR3-5).

Code writes every number and date. Claude returns only sentence IDs. Code checks that
each ID exists, applies to this forecast, and that the 50%-date sentence comes first.
Any other reply drops the AI text, and the plain report always shows.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from mcf.explain.bank import BANK, MANDATORY, applicable_ids, qualities
from mcf.explain.check import (
    REASON_TEXT,
    explain_checked,
    parse_selection,
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
        mc50=date(2020, 7, 20),  # 20 days after t
        mc85=date(2020, 7, 28),
        mc95=date(2020, 8, 2),  # 13 days after the 50% date: ratio 0.65 -> wide
        runs=10_000,
        velocity_date=date(2020, 7, 25),  # between the 50% and 85% dates
        velocity_per_sprint=31.5,
        points_needed=80.0,
        points_estimated=True,
        open_items=3,
        rows_no_date=1,
        bug_share_percent=21,
    )
    base.update(over)
    return ForecastFacts(**base)


# --- the sentence bank (PM-approved text) ---------------------------------------

CERTAIN = re.compile(
    r"\b(will|won't|shall|certainly|guarantee[ds]?|definite\w*|for sure|assured|no doubt|"
    r"count on|promise\w*|deadline|due date|target|must|always|never|confirmed|fixed|"
    r"likely|probabl\w*|reliable|rely)\b",
    re.I,
)


def test_bank_sentences_hold_no_numbers_except_the_labels():
    for sid, text in BANK.items():
        rest = re.sub(r"\b(50|85|95)%", "", text)
        assert not re.search(r"\d", rest), sid
        assert text.isascii(), sid


def test_bank_sentences_never_sound_certain():
    for sid, text in BANK.items():
        allowed = re.sub(r"\bnot certain\b", "", text, flags=re.I)
        assert not CERTAIN.search(allowed), (sid, text)


def test_the_mandatory_sentence_says_the_50_percent_date_is_not_certain():
    assert MANDATORY in BANK
    assert "50% date is not certain" in BANK[MANDATORY]


# --- qualities: code turns numbers into fixed words ----------------------------


def test_qualities_from_the_facts():
    q = qualities(facts())
    assert q == {
        "spread": "wide",
        "velocity": "between 50 and 85",
        "points": "estimated",
        "open_items": "some",
        "bugs": "low",
    }


@pytest.mark.parametrize(
    "velocity_day, expected",
    [
        (19, "before 50"),
        (20, "between 50 and 85"),
        (28, "between 50 and 85"),
        (29, "between 85 and 95"),
        (33, "between 85 and 95"),
        (34, "after 95"),
    ],
)
def test_velocity_position(velocity_day, expected):
    v = date(2020, 7, 1) + timedelta(days=velocity_day - 1)
    assert qualities(facts(velocity_date=v))["velocity"] == expected


def test_narrow_spread_and_other_qualities():
    q = qualities(
        facts(
            mc85=date(2020, 7, 22),
            mc95=date(2020, 7, 24),
            points_estimated=False,
            open_items=0,
            bug_share_percent=30,
        )
    )
    assert (q["spread"], q["points"], q["open_items"], q["bugs"]) == (
        "narrow",
        "given",
        "none",
        "high",
    )
    assert qualities(facts(bug_share_percent=None))["bugs"] == "none"


def test_applicable_ids_follow_the_qualities():
    ids = applicable_ids(facts())
    assert MANDATORY in ids
    assert "spread_wide" in ids and "spread_narrow" not in ids
    assert "velocity_50_85" in ids and "velocity_after_95" not in ids
    assert "points_estimated" in ids and "open_items" in ids
    assert "bugs_high" not in ids


# --- parse_selection: the closed check ------------------------------------------


def good_reply(*ids):
    return json.dumps({"sentences": list(ids)})


def test_a_valid_selection_renders_the_bank_text():
    text, reason = parse_selection(good_reply(MANDATORY, "share_85", "spread_wide"), facts())
    assert reason is None
    assert text == " ".join([BANK[MANDATORY], BANK["share_85"], BANK["spread_wide"]])


@pytest.mark.parametrize(
    "reply",
    [
        "The 50% date will happen.",  # free text
        good_reply("share_85", MANDATORY, "use_95"),  # mandatory not first
        good_reply(MANDATORY, "share_85"),  # too few
        good_reply(
            MANDATORY, "share_85", "use_95", "range", "pace_assumption", "simulated", "spread_wide"
        ),  # too many
        good_reply(MANDATORY, "share_85", "share_85"),  # duplicate
        good_reply(MANDATORY, "share_85", "made_up"),  # unknown ID
        good_reply(MANDATORY, "share_85", "spread_narrow"),  # does not apply: spread is wide
        good_reply(MANDATORY, "share_85", "velocity_after_95"),  # does not apply
        json.dumps({"sentences": [MANDATORY, "share_85", "use_95"], "note": "x"}),  # extra key
        "Here you go: " + good_reply(MANDATORY, "share_85", "use_95"),  # text around JSON
        json.dumps({"sentences": [MANDATORY, 1, "use_95"]}),
        json.dumps([MANDATORY, "share_85", "use_95"]),
        "",
    ],
)
def test_any_other_reply_is_dropped(reply):
    text, reason = parse_selection(reply, facts())
    assert text is None and reason == REASON_TEXT


def test_whitespace_around_the_json_is_fine():
    text, reason = parse_selection(
        "\n " + good_reply(MANDATORY, "share_85", "use_95") + " \n", facts()
    )
    assert reason is None and text


# --- prompt v4 --------------------------------------------------------------------


def test_prompt_lists_only_applicable_sentences_and_qualities_as_words():
    from mcf.explain.prompt import PROMPT_VERSION, build_prompt

    prompt = build_prompt(facts())
    assert PROMPT_VERSION == "4"
    user = prompt["messages"][0]["content"]
    for sid in applicable_ids(facts()):
        assert sid in user
    assert "spread_narrow" not in user
    assert "wide" in user
    rest = user
    for sid in applicable_ids(facts()):
        rest = rest.replace(sid, "")
    assert not re.search(r"\d", re.sub(r"\b(50|85|95)%|\b(50|85|95)\b", "", rest))


# --- the safe path (NFR5) -----------------------------------------------------


def transport(text: str | None = None, error: Exception | None = None):
    def send(url, headers, body, timeout):
        if error is not None:
            raise error
        return json.dumps(
            {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}
        ).encode()

    return send


def test_good_selection_is_returned():
    text, reason = explain_checked(
        facts(), transport=transport(good_reply(MANDATORY, "share_85", "use_95")), api_key="k"
    )
    assert reason is None and text.startswith(BANK[MANDATORY])


def test_free_text_is_dropped_with_a_fixed_reason():
    text, reason = explain_checked(facts(), transport=transport("It needs 41 items."), api_key="k")
    assert text is None and reason == REASON_TEXT


def test_api_failure_gives_no_text_and_a_reason():
    text, reason = explain_checked(facts(), transport=transport(error=OSError("x")), api_key="k")
    assert text is None and "API call failed" in reason


def test_missing_key_gives_no_text_and_a_reason(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, reason = explain_checked(facts(), transport=transport("{}"))
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


def test_cli_adds_the_selected_sentences(capsys, monkeypatch):
    code, out = run_cli(capsys, monkeypatch, transport(good_reply(MANDATORY, "share_85", "use_95")))
    assert code == 0
    assert out.startswith(EXPECTED)
    assert "Explanation (AI-selected, approved sentences):" in out
    assert BANK[MANDATORY] in out


def test_cli_drops_a_bad_reply_and_keeps_the_plain_report(capsys, monkeypatch):
    code, out = run_cli(capsys, monkeypatch, transport("It will be done by 2020-07-20."))
    assert code == 0
    assert out.startswith(EXPECTED)
    assert "will be done" not in out
    assert f"AI explanation not shown: {REASON_TEXT}" in out


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
    run_cli(capsys, monkeypatch, transport(good_reply(MANDATORY, "share_85", "use_95")))
    assert len(calls) == 1
