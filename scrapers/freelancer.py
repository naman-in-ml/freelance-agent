"""Freelancer.com job fetcher via the free public API (no auth required).

Endpoint: https://www.freelancer.com/api/projects/0.1/projects/active/?query=<q>
Returns JSON with active projects. No Cloudflare protection observed.
"""
import json
import time
import urllib.parse
import urllib.request

API = "https://www.freelancer.com/api/projects/0.1/projects/active/"

_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"


def _human_time(ts):
    try:
        return time.strftime("%Y-%m-%d", time.localtime(float(ts)))
    except Exception:
        return "unknown"


def fetch_freelancer_jobs(query: str, max_jobs: int = 20) -> list[dict]:
    params = {
        "query": query,
        "limit": max_jobs,
        "full_description": "true",
        "job_details": "true",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    if data.get("status") != "success":
        raise RuntimeError(f"Freelancer API error: {data.get('error') or data.get('status')}")

    jobs = []
    for p in data["result"]["projects"]:
        budget = p.get("budget") or {}
        cur = (p.get("currency") or {}).get("code", "")
        bmin, bmax = budget.get("minimum"), budget.get("maximum")
        budget_str = None
        if bmin or bmax:
            lo = f"{cur} {bmin:,.0f}" if bmin else None
            hi = f"{cur} {bmax:,.0f}" if bmax else None
            budget_str = f"{lo} - {hi}" if (lo and hi) else (lo or hi)

        jobs.append({
            "source": "freelancer",
            "title": p.get("title"),
            "url": "https://www.freelancer.com/projects/" + (p.get("seo_url") or ""),
            "budget": budget_str,
            "type": p.get("type"),
            "description": (p.get("preview_description") or p.get("description") or "")[:200],
            "posted": _human_time(p.get("time_submitted")),
            "skills": [],
        })

    return jobs
