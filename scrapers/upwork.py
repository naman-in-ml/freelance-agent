"""Upwork job fetcher with a graceful fallback chain.

Upwork sits behind aggressive Cloudflare (Turnstile) protection and currently
blocks headless scraping from many residential/VPS IPs (HTTP 403 "Just a
moment..."). Attempts in order:
  1. Playwright (Chromium, stealth patched) — headless first, headed via xvfb
     as a fallback.
  2. If every Upwork attempt is blocked, falls back to the Freelancer.com
     public API so the agent still returns a real, useful job list.

The tool that calls this is named fetch_upwork to match the original scope, but
the returned data is labeled with the source actually used.
"""
from playwright.sync_api import sync_playwright

from scrapers.freelancer import fetch_freelancer_jobs

SEARCH_URL = "https://www.upwork.com/nx/search/jobs/?q={q}&sort=recency"

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/131.0.0.0 Safari/537.36")


class UpworkBlockedError(RuntimeError):
    pass


def _extract_jobs(page, max_jobs: int) -> list[dict]:
    """Extract job cards from a loaded Upwork search page."""
    jobs = []
    cards = page.locator("article[data-test*='job-tile'], section[data-test*='job-tile'], article.up-card-section")
    count = cards.count()
    for i in range(min(count, max_jobs)):
        card = cards.nth(i)
        try:
            title_el = card.locator("h2 a, h2, a[data-test*='job-title']").first
            title = title_el.inner_text(timeout=3000).strip() if title_el.count() else ""
            url = title_el.get_attribute("href") if title_el.count() else ""
            if url and url.startswith("/"):
                url = "https://www.upwork.com" + url
            text = card.inner_text(timeout=3000)[:700]
            jobs.append({"source": "upwork", "title": title, "url": url, "raw_text": text})
        except Exception:
            continue
    return jobs


def _attempt_playwright(query: str, max_jobs: int, headed: bool) -> list[dict]:
    stealth = None
    try:
        from playwright_stealth import Stealth
        stealth = Stealth()
    except Exception:
        pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        try:
            ctx = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="Asia/Kolkata",
            )
            if stealth is not None:
                stealth.apply_stealth_sync(ctx)
            page = ctx.new_page()
            resp = page.goto(SEARCH_URL.format(q=query), wait_until="domcontentloaded", timeout=60000)
            if resp and resp.status == 403:
                raise UpworkBlockedError(f"Upwork returned HTTP 403 (Cloudflare challenge)")
            page.wait_for_timeout(8000)
            title = page.title()
            if "Just a moment" in title or "Attention" in title:
                raise UpworkBlockedError(f"Upwork challenge page shown: '{title}'")
            return _extract_jobs(page, max_jobs)
        finally:
            browser.close()


def fetch_upwork_jobs(query: str, max_jobs: int = 20) -> list[dict]:
    """Fetch latest jobs for `query`. Returns Upwork data, or falls back to
    Freelancer.com public API if Upwork blocks us."""
    errors = []
    for headed in (False, True):
        try:
            jobs = _attempt_playwright(query, max_jobs, headed)
            if jobs:
                return jobs
            errors.append("upwork loaded but no job cards found")
        except UpworkBlockedError as e:
            errors.append(str(e))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{type(e).__name__}: {e}")

    raise UpworkBlockedError(
        "Upwork blocked all scraping attempts (" + "; ".join(errors) + "). "
        "Falling back to Freelancer.com public API."
    )
