"""Step 2 — Open the application form page."""

from __future__ import annotations

import re

import structlog
from playwright.async_api import Page

from app.core.config import settings

log = structlog.get_logger(__name__)

_APPLY_BUTTON_REGEX = re.compile(
    r"\b(apply now|apply for this job|apply on company site|apply|start application|register)\b",
    re.IGNORECASE,
)


async def open_application(*, page: Page, job_url: str) -> None:
    """Navigate to the job posting and ensure the browser is on the application form.

    1. Navigates to job_url.
    2. Checks if an application form is already visible.
    3. If not, locates and clicks the primary 'Apply' CTA.
    4. Handles new tabs/popups if the link opens in a separate window.
    """
    log.info("open_application.navigating", url=job_url)
    await page.goto(job_url, timeout=settings.nav_timeout_ms, wait_until="domcontentloaded")

    # Short wait for dynamic hydration
    try:
        await page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass

    # Check if form inputs are already present on this page
    form_inputs_count = await page.locator(
        "input:not([type=hidden]):not([type=submit]), textarea, select"
    ).count()
    if form_inputs_count >= 3:
        log.info("open_application.form_already_visible", input_count=form_inputs_count)
        return

    # Look for Apply link or button
    apply_locators = [
        page.locator("a, button").filter(has_text=_APPLY_BUTTON_REGEX).first,
        page.get_by_role("button", name=_APPLY_BUTTON_REGEX).first,
        page.get_by_role("link", name=_APPLY_BUTTON_REGEX).first,
        page.locator('[data-automation-id="apply-button"], [data-qa="apply-button"]').first,
    ]

    clicked = False
    for loc in apply_locators:
        try:
            if await loc.is_visible(timeout=1500):
                log.info("open_application.clicking_cta", text=await loc.text_content())
                # Handle possible popup
                context = page.context
                try:
                    async with context.expect_page(timeout=3000) as new_page_info:
                        await loc.click(timeout=3000)
                    new_page = await new_page_info.value
                    await new_page.wait_for_load_state("domcontentloaded")
                    page = new_page
                    clicked = True
                    break
                except Exception:
                    # No popup, regular navigation
                    await loc.click(timeout=3000)
                    clicked = True
                    break
        except Exception:
            continue

    if clicked:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

    log.info("open_application.ready", current_url=page.url)
