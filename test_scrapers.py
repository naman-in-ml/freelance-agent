#!/usr/bin/env python
"""
Test the scrapers directly, bypassing LLM.
"""

import json
from scrapers.upwork import fetch_upwork_jobs
from scrapers.freelancer import fetch_freelancer_jobs

def main():
    query = "AI agent"
    max_jobs = 5
    print(f"Fetching Upwork jobs for '{query}'...")
    upwork = fetch_upwork_jobs(query, max_jobs)
    print(f"Got {len(upwork)} Upwork jobs")
    print(f"Fetching Freelancer jobs for '{query}'...")
    freelancer = fetch_freelancer_jobs(query, max_jobs)
    print(f"Got {len(freelancer)} Freelancer jobs")
    # Combine and deduplicate by URL
    seen = set()
    all_jobs = []
    for j in upwork + freelancer:
        url = j.get("url")
        if url and url not in seen:
            seen.add(url)
            all_jobs.append(j)
    print(f"After dedupe: {len(all_jobs)} unique jobs")
    # Print a simple markdown report
    print("\n=== Test Report ===")
    print(f"# Freelance Job Test – {query} ({len(all_jobs)} results)\n")
    for j in all_jobs:
        src = j.get("source", "?").title()
        title = j.get("title", "(no title)")
        url = j.get("url", "")
        budget = j.get("budget") or ""
        posted = j.get("posted") or ""
        print(f"- **[{title}]({url})**")
        print(f"  *Source:* {src}")
        if budget:
            print(f"  *Budget:* {budget}")
        if posted:
            print(f"  *Posted:* {posted}")
        print()
    print("=== End Test ===")

if __name__ == "__main__":
    main()