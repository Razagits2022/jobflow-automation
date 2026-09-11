"""Artifact persistence: screenshots and page HTML.

Artifacts are saved on both success (confirmation proof) and failure
(debugging evidence). The storage driver is selected by STORAGE_DRIVER env var.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog
from playwright.async_api import Page

from app.core.config import settings

log = structlog.get_logger(__name__)

# Base directory for local storage
_LOCAL_BASE = Path("artifacts")


async def save_artifact(
    page: Page,
    run_id: uuid.UUID,
    label: str,
) -> str:
    """Save a screenshot and the current page HTML for the given run.

    Args:
        page: The Playwright Page to capture from.
        run_id: UUID of the ApplicationRun — used to namespace the artifact files.
        label: Short human-readable label (e.g. ``"confirmation"``, ``"captcha"``,
               ``"validation_error"``, ``"failure"``).

    Returns:
        The storage key for the screenshot artifact (use as
        ``ApplicationRun.confirmation_artifact_key``).

    The HTML is saved alongside the screenshot with a ``.html`` suffix.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base_name = f"{run_id}/{timestamp}_{label}"

    screenshot_key = f"{base_name}.png"
    html_key = f"{base_name}.html"

    if settings.storage_driver == "local":
        return await _save_local(page, screenshot_key, html_key)
    elif settings.storage_driver == "supabase":
        return await _save_supabase(page, screenshot_key, html_key)
    elif settings.storage_driver == "s3":
        return await _save_s3(page, screenshot_key, html_key)
    else:
        raise ValueError(f"Unknown STORAGE_DRIVER: {settings.storage_driver}")


async def _save_supabase(page: Page, screenshot_key: str, html_key: str) -> str:
    """Save artifacts to Supabase Storage via REST API."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set when STORAGE_DRIVER=supabase"
        )

    base_url = settings.supabase_url.rstrip("/")
    bucket = settings.supabase_storage_bucket

    bytes_data = await page.screenshot(full_page=True)
    html_content = await page.content()
    html_bytes = html_content.encode("utf-8")

    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
        "x-upsert": "true",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Upload screenshot
        screenshot_url = f"{base_url}/storage/v1/object/{bucket}/{screenshot_key}"
        res_png = await client.post(
            screenshot_url,
            content=bytes_data,
            headers={**headers, "Content-Type": "image/png"},
        )
        res_png.raise_for_status()

        # Upload HTML
        html_url = f"{base_url}/storage/v1/object/{bucket}/{html_key}"
        res_html = await client.post(
            html_url,
            content=html_bytes,
            headers={**headers, "Content-Type": "text/html; charset=utf-8"},
        )
        res_html.raise_for_status()

    log.info(
        "artifacts.saved_supabase",
        key=screenshot_key,
        bytes=len(bytes_data),
    )
    return screenshot_key


async def _save_local(page: Page, screenshot_key: str, html_key: str) -> str:
    """Save artifacts to the local filesystem under ``artifacts/``."""
    screenshot_path = _LOCAL_BASE / screenshot_key
    html_path = _LOCAL_BASE / html_key

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    await page.screenshot(path=str(screenshot_path), full_page=True)
    html_content = await page.content()
    html_path.write_text(html_content, encoding="utf-8")

    log.info(
        "artifacts.saved_local",
        screenshot=str(screenshot_path),
        html=str(html_path),
    )
    return str(screenshot_path)


async def _save_s3(page: Page, screenshot_key: str, html_key: str) -> str:
    """Save artifacts to S3-compatible object storage.

    TODO (Phase 2): implement using httpx + S3 presigned PUT or boto3/aiobotocore.
    """
    raise NotImplementedError(
        "S3 artifact storage is not yet implemented. "
        "Set STORAGE_DRIVER=local or implement this function in Phase 2."
    )
