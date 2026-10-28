"""MCF-10 acceptance checks: download the TAWOS extract with checksums (D06, D08).

No test uses the network: each test passes a fake fetcher.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from mcf.data import download as dl


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fake_manifest(files: dict[str, bytes]) -> dict:
    return {
        "source": {
            "repo": "SOLAR-group/SPvsDevelopmentEffort",
            "commit": "e8ae43b",
            "folder": "Dataset/RQ2 and RQ3",
        },
        "files": [{"name": n, "sha256": sha(b), "rows": 1} for n, b in files.items()],
    }


def fetcher_for(files: dict[str, bytes], calls: list[str] | None = None):
    def fetch(url: str) -> bytes:
        if calls is not None:
            calls.append(url)
        name = dl.unquote(url.rsplit("/", 1)[1])
        return files[name]

    return fetch


# --- the real manifest (AC1) -------------------------------------------------


def test_manifest_pins_the_source_and_29_files_with_47205_rows():
    m = dl.load_manifest()
    assert m["source"]["repo"] == "SOLAR-group/SPvsDevelopmentEffort"
    assert m["source"]["commit"].startswith("e8ae43b")
    assert m["source"]["folder"] == "Dataset/RQ2 and RQ3"
    assert len(m["files"]) == 29
    assert len({f["name"] for f in m["files"]}) == 29
    assert sum(f["rows"] for f in m["files"]) == 47_205
    for f in m["files"]:
        assert f["name"].endswith(".csv")
        assert re.fullmatch(r"[0-9a-f]{64}", f["sha256"])


def test_url_uses_the_fixed_commit_and_escapes_spaces():
    url = dl.file_url(dl.load_manifest()["source"], "MESOS.csv")
    assert url.startswith(
        "https://raw.githubusercontent.com/SOLAR-group/SPvsDevelopmentEffort/e8ae43b"
    )
    assert url.endswith("/Dataset/RQ2%20and%20RQ3/MESOS.csv")


# --- download behaviour (AC1, AC2) -------------------------------------------


def test_download_writes_each_file_when_checksums_match(tmp_path):
    files = {"A.csv": b"x\n1\n", "B.csv": b"x\n2\n"}
    written = dl.download(tmp_path, fake_manifest(files), fetcher_for(files))
    assert sorted(p.name for p in written) == ["A.csv", "B.csv"]
    assert (tmp_path / "A.csv").read_bytes() == files["A.csv"]


def test_changed_file_stops_with_error_and_leaves_no_bad_file(tmp_path):
    good = {"A.csv": b"x\n1\n"}
    changed = {"A.csv": b"x\n999\n"}
    with pytest.raises(dl.ChecksumError, match="A.csv"):
        dl.download(tmp_path, fake_manifest(good), fetcher_for(changed))
    assert list(tmp_path.iterdir()) == []


def test_fetch_failure_stops_with_a_clear_error(tmp_path):
    def broken(url: str) -> bytes:
        raise OSError("connection refused")

    with pytest.raises(dl.DownloadError, match="A.csv.*connection refused"):
        dl.download(tmp_path, fake_manifest({"A.csv": b"x"}), broken)


def test_good_local_file_is_not_downloaded_again(tmp_path):
    files = {"A.csv": b"x\n1\n"}
    (tmp_path / "A.csv").write_bytes(files["A.csv"])
    calls: list[str] = []
    dl.download(tmp_path, fake_manifest(files), fetcher_for(files, calls))
    assert calls == []


def test_bad_local_file_is_replaced(tmp_path):
    files = {"A.csv": b"x\n1\n"}
    (tmp_path / "A.csv").write_bytes(b"tampered")
    dl.download(tmp_path, fake_manifest(files), fetcher_for(files))
    assert (tmp_path / "A.csv").read_bytes() == files["A.csv"]


# --- command line ------------------------------------------------------------


def test_cli_exit_codes(tmp_path, monkeypatch, capsys):
    files = {"A.csv": b"x\n1\n"}
    monkeypatch.setattr(dl, "load_manifest", lambda: fake_manifest(files))
    monkeypatch.setattr(dl, "http_get", fetcher_for(files))
    assert dl.main(["--dest", str(tmp_path)]) == 0
    assert "1 files OK" in capsys.readouterr().out

    monkeypatch.setattr(dl, "http_get", fetcher_for({"A.csv": b"changed"}))
    (tmp_path / "A.csv").unlink()
    assert dl.main(["--dest", str(tmp_path)]) == 1
    assert "checksum" in capsys.readouterr().err.lower()


def test_manifest_holds_metadata_only_no_data_rows():
    m = dl.load_manifest()
    assert set(m) == {"source", "files"}
    for f in m["files"]:
        assert set(f) == {"name", "sha256", "rows"}
