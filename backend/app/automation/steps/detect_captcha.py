"""Step 6 — Detect and Solve CAPTCHA and anti-bot walls."""

from __future__ import annotations

import structlog
from playwright.async_api import Page

from app.automation.errors import CaptchaEncounteredError
from app.automation.steps.solve_captcha import solve_captcha_if_present
from app.core.config import settings

log = structlog.get_logger(__name__)

_CHALLENGE_TITLES = (
    "just a moment",
    "security check",
    "ddos-guard",
    "attention required",
)

_CAPTCHA_SIGNALS = [
    (
        "Cloudflare Turnstile",
        (
            'iframe[src*="turnstile"], iframe[src*="challenges.cloudflare.com"], '
            "#challenge-stage, .cf-turnstile"
        ),
    ),
    (
        "Google reCAPTCHA",
        'iframe[src*="recaptcha"], .g-recaptcha:not(.grecaptcha-badge), #recaptcha',
    ),
    ("hCaptcha", 'iframe[src*="hcaptcha"], .h-captcha'),
    ("PerimeterX", '#px-captcha, iframe[src*="perimeterx"]'),
    ("DataDome", 'iframe[src*="datadome"], #datadome'),
    ("Arkose / FunCaptcha", 'iframe[src*="arkoselabs"], iframe[src*="funcaptcha"]'),
]


async def detect_captcha(*, page: Page) -> None:
    """Inspect the page for CAPTCHA iframes, anti-bot challenge elements, or challenge titles.

    If CapSolver is configured and an interactive challenge is found, attempts to solve it.
    If solving succeeds, continues pipeline. Otherwise, raises CaptchaEncounteredError.
    """
    # 1. Check for Email Verification Code Challenge (Greenhouse Human OTP) first
    # This is an email OTP, NOT a visual CAPTCHA, so CapSolver cannot solve it.
    try:
        email_verify = page.locator("#email-verification, .email-verification, input#security-input-0")
        if await email_verify.count() > 0 and await email_verify.first.is_visible(timeout=200):
            log.warning("detect_captcha.email_verification_detected")
            raise CaptchaEncounteredError(
                "Greenhouse Email Verification: An 8-character verification code was sent to your email inbox to confirm you are human."
            )
    except CaptchaEncounteredError:
        raise
    except Exception:
        pass

    # 2. Check page title
    try:
        title = (await page.title() or "").lower()
        if any(t in title for t in _CHALLENGE_TITLES):
            log.warning("detect_captcha.challenge_title_detected", title=title)
            # If CapSolver is configured, attempt to solve Turnstile / Cloudflare wall
            if settings.capsolver_api_key:
                solved = await solve_captcha_if_present(page=page)
                if solved:
                    log.info("detect_captcha.challenge_page_solved_via_capsolver")
                    return
            raise CaptchaEncounteredError(
                f"Cloudflare / anti-bot challenge page detected: '{title}'"
            )
    except CaptchaEncounteredError:
        raise
    except Exception:
        pass

    # 3. Proactive CapSolver solving if configured
    if settings.capsolver_api_key and "your-" not in settings.capsolver_api_key.lower():
        try:
            solved = await solve_captcha_if_present(page=page)
            if solved:
                log.info("detect_captcha.proactively_solved_via_capsolver")
                return
        except Exception as solve_err:
            log.warning("detect_captcha.proactive_solve_failed", error=str(solve_err))

    # 4. Check DOM selectors for real interactive challenges
    for name, selector in _CAPTCHA_SIGNALS:
        try:
            loc = page.locator(selector)
            count = await loc.count()
            if count == 0:
                continue

            for i in range(min(count, 5)):
                elem = loc.nth(i)
                try:
                    if not await elem.is_visible(timeout=300):
                        continue

                    # Filter out invisible background telemetry badges (e.g. Google reCAPTCHA Enterprise/v3)
                    is_invisible = await elem.evaluate(
                        """(el) => {
                            if (el.closest('.grecaptcha-badge')) return true;
                            const src = (el.getAttribute('src') || '').toLowerCase();
                            if (src.includes('size=invisible')) return true;
                            if (src.includes('/anchor') && !src.includes('bframe')) {
                                const badge = el.closest('.grecaptcha-badge') || el.closest('[style*="visibility: hidden"]');
                                if (badge) return true;
                            }
                            return false;
                        }"""
                    )
                    if is_invisible:
                        log.debug("detect_captcha.ignoring_invisible_badge", signal=name)
                        continue

                    # Check bounding box dimensions
                    box = await elem.bounding_box()
                    if box is None:
                        continue

                    # Real interactive challenges (bframe, turnstile box, hcaptcha popup)
                    # have noticeable width and height (typically >= 80x60 px).
                    if box["width"] < 80 or box["height"] < 60:
                        log.debug(
                            "detect_captcha.ignoring_tiny_element",
                            signal=name,
                            width=box["width"],
                            height=box["height"],
                        )
                        continue

                    # If it's positioned completely offscreen
                    if box["x"] + box["width"] <= 0 or box["y"] + box["height"] <= 0:
                        continue

                    log.warning(
                        "detect_captcha.challenge_element_detected",
                        signal=name,
                        selector=selector,
                        box=box,
                    )

                    # Attempt automated solving with CapSolver if key is present
                    if settings.capsolver_api_key:
                        log.info("detect_captcha.attempting_capsolver_solve", signal=name)
                        solved = await solve_captcha_if_present(page=page)
                        if solved:
                            log.info("detect_captcha.solved_via_capsolver", signal=name)
                            return

                    raise CaptchaEncounteredError(
                        f"Anti-bot challenge '{name}' detected on application page."
                    )
                except CaptchaEncounteredError:
                    raise
                except Exception:
                    continue
        except CaptchaEncounteredError:
            raise
        except Exception:
            continue

    log.debug("detect_captcha.clean")
