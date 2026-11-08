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

# MCF-39: contrast of each visible text (and input placeholder) against what is behind it.
# Colours are read through a canvas, so any CSS colour format works. See-through text,
# see-through backgrounds and the opacity of parent elements are blended in. A background
# image (for example a gradient) cannot be measured, so it is reported as a failure.
# WCAG allows 3:1 for large text; this check asks 4.5:1 for all text (stricter).
CONTRAST_JS = """() => {
  const cv = document.createElement("canvas"); cv.width = cv.height = 1;
  const cx = cv.getContext("2d", {willReadFrequently: true});
  const rgba = c => { cx.clearRect(0, 0, 1, 1); cx.fillStyle = "#000"; cx.fillStyle = c;
    cx.fillRect(0, 0, 1, 1); const d = cx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255]; };
  const over = (top, a, under) => top.map((v, i) => v * a + under[i] * (1 - a));
  const lum = c => c.map(v => { v /= 255;
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; })
    .reduce((a, v, i) => a + v * [0.2126, 0.7152, 0.0722][i], 0);
  const behind = e => {  // the solid colour behind e, or null for a background image
    const layers = [];
    for (let n = e; n; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.backgroundImage !== "none") return null;
      const c = rgba(s.backgroundColor);
      if (c[3] > 0) layers.push(c);
      if (c[3] === 1) break;
    }
    return layers.reverse().reduce((b, c) => over(c.slice(0, 3), c[3], b), [255, 255, 255]);
  };
  const fade = e => { let o = 1;
    for (let n = e; n; n = n.parentElement) o *= parseFloat(getComputedStyle(n).opacity);
    return o; };
  const out = [];
  const test = (e, t, color) => {
    if (e.closest("[data-testid='stVegaLiteChart'], [data-testid='stToolbar'], svg")) return;
    const s = getComputedStyle(e), o = fade(e), box = e.getBoundingClientRect();
    if (s.visibility === "hidden" || o === 0) return;
    if (box.width <= 1 || box.height <= 1) return;  // screen-reader-only text
    // An icon glyph is not text: WCAG 1.4.11 asks 3:1 for it.
    const icon = e.closest("[data-testid='stIconMaterial']") || /Material/.test(s.fontFamily);
    const bg = behind(e);
    if (!bg) { out.push(t.slice(0, 40) + " (background image)"); return; }
    const fg = rgba(color);
    const a = lum(over(fg.slice(0, 3), fg[3] * o, bg)), b = lum(bg);
    const r = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (r < (icon ? 3 : 4.5)) out.push(t.slice(0, 40) + " " + r.toFixed(2));
  };
  const root = document.querySelector("[data-testid='stApp']");
  const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n; (n = walk.nextNode());) {
    const e = n.parentElement, t = n.textContent.trim();
    if (t && e && e.getClientRects().length) test(e, t, getComputedStyle(e).color);
  }
  for (const e of root.querySelectorAll("input[placeholder], textarea[placeholder]")) {
    if (e.placeholder && !e.value && e.getClientRects().length)
      test(e, "placeholder " + e.placeholder, getComputedStyle(e, "::placeholder").color);
  }
  return [...new Set(out)];
}"""

