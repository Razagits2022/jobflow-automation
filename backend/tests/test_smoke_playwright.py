"""Smoke test: Playwright can launch headless Chromium, open a blank page, and close cleanly."""

from __future__ import annotations

import pytest
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_playwright_smoke() -> None:
    """Launch headless Chromium, navigate to about:blank, assert title is empty, close."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("about:blank")
        title = await page.title()
        assert title == ""
        await browser.close()
