"""Zyte API integration — fetch job posting content.

Uses Zyte's Automatic Extraction API (https://api.zyte.com/v1/extract)
with HTTP Basic auth (zyte_api_key, "").
"""

from __future__ import annotations

import asyncio
import html as html_lib
import re
from dataclasses import dataclass

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

_ZYTE_API_ENDPOINT = "https://api.zyte.com/v1/extract"


@dataclass
class JobPostingData:
    """Extracted job posting payload."""

    title: str
    description: str
    text: str


def _strip_html(html: str) -> str:
    """Remove HTML tags, script, and style blocks to yield plain readable text."""
    if not html:
        return ""
    # Strip scripts and styles
    clean = re.sub(
        r"<(script|style)\b[^>]*>([\s\S]*?)<\/(script|style)>",
        "",
        html,
        flags=re.IGNORECASE,
    )
    # Strip remaining tags
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html_lib.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


async def fetch_job_posting(url: str) -> JobPostingData:
    """Fetch job posting details using Zyte's Automatic Extraction API.

    1. First tries structured extraction: `{"url": url, "jobPosting": True}`.
    2. If missing or weak, retries with `{"url": url, "browserHtml": True}` and strips tags.
    3. Handles 429 rate limiting with backoff.
    4. Provides direct HTTP fetch fallback if Zyte key is unconfigured or returns auth failure.
    """
    has_zyte_key = bool(settings.zyte_api_key and "your-" not in settings.zyte_api_key.lower())

    if not has_zyte_key:
        log.warning("zyte.key_missing_using_direct_fetch", url=url)
        return await _fallback_fetch(url)

    auth = (settings.zyte_api_key, "")
    client_timeout = httpx.Timeout(30.0, connect=10.0)

    # 1. Attempt structured jobPosting extraction
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=client_timeout) as client:
                resp = await client.post(
                    _ZYTE_API_ENDPOINT,
                    auth=auth,
                    json={"url": url, "jobPosting": True},
                )

                if resp.status_code == 429:
                    wait_time = (attempt + 1) * 2.0
                    log.warning(
                        "zyte.rate_limited_backing_off", wait_seconds=wait_time, attempt=attempt
                    )
                    await asyncio.sleep(wait_time)
                    continue

                if resp.status_code in (401, 403):
                    log.error("zyte.auth_failed", status=resp.status_code)
                    return await _fallback_fetch(url)

                resp.raise_for_status()
                data = resp.json()

                job_obj = data.get("jobPosting")
                if job_obj and isinstance(job_obj, dict):
                    title = job_obj.get("title") or job_obj.get("headline") or ""
                    desc = job_obj.get("description") or job_obj.get("descriptionRawText") or ""
                    full_text = f"{title}\n\n{desc}".strip()
                    if full_text:
                        return JobPostingData(
                            title=title,
                            description=desc,
                            text=full_text,
                        )

                # If jobPosting was missing or empty, fall through to browserHtml
                break

        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            log.warning("zyte.structured_fetch_error", error=str(exc))
            break

    # 2. Retry with browserHtml extraction
    try:
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            resp = await client.post(
                _ZYTE_API_ENDPOINT,
                auth=auth,
                json={"url": url, "browserHtml": True},
            )
            if resp.is_success:
                data = resp.json()
                browser_html = data.get("browserHtml", "")
                plain_text = _strip_html(browser_html)
                return JobPostingData(
                    title="Job Opening",
                    description=plain_text[:5000],
                    text=plain_text[:8000],
                )
    except Exception as exc:  # noqa: BLE001
        log.warning("zyte.browser_html_failed", error=str(exc))

    return await _fallback_fetch(url)


async def _fallback_fetch(url: str) -> JobPostingData:
    """Direct HTTP client fallback when Zyte is unavailable or unconfigured."""
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        ) as client:
            resp = await client.get(url)
            if resp.is_success:
                text = _strip_html(resp.text)
                return JobPostingData(
                    title="Job Opening",
                    description=text[:4000],
                    text=text[:8000],
                )
    except Exception as exc:  # noqa: BLE001
        log.warning("zyte.direct_fetch_failed", url=url, error=str(exc))

    # Basic fallback from URL components
    url_slug = url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ").title()
    return JobPostingData(
        title=url_slug or "Job Application",
        description=f"Automated job application for {url}",
        text=f"Job listing at {url}",
    )


async def fetch_page_text(url: str) -> str:
    """Legacy helper returning plain text of the job posting."""
    data = await fetch_job_posting(url)
    return data.text
