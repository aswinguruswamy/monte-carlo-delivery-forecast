"""Download the TAWOS extract at a fixed commit and check each file (D06, D08).

The repository holds only the manifest (file names, SHA-256, row counts),
never the data. Run:

    python -m mcf.data.download --dest data
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from urllib.parse import quote, unquote

__all__ = [
    "ChecksumError",
    "DownloadError",
    "check_name",
    "download",
    "file_url",
    "load_manifest",
    "unquote",
]

RAW_BASE = "https://raw.githubusercontent.com"
TIMEOUT_SECONDS = 60
SAFE_NAME = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\.csv")

Fetch = Callable[[str], bytes]


class DownloadError(RuntimeError):
    """A file could not be fetched."""


class ChecksumError(DownloadError):
    """A fetched file does not match the manifest."""


def load_manifest() -> dict:
    text = resources.files("mcf.data").joinpath("tawos_manifest.json").read_text("utf-8")
    return json.loads(text)


def check_name(name: str) -> None:
    """Reject a file name that could write outside the destination folder."""
    if not SAFE_NAME.fullmatch(name or "") or Path(name).name != name:
        raise DownloadError(f"unsafe file name in the manifest: {name!r}")


def file_url(source: dict, name: str) -> str:
    folder = "/".join(quote(part) for part in source["folder"].split("/"))
    return f"{RAW_BASE}/{source['repo']}/{source['commit']}/{folder}/{quote(name)}"


def http_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        return response.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download(dest: Path, manifest: dict, fetch: Fetch) -> list[Path]:
    """Fetch each manifest file into dest. Stop at the first bad file.

    A file is written only after its checksum matches, so no bad file is left.
    A local file that already matches is not fetched again.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for entry in manifest["files"]:
        name, expected = entry["name"], entry["sha256"]
        check_name(name)
        target = dest / name
        if target.is_file():
            if _sha256(target.read_bytes()) == expected:
                written.append(target)
                continue
            target.unlink()  # a bad local file never stays in dest
        url = file_url(manifest["source"], name)
        try:
            data = fetch(url)
        except Exception as exc:  # noqa: BLE001 - report any fetch failure clearly
            raise DownloadError(f"could not fetch {name} from {url}: {exc}") from exc
        actual = _sha256(data)
        if actual != expected:
            raise ChecksumError(
                f"checksum mismatch for {name}: expected {expected}, got {actual}. "
                "The source changed; stop and check before using the data."
            )
        tmp = target.with_suffix(target.suffix + ".part")
        try:
            tmp.write_bytes(data)
            tmp.replace(target)
        except OSError as exc:
            raise DownloadError(f"could not write {name} to {dest}: {exc}") from exc
        finally:
            tmp.unlink(missing_ok=True)
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m mcf.data.download",
        description="Download the TAWOS extract at a fixed commit and check each file.",
    )
    parser.add_argument("--dest", default="data", help="folder for the files (default: data)")
    args = parser.parse_args(argv)
    manifest = load_manifest()
    try:
        files = download(Path(args.dest), manifest, http_get)
    except DownloadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rows = sum(f["rows"] for f in manifest["files"])
    print(f"{len(files)} files OK ({rows} data rows) in {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
