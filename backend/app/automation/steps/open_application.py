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
    r"\b(apply now|apply for this job|apply for vacancy|apply on company site|apply online|apply to job|start application|apply)\b",
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
            loading_indicator = page.locator(':has-text("Fetching application form"), [class*="loadingIndicator"], [class*="loading-spinner"], .formio-form, [data-sf-form-id]')
            if await loading_indicator.count() > 0 or any(k in page.url.lower() for k in ["ashbyhq.com", "lorien"]):
                await page.wait_for_selector('input[name*="first" i], input[name*="email" i], input[type="email"], input[type="file"], form, [class*="_applicationForm_"]', timeout=4000)
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

        # 2. If a visible file upload input or Form.io file component exists, it is an application form
        if await page.locator('input[type="file"]:visible, .formio-component-file:visible, [class*="formio-component-file"]:visible').count() > 0:
            return True

        # 3. Inspect candidate-relevant visible field indicators (Name, Email, Phone, CV)
        candidate_keywords = ["email", "phone", "first_name", "last_name", "firstname", "lastname", "resume", "cv", "candidate", "applicant"]
        inputs = page.locator("input:visible:not([type=hidden]):not([type=submit]):not([type=button]), textarea:visible, select:visible")
        count = await inputs.count()
        if count >= 2:
            candidate_fields_found = 0
            for i in range(min(count, 15)):
                inp = inputs.nth(i)
                name_attr = (await inp.get_attribute("name") or "").lower()
                id_attr = (await inp.get_attribute("id") or "").lower()
                aria_label = (await inp.get_attribute("aria-label") or "").lower()
                combined = f"{name_attr} {id_attr} {aria_label}"
                if any(kw in combined for kw in candidate_keywords):
                    candidate_fields_found += 1
            if candidate_fields_found >= 2:
                return True

        # If there are multiple visible Apply Now buttons and no candidate fields, it is a directory / search results page
        apply_links_count = await page.locator("a:visible, button:visible").filter(has_text=_APPLY_BUTTON_REGEX).count()
        if apply_links_count >= 2:
            return False

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
    max_hops: int = 3,
) -> Page:
    """Navigate to the job posting and autonomously reach the application form.

    Supports:
    - Multi-hop navigation (e.g. Job board landing page → Company page → Application form)
    - Handling new tabs/popups (returns the active Page reference to the caller)
    - Auto-dismissing cookie/country modal overlays
    - Expanding collapsible job application forms (e.g. WP Job Manager)
    - Directory/homepage matching based on candidate profile

    Returns:
        The active Page on the application form.
    """
    log.info("open_application.navigating", url=job_url)
    await page.goto(job_url, timeout=settings.nav_timeout_ms, wait_until="domcontentloaded")

    # Initial overlay dismissal
    await dismiss_overlays(page)

    current_page = page
    for hop in range(1, max_hops + 1):
        log.info("open_application.evaluating_page", hop=hop, url=current_page.url)

        # Check if form is already present
        if await _is_application_form_present(current_page):
            log.info("open_application.form_confirmed", hop=hop, url=current_page.url)
            return current_page

        # If on hop 1 and candidate profile is available, check for directory/homepage job cards
        if hop == 1 and candidate_profile:
            matched_job = await _match_and_navigate_directory(current_page, candidate_profile)
            if matched_job:
                log.info("open_application.directory_matched_job_navigated", new_url=current_page.url)
                if await _is_application_form_present(current_page):
                    log.info("open_application.form_confirmed_post_directory", url=current_page.url)
                    return current_page

        # Find visible Apply CTA
        apply_locators = current_page.locator("a:visible, button:visible").filter(has_text=_APPLY_BUTTON_REGEX)
        try:
            await apply_locators.first.wait_for(state="visible", timeout=2500)
        except Exception:
            pass

        cta_count = await apply_locators.count()

        cta = None
        for i in range(cta_count):
            candidate_cta = apply_locators.nth(i)
            try:
                if await candidate_cta.is_visible(timeout=500):
                    # Exclude navigation items in headers/footers like 'Submit Vacancy' or 'Submit CV'
                    text = (await candidate_cta.text_content() or "").strip()
                    if "submit vacancy" in text.lower() or "submit cv" in text.lower():
                        continue
                    cta = candidate_cta
                    break
            except Exception:
                continue

        if cta is None:
            # Fallback to href containing apply or QA attributes
            fallback_cta = current_page.locator(
                'a[href*="apply" i]:visible, [data-automation-id="apply-button"]:visible, [data-qa="apply-button"]:visible, .application_button:visible'
            ).first
            try:
                if await fallback_cta.is_visible(timeout=1500):
                    text = (await fallback_cta.text_content() or "").strip()
                    if not ("submit vacancy" in text.lower() or "submit cv" in text.lower()):
                        cta = fallback_cta
            except Exception:
                pass

        if cta is None:
            log.warning("open_application.no_apply_cta_found", hop=hop, url=current_page.url)
            break

        cta_text = (await cta.text_content() or "").strip()
        cta_href = await cta.get_attribute("href")
        log.info("open_application.clicking_cta", hop=hop, text=cta_text, href=cta_href)

        # Handle potential popup / new tab
        context = current_page.context
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
            pass

        if not navigated:
            if cta_href and not cta_href.startswith("#") and not cta_href.startswith("javascript:"):
                target_url = urljoin(current_page.url, cta_href)
                log.info("open_application.navigating_href", target_url=target_url)
                try:
                    await current_page.goto(target_url, timeout=settings.nav_timeout_ms, wait_until="domcontentloaded")
                except Exception as e:
                    log.warning("open_application.href_goto_failed", error=str(e))
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