# Review MCF-39: known unreadable texts that the contrast check must report.
CONTRAST_BAD = {
    "white text on white": '<p style="color:#fff">x</p>',
    "see-through text": '<p style="color:rgba(0,0,0,0.15)">x</p>',
    "faded parent": '<div style="opacity:0.15"><p style="color:#000">x</p></div>',
    "see-through dark box": (
        '<div style="background:rgba(0,0,0,0.9)"><p style="color:#000">x</p></div>'
    ),
    "background image": (
        '<div style="background-image:linear-gradient(#000,#000)"><p style="color:#111">x</p></div>'
    ),
    "oklch colour": '<p style="color:oklch(0.98 0 0)">x</p>',
    "pale icon": '<span data-testid="stIconMaterial" style="color:#ddd">add</span>',
    "pale placeholder": '<input placeholder="yyyy" style="color:#000">'
    "<style>input::placeholder{color:rgba(49,51,63,0.6)}</style>",
}
CONTRAST_GOOD = (
    '<div style="background:rgba(255,255,255,0.5)"><p style="color:#31333F">x</p>'
    '<input placeholder="yyyy"><style>input::placeholder{color:#5f6370}</style></div>'
)


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

            def contrast_check_works(browser=browser):
                """Review MCF-39: the contrast check reports each known bad case."""
                page = browser.new_page()
                body = '<body style="background:#fff"><div data-testid="stApp">{}</div></body>'
                missed = []
                for name, html in CONTRAST_BAD.items():
                    page.set_content(body.format(html))
                    if not page.evaluate(CONTRAST_JS):
                        missed.append(name)
                page.set_content(body.format(CONTRAST_GOOD))
                false_alarm = page.evaluate(CONTRAST_JS)
                page.close()
                assert not missed, f"not reported: {missed}"
                assert not false_alarm, f"readable text reported: {false_alarm}"

            check("the contrast check reports unreadable text", contrast_check_works)
            for width, label, scheme in (
                (1280, "desktop", "light"),
                (390, "phone", "light"),
                (390, "phone in dark mode", "dark"),  # MCF-39
            ):
                page = browser.new_page(
                    viewport={"width": width, "height": 900}, color_scheme=scheme
                )
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
                    hidden = {}
                    for c in cards.all():
                        label = c.get_attribute("data-label")
                        shown[label] = c.locator(".mcf-card-value").inner_text().strip()
                        hidden[label] = c.locator(".mcf-sr-only").count()
                    assert shown == want, f"label and date do not match: {shown}"
                    # MCF-40: only the highlighted card has the hidden "date to share" text
                    assert hidden["85% chance of completion"] == 1 == sum(hidden.values()), hidden
                    assert page.locator(".mcf-card-note").count() == 0, "a card shows a note"

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

                def text_contrast(page=page):
                    """MCF-39: all visible text on the page has 4.5:1 contrast or more."""
                    low = page.evaluate(CONTRAST_JS)
                    assert not low, f"{len(low)} low-contrast texts, first: {low[:3]}"

                def no_theme_switch(page=page):
                    """MCF-39: the menu has no System / Light / Dark switch."""
                    button = page.locator("[data-testid='stMainMenu']")
                    assert button.count() == 1, "the app menu button is not on the page"
                    button.click()
                    menu = page.locator("[data-testid='stMainMenuList']")
                    expect(menu).to_be_visible(timeout=10_000)
                    text = menu.inner_text()
                    page.keyboard.press("Escape")
                    words = text.lower()  # the icons are named dark_mode and light_mode
                    assert not any(w in words for w in ("dark", "light", "system")), (
                        "theme switch in the menu: " + " / ".join(text.split())
                    )

                check(f"{label}: each date is under its own label", sample_dates)
                check(f"{label}: all text has 4.5:1 contrast", text_contrast)
                check(f"{label}: no light / dark switch in the menu", no_theme_switch)
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
                    info = page.get_by_text("Upload a CSV file to see the forecast.")
                    expect(info).to_be_visible(timeout=30_000)
                    low = page.evaluate(CONTRAST_JS)  # review MCF-39: the blue info box
                    assert not low, f"low-contrast texts before a file: {low[:3]}"
                    page.locator("input[type='file']").set_input_files(
                        files=[{"name": "bad.csv", "mimeType": "text/csv", "buffer": BAD}]
                    )
                    alert = page.locator("[data-testid='stAlertContentError']")
                    expect(alert).to_contain_text(
                        "missing column(s): Resolution_Date.", timeout=30_000
                    )
                    expect(page.locator("[data-testid='stException']")).to_have_count(0)
                    expect(page.locator("[data-testid='stVegaLiteChart']")).to_have_count(0)
                    low = page.evaluate(CONTRAST_JS)  # review MCF-39: the error is readable
                    assert not low, f"low-contrast texts after a bad file: {low[:3]}"
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
