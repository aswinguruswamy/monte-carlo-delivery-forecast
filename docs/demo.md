# Demo

The web page runs as a free public demo on **Streamlit Community Cloud** (MCF-26, D01). If the cloud is not available, see the screenshots in the README.

## Deploy (the PM does this once)

1. Go to **share.streamlit.io** and sign in with GitHub. Give Streamlit access to the repository `aswinguruswamy/monte-carlo-delivery-forecast`.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Enter these settings:
   - Repository: `aswinguruswamy/monte-carlo-delivery-forecast`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: a short name, for example `mcf-forecast`
4. Open **Advanced settings**:
   - Python version: 3.12
   - Secrets: leave empty. **Do not add `ANTHROPIC_API_KEY`.** With no key, the page shows a saved AI example of the sample forecast, labelled "Saved example" (MCF v2, R10.1), and visitors cannot cause paid calls. The PM decides this at the MCF-26 review.
5. Click **Deploy**. The first start takes a few minutes.

How the install works: Community Cloud uses the first dependency file that it finds, in this order: `uv.lock`, `Pipfile`, `environment.yml`, `requirements.txt`, `pyproject.toml`. This repository has only `requirements.txt` from that list. It installs this package as an editable install with the `web` extra (`-e .[web]`), with the exact versions of the release lock file (`-c constraints.txt`), and the page finds the sample file in `examples/`. The settings in `.streamlit/config.toml` (10 MB uploads, no usage data, no Deploy button) apply because the app starts from the repository root.

The repository is public, so the app is public.

**After each release, reboot the app** (Manage app › ⋮ › Reboot app). Streamlit reloads the page script but not the package code, so an old copy can run against new files (a KeyError on 2026-11-23).

## Check the deployed page

1. Open the app in a browser first. If the app sleeps, click the button to wake it, and wait until the forecast shows.
2. Run the browser check against the app address. Add `/~/+/` at the end, so that the check opens the page itself and not the Community Cloud frame:

```bash
python scripts/browser_check.py --url https://mcf-forecast.streamlit.app/~/+/
```

If that address does not open the page, use the embed address instead: `https://mcf-forecast.streamlit.app/?embed=true`. (The `/~/+/` path is not in the Streamlit docs; `?embed=true` is.)

All checks must pass. "no live AI without a key" passes only when the app has no key: the only AI text then is the saved example with its label.

## Recorded video (A5)

```bash
pip install -e ".[web]" playwright==1.63.0 -c constraints.txt
python -m playwright install chromium
python scripts/record_demo.py --out demo.mp4
```

The script starts the page with no key and records the sample forecast, the chart, a new backlog, a section closed and opened again, the options and a bad file. The video is about 30 seconds and less than 2 MB. It is not stored in the repository; it goes with the GitHub release.

Which video goes with which release:

- **v1.0.0:** the v1.0 page.
- **v1.1.0:** the v1.1 page (MCF-43): help sidebar, "chance of completion" cards with no notes, collapsible sections, light theme only.
- **v2.0.0:** no video; the README shows 3 screenshots instead (`scripts/take_screenshots.py`; Aswin, 2026-11-23).
- **v1.2.0:** no new video (D55, PM decision 2026-11-09). The v1.1.0 video still shows the page; it does not show the dark theme, and its footer says "Version 1.1.0".

Each release keeps its own video. Record a new video for a new release only, after the version bump, so that the footer shows the new version. Use `--release`; the script stops if the footer shows another version:

```bash
python scripts/record_demo.py --release 1.1.0 --out mcf-demo-v1.1.0.mp4
```
