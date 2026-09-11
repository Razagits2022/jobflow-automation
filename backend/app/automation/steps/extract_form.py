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
        // 0. Form.io specific label
        if (el.classList && (el.classList.contains("formio-component") || el.closest(".formio-component"))) {
            const comp = el.classList.contains("formio-component") ? el : el.closest(".formio-component");
            const lbl = comp.querySelector("label, [ref='label']");
            if (lbl && cleanText(lbl.textContent)) return cleanText(lbl.textContent);
        }
        // 1. label[for=id]
        if (el.id) {
            const labelEl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
            if (labelEl && cleanText(labelEl.textContent)) {
                return cleanText(labelEl.textContent);
            }
        }
        // 2. Enclosing label
        const parentLabel = el.closest("label");
        if (parentLabel && cleanText(parentLabel.textContent)) {
            return cleanText(parentLabel.textContent);
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
            if (target && cleanText(target.textContent)) {
                return cleanText(target.textContent);
            }
        }
        // 5. Container / Field Entry label (e.g. Ashby, Greenhouse, Lever field groups)
        const fieldEntry = el.closest("[class*='fieldEntry'], [class*='field-entry'], [class*='form-group'], [class*='form-field'], [class*='field_'], .field");
        if (fieldEntry) {
            const entryLabel = fieldEntry.querySelector("label, [class*='question-title'], [class*='heading']");
            if (entryLabel && cleanText(entryLabel.textContent)) {
                return cleanText(entryLabel.textContent);
            }
        }
        // 6. placeholder if meaningful (not generic like 'Start typing...' or 'Type here...')
        if (el.placeholder && cleanText(el.placeholder) && !/^(start typing|type here|search|select|choose|enter|\.\.\.)/i.test(el.placeholder.trim())) {
            return cleanText(el.placeholder);
        }
        // 7. Preceding sibling or parent header
        const prev = el.previousElementSibling;
        if (prev && cleanText(prev.textContent) && cleanText(prev.textContent).length < 80) {
            return cleanText(prev.textContent);
        }
        // 8. name attribute as fallback
        return el.name || el.id || "Unknown Field";
    }

    function isSearchOrMarketingForm(form) {
        if (!form) return false;
        if (form.getAttribute("role") === "search") return true;
        const action = (form.getAttribute("action") || "").toLowerCase();
        const id = (form.id || "").toLowerCase();
        const cls = (typeof form.className === "string" ? form.className : "").toLowerCase();

        // Exclude HubSpot marketing forms / drawers
        if (id.includes("hsform") || cls.includes("hs-form") || id.includes("hubspot")) {
            return true;
        }

        if (action.includes("search") || id.includes("search") || cls.includes("search")) {
            const hasFile = form.querySelector('input[type="file"], .formio-component-file');
            const hasEmail = form.querySelector('input[type="email"], input[name*="email" i], input[id*="email" i]');
            const hasCv = form.querySelector('input[name*="cv" i], input[name*="resume" i], input[id*="cv" i]');
            if (!hasFile && !hasEmail && !hasCv) {
                return true;
            }
        }
        if (action.includes("search-result") || action.includes("search_result") || action.includes("job-search")) {
            return true;
        }
        return false;
    }

    const inputSelector = [
        "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset])",
        "select",
        "textarea"
    ].join(", ");

    // Gather candidate forms / containers
    let targetForm = null;
    const forms = Array.from(document.querySelectorAll("form")).filter(f => !isSearchOrMarketingForm(f));

    // Priority 1: Form with file upload input
    for (const f of forms) {
        if (f.querySelector('input[type="file"]')) {
            targetForm = f;
            break;
        }
    }

    // Priority 2: Fallback for SPA / Form.io forms not wrapped in <form> tag
    if (!targetForm) {
        const spaContainers = Array.from(document.querySelectorAll(
            ".primary-bg, .formio-form, [class*='apply-form'], [class*='job-form'], [class*='styles_root']"
        )).filter(c => !c.closest("header") && !c.closest("nav") && !c.closest("footer"));

        // Prefer container with "Apply" heading or file component
        for (const c of spaContainers) {
            if (c.querySelector('.formio-component-file, input[type="file"]') || /apply to this job/i.test(c.innerText || '')) {
                targetForm = c;
                break;
            }
        }

        if (!targetForm && forms.length > 0) {
            targetForm = forms[0];
        }
    }

    if (targetForm) {
        targetForm.setAttribute("data-jf-target-form", "true");
    }

    // Elements to extract: scoped to targetForm if found, else document
    let baseContainer = targetForm || document.body;
    const elements = Array.from(baseContainer.querySelectorAll(inputSelector)).filter(el => {
        if (el.closest("header") || el.closest("nav")) return false;
        if (isSearchOrMarketingForm(el.closest("form"))) return false;
        return true;
    });

    // Also include any primary resume upload file inputs outside targetForm (e.g. Phenom People .resume-upload-wrapper)
    const externalFileInputs = Array.from(document.querySelectorAll(
        '.resume-upload-wrapper input[type="file"], .resume-section input[type="file"], [class*="resume-upload"] input[type="file"], [class*="cv-upload"] input[type="file"], [class*="resumeSection"] input[type="file"]'
    )).filter(el => !elements.includes(el) && !el.closest("header") && !el.closest("nav") && !el.closest("footer"));
    elements.unshift(...externalFileInputs);

    // Also check for Form.io file components inside baseContainer without native input
    const formioFileComps = Array.from(baseContainer.querySelectorAll(
        '.formio-component-file, [class*="formio-component-file"]'
    ));

    let counter = 0;
    for (const el of elements) {
        // Exclude search forms and navigation inputs
        if (el.closest("header") || el.closest("nav") || isSearchOrMarketingForm(el.closest("form"))) {
            continue;
        }

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

        // Ignore internal dummy inputs used by custom select libraries (e.g. React-Select hidden requiredInput)
        if (el.getAttribute("aria-hidden") === "true" || el.tabIndex === -1 || (typeof el.className === "string" && el.className.includes("requiredInput"))) {
            if (el.type !== "file") {
                continue;
            }
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
            // CSS ID selector #<id> is only valid if it starts with a letter or underscore
            if (/^[a-zA-Z_][a-zA-Z0-9_-]*$/.test(el.id)) {
                selector = `#${el.id}`;
            } else {
                selector = `[id="${el.id.replace(/"/g, '\\"')}"]`;
            }
        } else if (el.name) {
            if (/^[a-zA-Z_][a-zA-Z0-9_-]*$/.test(el.name)) {
                selector = `${tag.toLowerCase()}[name="${el.name}"]`;
            } else {
                selector = `${tag.toLowerCase()}[name="${el.name.replace(/"/g, '\\"')}"]`;
            }
        } else {
            const entry = el.closest("[data-field-path]");
            if (entry && entry.getAttribute("data-field-path")) {
                const fp = entry.getAttribute("data-field-path");
                selector = `[data-field-path="${fp}"] input`;
            } else {
                counter++;
                el.setAttribute("data-jf-id", String(counter));
                selector = `[data-jf-id="${counter}"]`;
            }
        }

        // Detect React-Select or custom combobox
        const isReactSelect = Boolean(
            el.classList.contains("select__input") ||
            el.getAttribute("role") === "combobox" ||
            el.closest(".select-shell") ||
            el.closest(".select__container") ||
            (typeof el.className === "string" && el.className.includes("input-autocomplete")) ||
            el.placeholder === "Start typing..."
        );
        if (isReactSelect && type === "text") {
            type = "select";
        }

        // Handle Radios: group by name
        if (type === "radio" && el.name) {
            if (!radioGroups[el.name]) {
                function resolveGroupLabel(node) {
                    const labelledBy = node.getAttribute("aria-labelledby");
                    if (labelledBy) {
                        const target = document.getElementById(labelledBy);
                        if (target && cleanText(target.textContent)) {
                            const raw = cleanText(target.textContent);
                            const cleaned = raw.replace(/\\s*(?:yes|no|true|false)\\s*$/i, "").replace(/[:\\s]+$/, "").trim();
                            if (cleaned.length > 5) return cleaned;
                        }
                    }
                    const fieldset = node.closest("fieldset");
                    if (fieldset) {
                        const legend = fieldset.querySelector("legend");
                        if (legend && cleanText(legend.textContent)) return cleanText(legend.textContent);
                    }
                    const container = node.closest(".pad-v-3, .form-group, fieldset");
                    if (container) {
                        const title = container.querySelector(".external-form__label, [class*='label--title'], [class*='label__title'], legend");
                        if (title && cleanText(title.textContent)) return cleanText(title.textContent);
                    }
                    return "";
                }
                const groupLabel = resolveGroupLabel(el) || label.replace(/\\s*\\(.*\\)/, "").trim() || el.name;
                radioGroups[el.name] = {
                    id: `radio_group_${el.name}`,
                    label: groupLabel.replace(/\\*$/, "").trim(),
                    type: "radio",
                    required: required,
                    options: [],
                    selector: `input[name="${el.name.replace(/"/g, '\\"')}"]`,
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
            if (tag === "SELECT") {
                options = Array.from(el.options)
                    .map(o => cleanText(o.text || o.value))
                    .filter(Boolean);
            } else if (isReactSelect) {
                // 1. Try reading options directly from React Fiber tree (traversing up parents)
                try {
                    function findFiber(node) {
                        let currNode = node;
                        while (currNode) {
                            for (const k of Object.keys(currNode)) {
                                if (k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')) {
                                    return currNode[k];
                                }
                            }
                            currNode = currNode.parentElement;
                        }
                        return null;
                    }

                    const fiber = findFiber(el);
                    let curr = fiber;
                    let depth = 0;
                    while (curr && depth < 30) {
                        if (curr.memoizedProps && curr.memoizedProps.options && Array.isArray(curr.memoizedProps.options)) {
                            options = curr.memoizedProps.options.map(o => {
                                if (!o) return "";
                                return cleanText(typeof o === "string" ? o : (o.label || o.value || o.textEn || ""));
                            }).filter(Boolean);
                            break;
                        }
                        curr = curr.return;
                        depth++;
                    }
                } catch (e) {}

                // 2. Fallback to DOM options if already rendered
                if (options.length === 0) {
                    const shell = el.closest(".select-shell") || el.closest(".select__container");
                    if (shell) {
                        const optElements = shell.querySelectorAll(".select__option");
                        if (optElements.length > 0) {
                            options = Array.from(optElements).map(o => cleanText(o.innerText)).filter(Boolean);
                        }
                    }
                }

                // 3. Fallback for strictly boolean screening questions
                if (options.length === 0 && (/fluent|authorized|sponsorship|eligible/i.test(label) || /^(are you|do you|will you)\b/i.test(label))) {
                    options = ["Yes", "No"];
                }
            }
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

    // Add Form.io file components if no native file input was present
    for (const comp of formioFileComps) {
        const hasExisting = fields.some(f => f.type === "file");
        if (!hasExisting) {
            counter++;
            const compLabel = resolveLabel(comp) || "Resume / CV";
            let selector = "";
            if (comp.id) {
                selector = `#${CSS.escape(comp.id)}`;
            } else {
                comp.setAttribute("data-jf-id", String(counter));
                selector = `[data-jf-id="${counter}"]`;
            }
            fields.push({
                id: comp.id || `field_${counter}`,
                label: compLabel.replace(/\\*$/, "").trim(),
                type: "file",
                required: comp.classList.contains("required") || compLabel.includes("*"),
                options: [],
                selector: selector,
            });
        }
    }

    // Append grouped radios
    for (const group of Object.values(radioGroups)) {
        fields.push(group);
    }

    // Append Ashby yes/no button groups (.ashby-application-form-input-yesno)
    const ashbyYesNoGroups = Array.from(baseContainer.querySelectorAll('.ashby-application-form-input-yesno, div[class*="input-yesno"]')).filter(g => g.querySelector('button[data-option]'));
    for (const group of ashbyYesNoGroups) {
        const entry = group.closest('[class*="fieldEntry"], [class*="field-entry"]') || group.parentElement;
        const labelEl = entry ? entry.querySelector('label, [class*="question-title"], [class*="heading"]') : null;
        const rawLabel = labelEl ? cleanText(labelEl.textContent) : "Yes/No Question";
        const fieldPath = entry ? entry.getAttribute("data-field-path") : null;
        const input = group.querySelector("input[name]");
        const inputName = input ? input.getAttribute("name") : null;

        let selector = "";
        if (fieldPath) {
            selector = `[data-field-path="${fieldPath}"]`;
        } else if (inputName) {
            selector = `input[name="${inputName}"]`;
        } else {
            counter++;
            group.setAttribute("data-jf-id", String(counter));
            selector = `[data-jf-id="${counter}"]`;
        }

        fields.push({
            id: fieldPath || inputName || `ashby_yesno_${counter}`,
            label: rawLabel.replace(/\\*$/, "").trim(),
            type: "radio",
            required: rawLabel.includes("*") || Boolean(entry && entry.querySelector('[class*="required"]')),
            options: ["Yes", "No"],
            selector: selector,
        });
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
