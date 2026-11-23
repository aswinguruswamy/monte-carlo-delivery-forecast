"""Save one live AI explanation of the sample forecast (MCF v2 spec R10.1, decision MD2).

Runs once, by hand, in the "Save AI example" workflow (it needs ANTHROPIC_API_KEY).
The keyless public demo then shows this saved text, labelled as a saved example.
The text passes the v1 check (approved sentences only) before it is saved.

    python scripts/save_example.py examples/saved_explanation.json
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from mcf.ai_run import ai_run_line
from mcf.explain.check import explain_checked
from mcf.explain.client import Transport, urllib_transport
from mcf.web.logic import forecast_from_bytes, sample_bytes

BACKLOG = 40  # the page's default backlog for the sample file


def main(out: Path, *, transport: Transport = urllib_transport) -> int:
    data = sample_bytes()
    if data is None:
        print("save_example: the sample file is missing", file=sys.stderr)
        return 1
    facts = forecast_from_bytes(data, backlog=BACKLOG).facts
    text, reason = explain_checked(facts, transport=transport)
    if text is None:
        print(f"save_example: no text saved: {reason}", file=sys.stderr)
        return 1
    record = {
        "text": text,
        "ai_run": ai_run_line(),
        "backlog": BACKLOG,
        "made": date.today().isoformat(),
    }
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "saved_explanation.json")))
