"""Playwright browser lifecycle management.

Each job gets its own isolated BrowserContext (cookies, storage, viewport).
The context and its page are *always* closed in a ``finally`` block so that
a crash on one site cannot leak resources or affect the next job.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from app.core.config import settings

log = structlog.get_logger(__name__)


@asynccontextmanager
async def managed_page() -> AsyncGenerator[tuple[BrowserContext, Page], None]:
    """Async context manager that yields a fresh (context, page) pair.

    Usage::

        async with managed_page() as (context, page):
            await page.goto(url)
            # ... do work ...

    The context (cookies, local storage, viewport) and the page are always
    closed in the finally block, even if an exception propagates out.

    Raises:
        playwright.async_api.Error: If Chromium cannot be launched.
    """
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=settings.browser_headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            # TODO Phase 2: support loading saved cookies / auth state here
        )
        page = await context.new_page()
        page.set_default_timeout(settings.nav_timeout_ms)
        log.debug("browser.context_opened")
        try:
            yield context, page
        finally:
            log.debug("browser.context_closing")
            try:
                await page.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                await context.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                await browser.close()
            except Exception:  # noqa: BLE001
                pass
            log.debug("browser.context_closed")


# ---------------------------------------------------------------------------
# TODO (Phase 2 — remote browser support)
# ---------------------------------------------------------------------------
# To connect to a remote Chromium over CDP (e.g. Browserless, Bright Data):
#
#   browser = await playwright.chromium.connect_over_cdp(settings.cdp_endpoint)
#
# The managed_page() interface stays the same; only the launch line changes.
# Add CDP_ENDPOINT to Settings and swap the launch call above.
