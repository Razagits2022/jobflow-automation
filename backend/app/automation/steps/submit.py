"""Step 8 — Submit the application form and verify confirmation."""

from __future__ import annotations

import re
import uuid

import structlog
from playwright.async_api import Page

from app.automation.errors import CaptchaEncounteredError, ValidationFailedError
from app.automation.steps import detect_captcha
from app.automation.steps.solve_captcha import solve_captcha_if_present
from app.core.config import settings

log = structlog.get_logger(__name__)

CLICK_TIMEOUT_MS = 10_000
NAV_TIMEOUT_MS = 15_000
CONFIRM_POLL_SECONDS = 20
CONFIRM_POLL_INTERVAL_MS = 1000

_PRIMARY_SUBMIT_REGEX = re.compile(
    r"\b(submit application|submit|send application|send message|complete application|send)\b",
    re.IGNORECASE,
)
_FALLBACK_SUBMIT_REGEX = re.compile(
    r"\b(apply for this job|apply now|apply)\b",
    re.IGNORECASE,
)

_CONFIRMATION_TEXT_REGEX = re.compile(
    r"\b("
    r"thank you for (your )?(application|message)|"
    r"thank you for (getting in touch|reaching out|contacting us|applying|your interest)|"
    r"application success(ful(ly)?)?|"
    r"application (has been )?submitted|"
    r"application received|"
    r"successfully submitted|"
    r"we have received your application|"
    r"your application has been received|"
    r"we('ve| have) received your application|"
    r"application complete|"
    r"application sent|"
    r"successfully applied|"
    r"you have applied|"
    r"we will be in touch|"
    r"thanks for (applying|reaching out)|"
    r"application confirmed|"
    r"it has been sent|"
    r"your message (has been|was) sent|"
    r"message has been sent|"
    r"submission received|"
    r"your submission has been received|"
    r"form submitted successfully|"
    r"form has been submitted"
    r")\b",
    re.IGNORECASE,
)

_STEP_ADVANCE_REGEX = re.compile(
    r"\b(next step|next|continue|proceed|save & continue|save and continue)\b",
    re.IGNORECASE,
)


def is_confirmation_text(text: str) -> bool:
    """Check if given text represents an application confirmation rather than an error."""
    if not text:
        return False
    if _CONFIRMATION_TEXT_REGEX.search(text):
        return True
    lower = text.lower()
    if "thank you" in lower and any(k in lower for k in ["sent", "message", "application", "received", "submitted", "interest"]):
        return True
    if any(phrase in lower for phrase in ["it has been sent", "message was sent", "message has been sent", "form submitted successfully"]):
        return True
    return False

_URL_STRONG_KEYWORDS = (
    "thank",
    "confirm",
    "success",
    "submitted",
    "complete",
    "done",
    "received",
    "applied",
)

_VALIDATION_ERROR_SELECTORS = (
    '[role="alert"]:not(#__next-route-announcer__):not([id*="announcer"]), [aria-invalid="true"], '
    ".error-message, .field-error, .help-block, .invalid-feedback, "
    ".form-error, .text-danger, span.error, .has-error, .is-invalid, "
    '.error, [class*="error-"], [class*="-error"], '
    '.callout--danger, .callout-danger, [class*="alert-danger"], .alert-danger'
)

_CONFIRMATION_HEADING_SELECTORS = (
    'h1, h2, .success, .confirmation, [class*="success"], [class*="confirm"], '
    '[class*="thank"], .wpcf7-response-output, [data-status="sent"]'
)


