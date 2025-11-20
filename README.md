
# Status Dashboard (GitHub Pages + GitHub Actions)

This repository hosts a static status dashboard that auto-updates using a scheduled GitHub Action. The runner fetches public status from various vendors and writes `data/status.json`, which the page renders.

## How it works
- `scripts/fetch_status.py` runs on a schedule (every 10 minutes) and pulls data from:
  - Statuspage providers via `api/v2/summary.json` (e.g., GitHub, Elastic, Octopus, Lucid, Jira/Confluence, CucumberStudio, Fivetran, Port).
  - Azure DevOps via `https://status.dev.azure.com/_apis/status/health?api-version=7.1-preview.1`.
  - Azure global via the public status page and RSS feed.
  - Brainboard via `https://status.brainboard.co/index.json`.
- The workflow commits `data/status.json` back to the repo.
- `index.html` reads `data/status.json` and displays the table.

## Getting started
1. Push this repo to GitHub.
2. Enable GitHub Actions (Actions tab) and run the workflow manually once, or wait for the cron.
3. Enable GitHub Pages (Settings → Pages → Source: main / root). Visit your public URL.

## Customize
- Add/remove services in `scripts/fetch_status.py`.
- Adjust colors and layout in `styles.css`.

## Notes
- Azure global page publishes widespread incidents only. Many service-specific issues appear in tenant Service Health (not public).
- Statuspage ‘indicator’ values are normalized to Operational/Degraded/Partial Outage/Major Outage.
