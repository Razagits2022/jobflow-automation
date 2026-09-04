"""Step 8 — Submit the application form and verify confirmation."""

from __future__ import annotations

import re
import uuid

import structlog
from playwright.async_api import Page

log = structlog.get_logger(__name__)

_SUBMIT_BUTTON_REGEX = re.compile(
    r"\b(submit application|submit|send application|complete application|apply)\b",
    re.IGNORECASE,
)

_CONFIRMATION_TEXT_REGEX = re.compile(
    r"\b(thank you for (your )?application|application (has been )?submitted|"
    r"application received|successfully submitted|we have received your application)\b",
    re.IGNORECASE,
)



async def submit(*, page: Page, run_id: uuid.UUID) -> None:
    """Locate and click the submit button, then verify successful confirmation.

    Raises:
        RuntimeError: If the submit button cannot be found or if no confirmation signal is received.
    """
    initial_url = page.url
    log.info("submit.attempting", run_id=str(run_id), url=initial_url)

    # 1. Locate submit button
    submit_locators = [
        page.locator('button[type="submit"]').first,
        page.locator('input[type="submit"]').first,
        page.get_by_role("button", name=_SUBMIT_BUTTON_REGEX).first,
        page.locator("button, a.btn").filter(has_text=_SUBMIT_BUTTON_REGEX).first,
    ]

    submit_btn = None
    for loc in submit_locators:
        try:
            if await loc.is_visible(timeout=1500):
                submit_btn = loc
                break
        except Exception:
            continue

    if submit_btn is None:
        raise RuntimeError("Could not find a visible submit button on the application form.")

    # 2. Click submit
    log.info("submit.clicking_submit_button")
    await submit_btn.click(timeout=5000)

    # 3. Wait for confirmation signal
    # Signal A: URL change
    confirmed = False
    for _ in range(8):  # Poll for up to 8 seconds
        await page.wait_for_timeout(1000)
        current_url = page.url.lower()

        if current_url != initial_url.lower() and any(
            token in current_url
            for token in ("thank", "confirm", "success", "submitted", "complete", "done")
        ):
            log.info("submit.confirmed_via_url", new_url=current_url)
            confirmed = True
            break

        # Signal B: Confirmation text in DOM
        try:
            matched_text = (
                await page.locator("body").filter(has_text=_CONFIRMATION_TEXT_REGEX).count()
            )
            if matched_text > 0:
                log.info("submit.confirmed_via_text")
                confirmed = True
                break
        except Exception:
            pass

    if not confirmed:
        # Check if validation errors blocked submission
        error_count = await page.locator(
            '[role="alert"], [aria-invalid="true"], .error-message'
        ).count()
        if error_count > 0:
            raise RuntimeError(
                f"Submission halted: {error_count} field error(s) flagged after clicking submit."
            )
        raise RuntimeError(
            "Application submission could not be confirmed "
            "(timeout waiting for confirmation screen)."
        )

    log.info("submit.successful", run_id=str(run_id))
