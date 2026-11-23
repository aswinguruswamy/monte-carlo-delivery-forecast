"""MCF v2 task M5 (spec R10.1): one live run saves the AI explanation of the sample file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import save_example  # noqa: E402

from tests_helpers_ai import bad_transport, good_transport  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "save-example.yml"


def test_a_good_reply_is_saved_with_the_run_details(tmp_path, monkeypatch):
    monkeypatch.delenv("MCF_MODEL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")  # the fake transport ignores it
    out = tmp_path / "saved.json"
    assert save_example.main(out, transport=good_transport()) == 0
    data = json.loads(out.read_text())
    assert data["text"].startswith("The 50% date is not certain")
    assert data["backlog"] == save_example.BACKLOG == 40
    assert data["ai_run"].startswith("AI: ") and " · prompt v" in data["ai_run"]
    assert set(data) == {"text", "ai_run", "backlog", "made"}


def test_a_dropped_reply_saves_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    out = tmp_path / "saved.json"
    assert save_example.main(out, transport=bad_transport()) == 1
    assert not out.exists()


def test_the_workflow_runs_only_by_hand_and_takes_the_key_from_a_secret():
    wf = yaml.safe_load(WORKFLOW.read_text())
    wf["on"] = wf.pop(True, wf.get("on"))
    assert set(wf["on"]) == {"workflow_dispatch"}
    assert wf["permissions"] == {"contents": "read"}
    text = WORKFLOW.read_text()
    assert "${{ secrets.ANTHROPIC_API_KEY }}" in text
    assert "scripts/save_example.py" in text
