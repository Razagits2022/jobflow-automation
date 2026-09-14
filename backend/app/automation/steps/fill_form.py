"""Step 5 — Fill the application form fields using Playwright."""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

import structlog
from playwright.async_api import Page

from app.automation.steps.map_fields import FieldMapping

log = structlog.get_logger(__name__)


async def _is_custom_combobox(loc: Any) -> bool:
    """Check if an input is a react-select or custom combobox widget."""
    try:
        return bool(
            await loc.evaluate(
                """el => {
                if (el.getAttribute('role') === 'combobox') return true;
                if (el.classList.contains('select__input')) return true;
                if (typeof el.className === 'string' && el.className.includes('input-autocomplete')) return true;
                if (el.placeholder === 'Start typing...') return true;
                if (el.closest('.select-shell') || el.closest('.select__container') || el.closest('.select__control')) return true;
                return false;
            }"""
            )
        )
    except Exception:
        return False


async def _fill_combobox_or_select(
    page: Page,
    loc: Any,
    value: str,
    *,
    label_hint: str = "",
    selector: str = "",
) -> None:
    """Handle custom JS comboboxes, react-select, and location autocomplete widgets."""
    try:
        await loc.scroll_into_view_if_needed(timeout=1500)
    except Exception:
        pass

    try:
        await loc.click(force=True, timeout=2000)
    except Exception:
        try:
            await loc.evaluate(
                """el => {
                    const c = el.closest('[class*="-control"], [class*="select__control"], .select-shell, .select__container') || el;
                    c.scrollIntoView({block: 'center'});
                    c.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                    el.focus();
                }"""
            )
        except Exception:
            pass
    await page.wait_for_timeout(250)

    is_location = any(
        w in label_hint.lower() or w in selector.lower()
        for w in ["location", "city", "address", "country", "based in"]
    )

    if is_location:
        # Location autocomplete (e.g. Greenhouse geocode-earth API or Ashby location)
        try:
            await loc.fill("")
        except Exception:
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")

        city_query = value.split(",")[0].strip() if "," in value else value.strip()
        await page.keyboard.type(city_query, delay=75)

        # Wait up to 3.5 seconds for suggestions to populate
        matched = False
        opts = page.locator(
            "#react-select-candidate-location-listbox div.select__option, "
            "#react-select-candidate-location-listbox > div, "
            ".select__menu div.select__option, "
            ".select__menu-list > div, "
            "div.select__option, "
            ".react-select__option, "
            "[role='option'], "
            ".ashby-application-form-input-autocomplete-popup-result"
        )
        for _ in range(14):
            await page.wait_for_timeout(250)
            count = await opts.count()
            if count > 0:
                first_text = (await opts.first.inner_text()).strip()
                if first_text and first_text.lower() != "loading...":
                    city_part = city_query.lower()
                    for i in range(count):
                        opt_text = (await opts.nth(i).inner_text()).strip()
                        if city_part and city_part in opt_text.lower():
                            await opts.nth(i).click()
                            matched = True
                            break
                    if not matched:
                        await opts.first.click()
                        matched = True
                    break

        if not matched:
            locate_btn = page.locator("button:has-text('Locate me')")
            if await locate_btn.count() > 0 and await locate_btn.first.is_visible():
                await locate_btn.first.click()
                await page.wait_for_timeout(1000)
            else:
                await page.keyboard.press("Enter")
    else:
        # Try typing into input to trigger custom options
        try:
            await loc.fill(value or "")
            await page.wait_for_timeout(250)
        except Exception:
            pass

        # Standard React-Select or custom combobox
        opts = page.locator(
            ".react-select__option, .select__menu div.select__option, .select__menu-list > div, div.select__option, [class*='-option'], [role='option'], .ashby-application-form-input-autocomplete-popup-result"
        )
        count = await opts.count()
        if count == 0:
            # Try keyboard ArrowDown to trigger menu if not already open
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(300)
            count = await opts.count()

        if count > 0:
            options_text = [(await opts.nth(i).inner_text()).strip() for i in range(count)]
            chosen_index: int | None = None

            # 1. Exact or substring match
            val_low = (value or "").lower().strip()
            for i, opt in enumerate(options_text):
                opt_clean = opt.lower().strip()
                if opt_clean == val_low or (val_low and val_low in opt_clean):
                    chosen_index = i
                    break

            # 2. Semantic matching for No / None / Clearance / Yes / Source
            if chosen_index is None:
                if val_low in ("no", "false", "none") or "clearance" in label_hint.lower():
                    for i, opt in enumerate(options_text):
                        if any(w in opt.lower() for w in ["no clearance", "none", "not held", "never", "no "]):
                            chosen_index = i
                            break
                elif val_low in ("yes", "true"):
                    for i, opt in enumerate(options_text):
                        if "yes" in opt.lower():
                            chosen_index = i
                            break
                elif any(w in label_hint.lower() for w in ["hear", "source"]):
                    for i, opt in enumerate(options_text):
                        if any(
                            s in opt.lower()
                            for s in ["linkedin", "website", "career", "job board", "online"]
                        ):
                            chosen_index = i
                            break

            # 3. Fallback to first available option
            if chosen_index is None and count > 0:
                chosen_index = 0

            if chosen_index is not None:
                await opts.nth(chosen_index).click()
            else:
                await page.keyboard.press("Enter")
        else:
            # Fallback if no dropdown menu rendered
            try:
                await loc.fill(value or "", timeout=2000)
            except Exception:
                pass
            await page.keyboard.press("Enter")


