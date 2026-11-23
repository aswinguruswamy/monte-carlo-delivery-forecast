"""Take the README screenshots of the web page (MCF v2 spec R11.1, Aswin 2026-11-23).

The page runs locally with no API key (no paid call), so it shows the saved AI example.
It needs Playwright (`pip install playwright==1.65.0`, to match the installed Chromium).
The images go to docs/images/.

    python scripts/take_screenshots.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record_demo import SIZE, free_port, wait_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
CHARTER = "2026/11/15"  # the charter date shown in the screenshots


def take(url: str) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport=SIZE, device_scale_factor=2, color_scheme="light")
        page.goto(url)
        expect(page.locator(".mcf-card")).to_have_count(4, timeout=60_000)
        year, month, day = CHARTER.split("/")
        for part, value in (("year", year), ("month", month), ("day", day)):
            field = page.get_by_role("spinbutton", name=f"{part}, Charter date (optional)")
            field.click()
            page.keyboard.type(value)
        page.keyboard.press("Enter")
        page.keyboard.press("Escape")
        page.locator("h1").first.click()  # move the focus off the date field
        expect(page.get_by_text("chance to finish by")).to_be_visible(timeout=30_000)
        page.wait_for_timeout(1500)
        for n, name in ((1, "mcf-inputs.png"), (2, "mcf-dates-and-chance.png")):
            section = page.locator(f".st-key-section-{n}")
            section.scroll_into_view_if_needed()
            path = OUT / name
            section.screenshot(path=str(path))
            shots.append(path)
        page.locator("summary").get_by_text("How accurate is it?").click()
        page.wait_for_timeout(800)
        section = page.locator(".st-key-section-4")
        section.scroll_into_view_if_needed()
        path = OUT / "mcf-accuracy.png"
        section.screenshot(path=str(path))
        shots.append(path)
        browser.close()
    return shots


def main() -> int:
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
        for path in take(url):
            print(path.relative_to(ROOT))
    finally:
        server.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
