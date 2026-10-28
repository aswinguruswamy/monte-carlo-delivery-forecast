"""MCF-9 acceptance checks: licence and notice files (D08, D09)."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# SHA-256 of the unchanged official Apache License 2.0 text, as shipped in the
# LICENSE files of cyclonedx-python-lib and license-expression (two identical
# copies; same terms, word for word, as /usr/share/common-licenses/Apache-2.0).
APACHE_2_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"


def test_licence_is_unchanged_apache_2():
    digest = hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest()
    assert digest == APACHE_2_SHA256


def test_notice_names_owner_states_no_dataset_and_cites_tawos():
    text = " ".join((ROOT / "NOTICE").read_text(encoding="utf-8").split())
    assert "Copyright 2026 Aswin Guruswamy" in text
    assert "This repository includes no dataset files." in text
    assert "A Versatile Dataset of Agile Open Source Software Projects" in text
    assert "MSR 2022" in text


def test_package_licence_matches():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = "Apache-2.0"' in text
