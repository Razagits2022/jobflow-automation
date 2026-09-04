"""Step 6 — Detect CAPTCHA and anti-bot walls."""

from __future__ import annotations

import structlog
from playwright.async_api import Page

from app.automation.errors import CaptchaEncounteredError

log = structlog.get_logger(__name__)

_CAPTCHA_SIGNALS = [
    (
        "Cloudflare Turnstile",
        (
            'iframe[src*="turnstile"], iframe[src*="challenges.cloudflare.com"], '
            ".cf-turnstile, #challenge-stage"
        ),
    ),
    ("Google reCAPTCHA", 'iframe[src*="recaptcha"], .g-recaptcha, #recaptcha'),

    ("hCaptcha", 'iframe[src*="hcaptcha"], .h-captcha'),
    ("PerimeterX", '#px-captcha, iframe[src*="perimeterx"]'),
    ("DataDome", 'iframe[src*="datadome"], #datadome'),
    ("Arkose / FunCaptcha", 'iframe[src*="arkoselabs"], iframe[src*="funcaptcha"]'),
]


async def detect_captcha(*, page: Page) -> None:
    """Inspect the page for CAPTCHA iframes, anti-bot challenge elements, or challenge titles.

    Raises:
        CaptchaEncounteredError: When an anti-bot challenge is detected.
    """
    # 1. Check page title
    try:
        title = (await page.title() or "").lower()
        if "just a moment" in title or "security check" in title or "ddos-guard" in title:
            log.warning("detect_captcha.challenge_title_detected", title=title)
            raise CaptchaEncounteredError(
                f"Cloudflare / anti-bot challenge page detected: '{title}'"
            )
    except CaptchaEncounteredError:
        raise
    except Exception:
        pass

    # 2. Check DOM selectors
    for name, selector in _CAPTCHA_SIGNALS:
        try:
            count = await page.locator(selector).count()
            if count > 0:
                # Confirm it is attached
                first = page.locator(selector).first
                if await first.is_visible(timeout=500):
                    log.warning(
                        "detect_captcha.challenge_element_detected", signal=name, selector=selector
                    )
                    raise CaptchaEncounteredError(
                        f"Anti-bot challenge '{name}' detected on application page."
                    )
        except CaptchaEncounteredError:
            raise
        except Exception:
            continue

    log.debug("detect_captcha.clean")
