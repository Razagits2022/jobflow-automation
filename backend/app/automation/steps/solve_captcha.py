"""Step: Solve detected CAPTCHAs automatically via CapSolver."""

from __future__ import annotations

import re

import structlog
from playwright.async_api import Page

from app.core.config import settings
from app.integrations import capsolver

log = structlog.get_logger(__name__)


async def extract_recaptcha_sitekey(page: Page) -> str | None:
    """Find the Google reCAPTCHA sitekey from DOM elements or iframe URLs."""
    # Check DOM attributes first
    try:
        data_sitekey = await page.locator(
            ".g-recaptcha[data-sitekey], #recaptcha[data-sitekey], [data-recaptcha-site-key]"
        ).first.get_attribute("data-sitekey", timeout=1000)
        if data_sitekey:
            return data_sitekey.strip()
    except Exception:
        pass

    # Check recaptcha iframes
    try:
        iframes = page.locator('iframe[src*="recaptcha"]')
        count = await iframes.count()
        for i in range(count):
            src = await iframes.nth(i).get_attribute("src") or ""
            match = re.search(r"[?&]k=([a-zA-Z0-9_\-]+)", src)
            if match:
                return match.group(1).strip()
    except Exception:
        pass

    return None


async def extract_turnstile_sitekey(page: Page) -> str | None:
    """Find the Cloudflare Turnstile sitekey from DOM elements or iframe URLs."""
    try:
        data_sitekey = await page.locator(
            ".cf-turnstile[data-sitekey], [data-cf-turnstile-sitekey]"
        ).first.get_attribute("data-sitekey", timeout=1000)
        if data_sitekey:
            return data_sitekey.strip()
    except Exception:
        pass

    try:
        iframes = page.locator('iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"]')
        count = await iframes.count()
        for i in range(count):
            src = await iframes.nth(i).get_attribute("src") or ""
            match = re.search(r"[?&]sitekey=([a-zA-Z0-9_\-]+)", src)
            if match:
                return match.group(1).strip()
    except Exception:
        pass

    return None


async def solve_captcha_if_present(*, page: Page) -> bool:
    """Inspect the page for CAPTCHAs, solve via CapSolver, and inject response token.

    Returns:
        bool: True if a supported CAPTCHA was found and successfully solved; False otherwise.
    """
    if not settings.capsolver_api_key or "your-" in settings.capsolver_api_key.lower():
        log.debug("solve_captcha.unconfigured_skipping")
        return False

    page_url = page.url

    # 1. Check for Google reCAPTCHA
    recaptcha_key = await extract_recaptcha_sitekey(page)
    if recaptcha_key:
        is_v3 = False
        is_invisible = False
        try:
            is_v3 = bool(await page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script[src*="recaptcha"]'));
                return scripts.some(s => (s.src || '').includes('render=') && !(s.src || '').includes('render=explicit'));
            }"""))
            is_invisible = bool(await page.evaluate("""() => {
                const el = document.querySelector('.g-recaptcha, [data-sitekey]');
                if (el && el.getAttribute('data-size') === 'invisible') return true;
                const iframes = Array.from(document.querySelectorAll('iframe[src*="recaptcha"]'));
                return iframes.some(f => (f.src || '').includes('size=invisible'));
            }"""))
        except Exception:
            pass

        api_domain = None
        action = "job_apply" if "ashbyhq.com" in page_url else "submit"
        try:
            domain_eval = await page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script[src*="recaptcha"]'));
                for (const s of scripts) {
                    const src = s.src || '';
                    if (src.includes('recaptcha.net')) return 'https://www.recaptcha.net/';
                    if (src.includes('google.com')) return 'https://www.google.com/';
                }
                return null;
            }""")
            if domain_eval:
                api_domain = domain_eval

            if action == "submit":
                detected_action = await page.evaluate("""() => {
                    const el = document.querySelector('[data-recaptcha-action], [data-action]');
                    return el ? (el.getAttribute('data-recaptcha-action') || el.getAttribute('data-action')) : null;
                }""")
                if detected_action:
                    action = detected_action
        except Exception:
            pass

        log.info("solve_captcha.recaptcha_found", sitekey=recaptcha_key, is_v3=is_v3, is_invisible=is_invisible, action=action, api_domain=api_domain, url=page_url)
        try:
            if is_v3:
                token = await capsolver.solve_recaptcha_v3(
                    website_url=page_url,
                    sitekey=recaptcha_key,
                    page_action=action,
                    api_domain=api_domain,
                    min_score=0.9,
                )
            else:
                token = await capsolver.solve_recaptcha_v2(
                    website_url=page_url,
                    sitekey=recaptcha_key,
                    is_invisible=is_invisible,
                )

            # Inject token, hook grecaptcha.execute, and invoke client callbacks recursively
            await page.evaluate(
                """(token) => {
                    // Hook grecaptcha.execute and enterprise for reCAPTCHA v3 / invisible Promise-based callers
                    const hookObj = (target) => {
                        if (target && typeof target === 'object') {
                            try {
                                target.execute = function(...args) {
                                    return Promise.resolve(token);
                                };
                            } catch (e) {}
                        }
                    };
                    if (window.grecaptcha) {
                        hookObj(window.grecaptcha);
                        hookObj(window.grecaptcha.enterprise);
                    }

                    const elements = document.querySelectorAll(
                        '#g-recaptcha-response, [name="g-recaptcha-response"], [id*="g-recaptcha-response"]'
                    );
                    for (const el of elements) {
                        el.value = token;
                        el.innerHTML = token;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // Recursively search and call all callbacks in ___grecaptcha_cfg
                    function searchAndCall(obj, depth = 0) {
                        if (!obj || depth > 5) return;
                        for (const k of Object.keys(obj)) {
                            const val = obj[k];
                            if (typeof val === 'function' && (k.toLowerCase().includes('callback') || (val.name && val.name.toLowerCase().includes('callback')))) {
                                try { val(token); } catch(e) {}
                            } else if (typeof val === 'object' && val !== null) {
                                searchAndCall(val, depth + 1);
                            }
                        }
                    }
                    if (window.___grecaptcha_cfg) {
                        searchAndCall(window.___grecaptcha_cfg);
                    }
                }""",
                token,
            )
            log.info("solve_captcha.recaptcha_solved_and_injected", token_len=len(token), is_v3=is_v3)
            await page.wait_for_timeout(1500)
            return True
        except Exception as exc:
            log.error("solve_captcha.recaptcha_solve_failed", error=str(exc))
            return False

    # 2. Check for Cloudflare Turnstile
    turnstile_key = await extract_turnstile_sitekey(page)
    if turnstile_key:
        log.info("solve_captcha.turnstile_found", sitekey=turnstile_key, url=page_url)
        try:
            token = await capsolver.solve_turnstile(
                website_url=page_url,
                sitekey=turnstile_key,
            )
            await page.evaluate(
                """(token) => {
                    const elements = document.querySelectorAll(
                        '[name="cf-turnstile-response"], [name="cf_challenge_response"]'
                    );
                    for (const el of elements) {
                        el.value = token;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""",
                token,
            )
            log.info("solve_captcha.turnstile_solved_and_injected", token_len=len(token))
            await page.wait_for_timeout(1500)
            return True
        except Exception as exc:
            log.error("solve_captcha.turnstile_solve_failed", error=str(exc))
            return False

    return False
