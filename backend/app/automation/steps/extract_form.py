"""Step 3 — Extract form fields from the live DOM."""

from __future__ import annotations

from typing import Any

import structlog
from playwright.async_api import Page

log = structlog.get_logger(__name__)

_DOM_EXTRACTION_SCRIPT = """
() => {
    const fields = [];
    const radioGroups = {};

    function cleanText(txt) {
        if (!txt) return "";
        return txt.replace(/\\s+/g, " ").trim();
    }

    function resolveLabel(el) {
        // 1. label[for=id]
        if (el.id) {
            const labelEl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
            if (labelEl && cleanText(labelEl.innerText)) {
                return cleanText(labelEl.innerText);
            }
        }
        // 2. Enclosing label
        const parentLabel = el.closest("label");
        if (parentLabel && cleanText(parentLabel.innerText)) {
            return cleanText(parentLabel.innerText);
        }
        // 3. aria-label
        const ariaLabel = el.getAttribute("aria-label");
        if (ariaLabel && cleanText(ariaLabel)) {
            return cleanText(ariaLabel);
        }
        // 4. aria-labelledby
        const labelledBy = el.getAttribute("aria-labelledby");
        if (labelledBy) {
            const target = document.getElementById(labelledBy);
            if (target && cleanText(target.innerText)) {
                return cleanText(target.innerText);
            }
        }
        // 5. placeholder
        if (el.placeholder && cleanText(el.placeholder)) {
            return cleanText(el.placeholder);
        }
        // 6. Preceding sibling or parent header
        const prev = el.previousElementSibling;
        if (prev && cleanText(prev.innerText) && cleanText(prev.innerText).length < 80) {
            return cleanText(prev.innerText);
        }
        // 7. name attribute as fallback
        return el.name || el.id || "Unknown Field";
    }

    const inputSelector = [
        "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset])",
        "select",
        "textarea"
    ].join(", ");
    const elements = document.querySelectorAll(inputSelector);

    let counter = 0;
    for (const el of elements) {
        counter++;
        const tag = el.tagName.toUpperCase();
        let type = "text";

        if (tag === "SELECT") {
            type = "select";
        } else if (tag === "TEXTAREA") {
            type = "textarea";
        } else {
            type = (el.type || "text").toLowerCase();
        }

        const hasBox = el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0;
        const isVisible = el.type === "file" || hasBox;
        if (!isVisible && el.type !== "file") {
            continue;
        }


        const label = resolveLabel(el);
        const required = Boolean(
            el.required ||
            el.getAttribute("aria-required") === "true" ||
            label.includes("*") ||
            el.classList.contains("required")
        );

        // Compute reliable selector
        let selector = "";
        if (el.id) {
            selector = `#${CSS.escape(el.id)}`;
        } else if (el.name) {
            selector = `${tag.toLowerCase()}[name="${CSS.escape(el.name)}"]`;
        } else {
            selector = `${tag.toLowerCase()}:nth-of-type(${counter})`;
        }

        // Handle Radios: group by name
        if (type === "radio" && el.name) {
            if (!radioGroups[el.name]) {
                radioGroups[el.name] = {
                    id: `radio_group_${el.name}`,
                    label: label.replace(/\\s*\\(.*\\)/, "").trim() || el.name,
                    type: "radio",
                    required: required,
                    options: [],
                    selector: `input[name="${CSS.escape(el.name)}"]`,
                };
            }
            const optVal = cleanText(el.value) || label;
            if (optVal && !radioGroups[el.name].options.includes(optVal)) {
                radioGroups[el.name].options.push(optVal);
            }
            continue;
        }

        // Collect options for select
        let options = [];
        if (type === "select") {
            options = Array.from(el.options)
                .map(o => cleanText(o.text || o.value))
                .filter(Boolean);
        }

        fields.push({
            id: el.id || `field_${counter}`,
            label: label.replace(/\\*$/, "").trim(),
            type: type,
            required: required,
            options: options,
            selector: selector,
        });
    }

    // Append grouped radios
    for (const group of Object.values(radioGroups)) {
        fields.push(group);
    }

    return fields;
}
"""


async def extract_form(*, page: Page) -> list[dict[str, Any]]:
    """Walk the live DOM (including child iframes if present) and extract structured form fields."""
    log.info("extract_form.evaluating_dom")

    # 1. Evaluate on top-level page
    try:
        fields: list[dict[str, Any]] = await page.evaluate(_DOM_EXTRACTION_SCRIPT)
    except Exception as exc:
        log.error("extract_form.evaluation_error", error=str(exc))
        fields = []

    # 2. Check iframes if top-level found few fields
    if len(fields) < 2:
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                frame_fields: list[dict[str, Any]] = await frame.evaluate(_DOM_EXTRACTION_SCRIPT)
                if frame_fields and len(frame_fields) > len(fields):
                    log.info(
                        "extract_form.found_in_iframe", frame_url=frame.url, count=len(frame_fields)
                    )
                    fields = frame_fields
            except Exception:
                continue

    log.info("extract_form.extracted_fields", count=len(fields))
    return fields
