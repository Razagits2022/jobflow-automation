"""AtsAdapter protocol — the contract every ATS adapter must satisfy."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from playwright.async_api import Page


@runtime_checkable
class AtsAdapter(Protocol):
    """Protocol for ATS-specific overrides of the generic pipeline steps.

    Adapters override only the steps that differ from the generic behaviour.
    Methods not overridden fall back to the generic implementation.

    Each method signature mirrors the corresponding step function.
    """

    async def open_application(self, *, page: Page, job_url: str) -> None:
        """Navigate to and reach the application form for this ATS."""
        ...

    async def extract_form(self, *, page: Page) -> list[dict[str, Any]]:
        """Extract form fields using ATS-specific DOM knowledge."""
        ...

    async def fill_form(
        self,
        *,
        page: Page,
        field_values: list[Any],
        resume_path: str | None = None,
    ) -> list[dict[str, str]]:
        """Fill form fields using ATS-specific widget handling."""
        ...


    async def submit(self, *, page: Page, run_id: object) -> None:
        """Submit the form and capture confirmation proof."""
        ...
