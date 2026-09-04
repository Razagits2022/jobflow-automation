"""Step 5 — Fill the application form fields using Playwright."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from playwright.async_api import Page

from app.automation.steps.map_fields import FieldMapping

log = structlog.get_logger(__name__)


async def fill_form(
    *,
    page: Page,
    field_values: list[FieldMapping] | list[dict[str, Any]],
    resume_path: str | None = None,
) -> list[dict[str, str]]:
    """Fill each mapped field according to its action and record outcomes.

    Supported actions:
      - 'fill': text, email, tel, number, textarea
      - 'select': select dropdowns
      - 'check': radio buttons and checkboxes
      - 'upload': file upload with resume_path
      - 'skip': skipped without error

    Returns:
        List of dicts with keys 'field_label', 'mapped_value', and 'status'.
    """

    results: list[dict[str, str]] = []

    for item in field_values:
        mapping = item if isinstance(item, FieldMapping) else FieldMapping(**item)
        selector = mapping.selector
        value = mapping.value
        action = mapping.action

        # Generate label for audit
        label = (
            selector.replace("#", "").replace("input[name=", "").replace("]", "").replace('"', "")
        )

        if action == "skip" or not selector:
            results.append(
                {
                    "field_label": label,
                    "mapped_value": value,
                    "status": "skipped",
                }
            )
            continue

        try:
            loc = page.locator(selector).first

            if action == "upload":
                if resume_path and Path(resume_path).exists():
                    log.info("fill_form.uploading_resume", selector=selector, path=resume_path)
                    await loc.set_input_files(resume_path, timeout=5000)
                    results.append(
                        {
                            "field_label": "Resume / CV",
                            "mapped_value": Path(resume_path).name,
                            "status": "filled",
                        }
                    )
                else:
                    log.warning("fill_form.resume_path_missing", path=resume_path)
                    results.append(
                        {
                            "field_label": "Resume / CV",
                            "mapped_value": "No resume file available",
                            "status": "skipped",
                        }
                    )

            elif action == "fill":
                log.debug("fill_form.filling_text", selector=selector, value=value[:30])
                await loc.fill(value, timeout=4000)
                results.append(
                    {
                        "field_label": label,
                        "mapped_value": value,
                        "status": "filled",
                    }
                )

            elif action == "select":
                log.debug("fill_form.selecting_option", selector=selector, value=value)
                try:
                    await loc.select_option(label=value, timeout=3000)
                except Exception:
                    await loc.select_option(value=value, timeout=3000)
                results.append(
                    {
                        "field_label": label,
                        "mapped_value": value,
                        "status": "filled",
                    }
                )

            elif action == "check":
                log.debug("fill_form.checking_option", selector=selector, value=value)
                # Check if this is a radio group with multiple options
                radio = page.locator(f'{selector}[value="{value}"]').first
                if await radio.count() > 0:
                    await radio.check(timeout=3000)
                else:
                    # Look for input near label text
                    matched = page.locator("label").filter(has_text=value).locator("input").first
                    if await matched.count() > 0:
                        await matched.check(timeout=3000)
                    else:
                        await loc.check(timeout=3000)
                results.append(
                    {
                        "field_label": label,
                        "mapped_value": value,
                        "status": "filled",
                    }
                )

            # Minor delay between inputs to mimic human interaction
            await page.wait_for_timeout(100)

        except Exception as exc:
            log.warning("fill_form.field_failed", selector=selector, error=str(exc))
            results.append(
                {
                    "field_label": label,
                    "mapped_value": value,
                    "status": "failed",
                }
            )

    return results
