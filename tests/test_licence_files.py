"""MCF-9 acceptance checks: licence and notice files (D08, D09)."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# MD5 of the unchanged, official Apache License 2.0 text.
APACHE_2_MD5 = "86d3f3a95c324c9479bd8986968f4327"


def test_licence_is_apache_2():
    text = (ROOT / "LICENSE").read_text()
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION" in text
    assert "END OF TERMS AND CONDITIONS" in text
    assert hashlib.md5((ROOT / "LICENSE").read_bytes()).hexdigest() == APACHE_2_MD5


def test_notice_names_owner_and_states_no_dataset():
    text = (ROOT / "NOTICE").read_text()
    assert "Copyright 2026 Aswin Guruswamy" in text
    assert "Apache License, Version 2.0" in text
    assert "does not include" in text and "TAWOS" in text


def test_package_licence_matches():
    assert 'license = "Apache-2.0"' in (ROOT / "pyproject.toml").read_text()
