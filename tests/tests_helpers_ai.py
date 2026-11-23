"""Fake AI transports for tests (CLAUDE.md test rule 2: no real paid API)."""

from __future__ import annotations

import json

MANDATORY = "fifty_not_certain"


def _reply(text: str):
    def send(url, headers, body, timeout):
        return json.dumps(
            {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}
        ).encode()

    return send


def good_transport():
    return _reply(json.dumps({"sentences": [MANDATORY, "share_85", "use_95"]}))


def bad_transport():
    return _reply("It will be done by 2020-07-20.")
