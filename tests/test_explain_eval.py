"""MCF-23 checks for the AI evaluation set (D35; success measure 3; NFR4).

The live run is a manual GitHub workflow with the PM's key. These tests use fakes
only (CLAUDE.md test rule 2): no test calls the paid API.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from mcf.explain import eval as ev
from mcf.explain.bank import BANK, CONDITIONS, MANDATORY, applicable_ids, qualities
from mcf.explain.prompt import build_prompt
from mcf.result import ForecastFacts

ROOT = Path(__file__).resolve().parents[1]
EVAL_WORKFLOW = ROOT / ".github" / "workflows" / "eval.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
KEY = "sk-ant-test-0000-SECRET"


def good_reply(facts: ForecastFacts) -> bytes:
    ids = applicable_ids(facts)
    others = [i for i in ids if i != MANDATORY][:3]
    text = json.dumps({"sentences": [MANDATORY, *others]})
    return json.dumps(
        {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}
    ).encode()


def text_reply(text: str) -> bytes:
    return json.dumps(
        {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}
    ).encode()


class FakeTransport:
    """Answers with a valid choice for the facts in the request, or a fixed reply."""

    def __init__(self, fixed: bytes | None = None, fail: Exception | None = None):
        self.fixed, self.fail, self.calls, self.headers = fixed, fail, 0, []

    def __call__(self, url, headers, body, timeout):
        self.calls += 1
        self.headers.append(headers)
        if self.fail is not None:
            raise self.fail
        if self.fixed is not None:
            return self.fixed
        # choose IDs from the sentences offered in the prompt
        content = json.loads(body)["messages"][0]["content"]
        offered = [ln[2:].split(":")[0] for ln in content.splitlines() if ln.startswith("- ")]
        offered = [i for i in offered if i in BANK]
        ids = [MANDATORY, *[i for i in offered if i != MANDATORY][:3]]
        return text_reply(json.dumps({"sentences": ids}))


# --- the fixed cases ---------------------------------------------------------------


def test_there_are_10_fixed_cases_with_unique_ids():
    cases = ev.cases()
    assert len(cases) == 10
    assert len({c.case_id for c in cases}) == 10


def test_each_case_makes_valid_facts_and_is_repeatable():
    first = [c.facts() for c in ev.cases()]
    second = [c.facts() for c in ev.cases()]
    assert all(isinstance(f, ForecastFacts) for f in first)
    assert first == second


def test_the_cases_cover_every_quality_value_and_every_bank_sentence():
    facts = [c.facts() for c in ev.cases()]
    seen = {(k, v) for f in facts for k, v in qualities(f).items()}
    assert set(CONDITIONS.values()) <= seen
    assert ("bugs", "low") in seen and ("bugs", "none") in seen
    assert ("points", "given") in seen and ("open_items", "none") in seen
    offered = {i for f in facts for i in applicable_ids(f)}
    assert offered == set(BANK)


def test_one_case_is_the_injection_case_built_from_a_csv():
    inj = [c for c in ev.cases() if c.injection]
    assert len(inj) == 1
    assert inj[0].forbidden  # the instruction text that must never reach the prompt


def test_the_injection_text_never_reaches_the_prompt():
    case = next(c for c in ev.cases() if c.injection)
    prompt = json.dumps(build_prompt(case.facts())).lower()
    for token in case.forbidden:
        assert token.lower() not in prompt


# --- the number and date check --------------------------------------------------------


def test_bank_text_has_no_wrong_numbers_or_dates():
    for text in BANK.values():
        assert ev.wrong_numbers(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "Done by 2026-11-05.",
        "About 12 days.",
        "The 80% date is safe.",
        "It ends in November.",
        "Ready on Friday.",
        "3.5 weeks left.",
    ],
)
def test_wrong_numbers_finds_numbers_dates_months_and_weekdays(text):
    assert ev.wrong_numbers(text) != []


# --- running the set with fakes -------------------------------------------------------


def test_a_good_model_passes_with_30_records():
    fake = FakeTransport()
    result = ev.run_eval(ev.cases(), runs=3, transport=fake, api_key=KEY)
    s = result["summary"]
    assert fake.calls == 30
    assert s["runs_total"] == 30
    assert s["format_pass"] == 30
    assert s["wrong_numbers"] == 0
    assert s["api_errors"] == 0
    assert s["injection_prompt_clean"] is True
    assert s["injection_runs_pass"] == 3
    assert s["passed"] is True


def test_a_reply_with_free_text_fails_the_format_check():
    fake = FakeTransport(fixed=text_reply("The 50% date is 2026-11-05 for sure."))
    result = ev.run_eval(ev.cases(), runs=1, transport=fake, api_key=KEY)
    s = result["summary"]
    assert s["format_pass"] == 0
    assert s["passed"] is False
    # the rejected reply text never becomes shown text
    assert all(r["shown_text"] is None for r in result["records"])


def test_an_api_failure_is_counted_and_fails_the_set():
    fake = FakeTransport(fail=TimeoutError())
    result = ev.run_eval(ev.cases(), runs=1, transport=fake, api_key=KEY)
    s = result["summary"]
    assert s["api_errors"] == 10
    assert s["passed"] is False


def test_one_bad_run_fails_the_whole_set():
    good = FakeTransport()
    calls = {"n": 0}

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        if calls["n"] == 7:
            return text_reply('{"sentences": ["range"]}')
        return good(url, headers, body, timeout)

    s = ev.run_eval(ev.cases(), runs=3, transport=transport, api_key=KEY)["summary"]
    assert s["format_pass"] == 29
    assert s["passed"] is False


def test_the_key_is_never_in_the_result():
    fake = FakeTransport(fail=RuntimeError(KEY))
    result = ev.run_eval(ev.cases(), runs=1, transport=fake, api_key=KEY)
    assert KEY not in json.dumps(result)
    assert KEY not in ev.summary_block(result)


def test_the_result_records_the_prompt_version_model_and_runs():
    result = ev.run_eval(ev.cases(), runs=1, transport=FakeTransport(), api_key=KEY, model="m-1")
    assert result["prompt_version"] == "4"
    assert result["model"] == "m-1"
    assert result["runs_per_case"] == 1


def test_the_summary_block_has_clear_start_and_end_markers():
    result = ev.run_eval(ev.cases(), runs=1, transport=FakeTransport(), api_key=KEY)
    block = ev.summary_block(result)
    lines = block.splitlines()
    assert lines[0] == "===== EVAL RESULT START ====="
    assert lines[-1] == "===== EVAL RESULT END ====="
    assert "PASS" in block


# --- the command ---------------------------------------------------------------------


def test_main_without_a_key_makes_no_call_and_exits_2(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake = FakeTransport()
    monkeypatch.setattr(ev, "TRANSPORT", fake)
    assert ev.main(["--out", str(tmp_path / "r.json")]) == 2
    assert fake.calls == 0
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_main_writes_json_and_exits_0_on_pass(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setattr(ev, "TRANSPORT", FakeTransport())
    out = tmp_path / "r.json"
    assert ev.main(["--out", str(out), "--runs", "3"]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["summary"]["runs_total"] == 30
    printed = capsys.readouterr().out
    assert "===== EVAL RESULT START =====" in printed
    assert KEY not in printed and KEY not in out.read_text(encoding="utf-8")


def test_main_exits_1_on_fail(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setattr(ev, "TRANSPORT", FakeTransport(fixed=text_reply("no")))
    assert ev.main(["--out", str(tmp_path / "r.json")]) == 1


@pytest.mark.parametrize("bad", ["0", "-1", "x", "11"])
def test_main_rejects_a_bad_run_count(bad, tmp_path):
    with pytest.raises(SystemExit):
        ev.main(["--runs", bad, "--out", str(tmp_path / "r.json")])


# --- the workflow (D35) ---------------------------------------------------------------


def _workflow(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["on"] = data.pop(True, data.get("on"))  # YAML 1.1 reads "on" as True
    return data


def test_the_eval_workflow_runs_only_by_hand():
    wf = _workflow(EVAL_WORKFLOW)
    assert set(wf["on"]) == {"workflow_dispatch"}


def test_the_eval_workflow_reads_only_and_takes_the_key_from_a_secret():
    wf = _workflow(EVAL_WORKFLOW)
    assert wf["permissions"] == {"contents": "read"}
    text = EVAL_WORKFLOW.read_text(encoding="utf-8")
    assert "${{ secrets.ANTHROPIC_API_KEY }}" in text
    assert "python -m mcf.explain.eval" in text
    assert "sk-ant" not in text


def test_ci_never_runs_the_live_eval():
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "mcf.explain.eval" not in text
    assert "ANTHROPIC_API_KEY" not in text
