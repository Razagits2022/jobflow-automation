"""ATS adapter registry.

Inspects the job URL and optionally the page DOM to detect the ATS platform
and return the appropriate adapter. Defaults to GenericAdapter.
"""

from __future__ import annotations

import structlog
from playwright.async_api import Page

from app.automation.ats.base import AtsAdapter
from app.automation.ats.generic import GenericAdapter
from app.automation.ats.greenhouse import GreenhouseAdapter
from app.automation.ats.icims import ICIMSAdapter
from app.automation.ats.lever import LeverAdapter
from app.automation.ats.workday import WorkdayAdapter

log = structlog.get_logger(__name__)

# URL substring patterns → adapter class
_URL_PATTERNS: list[tuple[str, type[AtsAdapter]]] = [
    ("myworkdayjobs.com", WorkdayAdapter),
    ("greenhouse.io", GreenhouseAdapter),
    ("lever.co", LeverAdapter),
    ("icims.com", ICIMSAdapter),
]


def detect_ats_from_url(url: str) -> str:
    """Return the ATS platform name detected from the URL, or 'generic'."""
    url_lower = url.lower()
    for pattern, adapter_cls in _URL_PATTERNS:
        if pattern in url_lower:
            name = adapter_cls.__name__.replace("Adapter", "").lower()
            return name
    return "generic"


async def get_adapter(url: str, page: Page | None = None) -> AtsAdapter:
    """Resolve and return the ATS adapter for a given job URL.

    First checks URL patterns. If no match, and a page is provided,
    may inspect the DOM for ATS-specific markers (TODO Phase 2).
    Falls back to GenericAdapter.

    Args:
        url:  The job posting or application URL.
        page: Optional Playwright page for DOM inspection (not used yet).

    Returns:
        An AtsAdapter instance appropriate for the URL.
    """
    url_lower = url.lower()
    for pattern, adapter_cls in _URL_PATTERNS:
        if pattern in url_lower:
            log.info("ats.detected", ats=adapter_cls.__name__, url=url)
            return adapter_cls()

    # TODO (Phase 2): inspect page DOM for ATS-specific meta tags or script srcs
    log.info("ats.fallback_generic", url=url)
    return GenericAdapter()