async def fill_form(
    *,
    page: Page,
    field_values: list[FieldMapping] | list[dict[str, Any]],
    resume_path: str | None = None,
    form_fields: list[dict[str, Any]] | None = None,
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

    labels_by_selector: dict[str, str] = {}
    if form_fields:
        for f in form_fields:
            sel = f.get("selector", "")
            lbl = f.get("label")
            if sel and lbl and lbl != "Unknown Field":
                labels_by_selector[sel] = lbl
                labels_by_selector[sel.replace("\\", "")] = lbl

    # Separate upload fields from other form inputs so resume upload runs first
    upload_items = []
    other_items = []
    for item in field_values:
        mapping = item if isinstance(item, FieldMapping) else FieldMapping(**item)
        if mapping.action == "upload":
            upload_items.append(mapping)
        else:
            other_items.append(mapping)

    def _resolve_label(selector: str) -> str:
        norm_sel = selector.replace("\\", "")
        lbl = labels_by_selector.get(selector) or labels_by_selector.get(norm_sel) or ""
        if not lbl:
            raw = (
                selector.replace("#", "")
                .replace("input[name=", "")
                .replace("]", "")
                .replace("[", " ")
                .replace('"', "")
                .replace("application_form_application_", "")
                .replace("application_form_", "")
                .replace("equality_monitoring_", "")
                .replace("_text_answer", "")
                .replace("_boolean_answer", "")
                .replace("_attributes_", " ")
                .replace("_", " ")
                .strip()
            )
            lbl = " ".join(w.capitalize() for w in raw.split()) or "Field"
        return lbl

    # Pass 1: Execute all file upload fields first
    has_uploaded = False
    for mapping in upload_items:
        if has_uploaded:
            log.debug("fill_form.skipping_duplicate_upload", selector=mapping.selector)
            continue
        selector = mapping.selector
        label = "Resume / CV"
        if not selector:
            results.append({"field_label": label, "mapped_value": mapping.value, "status": "skipped"})
            continue

        try:
            loc = page.locator(selector).first
            try:
                await loc.scroll_into_view_if_needed(timeout=1500)
            except Exception:
                pass
            if resume_path and Path(resume_path).exists():
                log.info("fill_form.uploading_resume", selector=selector, path=resume_path)
                # Check if this is a Form.io component
                is_formio = False
                try:
                    is_formio = await loc.evaluate(
                        "el => !!(el.component && el.component.type === 'file') || el.classList.contains('formio-component-file')"
                    )
                except Exception:
                    pass

                if is_formio:
                    log.info("fill_form.uploading_to_formio_component", selector=selector)
                    with open(resume_path, "rb") as resume_file:
                        b64_data = base64.b64encode(resume_file.read()).decode("ascii")
                    fname = Path(resume_path).name
                    await loc.evaluate(
                        """async (el, args) => {
                            const c = el.component || (el.querySelector('.formio-component-file') ? el.querySelector('.formio-component-file').component : null);
                            if (c && typeof c.upload === 'function') {
                                const byteCharacters = atob(args.b64);
                                const byteNumbers = new Array(byteCharacters.length);
                                for (let i = 0; i < byteCharacters.length; i++) byteNumbers[i] = byteCharacters.charCodeAt(i);
                                const byteArray = new Uint8Array(byteNumbers);
                                const blob = new Blob([byteArray], {type: 'application/pdf'});
                                const file = new File([blob], args.filename, {type: 'application/pdf'});
                                c.upload([file]);
                            }
                        }""",
                        {"b64": b64_data, "filename": fname},
                    )
                else:
                    await loc.set_input_files(resume_path, timeout=5000)

                has_uploaded = True
                results.append({
                    "field_label": label,
                    "mapped_value": Path(resume_path).name,
                    "status": "filled",
                })
            else:
                log.warning("fill_form.resume_path_missing", path=resume_path)
                results.append({
                    "field_label": label,
                    "mapped_value": "No resume file available",
                    "status": "skipped",
                })
        except Exception as exc:
            log.warning("fill_form.upload_failed", selector=selector, error=str(exc))
            results.append({"field_label": label, "mapped_value": mapping.value, "status": "failed"})

    # If a resume was uploaded, wait for background ATS parsers (e.g. Ashby, Phenom People) to complete
    if has_uploaded:
        log.info("fill_form.waiting_for_ats_resume_parser_to_settle")
        for _ in range(16):
            await page.wait_for_timeout(500)
            settled = False
            try:
                settled = await page.evaluate("""() => {
                    const bodyText = document.body ? document.body.innerText : '';
                    if (bodyText.includes('Parsing your resume') || bodyText.includes('Autofilling key fields')) {
                        return false;
                    }
                    const spinner = document.querySelector('.spinner, [role="progressbar"], [class*="Autofill-pending"]');
                    if (spinner && spinner.offsetWidth > 0) return false;
                    return true;
                }""")
            except Exception:
                settled = True
            if settled:
                break
        await page.wait_for_timeout(1000)

    # Pass 2: Fill text, select, and checkbox fields
    for mapping in other_items:
        selector = mapping.selector
        value = mapping.value
        action = mapping.action
        label = _resolve_label(selector)

        if action == "skip" or not selector:
            results.append({"field_label": label, "mapped_value": value, "status": "skipped"})
            continue

        try:
            loc = page.locator(selector).first
            try:
                await loc.scroll_into_view_if_needed(timeout=1500)
            except Exception:
                pass

            if action == "fill":
                log.debug("fill_form.filling_text", selector=selector, value=value[:30])
                if await _is_custom_combobox(loc):
                    log.info("fill_form.filling_custom_combobox", selector=selector, value=value)
                    await _fill_combobox_or_select(page, loc, value, label_hint=label, selector=selector)
                else:
                    fill_val = value
                    if any(k in label.lower() for k in ["phone", "mobile", "tel"]):
                        clean_digits = re.sub(r"[^\d+]", "", value)
                        if clean_digits.startswith("+44"):
                            fill_val = clean_digits[3:]
                        elif clean_digits.startswith("0044"):
                            fill_val = clean_digits[4:]
                        elif clean_digits.startswith("+1"):
                            fill_val = clean_digits[2:]
                        elif clean_digits.startswith("+"):
                            fill_val = re.sub(r"^\+\d{1,3}", "", clean_digits)
                    elif any(k in label.lower() for k in ["experience", "how many years", "total work", "years of"]) and any(c.isdigit() for c in str(fill_val)):
                        if not any(w in label.lower() for w in ["summary", "description", "details", "explain", "why"]):
                            digits = re.search(r"\d+", str(fill_val))
                            if digits:
                                fill_val = digits.group(0)
                    else:
                        try:
                            input_type = await loc.get_attribute("type")
                            if input_type == "number":
                                digits = re.search(r"\d+", str(fill_val))
                                if digits:
                                    fill_val = digits.group(0)
                        except Exception:
                            pass

                    # Type cleanly to trigger native keypress and synthetic React handlers
                    try:
                        await loc.click(force=True, timeout=1000)
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Backspace")
                        await loc.press_sequentially(fill_val, delay=10)
                    except Exception:
                        await loc.fill(fill_val, timeout=4000)

                    # Also invoke prototype value descriptor setter to guarantee React state sync
                    try:
                        await loc.evaluate("""(el, val) => {
                            if (el._valueTracker) {
                                el._valueTracker.setValue('');
                            }
                            const desc = Object.getOwnPropertyDescriptor(
                                el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype,
                                'value'
                            );
                            if (desc && desc.set) desc.set.call(el, val);
                            else el.value = val;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            el.dispatchEvent(new Event('blur', { bubbles: true }));
                        }""", fill_val)
                    except Exception:
                        pass
                results.append({"field_label": label, "mapped_value": value, "status": "filled"})

            elif action == "select":
                log.debug("fill_form.selecting_option", selector=selector, value=value)
                is_native_select = False
                try:
                    tag_name = await loc.evaluate("el => el.tagName.toUpperCase()")
                    is_native_select = (tag_name == "SELECT")
                except Exception:
                    pass

                # Check for Ashby Yes/No toggle button group
                is_ashby_yesno = False
                try:
                    is_ashby_yesno = await loc.evaluate(
                        "el => el.classList.contains('ashby-application-form-input-yesno') || !!el.querySelector('button[data-option]')"
                    )
                except Exception:
                    pass

                if is_ashby_yesno:
                    opt_key = "yes" if str(value).lower().strip() in ("yes", "true", "1", "y") else "no"
                    btn = loc.locator(f'button[data-option="{opt_key}"]').first
                    if await btn.count() == 0:
                        btn = page.locator(f'{selector} button[data-option="{opt_key}"]').first
                    if await btn.count() == 0:
                        btn = page.locator(f'button[data-option="{opt_key}"]').first
                    if await btn.count() > 0:
                        try:
                            await btn.scroll_into_view_if_needed(timeout=1500)
                        except Exception:
                            pass
                        await btn.click(timeout=3000)
                        await page.wait_for_timeout(300)
                elif is_native_select:
                    selected_via_js = False
                    try:
                        selected_via_js = await loc.evaluate("""(el, targetVal) => {
                            if (!targetVal || !el || el.tagName !== 'SELECT') return false;
                            const target = String(targetVal).trim().toLowerCase();
                            const options = Array.from(el.options);
                            if (options.length === 0) return false;

                            const aliases = {
                                "united kingdom": ["uk", "gbr", "great britain", "+44", "44", "gbr_44"],
                                "uk": ["united kingdom", "gbr", "great britain", "+44", "44", "gbr_44"],
                                "united states": ["usa", "us", "united states of america", "+1", "1", "usa_1"],
                                "usa": ["united states", "us", "united states of america", "+1", "1", "usa_1"],
                            };

                            let matched = options.find(o => o.text.trim().toLowerCase() === target);
                            if (!matched) matched = options.find(o => o.value.trim().toLowerCase() === target);
                            if (!matched && target.length >= 2) {
                                matched = options.find(o => o.text.trim().toLowerCase().includes(target) || o.value.trim().toLowerCase().includes(target));
                            }
                            if (!matched) {
                                matched = options.find(o => {
                                    const txt = o.text.trim().toLowerCase();
                                    return txt.length >= 4 && target.includes(txt);
                                });
                            }
                            if (!matched) {
                                for (const [key, aliasList] of Object.entries(aliases)) {
                                    if (target === key || target.includes(key) || aliasList.includes(target)) {
                                        matched = options.find(o => {
                                            const txt = o.text.trim().toLowerCase();
                                            const val = o.value.trim().toLowerCase();
                                            return txt === key || txt.includes(key) || aliasList.some(a => txt === a || txt.includes(a) || val === a || val.includes(a));
                                        });
                                        if (matched) break;
                                    }
                                }
                            }

                            if (matched) {
                                el.value = matched.value;
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                el.dispatchEvent(new Event('blur', { bubbles: true }));
                                return true;
                            }
                            return false;
                        }""", value)
                    except Exception:
                        pass

                    if not selected_via_js:
                        try:
                            await loc.select_option(label=value, timeout=3000)
                        except Exception:
                            await loc.select_option(value=value, timeout=3000)
                        try:
                            await loc.evaluate("el => { el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); el.dispatchEvent(new Event('blur', {bubbles: true})); }")
                        except Exception:
                            pass
                else:
                    log.info("fill_form.selecting_custom_combobox", selector=selector, value=value)
                    await _fill_combobox_or_select(page, loc, value, label_hint=label, selector=selector)

                results.append({"field_label": label, "mapped_value": value, "status": "filled"})

            elif action == "check":
                log.debug("fill_form.checking_option", selector=selector, value=value)
                is_checkbox = False
                try:
                    tag = await loc.evaluate("el => el.tagName.toUpperCase()")
                    typ = await loc.evaluate("el => (el.getAttribute('type') || '').toLowerCase()")
                    is_checkbox = (tag == "INPUT" and typ == "checkbox")
                except Exception:
                    pass

                # Check for Ashby Yes/No toggle button group
                is_ashby_yesno = False
                try:
                    is_ashby_yesno = (
                        "yesno" in selector
                        or await loc.evaluate(
                            "el => el.classList.contains('ashby-application-form-input-yesno') || !!el.querySelector('button[data-option]')"
                        )
                    )
                except Exception:
                    pass

                if not is_ashby_yesno:
                    try:
                        is_ashby_yesno = (await page.locator(f"{selector} button[data-option]").count() > 0)
                    except Exception:
                        pass

                if is_ashby_yesno:
                    opt_key = "yes" if str(value).lower().strip() in ("yes", "true", "1", "y") else "no"
                    btn = loc.locator(f'button[data-option="{opt_key}"]').first
                    if await btn.count() == 0:
                        btn = page.locator(f'{selector} button[data-option="{opt_key}"]').first
                    if await btn.count() == 0:
                        btn = page.locator(f'button[data-option="{opt_key}"]').first
                    if await btn.count() > 0:
                        try:
                            await btn.scroll_into_view_if_needed(timeout=1500)
                        except Exception:
                            pass
                        await btn.click(timeout=3000)
                        await page.wait_for_timeout(300)
                elif is_checkbox:
                    truthy = str(value).lower().strip() in ("on", "true", "1", "yes", "checked", "") or bool(value)
                    if truthy:
                        try:
                            await loc.check(force=True, timeout=3000)
                            await loc.evaluate("el => { el.dispatchEvent(new Event('change', {bubbles: true})); el.dispatchEvent(new Event('input', {bubbles: true})); }")
                        except Exception:
                            await loc.evaluate("""el => {
                                el.checked = true;
                                (el.closest('label') || document.querySelector(`label[for='${CSS.escape(el.id)}']`) || el).click();
                                el.dispatchEvent(new Event('change', {bubbles: true}));
                                el.dispatchEvent(new Event('input', {bubbles: true}));
                            }""")
                    else:
                        try:
                            await loc.uncheck(force=True, timeout=3000)
                            await loc.evaluate("el => { el.dispatchEvent(new Event('change', {bubbles: true})); el.dispatchEvent(new Event('input', {bubbles: true})); }")
                        except Exception:
                            pass
                else:
                    clicked = False
                    clean_val = str(value).strip(";").strip()

                    # 1. Direct label click matching option text (triggers native HTML & React state)
                    if clean_val and clean_val.lower() not in ("on", "true", "yes"):
                        opt_label = page.locator("label").filter(has_text=clean_val).first
                        if await opt_label.count() > 0:
                            try:
                                await opt_label.scroll_into_view_if_needed(timeout=1000)
                                await opt_label.click(force=True, timeout=2000)
                                clicked = True
                            except Exception:
                                pass

                    # 2. Try input matching value attribute
                    if not clicked:
                        radio = page.locator(f'{selector}[value="{value}"]').first
                        if await radio.count() > 0:
                            try:
                                await radio.check(force=True, timeout=2000)
                                await radio.evaluate("el => { el.dispatchEvent(new Event('change', {bubbles: true})); el.dispatchEvent(new Event('input', {bubbles: true})); }")
                                clicked = True
                            except Exception:
                                try:
                                    await radio.evaluate("""el => {
                                        el.checked = true;
                                        (el.closest('label') || document.querySelector(`label[for='${CSS.escape(el.id)}']`) || el).click();
                                        el.dispatchEvent(new Event('change', {bubbles: true}));
                                        el.dispatchEvent(new Event('input', {bubbles: true}));
                                    }""")
                                    clicked = True
                                except Exception:
                                    pass

                    # 3. Match role="radio" or card with text
                    if not clicked:
                        role_radio = page.locator(f'[role="radio"]:has-text("{clean_val}"), button:has-text("{clean_val}")').first
                        if await role_radio.count() > 0:
                            try:
                                await role_radio.click(force=True, timeout=2000)
                                clicked = True
                            except Exception:
                                pass

                    # 4. Fallback: click first label or radio in this radio group so it is NEVER left unselected
                    if not clicked:
                        try:
                            radio_inp = page.locator(selector).first
                            if await radio_inp.count() > 0:
                                inp_id = await radio_inp.get_attribute("id")
                                if inp_id:
                                    fallback_lbl = page.locator(f'label[for="{inp_id}"]').first
                                    if await fallback_lbl.count() > 0:
                                        await fallback_lbl.click(force=True, timeout=2000)
                                        clicked = True
                                if not clicked:
                                    await radio_inp.check(force=True, timeout=2000)
                                    await radio_inp.evaluate("el => (el.closest('label') || el).click()")
                                    clicked = True
                        except Exception:
                            pass

                    # Guarantee React state catches the checked radio
                    try:
                        radio_checked = page.locator("input[type='radio']:checked, input[type='checkbox']:checked").first
                        if await radio_checked.count() > 0:
                            await radio_checked.evaluate("""(el) => {
                                const desc = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'checked');
                                if (desc && desc.set) desc.set.call(el, true);
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }""")
                    except Exception:
                        pass

                results.append({"field_label": label, "mapped_value": value, "status": "filled"})

            await page.wait_for_timeout(100)

        except Exception as exc:
            log.warning("fill_form.field_failed", selector=selector, error=str(exc))
            results.append({"field_label": label, "mapped_value": value, "status": "failed"})

    # Pass 3 (Safety Sweep): Re-fill any text field that was wiped back to empty by a late ATS response
    for mapping in other_items:
        if mapping.action == "fill" and mapping.selector and mapping.value:
            try:
                field_loc = page.locator(mapping.selector).first
                if await field_loc.count() > 0 and await field_loc.is_visible(timeout=200):
                    # Never safety-sweep custom comboboxes / autocompletes — raw fill wipes selected tokens
                    if await _is_custom_combobox(field_loc):
                        continue
                    cur_val = await field_loc.input_value()
                    if not cur_val or cur_val.strip() == "":
                        log.info("fill_form.safety_sweep_refilling", selector=mapping.selector, value=mapping.value)
                        await field_loc.fill(mapping.value, timeout=2000)
                        try:
                            await field_loc.evaluate("el => { el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); el.dispatchEvent(new Event('blur', {bubbles: true})); }")
                        except Exception:
                            pass
            except Exception:
                pass

    return results
