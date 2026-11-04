"""Browser check of the web page (MCF-24 AC3), with Playwright and Chromium.

The webapp-testing skill named in AC3 is not available in the build session, so
this script runs the same kind of checks in a real browser. It starts the page
with no API key (no paid call), so the AI part is the "off" state.

    python scripts/browser_check.py [--screenshots DIR]
    python scripts/browser_check.py --url https://APP.streamlit.app/~/+/   (deployed demo)

Exit 0 = all checks pass, 1 = a check failed.
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcf.web.logic import (  # noqa: E402
    forecast_from_bytes,
    long_date,
    sample_bytes,
)

BAD = b"Issue_Key,Type\nA-1,Story\n"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", type=Path, default=None)
    parser.add_argument(
        "--url",
        default=None,
        help="check a deployed page (no key on the server) instead of a local one",
    )
    args = parser.parse_args()
    shots = args.screenshots
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    expected = forecast_from_bytes(sample_bytes(), backlog=40).facts
    server = None
    if args.url:
        url = args.url
    else:
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
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn) -> None:
        try:
            fn()
            results.append((name, True, ""))
        except Exception as exc:  # report every check, do not stop at the first
            results.append((name, False, str(exc).splitlines()[0][:200]))

    try:
        if server is not None:
            wait_for(url)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for width, label in ((1280, "desktop"), (390, "phone")):
                page = browser.new_page(viewport={"width": width, "height": 900})
                errors: list[str] = []
                page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
                page.on(
                    "console",
                    lambda m, errors=errors: errors.append(m.text) if m.type == "error" else None,
                )
                page.goto(url, timeout=120_000)  # a sleeping cloud app can take a minute
                main_area = page.locator("[data-testid='stMain']")

                def boxes_and_captions(page=page):
                    """MCF-37 review: white boxes on a grey page; captions 4.5:1 or more."""
                    page.wait_for_function(  # the boxes below the chart render a moment later
                        """() => [...document.querySelectorAll("[data-testid='stVerticalBlock']")]
                        .filter(e => parseFloat(getComputedStyle(e).borderTopWidth) > 0)
                        .length >= 5""",
                        timeout=30_000,
                    )
                    got = page.evaluate(
                        """() => {
                        const boxes = [...document.querySelectorAll(
                          "[data-testid='stVerticalBlock']")].filter(e => {
                            const s = getComputedStyle(e);
                            return parseFloat(s.borderTopWidth) > 0
                              && s.backgroundColor === 'rgb(255, 255, 255)';});
                        const main = getComputedStyle(
                          document.querySelector("[data-testid='stMain']")).backgroundColor;
                        const caps = [...document.querySelectorAll(
                          "[data-testid='stMain'] [data-testid='stCaptionContainer']")]
                          .map(e => { const s = getComputedStyle(e);
                            return s.color + '|' + s.opacity; });
                        return {boxes: boxes.length, main, caps: [...new Set(caps)]};
                        }"""
                    )
                    assert got["boxes"] >= 5, f"white bordered boxes: {got['boxes']}"
                    assert got["main"] == "rgb(245, 246, 248)", got["main"]
                    assert got["caps"] == ["rgb(95, 99, 112)|1"], got["caps"]

                def sample_dates(page=page):
                    expect(
                        page.get_by_text("2. When the 40 work items will be done")
                    ).to_be_visible(timeout=30_000)
                    want = {
                        "50% chance of completion": long_date(expected.mc50),
                        "85% chance of completion": long_date(expected.mc85),
                        "95% chance of completion": long_date(expected.mc95),
                        "Velocity date": long_date(expected.velocity_date),
                    }
                    cards = page.locator(".mcf-card")
                    expect(cards).to_have_count(4, timeout=30_000)
                    shown = {}
                    for c in cards.all():
                        shown[c.locator(".mcf-card-label").inner_text().strip()] = (
                            c.locator(".mcf-card-value").inner_text().strip()
                        )
                    assert shown == want, f"label and date do not match: {shown}"

                def sidebar_first(page=page):
                    first = page.evaluate(
                        """() => {
                        const s = document.querySelector("[data-testid='stSidebar']");
                        const m = document.querySelector("[data-testid='stMain']");
                        return !!s && !!m &&
                          !!(s.compareDocumentPosition(m) & Node.DOCUMENT_POSITION_FOLLOWING);
                        }"""
                    )
                    assert first, "the help sidebar is not before the main page in reading order"

                def chart(page=page):
                    expect(page.locator("[data-testid='stVegaLiteChart']")).to_be_visible()
                    expect(
                        page.locator(
                            "[data-testid='stVegaLiteChart'] canvas, "
                            "[data-testid='stVegaLiteChart'] svg"
                        ).first
                    ).to_be_visible()

                def not_certain(page=page):
                    expect(page.get_by_text("The 50% date is not certain").first).to_be_visible()

                def ai_off(page=page):
                    main_text = page.locator("[data-testid='stMain']").inner_text()
                    assert not re.search(r"\bAI\b", main_text), "an AI line shows without a key"

                def no_keys(main_area=main_area):
                    assert "SAMPLE-" not in main_area.inner_text()

                def no_horizontal_scroll(page=page):
                    sw = page.evaluate("document.documentElement.scrollWidth")
                    cw = page.evaluate("document.documentElement.clientWidth")
                    assert sw <= cw + 1, f"page is {sw}px wide in a {cw}px window"

                def dates_not_cut(page=page):
                    expect(page.locator(".mcf-card-value")).to_have_count(4)
                    cut = page.evaluate(
                        """() => [...document.querySelectorAll(".mcf-card-value")]
                        .filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.textContent)"""
                    )
                    assert not cut, f"dates cut off: {cut}"

                check(f"{label}: each date is under its own label", sample_dates)
                check(f"{label}: dates are not cut off", dates_not_cut)
                check(f"{label}: help sidebar first in reading order", sidebar_first)
                check(f"{label}: white boxes on a grey page, readable captions", boxes_and_captions)
                check(f"{label}: chart is drawn", chart)
                check(f"{label}: the 50% date is not certain", not_certain)
                check(f"{label}: no AI line without a key", ai_off)
                check(f"{label}: no issue keys on the page", no_keys)
                check(f"{label}: no horizontal scroll", no_horizontal_scroll)
                if shots:
                    page.screenshot(path=str(shots / f"sample-{label}.png"), full_page=True)

                def bad_file(page=page, label=label):
                    page.get_by_text("Upload a CSV file", exact=True).click()
                    page.locator("input[type='file']").set_input_files(
                        files=[{"name": "bad.csv", "mimeType": "text/csv", "buffer": BAD}]
                    )
                    alert = page.locator("[data-testid='stAlertContentError']")
                    expect(alert).to_contain_text(
                        "missing column(s): Resolution_Date.", timeout=30_000
                    )
                    expect(page.locator("[data-testid='stException']")).to_have_count(0)
                    expect(page.locator("[data-testid='stVegaLiteChart']")).to_have_count(0)
                    if shots:
                        page.screenshot(path=str(shots / f"bad-file-{label}.png"), full_page=True)

                check(f"{label}: bad file shows a clear error, no stack trace", bad_file)
                check(
                    f"{label}: no browser errors",
                    lambda errors=errors: (
                        (_ for _ in ()).throw(AssertionError(errors[0])) if errors else None
                    ),
                )
                page.close()
            browser.close()
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=10)

    print("===== BROWSER CHECK START =====")
    for name, ok, why in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({why})" if why else ""))
    passed = sum(ok for _, ok, _ in results)
    print(f"Result: {passed} of {len(results)} checks passed")
    print("===== BROWSER CHECK END =====")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
