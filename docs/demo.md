# Demo

The web page runs as a free public demo on **Streamlit Community Cloud** (MCF-26, D01). If the cloud is not available, use the recorded video instead (A5).

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
   - Secrets: leave empty. **Do not add `ANTHROPIC_API_KEY`.** With no key, the AI explanation is off, so visitors cannot cause paid calls. The PM decides this at the MCF-26 review.
5. Click **Deploy**. The first start takes a few minutes.

How the install works: Community Cloud uses the first dependency file that it finds, in this order: `uv.lock`, `Pipfile`, `environment.yml`, `requirements.txt`, `pyproject.toml`. This repository has only `requirements.txt` from that list. It installs this package as an editable install with the `web` extra (`-e .[web]`), with the exact versions of the release lock file (`-c constraints.txt`), and the page finds the sample file in `examples/`. The settings in `.streamlit/config.toml` (10 MB uploads, no usage data, no Deploy button) apply because the app starts from the repository root.

A private repository: Community Cloud can deploy from a private repository, but then the app is private too. The repository becomes public at the release (MCF-27). Deploy after that, or share the app with named viewers until then.

## Check the deployed page

1. Open the app in a browser first. If the app sleeps, click the button to wake it, and wait until the forecast shows.
2. Run the browser check against the app address. Add `/~/+/` at the end, so that the check opens the page itself and not the Community Cloud frame:

```bash
python scripts/browser_check.py --url https://mcf-forecast.streamlit.app/~/+/
```

If that address does not open the page, use the embed address instead: `https://mcf-forecast.streamlit.app/?embed=true`. (The `/~/+/` path is not in the Streamlit docs; `?embed=true` is.)

All checks must pass. "AI off without a key" passes only when the app has no key.

## Recorded video (A5)

```bash
pip install -e ".[web]" playwright==1.63.0 -c constraints.txt
python -m playwright install chromium
python scripts/record_demo.py --out demo.mp4
```

The script starts the page with no key and records the sample forecast, the chart, a new backlog, the options and a bad file. The video is about 20 seconds and less than 1 MB. It is not stored in the repository; it goes with the GitHub release.

The v1.0.0 video shows the v1.0 page. The page changed in v1.1 (MCF-33: help sidebar, plain labels, written-out dates). The v1.0.0 release keeps its video. Record a new video for a new release only.
