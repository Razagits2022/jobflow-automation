"""Generic ATS adapter — AI-driven fallback for unknown platforms.

Delegates directly to the shared step functions in ``app.automation.steps``.
"""

from __future__ import annotations

import uuid
from typing import Any

from playwright.async_api import Page

from app.automation.ats.base import AtsAdapter
from app.automation.steps import extract_form, fill_form, open_application, submit


class GenericAdapter:
    """Fallback adapter: uses generic pipeline steps without ATS-specific overrides."""

    async def open_application(self, *, page: Page, job_url: str) -> None:
        """Use generic CTA detection to reach the form."""
        await open_application.open_application(page=page, job_url=job_url)

    async def extract_form(self, *, page: Page) -> list[dict[str, Any]]:
        """Use generic DOM traversal to extract fields."""
        return await extract_form.extract_form(page=page)

    async def fill_form(
        self,
        *,
        page: Page,
        field_values: list[Any],
        resume_path: str | None = None,
    ) -> list[dict[str, str]]:
        """Use generic Playwright fill strategies."""
        return await fill_form.fill_form(
            page=page,
            field_values=field_values,
            resume_path=resume_path,
        )

    async def submit(self, *, page: Page, run_id: object) -> None:
        """Locate and click submit, capture confirmation."""
        run_uuid = run_id if isinstance(run_id, uuid.UUID) else uuid.UUID(str(run_id))
        await submit.submit(page=page, run_id=run_uuid)


_: AtsAdapter = GenericAdapter()
