
import os, json
from datetime import datetime, timezone, timedelta
import requests
import feedparser

OUT_DIR = "data"
OUT_FILE = os.path.join(OUT_DIR, "status.json")
TIMEOUT = 25

# Normalize status labels
def normalize_status(label: str) -> str:
    if not label:
        return "Unknown"
    s = label.strip().lower()
    if s in ("none", "operational", "healthy", "ok"):
        return "Operational"
    if "degrad" in s or s in ("minor",):
        return "Degraded"
    if "partial" in s or s in ("major",):
        return "Partial Outage"
    if "critical" in s or "down" in s or "outage" in s or "unhealthy" in s:
        return "Major Outage"
    if "maintenance" in s:
        return "Maintenance"
    return label

# Statuspage summary.json
def status_from_statuspage(base_url: str):
    url = base_url.rstrip("/") + "/api/v2/summary.json"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    ind = data.get("status", {}).get("indicator", "")
    desc = data.get("status", {}).get("description", "") or "—"
    return normalize_status(ind), desc

# Azure DevOps service health
def status_azure_devops():
    url = "https://status.dev.azure.com/_apis/status/health?api-version=7.1-preview.1"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    rollup = (data.get("status") or {}).get("health", "")
    msg = (data.get("status") or {}).get("message", "") or "—"
    return normalize_status(rollup), msg

# Azure global status: HTML + RSS
def status_azure_global():
    try:
        html = requests.get("https://azure.status.microsoft/", timeout=TIMEOUT).text
        if "There are currently no active events" in html:
            return "Operational", "No active events"
    except Exception:
        pass
    try:
        feed = feedparser.parse("https://azurestatuscdn.azureedge.net/en-us/status/feed/")
        if getattr(feed, "entries", []):
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
            recent = []
            for e in feed.entries:
                dt = None
                if getattr(e, "published_parsed", None):
                    from time import struct_time
                    if isinstance(e.published_parsed, struct_time):
                        dt = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                if dt and dt >= recent_cutoff:
                    recent.append(e)
            if recent:
                title = recent[0].title if hasattr(recent[0], "title") else "Recent incident"
                return "Degraded", title
        return "Operational", "No recent incidents in RSS"
    except Exception as e:
        return "Unknown", f"Fetch error: {e}"

# Brainboard index.json
def status_brainboard():
    url = "https://status.brainboard.co/index.json"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        agg = ((data.get("data") or {}).get("attributes") or {}).get("aggregate_state", "")
        return normalize_status(agg), f"Aggregate state: {agg or '—'}"
    except Exception as e:
        return "Unknown", f"Fetch error: {e}"

# Helper
def svc(name, source, status, description):
    return {"name": name, "status": status, "description": description, "source": source}


def main():
    services = []

    # Azure global
    s, d = status_azure_global()
    services.append(svc("Azure", "https://azure.status.microsoft/", s, d))

    # Azure DevOps
    s, d = status_azure_devops()
    services.append(svc("Azure DevOps", "https://status.dev.azure.com/", s, d))

    # Statuspage-backed vendors
    statuspage_sources = [
        ("Azure Databricks", "https://status.azuredatabricks.net"),
        ("JFrog", "https://status.jfrog.io"),
        ("Elastic", "https://status.elastic.co"),
        ("Octopus Deploy", "https://status.octopus.com"),
        ("Lucid", "https://status.lucid.co"),
        ("Jira", "https://jira-software.status.atlassian.com"),
        ("Confluence", "https://confluence.status.atlassian.com"),
        ("GitHub", "https://www.githubstatus.com"),
        ("CucumberStudio", "https://status.cucumberstudio.com"),
        ("Fivetran", "https://status.fivetran.com"),
        ("Port", "https://status.port.io"),
    ]
    for name, base in statuspage_sources:
        try:
            s, d = status_from_statuspage(base)
        except Exception as e:
            s, d = "Unknown", f"Fetch error: {e}"
        services.append(svc(name, base, s, d))

    # Brainboard
    s, d = status_brainboard()
    services.append(svc("Brainboard", "https://status.brainboard.co", s, d))

    out = {"updatedAt": datetime.now(timezone.utc).isoformat(), "services": services}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
