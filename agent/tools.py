"""Tools exposed to the LangGraph agent."""
import json
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

from scrapers.upwork import UpworkBlockedError, fetch_upwork_jobs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


@tool
def fetch_upwork(search_query: str) -> str:
    """Fetch the latest freelance job postings matching search_query.

    Tries Upwork first; if Upwork blocks scraping, transparently falls back to
    the Freelancer.com public API. Returns a JSON list of jobs with fields:
    source, title, url, budget, type, description, posted, skills.
    """
    try:
        jobs = fetch_upwork_jobs(search_query, max_jobs=12)
    except UpworkBlockedError as e:
        from scrapers.freelancer import fetch_freelancer_jobs
        jobs = fetch_freelancer_jobs(search_query, max_jobs=12)
        note = f"Upwork blocked; used Freelancer.com API instead. {e}"
    else:
        note = f"Fetched from Upwork. {len(jobs)} jobs found."

    payload = {"_note": note, "_query": search_query, "jobs": jobs}
    return json.dumps(payload, indent=2)


@tool
def save_report(markdown: str) -> str:
    """Save the complete markdown report to the reports/ directory.

    The markdown must be a finished, well-formatted report (no placeholders).
    """
    fname = REPORTS_DIR / f"jobs-report-{datetime.now().strftime('%Y-%m-%d')}.md"
    fname.write_text(markdown, encoding="utf-8")
    return f"Report saved to {fname}"
