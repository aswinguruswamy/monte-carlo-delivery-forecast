"""Record the demo video of the web page (MCF-26, A5), with Playwright and ffmpeg.

The page runs locally with no API key (no paid call). The video shows the
sample forecast, the chart, a new backlog, a section closed and opened again
(MCF-43), the options and a bad file.

    python scripts/record_demo.py --out demo.mp4

The MP4 is not committed to the repository; it goes with the GitHub release.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BAD = b"Issue_Key,Type\nA-1,Story\n"
SIZE = {"width": 1280, "height": 800}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for(url: str, seconds: float = 60) -> None:
    end = time.time() + seconds
    while time.time() < end:
        try:
            urllib.request.urlopen(url + "/_stcore/health", timeout=2)  # noqa: S310
            return
        except OSError:
            time.sleep(0.5)
    raise SystemExit(f"the page did not start within {seconds} s")


def _show(page, testid: str) -> None:
    page.locator(f"[data-testid='{testid}']").first.scroll_into_view_if_needed()


def _section(page, n: int):
    """The box of section n (MCF-41: an expander with the key section-n)."""
    return page.locator(f".st-key-section-{n} > [data-testid='stExpander'] > details")


def close_and_open(page, n: int) -> None:
    """MCF-43: show that a section can close and open again."""
    summary = _section(page, n).locator("> summary")
    summary.scroll_into_view_if_needed()
    page.wait_for_timeout(800)
    summary.click()
    page.wait_for_timeout(2500)  # review MCF-43: long enough to see it closed
    summary.click()
    page.wait_for_timeout(1200)


def record(url: str, video_dir: Path, release: str | None = None) -> tuple[Path, float]:
    """Return the video and the second at which the page is ready (cut before it)."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport=SIZE, record_video_dir=str(video_dir), record_video_size=SIZE
        )
        start = time.monotonic()
        page = context.new_page()
        page.goto(url)
        expect(page.locator(".mcf-card")).to_have_count(4, timeout=60_000)
        expect(page.locator("[data-testid='stVegaLiteChart']")).to_be_visible(timeout=30_000)
        if release:  # review MCF-43: a release video shows that release in the footer
            footer = page.get_by_text(f"Version {release}")
            if footer.count() == 0:
                raise SystemExit(f"the page footer does not show Version {release}")
        page.wait_for_timeout(1000)
        ready = time.monotonic() - start
        page.wait_for_timeout(2000)
        page.locator(".mcf-card").first.scroll_into_view_if_needed()  # MCF-43: the cards
        page.wait_for_timeout(3000)
        _show(page, "stVegaLiteChart")  # the chart
        page.wait_for_timeout(4000)
        _section(page, 1).scroll_into_view_if_needed()

        backlog = page.get_by_label("How many work items are left? (backlog)")
        backlog.fill("80")
        backlog.press("Enter")
        expect(
            page.locator("summary").get_by_text("2. When the 80 work items will be done")
        ).to_be_visible(timeout=30_000)
        page.wait_for_timeout(1000)
        page.locator(".mcf-card").first.scroll_into_view_if_needed()  # the dates for 80
        page.wait_for_timeout(2500)
        _show(page, "stVegaLiteChart")
        page.wait_for_timeout(3000)
        close_and_open(page, 3)  # MCF-41: the chart section closes and opens
        footer_line = page.get_by_text("Version ", exact=False).last  # review MCF-44
        # the whole version line in the middle of the screen (not at the bottom edge)
        footer_line.evaluate("e => e.scrollIntoView({block: 'center'})")
        page.wait_for_timeout(2000)
        _section(page, 1).scroll_into_view_if_needed()

        page.locator("summary").get_by_text("More options").click()
        page.wait_for_timeout(2500)
        page.locator("summary").get_by_text("More options").click()

        page.get_by_text("Upload a CSV file", exact=True).click()
        page.locator("input[type='file']").set_input_files(
            files=[{"name": "bad.csv", "mimeType": "text/csv", "buffer": BAD}]
        )
        expect(page.locator("[data-testid='stAlertContentError']")).to_be_visible(timeout=30_000)
        page.wait_for_timeout(3500)

        video = page.video.path()
        context.close()
        browser.close()
    return Path(video), ready


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("demo.mp4"))
    parser.add_argument("--release", help="stop if the page footer does not show this version")
    args = parser.parse_args()
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is needed to make the MP4")

    port = free_port()
    url = f"http://127.0.0.1:{port}"
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT / "streamlit_app.py"),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for(url)
        with tempfile.TemporaryDirectory() as tmp:
            webm, ready = record(url, Path(tmp), args.release)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{ready:.1f}",
                    "-i",
                    str(webm),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "28",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(args.out),
                ],
                check=True,
            )
    finally:
        server.terminate()
        server.wait(timeout=10)
    print(f"demo video: {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
