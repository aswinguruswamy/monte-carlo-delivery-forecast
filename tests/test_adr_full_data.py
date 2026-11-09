"""MCF-28 checks: ADR 0003 (full TAWOS data rules) is accepted before any run (R2)."""

from __future__ import annotations

import hashlib
from pathlib import Path

ADR = Path(__file__).resolve().parents[1] / "docs" / "adr" / "0003-full-tawos-data.md"
# Change rule: a change to the accepted ADR needs a new decision; this checksum shows it in CI.
ACCEPTED_SHA256 = "25736f726a5f1cb6cae0b4b50cb971b8f9c5b8596c6366daed7e9692da179715"


def text() -> str:
    return ADR.read_text(encoding="utf-8")


def test_the_adr_is_accepted_before_any_run():
    assert "Accepted by the PM on 2026-11-09 (D54), **before any v2 back-test run** (R2)" in text()


def test_the_adr_fixes_the_file_and_the_columns():
    t = text()
    assert "97dc0deaaa02ac75017d2b9cbe0765ac3377b5d7c10f9f88bc62de838f34badd" in t
    assert "`Resolution_Date`" in t and "**No other column is kept**" in t


def test_the_two_decisions_are_recorded():
    t = text()
    assert t.count("**Decided (PM, D54): A**") == 2


def test_the_adr_is_unchanged_since_acceptance():
    assert hashlib.sha256(ADR.read_bytes()).hexdigest() == ACCEPTED_SHA256
