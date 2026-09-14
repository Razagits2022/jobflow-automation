"""Step 2 — Open the application form page with multi-hop navigation and overlay dismissal."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import structlog
from playwright.async_api import Page

from app.core.config import settings

log = structlog.get_logger(__name__)

_APPLY_BUTTON_REGEX = re.compile(
    r"\b("
    r"apply now|"
    r"apply for this job|"
    r"apply for this role|"
    r"apply for position|"
    r"apply for vacancy|"
    r"apply on company site|"
    r"apply on website|"
    r"apply online|"
    r"apply to job|"
    r"start application|"
    r"go to application|"
    r"continue to application|"
    r"proceed to application|"
    r"open application|"
    r"fill out application|"
    r"apply manually|"
    r"apply with resume|"
    r"apply without resume|"
    r"click here to apply|"
    r"click to apply|"
    r"apply directly|"
    r"apply externally|"
    r"i'm interested|"
    r"apply"
    r")\b",
    re.IGNORECASE,
)

_INTERMEDIATE_NAV_REGEX = re.compile(
    r"\b("
    r"go to form|"
    r"go to application|"
    r"continue to form|"
    r"continue to application|"
    r"proceed to form|"
    r"proceed to application|"
    r"click on this to go form page|"
    r"click here to go to form|"
    r"fill out form|"
    r"complete application|"
    r"next step|"
    r"proceed|"
    r"continue|"
    r"get started|"
    r"start"
    r")\b",
    re.IGNORECASE,
)


async def dismiss_overlays(page: Page) -> None:
    """Proactively dismiss cookie banners, country switcher modals, and lingering backdrops."""
    try:
        await page.evaluate(
            """() => {
                // 1. Click close buttons on modals / popups
                const closeBtns = document.querySelectorAll('.x-modal_close, button[data-x-modal-close], [aria-label="Close"], button.close, #cookiesareaclose a, #cookiesareaclose img');
                for (const b of closeBtns) {
                    if (b.offsetWidth > 0 || b.offsetHeight > 0 || b.click) {
                        try { b.click(); } catch(e) {}
                    }
                }
                // 2. Remove lingering blocking backdrops
                const backdrops = document.querySelectorAll('.x-modal_backdrop, .modal-backdrop, .onetrust-pc-dark-filter, #onetrust-consent-sdk, .ot-fade-in');
                for (const bd of backdrops) {
                    try { bd.remove(); } catch(e) {}
                }
                // 3. Click cookie accept buttons (strictly excluding info/policy links)
                const cookieBtns = document.querySelectorAll('#moove_gdpr_cookie_info_bar button, #onetrust-accept-btn-handler, [class*="cookie"] button, button[id*="cookie"]');
                for (const cb of cookieBtns) {
                    if (cb.tagName === "A") {
                        const href = (cb.getAttribute("href") || "").toLowerCase();
                        if (href.includes("policy") || href.includes("privacy") || href.includes("terms") || href.includes("cookie")) {
                            continue;
                        }
                    }
                    const txt = (cb.textContent || "").trim();
                    if (/accept|agree|allow|ok/i.test(txt)) {
                        try { cb.click(); } catch(e) {}
                        break;
                    }
                }
            }"""
        )
    except Exception:
        pass


async def _is_application_form_present(page: Page) -> bool:
    """Check if the page currently renders an application form with candidate inputs."""
    try:
        # Check for dynamic SPA form loading (e.g. Ashby, Form.io, loading spinners)
        try:
            loading_indicator = page.locator(
                ':has-text("Fetching application form"), [class*="loadingIndicator"], [class*="loading-spinner"], .formio-form, [data-sf-form-id]'
            )
            if await loading_indicator.count() > 0 or any(k in page.url.lower() for k in ["ashbyhq.com", "lorien"]):
                await page.wait_for_selector(
                    'input[name*="first" i], input[name*="email" i], input[type="email"], input[type="file"], form, [class*="_applicationForm_"]',
                    timeout=3000,
                )
        except Exception:
            pass

        # 1. Check for WP Job Manager collapsed application button and click it to reveal form
        app_btn = page.locator('.application_button, input[value*="Apply for job"], button.application_button').first
        if await app_btn.count() > 0:
            try:
                if await app_btn.is_visible(timeout=500):
                    log.info("open_application.expanding_wp_job_manager_form")
                    await app_btn.click(force=True, timeout=2000)
                    await page.wait_for_timeout(1000)
            except Exception:
                pass

        # Evaluate candidate input signals in a single DOM query
        form_status = await page.evaluate("""() => {
            const fileInputs = Array.from(document.querySelectorAll('input[type="file"]')).filter(
                el => el.offsetWidth > 0 || el.offsetHeight > 0 || (el.parentElement && el.parentElement.offsetWidth > 0)
            );
            const hasFileInput = fileInputs.length > 0;

            const hasAshbyForm = !!document.querySelector('[class*="_applicationForm_"], form[class*="application"]');
            const hasFormio = !!document.querySelector('.formio-component-file, [class*="formio-component"]');

            const candidateKeywords = [
                "email", "phone", "first_name", "last_name", "firstname", "lastname",
                "full_name", "fullname", "name", "resume", "cv", "candidate", "applicant",
                "linkedin", "location", "address"
            ];
            const allInputs = Array.from(document.querySelectorAll(
                'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]), textarea, select'
            )).filter(el => el.offsetWidth > 0 && el.offsetHeight > 0);

            let candidateFields = 0;
            let hasEmailField = false;

            for (const el of allInputs) {
                if (el.type === 'email' || el.autocomplete === 'email') {
                    hasEmailField = true;
                    candidateFields++;
                    continue;
                }
                const name = (el.name || '').toLowerCase();
                const id = (el.id || '').toLowerCase();
                const placeholder = (el.placeholder || '').toLowerCase();
                const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
                const parent = el.closest('label, div[class*="field"], div[class*="form-group"]') || el.parentElement;
                const parentText = parent ? (parent.innerText || '').toLowerCase().slice(0, 50) : '';

                const combined = `${name} ${id} ${placeholder} ${ariaLabel} ${parentText}`;
                if (candidateKeywords.some(kw => combined.includes(kw))) {
                    candidateFields++;
                }
            }

            const applyBtns = Array.from(document.querySelectorAll('a, button')).filter(el => {
                if (el.offsetWidth <= 0 || el.offsetHeight <= 0) return false;
                const txt = (el.innerText || '').trim().toLowerCase();
                return /^(apply now|apply for this job|apply on company site|apply online|start application)$/i.test(txt);
            });

            return {
                hasFileInput,
                hasAshbyForm,
                hasFormio,
                hasEmailField,
                candidateFields,
                totalInputs: allInputs.length,
                applyBtnCount: applyBtns.length
            };
        }""")

        # If a file input exists and candidate fields >= 1 or totalInputs >= 2, it is a form
        if form_status.get("hasFileInput") and (form_status.get("candidateFields", 0) >= 1 or form_status.get("totalInputs", 0) >= 2):
            return True

        # If hasAshbyForm or hasFormio and has inputs
        if (form_status.get("hasAshbyForm") or form_status.get("hasFormio")) and form_status.get("totalInputs", 0) >= 2:
            return True

        # If email field + at least 1 other candidate field
        if form_status.get("hasEmailField") and form_status.get("candidateFields", 0) >= 2:
            return True

        # General threshold: at least 2 candidate-specific fields and not an overview page with multiple apply buttons
        if form_status.get("candidateFields", 0) >= 2 and form_status.get("applyBtnCount", 0) < 3:
            return True

        # If page URL ends with /application or /apply and has inputs
        path = page.url.lower().rstrip("/")
        if (path.endswith("/application") or path.endswith("/apply") or "/job-apply" in path) and form_status.get("totalInputs", 0) >= 2:
            return True

        return False
    except Exception:
        return False


async def _match_and_navigate_directory(page: Page, candidate_profile: dict[str, Any]) -> bool:
    """Detect if page is a directory/homepage with multiple job cards and navigate to the best matching job."""
    try:
        title = (candidate_profile.get("title") or "").lower()
        skills = [s.lower() for s in candidate_profile.get("skills", [])]
        stopwords = {"and", "the", "with", "for", "in", "of", "to", "a", "an", "is", "at"}
        title_words = [w for w in re.findall(r"\w+", title) if w not in stopwords and len(w) > 2]
        skill_words = []
        for s in skills:
            skill_words.extend([w for w in re.findall(r"\w+", s) if w not in stopwords and len(w) > 2])

        jobs = await page.evaluate("""() => {
            const selectors = [
                'a[href*="/jobs/"]', 'a[href*="/job/"]', 'a[href*="/vacancies/"]',
                'a[href*="/careers/"]', 'a[href*="/openings/"]', '[class*="job-card"] a',
                '[class*="jobCard"] a', '[class*="job-title"] a'
            ];
            const links = Array.from(document.querySelectorAll(selectors.join(', ')));
            const seen = new Set();
            const results = [];
            for (const a of links) {
                const href = a.href;
                if (!href || seen.has(href)) continue;
                try {
                    const path = new URL(href, window.location.href).pathname.toLowerCase();
                    if (path === '/jobs' || path === '/jobs/' || path === '/careers' || path === '/careers/') continue;
                } catch(e) {
                    continue;
                }
                if (a.closest('header') || a.closest('nav') || a.closest('footer')) continue;
                seen.add(href);
                const text = (a.innerText || a.getAttribute('title') || '').trim();
                const parent = a.closest('[class*="job"], [class*="card"], article, li, div');
                const parentText = parent ? (parent.innerText || '').trim() : '';
                results.push({
                    href: href,
                    text: text || parentText.substring(0, 100),
                    fullText: parentText || text
                });
            }
            return results;
        }""")

        if len(jobs) < 2:
            return False

        negative_keywords = {"accountant", "sales", "marketing", "recruiter", "hr", "finance", "legal", "nurse", "payroll"}
        scored_jobs = []
        for job in jobs:
            job_str = (job["text"] + " " + job["fullText"] + " " + job["href"]).lower()
            score = 0
            for tw in title_words:
                if tw in job_str:
                    score += 5
            for sw in skill_words:
                if sw in job_str:
                    score += 2
            for nw in negative_keywords:
                if nw in job_str and nw not in title:
                    score -= 10
            scored_jobs.append((score, job))

        scored_jobs.sort(key=lambda x: x[0], reverse=True)
        best_score, best_job = scored_jobs[0]
        log.info("open_application.directory_job_selected", score=best_score, title=best_job["text"][:60], href=best_job["href"])

        await page.goto(best_job["href"], timeout=settings.nav_timeout_ms, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await dismiss_overlays(page)
        return True
    except Exception as exc:
        log.warning("open_application.directory_matching_failed", error=str(exc))
        return False


async def open_application(
    *,
    page: Page,
    job_url: str,
    candidate_profile: dict[str, Any] | None = None,
    max_hops: int = 5,
) -> Page:
    """Navigate to the job posting and autonomously reach the application form.

    Supports:
    - Multi-hop navigation (e.g. Job board landing page → Company page → Application form)
    - Handling new tabs/popups (returns the active Page reference to the caller)
    - Auto-dismissing cookie/country modal overlays
    - Expanding collapsible job application forms (e.g. WP Job Manager, accordion `#apply`)
    - Intermediate progression pages ("Go to application", "Proceed to form", "Apply manually")
    - Directory/homepage matching based on candidate profile

    Returns:
        The active Page on the application form.
    """
    log.info("open_application.navigating", url=job_url)
    await page.goto(job_url, timeout=settings.nav_timeout_ms, wait_until="domcontentloaded")

    # Initial overlay dismissal
    await dismiss_overlays(page)

    current_page = page
    visited_urls: set[str] = set()

    for hop in range(1, max_hops + 1):
        clean_url = current_page.url.split("#")[0].rstrip("/")
        visited_urls.add(clean_url)
        log.info("open_application.evaluating_page", hop=hop, url=current_page.url)

        # 1. Check if form is already present
        if await _is_application_form_present(current_page):
            log.info("open_application.form_confirmed", hop=hop, url=current_page.url)
            return current_page

        # 2. If on hop 1 and candidate profile is available, check for directory/homepage job cards
        if hop == 1 and candidate_profile:
            matched_job = await _match_and_navigate_directory(current_page, candidate_profile)
            if matched_job:
                log.info("open_application.directory_matched_job_navigated", new_url=current_page.url)
                if await _is_application_form_present(current_page):
                    log.info("open_application.form_confirmed_post_directory", url=current_page.url)
                    return current_page

        # 3. Locate CTA button / link:
        # Tier 1: Explicit apply buttons / links
        apply_locators = current_page.locator("a:visible, button:visible").filter(has_text=_APPLY_BUTTON_REGEX)
        try:
            await apply_locators.first.wait_for(state="visible", timeout=2000)
        except Exception:
            pass

        cta = None
        cta_count = await apply_locators.count()
        for i in range(cta_count):
            candidate_cta = apply_locators.nth(i)
            try:
                if await candidate_cta.is_visible(timeout=300):
                    text = (await candidate_cta.text_content() or "").strip()
                    if any(bad in text.lower() for bad in ["submit vacancy", "submit cv", "terms of", "cookie"]):
                        continue
                    cta = candidate_cta
                    break
            except Exception:
                continue

        # Tier 2: Fallback to href containing apply or QA attributes
        if cta is None:
            fallback_cta = current_page.locator(
                'a[href*="apply" i]:visible, a[href*="application" i]:visible, [data-automation-id="apply-button"]:visible, [data-qa="apply-button"]:visible, .application_button:visible, button[id*="apply" i]:visible, a[id*="apply" i]:visible'
            ).first
            try:
                if await fallback_cta.is_visible(timeout=1000):
                    text = (await fallback_cta.text_content() or "").strip()
                    if not any(bad in text.lower() for bad in ["submit vacancy", "submit cv", "terms of", "cookie"]):
                        cta = fallback_cta
            except Exception:
                pass

        # Tier 3: Intermediate progression CTAs (for multi-hop transitions like "Continue to application", "Proceed", "Go to form")
        if cta is None and hop >= 2:
            inter_locators = current_page.locator("a:visible, button:visible").filter(has_text=_INTERMEDIATE_NAV_REGEX)
            try:
                if await inter_locators.count() > 0 and await inter_locators.first.is_visible(timeout=1000):
                    cta = inter_locators.first
            except Exception:
                pass

        if cta is None:
            log.warning("open_application.no_apply_cta_found", hop=hop, url=current_page.url)
            break

        cta_text = (await cta.text_content() or "").strip()
        cta_href = await cta.get_attribute("href")
        log.info("open_application.clicking_cta", hop=hop, text=cta_text, href=cta_href)

        # If CTA is an in-page hash anchor (e.g. #apply, #application), click and verify if form expanded
        if cta_href and cta_href.startswith("#") and len(cta_href) > 1:
            try:
                await cta.scroll_into_view_if_needed(timeout=1000)
                await cta.click(force=True, timeout=2000)
                await current_page.wait_for_timeout(1500)
                await dismiss_overlays(current_page)
                if await _is_application_form_present(current_page):
                    log.info("open_application.form_confirmed_via_hash_anchor", hop=hop, anchor=cta_href)
                    return current_page
            except Exception as anchor_err:
                log.warning("open_application.anchor_click_failed", error=str(anchor_err))

        # Handle potential popup / new tab
        context = current_page.context
        pages_before = set(context.pages)
        navigated = False

        try:
            async with context.expect_page(timeout=3500) as new_page_info:
                await cta.click(force=True, timeout=3000)
            new_page = await new_page_info.value
            await new_page.wait_for_load_state("domcontentloaded")
            current_page = new_page
            navigated = True
            log.info("open_application.switched_to_new_tab", url=current_page.url)
        except Exception:
            # Fallback: check if context opened a new page despite expect_page timing out
            new_pages = [p for p in context.pages if p not in pages_before]
            if new_pages:
                current_page = new_pages[-1]
                await current_page.wait_for_load_state("domcontentloaded")
                navigated = True
                log.info("open_application.detected_new_tab_in_context", url=current_page.url)

        if not navigated:
            if cta_href and not cta_href.startswith("#") and not cta_href.startswith("javascript:"):
                target_url = urljoin(current_page.url, cta_href)
                target_clean = target_url.split("#")[0].rstrip("/")
                if target_clean not in visited_urls:
                    log.info("open_application.navigating_href", target_url=target_url)
                    try:
                        await current_page.goto(target_url, timeout=settings.nav_timeout_ms, wait_until="domcontentloaded")
                    except Exception as e:
                        log.warning("open_application.href_goto_failed", error=str(e))
                        await cta.click(force=True, timeout=3000)
                else:
                    await cta.click(force=True, timeout=3000)
            else:
                try:
                    await cta.click(force=True, timeout=3000)
                    await current_page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception as e:
                    log.warning("open_application.click_failed", error=str(e))

        # Dismiss overlays on the newly reached page
        await dismiss_overlays(current_page)
        await current_page.wait_for_timeout(1000)

    log.info("open_application.ready", final_url=current_page.url)
    return current_page
