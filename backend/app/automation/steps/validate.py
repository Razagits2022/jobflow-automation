"""Step 7 — Detect form validation errors after fill."""

from __future__ import annotations

import structlog
from playwright.async_api import Page

from app.automation.errors import ValidationFailedError

log = structlog.get_logger(__name__)

_ERROR_SELECTORS = [
    '[role="alert"]:not(#__next-route-announcer__):not([id*="announcer"])',
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

    # Settle validation: ensure inputs with non-empty values have dispatched blur/change
    try:
        await page.evaluate("""() => {
            const inputs = document.querySelectorAll('input:not([type=hidden]), textarea');
            for (const inp of inputs) {
                if (inp.value && inp.value.trim().length > 0 && inp.getAttribute('aria-invalid') === 'true') {
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                    inp.dispatchEvent(new Event('blur', {bubbles: true}));
                }
            }
        }""")
        await page.wait_for_timeout(200)
    except Exception:
        pass

    for selector in _ERROR_SELECTORS:
        try:
            locators = page.locator(selector)
            count = await locators.count()
            for i in range(min(count, 5)):
                loc = locators.nth(i)
                if await loc.is_visible(timeout=300):
                    el_id = (await loc.get_attribute("id") or "").lower()
                    if "announcer" in el_id:
                        continue
                    text = (await loc.text_content() or "").strip()
                    if not text or len(text) >= 200:
                        continue
                    if any(w in text.lower() for w in ["cookie", "privacy", "copyright", "terms of use"]):
                        continue
                    field_errors[f"field_{i + 1}"] = text
        except Exception:
            continue

    if field_errors:
        err_msg = "; ".join(field_errors.values())
        log.warning("validate.form_validation_failed", errors=err_msg)
        raise ValidationFailedError(f"Form validation errors: {err_msg}", field_errors=field_errors)

    log.debug("validate.passed")
