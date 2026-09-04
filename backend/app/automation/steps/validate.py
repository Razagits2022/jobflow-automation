"""Step 7 — Detect form validation errors after fill."""

from __future__ import annotations

import structlog
from playwright.async_api import Page

from app.automation.errors import ValidationFailedError

log = structlog.get_logger(__name__)

_ERROR_SELECTORS = [
    '[role="alert"]',
    '[aria-invalid="true"]',
    ".error-message",
    ".invalid-feedback",
    ".field-error",
    ".form-error",
    "span.error",
    "p.error",
]


async def validate(*, page: Page) -> None:
    """Inspect the filled form for blocking client-side validation error messages.

    Raises:
        ValidationFailedError: When field-level error messages are detected.
    """
    field_errors: dict[str, str] = {}

    for selector in _ERROR_SELECTORS:
        try:
            locators = page.locator(selector)
            count = await locators.count()
            for i in range(min(count, 5)):
                loc = locators.nth(i)
                if await loc.is_visible(timeout=300):
                    text = (await loc.text_content() or "").strip()
                    if text and len(text) < 200:
                        field_errors[f"field_{i + 1}"] = text
        except Exception:
            continue

    if field_errors:
        err_msg = "; ".join(field_errors.values())
        log.warning("validate.form_validation_failed", errors=err_msg)
        raise ValidationFailedError(f"Form validation errors: {err_msg}", field_errors=field_errors)

    log.debug("validate.passed")
