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
KEY = "fake-test-key-0000-SECRET"


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
        content = content.split("Sentences you can choose:", 1)[1]
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
    assert "sk-" + "ant-" not in text


def test_ci_never_runs_the_live_eval():
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "mcf.explain.eval" not in text
    assert "ANTHROPIC_API_KEY" not in text


def test_injection_text_in_the_prompt_fails_the_set():
    # Plant the bug: a case whose "forbidden" text is in every prompt.
    leaky = ev.Case("leak", ev.cases()[0].facts, injection=True, forbidden=("sentences",))
    s = ev.run_eval([leaky], runs=1, transport=FakeTransport(), api_key=KEY)["summary"]
    assert s["format_pass"] == 1
    assert s["injection_prompt_clean"] is False
    assert s["passed"] is False


# --- review fixes (PR #24) -------------------------------------------------------------


def fixed_choice(*ids: str) -> bytes:
    return text_reply(json.dumps({"sentences": list(ids)}))


def test_a_number_in_a_shown_sentence_fails_the_set(monkeypatch):
    monkeypatch.setitem(BANK, "share_85", "Share the 85% date in 12 days.")
    calls = {"n": 0}

    def transport(url, headers, body, timeout):  # the injection case (last) stays clean,
        calls["n"] += 1  # so only the wrong-number gate can fail the set
        if calls["n"] == 10:
            return fixed_choice(MANDATORY, "range", "use_95")
        return fixed_choice(MANDATORY, "share_85", "range")

    assert ev.cases()[-1].injection
    result = ev.run_eval(ev.cases(), runs=1, transport=transport, api_key=KEY)
    assert result["summary"]["wrong_numbers"] == 9
    assert result["summary"]["injection_runs_pass"] == 1
    assert result["summary"]["status"] == "FAIL"
    assert result["summary"]["passed"] is False


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError(KEY),
        __import__("urllib.error").error.HTTPError("https://x", 500, KEY, None, None),
    ],
)
def test_main_never_shows_the_key_from_the_environment(monkeypatch, tmp_path, capsys, error):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setattr(ev, "TRANSPORT", FakeTransport(fail=error))
    out = tmp_path / "r.json"
    code = ev.main(["--out", str(out), "--runs", "1"])
    printed = capsys.readouterr()
    assert code == 3  # inconclusive: no answer from the API
    for text in (printed.out, printed.err, out.read_text(encoding="utf-8")):
        assert KEY not in text


def test_a_transient_api_error_is_retried_once():
    good = FakeTransport()
    calls = {"n": 0}

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError()
        return good(url, headers, body, timeout)

    s = ev.run_eval(ev.cases(), runs=1, transport=transport, api_key=KEY)["summary"]
    assert calls["n"] == 11
    assert s["api_errors"] == 0
    assert s["status"] == "PASS"


def test_api_errors_make_the_set_inconclusive_not_a_format_failure():
    fake = FakeTransport(fail=TimeoutError())
    result = ev.run_eval(ev.cases(), runs=1, transport=fake, api_key=KEY)
    s = result["summary"]
    assert fake.calls == 20  # one retry for each run
    assert s["api_errors"] == 10
    assert s["runs_answered"] == 0
    assert s["format_pass"] == 0
    assert s["status"] == "INCONCLUSIVE"
    assert "Format checks passed: 0 of 0 answered runs" in ev.summary_block(result)


def test_a_failed_run_with_some_api_errors_is_still_a_fail():
    calls = {"n": 0}

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise TimeoutError()
        return text_reply("free text")

    s = ev.run_eval(ev.cases(), runs=1, transport=transport, api_key=KEY)["summary"]
    assert s["api_errors"] == 1
    assert s["status"] == "FAIL"


def test_a_reply_that_did_not_stop_normally_is_a_model_failure_not_an_api_error():
    reply = json.dumps(
        {"content": [{"type": "text", "text": "{"}], "stop_reason": "max_tokens"}
    ).encode()
    s = ev.run_eval(ev.cases(), runs=1, transport=FakeTransport(fixed=reply), api_key=KEY)[
        "summary"
    ]
    assert s["api_errors"] == 0
    assert s["format_pass"] == 0
    assert s["status"] == "FAIL"


def test_a_setup_error_exits_2_with_a_fixed_message(monkeypatch, tmp_path, capsys):
    from mcf.data.load import LoadError

    def broken() -> ForecastFacts:
        raise LoadError("secret detail")

    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    fake = FakeTransport()
    monkeypatch.setattr(ev, "TRANSPORT", fake)
    monkeypatch.setattr(ev, "cases", lambda: [ev.Case("broken", broken)])
    assert ev.main(["--out", str(tmp_path / "r.json")]) == 2
    err = capsys.readouterr().err
    assert "eval: setup error (LoadError); no call was made" in err
    assert "secret detail" not in err
    assert fake.calls == 0


def test_a_set_without_the_injection_case_cannot_pass():
    no_injection = [c for c in ev.cases() if not c.injection]
    result = ev.run_eval(no_injection, runs=1, transport=FakeTransport(), api_key=KEY)
    assert result["summary"]["status"] == "FAIL"


def test_the_summary_shows_injection_runs_as_x_of_y():
    result = ev.run_eval(ev.cases(), runs=3, transport=FakeTransport(), api_key=KEY)
    assert "Injection-case runs passed: 3 of 3" in ev.summary_block(result)


def test_the_eval_workflow_is_hardened():
    wf = yaml.safe_load(EVAL_WORKFLOW.read_text())
    job = wf["jobs"]["eval"]
    assert job["timeout-minutes"] >= 60
    checkout = next(s for s in job["steps"] if "actions/checkout" in s.get("uses", ""))
    assert checkout["with"]["persist-credentials"] is False
    runs = wf[True]["workflow_dispatch"]["inputs"]["runs"]  # yaml reads "on" as True
    assert runs["type"] == "choice"
    assert runs["options"] == [str(n) for n in range(1, 11)]
