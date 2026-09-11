"""Playwright browser lifecycle management.

Each job gets its own isolated BrowserContext (cookies, storage, viewport).
The context and its page are *always* closed in a ``finally`` block so that
a crash on one site cannot leak resources or affect the next job.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

import structlog
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from app.automation.proxy import get_playwright_proxy_config
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
        proxy_config = get_playwright_proxy_config()
        launch_kwargs: dict[str, Any] = {
            "headless": settings.browser_headless,
            "channel": "chromium",  # use full chromium, not chrome-headless-shell
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        }
        if proxy_config:
            launch_kwargs["proxy"] = proxy_config
            raw_proxy = settings.proxy_url or ""
            parsed = urlparse(raw_proxy if "://" in raw_proxy else f"http://{raw_proxy}")
            host_port = f"{parsed.hostname}:{parsed.port}" if parsed.port else (parsed.hostname or "")
            log.info("browser.proxy_enabled", server=host_port or proxy_config.get("server", ""))

        browser = await playwright.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/Chicago",
        )
        # Apply anti-bot stealth overrides
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
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