async def submit(*, page: Page, run_id: uuid.UUID) -> str:
    """Locate and click the submit button, then verify successful confirmation or step progression.

    Returns:
        "CONFIRMED" if final application confirmation was verified.
        "STEP_ADVANCED" if the form advanced to the next step of a multi-step wizard.

    Raises:
        ValidationFailedError: If form validation errors are detected after submission.
        RuntimeError: If the submit button cannot be found or if confirmation times out.
    """
    initial_url = page.url
    log.info("submit.attempting", run_id=str(run_id), url=initial_url)

    # 1. Locate submit button with strict priority
    target_form_loc = page.locator('form[data-jf-target-form="true"], [data-jf-target-form="true"]')
    has_target_form = False
    try:
        has_target_form = await target_form_loc.count() > 0
    except Exception:
        pass

    primary_locators = []
    if has_target_form:
        primary_locators.extend([
            target_form_loc.locator('button[type="submit"]').first,
            target_form_loc.locator('input[type="submit"]').first,
            target_form_loc.get_by_role("button", name=_PRIMARY_SUBMIT_REGEX).first,
            target_form_loc.locator("button, input, a.btn").filter(has_text=_PRIMARY_SUBMIT_REGEX).first,
            target_form_loc.get_by_role("button", name=_FALLBACK_SUBMIT_REGEX).first,
            target_form_loc.locator("button, input, a.btn").filter(has_text=_FALLBACK_SUBMIT_REGEX).first,
        ])

    # Global search (excluding header/nav):
    # Tier 1: Explicit submit type & primary submit text
    primary_locators.extend([
        page.locator('button[type="submit"]:not(header *):not(nav *)').first,
        page.locator('input[type="submit"]:not(header *):not(nav *)').first,
        page.get_by_role("button", name=_PRIMARY_SUBMIT_REGEX).first,
        page.locator('button:not(header *):not(nav *)').filter(has_text=_PRIMARY_SUBMIT_REGEX).first,
        page.locator('input[type="submit"]:not(header *):not(nav *)').filter(has_text=_PRIMARY_SUBMIT_REGEX).first,
        page.locator("button, a.btn").filter(has_text=_PRIMARY_SUBMIT_REGEX).first,
    ])

    # Tier 2: Fallback to "apply" text ONLY if no submit button was found
    fallback_locators = [
        page.get_by_role("button", name=_FALLBACK_SUBMIT_REGEX).first,
        page.locator('button:not(header *):not(nav *)').filter(has_text=_FALLBACK_SUBMIT_REGEX).first,
        page.locator("button, a.btn").filter(has_text=_FALLBACK_SUBMIT_REGEX).first,
    ]

    # Tier 3: Step advance / next buttons (for multi-step forms)
    step_advance_locators = []
    if has_target_form:
        step_advance_locators.extend([
            target_form_loc.locator('button#next, button.btn-next, button.btn-navigate, button[id*="next" i]').first,
            target_form_loc.get_by_role("button", name=_STEP_ADVANCE_REGEX).first,
            target_form_loc.locator("button, input, a.btn").filter(has_text=_STEP_ADVANCE_REGEX).first,
        ])
    step_advance_locators.extend([
        page.locator('button#next:not(header *):not(nav *), button.btn-next:not(header *):not(nav *), button[id*="next" i]:not(header *):not(nav *)').first,
        page.get_by_role("button", name=_STEP_ADVANCE_REGEX).first,
        page.locator('button:not(header *):not(nav *)').filter(has_text=_STEP_ADVANCE_REGEX).first,
        page.locator("button, a.btn").filter(has_text=_STEP_ADVANCE_REGEX).first,
    ])

    submit_btn = None
    for loc in primary_locators + fallback_locators + step_advance_locators:
        try:
            if await loc.is_visible(timeout=1000):
                # Verify button is not inside a search form or site navigation header
                is_search = await loc.evaluate("""el => {
                    if (el.closest('header') || el.closest('nav')) return true;
                    const text = (el.innerText || el.value || '').trim().toLowerCase();
                    if (text === 'search' || text.startsWith('search ')) return true;
                    const f = el.closest('form');
                    if (!f) {
                        const sec = el.closest('section, div');
                        const secId = (sec ? (sec.id || '') + ' ' + (sec.className || '') : '').toLowerCase();
                        if (secId.includes('search')) return true;
                        return false;
                    }
                    const action = (f.getAttribute('action') || '').toLowerCase();
                    const id = (f.id || '').toLowerCase();
                    const cls = (typeof f.className === 'string' ? f.className : '').toLowerCase();
                    if (action.includes('search') || id.includes('search') || cls.includes('search')) {
                        const hasFile = f.querySelector('input[type="file"]');
                        const hasEmail = f.querySelector('input[type="email"], input[name*="email" i]');
                        if (!hasFile && !hasEmail) return true;
                    }
                    return false;
                }""")
                if not is_search:
                    submit_btn = loc
                    break
        except Exception:
            continue

    if submit_btn is None:
        raise RuntimeError("Could not find a visible submit button on the application form.")

    is_step_advance_button = False
    try:
        btn_text = (await submit_btn.text_content() or await submit_btn.get_attribute("value") or "").strip()
        btn_id = (await submit_btn.get_attribute("id") or "").lower()
        btn_class = (await submit_btn.get_attribute("class") or "").lower()
        if (
            _STEP_ADVANCE_REGEX.search(btn_text)
            or btn_id in ("next", "btn-next", "next-step", "continue-btn", "btn-continue")
            or any(c in btn_class for c in ["btn-next", "step-next", "btn-navigate", "continue-button"])
        ):
            is_step_advance_button = True
    except Exception:
        pass
    log.info("submit.button_identified", is_step_advance=is_step_advance_button)

    # Identify the containing form or container element if present (for Signal D: form removed)
    form_locator = None
    try:
        candidate_form = page.locator("form").filter(has=submit_btn).first
        if await candidate_form.count() > 0:
            form_locator = candidate_form
        else:
            candidate_container = page.locator("section, div").filter(has=submit_btn).filter(has=page.locator("input")).last
            if await candidate_container.count() > 0:
                form_locator = candidate_container
    except Exception:
        pass

    # 2A. Record visible field signatures before clicking submit (for client-side step progression detection)
    initial_field_signatures: set[str] = set()
    try:
        raw_sigs = await page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), textarea, select'));
            return els.filter(el => el.offsetWidth > 0 && el.offsetHeight > 0).map(el => (el.id || '') + '::' + (el.name || '')).filter(Boolean);
        }""")
        initial_field_signatures = set(raw_sigs)
    except Exception:
        pass

    # Click submit button
    log.info("submit.clicking_submit_button")
    try:
        await submit_btn.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    try:
        await submit_btn.click(timeout=CLICK_TIMEOUT_MS)
    except Exception:
        # If button is disabled or obstructed, try JS click
        await submit_btn.evaluate("""btn => {
            btn.removeAttribute('disabled');
            btn.disabled = false;
            btn.click();
        }""")

    # 2B. Poll for confirmation signals
    confirmed = False
    waited_seconds = 0

    captcha_recovery_attempted = False
    for iteration in range(1, CONFIRM_POLL_SECONDS + 1):
        await page.wait_for_timeout(CONFIRM_POLL_INTERVAL_MS)
        waited_seconds = iteration
        current_url = page.url

        # Check for false-positive Search Results redirect
        is_search_page = False
        try:
            is_search_page = await page.evaluate("""() => {
                const url = window.location.href.toLowerCase();
                const body = (document.body ? document.body.innerText : '').toLowerCase();

                // If explicit confirmation indicators are present, it is NOT a search results page
                if (url.includes('application-sent') || url.includes('application_success') || url.includes('thank-you') ||
                    body.includes('application sent') || body.includes('thank you for your application') || body.includes('application submitted') ||
                    body.includes('your job application has been submitted')) {
                    return false;
                }

                if (url.includes('search-results') || url.includes('search_results') || url.includes('job-search-results')) {
                    return true;
                }
                if (body.includes('no jobs that match your search') || body.includes('there are no jobs that match') || body.includes('0 jobs found')) {
                    return true;
                }
                return false;
            }""")
        except Exception:
            pass

        if is_search_page:
            log.error("submit.search_results_page_detected", current_url=current_url)
            raise RuntimeError("Submission redirected to a job search results page instead of application confirmation.")

        # Check for immediate validation error banners on the page
        error_texts: list[str] = []
        try:
            # 1. Prioritize prominent alert banners first (.alert-danger, .alert, [role="alert"])
            alert_locators = page.locator('.alert-danger, [role="alert"]:not(#__next-route-announcer__):not([id*="announcer"]), .alert, .formio-errors')
            alert_count = await alert_locators.count()
            for i in range(min(alert_count, 5)):
                loc = alert_locators.nth(i)
                if await loc.is_visible(timeout=100):
                    text = (await loc.text_content() or "").strip()
                    if is_confirmation_text(text):
                        log.info("submit.confirmed", signal="alert_with_confirmation_text", response_text=text[:120])
                        confirmed = True
                        break
                    if text and len(text) < 300 and text not in error_texts:
                        if not any(w in text.lower() for w in ["cookie", "privacy", "copyright"]):
                            error_texts.append(text[:120])

            # 2. General field error indicators
            if not confirmed and len(error_texts) < 3:
                err_locators = page.locator(_VALIDATION_ERROR_SELECTORS)
                count = await err_locators.count()
                for i in range(min(count, 15)):
                    loc = err_locators.nth(i)
                    if await loc.is_visible(timeout=100):
                        el_id = (await loc.get_attribute("id") or "").lower()
                        if "announcer" in el_id:
                            continue
                        text = (await loc.text_content() or "").strip()
                        if is_confirmation_text(text):
                            log.info("submit.confirmed", signal="alert_with_confirmation_text", response_text=text[:120])
                            confirmed = True
                            break
                        if text and len(text) < 300 and text not in error_texts:
                            if not any(w in text.lower() for w in ["cookie", "privacy", "copyright"]):
                                error_texts.append(text[:120])
                        if len(error_texts) >= 3:
                            break
        except Exception:
            pass

        # If only generic button label was caught early while server API call is in-flight, give it a moment to resolve
        if error_texts and all("please check the form" in e.lower() for e in error_texts) and waited_seconds < 3:
            await page.wait_for_timeout(1000)
            try:
                late_alerts = page.locator('.alert-danger, .alert, [role="alert"]')
                for i in range(await late_alerts.count()):
                    late_text = (await late_alerts.nth(i).text_content() or "").strip()
                    if late_text and late_text not in error_texts:
                        error_texts.insert(0, late_text[:150])
            except Exception:
                pass

        if confirmed:
            break

        if error_texts:
            joined_errs = "; ".join(error_texts)
            if any(k in err.lower() for err in error_texts for k in ["captcha", "recaptcha", "spam"]):
                log.warning("submit.captcha_error_detected", errors=joined_errs, waited_seconds=waited_seconds)
                # CapSolver auto-recovery if configured
                if settings.capsolver_api_key and "your-" not in settings.capsolver_api_key.lower() and not captcha_recovery_attempted:
                    captcha_recovery_attempted = True
                    log.info("submit.attempting_capsolver_recovery")
                    solved = await solve_captcha_if_present(page=page)
                    if solved:
                        log.info("submit.capsolver_solved_reclicking_submit")
                        await page.wait_for_timeout(1000)
                        try:
                            await submit_btn.click(timeout=5000)
                        except Exception:
                            await submit_btn.evaluate("btn => btn.click()")
                        error_texts.clear()
                        continue
                raise CaptchaEncounteredError(f"Submission blocked by CAPTCHA/Anti-Spam: {joined_errs}")
            log.warning("submit.validation_errors_detected", errors=joined_errs, waited_seconds=waited_seconds)
            raise ValidationFailedError(
                f"Form validation errors flagged after clicking submit: {joined_errs}"
            )

        # Check if URL change represents advancing to next step of a multi-step form
        if current_url.lower() != initial_url.lower():
            is_strong = any(token in current_url.lower() for token in _URL_STRONG_KEYWORDS)
            is_step_url = any(k in current_url.lower() for k in ["step=", "stepname=", "page=", "/step-", "/step/", "/stage/"])
            if (is_step_url or is_step_advance_button) and not is_strong:
                log.info("submit.step_advanced", previous_url=initial_url, new_url=current_url, waited_seconds=waited_seconds)
                return "STEP_ADVANCED"

        # Client-side multi-step wizard transition (URL remains identical, but inputs changed)
        if is_step_advance_button and waited_seconds >= 2 and not error_texts and initial_field_signatures:
            try:
                raw_current_sigs = await page.evaluate("""() => {
                    const els = Array.from(document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), textarea, select'));
                    return els.filter(el => el.offsetWidth > 0 && el.offsetHeight > 0).map(el => (el.id || '') + '::' + (el.name || '')).filter(Boolean);
                }""")
                current_field_signatures = set(raw_current_sigs)
                new_fields = current_field_signatures - initial_field_signatures
                if new_fields and not confirmed:
                    log.info("submit.step_advanced_client_side", new_fields_count=len(new_fields), waited_seconds=waited_seconds)
                    return "STEP_ADVANCED"
            except Exception:
                pass

        # Signal A — URL change: page.url != initial_url
        if current_url.lower() != initial_url.lower():
            is_strong = any(token in current_url.lower() for token in _URL_STRONG_KEYWORDS)
            # Only treat weak URL change as confirmed if form is no longer visible
            still_has_form = False
            if not is_strong and form_locator is not None:
                try:
                    still_has_form = await form_locator.is_visible(timeout=200)
                except Exception:
                    pass

            # If weak URL change redirected back to a general directory (/jobs, /careers, /search), reject it
            clean_new_path = current_url.split("?")[0].rstrip("/").lower()
            is_directory_url = clean_new_path.endswith(("/jobs", "/careers", "/vacancies", "/search", "/openings", "/search-results"))
            if not is_strong and (is_directory_url or form_locator is None):
                log.warning("submit.redirected_to_directory_or_unbound", new_url=current_url)
                continue

            if is_strong or not still_has_form:
                signal_name = "url_change_strong" if is_strong else "url_change_weak"
                log.info(
                    "submit.confirmed",
                    signal=signal_name,
                    new_url=current_url,
                    waited_seconds=waited_seconds,
                )
                confirmed = True
                break

        # Signal B — Confirmation text across body
        try:
            body_text = await page.inner_text("body", timeout=500)
            if _CONFIRMATION_TEXT_REGEX.search(body_text):
                log.info(
                    "submit.confirmed",
                    signal="text",
                    new_url=current_url,
                    waited_seconds=waited_seconds,
                )
                confirmed = True
                break
        except Exception:
            pass

        # Signal C — Confirmation-like heading
        try:
            heading_locators = page.locator(_CONFIRMATION_HEADING_SELECTORS)
            count = await heading_locators.count()
            heading_matched = False
            for i in range(min(count, 8)):
                h_loc = heading_locators.nth(i)
                if await h_loc.is_visible(timeout=200):
                    h_text = (await h_loc.text_content() or "").strip()
                    if _CONFIRMATION_TEXT_REGEX.search(h_text):
                        log.info(
                            "submit.confirmed",
                            signal="heading",
                            new_url=current_url,
                            waited_seconds=waited_seconds,
                        )
                        confirmed = True
                        heading_matched = True
                        break
            if heading_matched:
                break
        except Exception:
            pass

        # Signal D — Form removed or hidden
        if form_locator is not None:
            try:
                form_count = await form_locator.count()
                if form_count == 0 or not (await form_locator.is_visible(timeout=200)):
                    log.info(
                        "submit.confirmed",
                        signal="form_removed",
                        new_url=current_url,
                        waited_seconds=waited_seconds,
                    )
                    confirmed = True
                    break
            except Exception:
                pass

        # Signal E — Form status attribute or response container (e.g. Contact Form 7 / WP)
        try:
            cf7_sent = page.locator('form[data-status="sent"], form.sent, .wpcf7-mail-sent-ok, .wpcf7-response-output').first
            if await cf7_sent.count() > 0 and await cf7_sent.is_visible(timeout=200):
                resp_text = (await cf7_sent.text_content() or "").strip()
                if not any(err in resp_text.lower() for err in ["error", "fail", "invalid", "required", "try again"]):
                    log.info(
                        "submit.confirmed",
                        signal="form_status_sent",
                        response_text=resp_text,
                        new_url=current_url,
                        waited_seconds=waited_seconds,
                    )
                    confirmed = True
                    break
        except Exception:
            pass

    # 2D. Safety net: wait for networkidle and re-check Signal A & text
    if not confirmed:
        try:
            await page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass

        current_url = page.url
        if current_url.lower() != initial_url.lower():
            is_strong = any(token in current_url.lower() for token in _URL_STRONG_KEYWORDS)
            clean_new_path = current_url.split("?")[0].rstrip("/").lower()
            is_directory_url = clean_new_path.endswith(("/jobs", "/careers", "/vacancies", "/search", "/openings", "/search-results"))
            if is_strong or (not is_directory_url and form_locator is not None):
                signal_name = "url_change_strong" if is_strong else "url_change_weak"
                log.info(
                    "submit.confirmed",
                    signal=signal_name,
                    new_url=current_url,
                    waited_seconds=waited_seconds,
                )
                confirmed = True

        if not confirmed:
            try:
                body_text = await page.inner_text("body", timeout=500)
                if _CONFIRMATION_TEXT_REGEX.search(body_text):
                    log.info(
                        "submit.confirmed",
                        signal="text_safetynet",
                        new_url=current_url,
                        waited_seconds=waited_seconds,
                    )
                    confirmed = True
            except Exception:
                pass

    # 2C. Better validation-error detection when unconfirmed
    if not confirmed:
        unconfirmed_err_texts: list[str] = []
        try:
            err_locators = page.locator(_VALIDATION_ERROR_SELECTORS)
            count = await err_locators.count()
            for i in range(min(count, 15)):
                loc = err_locators.nth(i)
                if await loc.is_visible(timeout=200):
                    el_id = (await loc.get_attribute("id") or "").lower()
                    if "announcer" in el_id:
                        continue
                    text = (await loc.text_content() or "").strip()
                    if is_confirmation_text(text):
                        log.info("submit.confirmed", signal="alert_with_confirmation_text", response_text=text[:120])
                        confirmed = True
                        break
                    if text and len(text) < 300 and text not in unconfirmed_err_texts:
                        if not any(w in text.lower() for w in ["cookie", "privacy", "copyright"]):
                            unconfirmed_err_texts.append(text[:120])
                    if len(unconfirmed_err_texts) >= 3:
                        break
        except Exception:
            pass

        if not confirmed and unconfirmed_err_texts:
            joined_errs = "; ".join(unconfirmed_err_texts)
            if any("captcha" in err.lower() or "recaptcha" in err.lower() for err in unconfirmed_err_texts):
                log.warning("submit.captcha_error_detected", errors=joined_errs, waited_seconds=waited_seconds)
                raise CaptchaEncounteredError(f"Submission blocked by CAPTCHA: {joined_errs}")
            log.warning(
                "submit.validation_errors_detected",
                errors=joined_errs,
                waited_seconds=waited_seconds,
            )
            raise ValidationFailedError(
                f"Form validation errors flagged after clicking submit: {joined_errs}"
            )

        if not confirmed:
            # Check if an anti-bot challenge appeared post-submit
            try:
                await detect_captcha.detect_captcha(page=page)
            except CaptchaEncounteredError:
                log.warning("submit.captcha_detected_post_submit")
                raise

            # Check if form transitioned to the next step of a multi-step wizard
            url_changed = page.url.lower() != initial_url.lower()
            url_has_step_indicator = any(k in page.url.lower() for k in ["step=", "stepname=", "page=", "/step-", "/step/", "/stage/"])

            has_client_side_advance = False
            if is_step_advance_button and initial_field_signatures:
                try:
                    raw_current_sigs = await page.evaluate("""() => {
                        const els = Array.from(document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), textarea, select'));
                        return els.filter(el => el.offsetWidth > 0 && el.offsetHeight > 0).map(el => (el.id || '') + '::' + (el.name || '')).filter(Boolean);
                    }""")
                    current_field_signatures = set(raw_current_sigs)
                    new_fields = current_field_signatures - initial_field_signatures
                    if new_fields:
                        has_client_side_advance = True
                except Exception:
                    pass

            if (url_changed and (url_has_step_indicator or is_step_advance_button)) or has_client_side_advance:
                log.info("submit.step_advanced", previous_url=initial_url, new_url=page.url, waited_seconds=waited_seconds)
                return "STEP_ADVANCED"

            log.error(
                "submit.timeout_unconfirmed",
                url=page.url,
                waited_seconds=waited_seconds,
            )
            raise RuntimeError(
                f"Application submission could not be confirmed after {waited_seconds}s "
                "(timeout waiting for confirmation screen or URL change)."
            )

    # Settle wait: Ensure SPA routing / thank-you page has fully finished rendering before taking screenshot
    log.info("submit.settling_confirmation_page", final_url=page.url)
    try:
        # If not yet on a strong URL, give SPA router up to 4s to transition to thank-you / confirmation page
        if not any(token in page.url.lower() for token in _URL_STRONG_KEYWORDS):
            for _ in range(4):
                await page.wait_for_timeout(1000)
                if any(token in page.url.lower() for token in _URL_STRONG_KEYWORDS):
                    break
        await page.wait_for_load_state("domcontentloaded", timeout=4000)
        await page.wait_for_timeout(1500)
    except Exception:
        pass

    log.info("submit.successful", run_id=str(run_id), final_url=page.url)
    return "CONFIRMED"
