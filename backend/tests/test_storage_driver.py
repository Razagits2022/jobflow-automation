"""Test Supabase storage driver and signed URL endpoint."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import Response

from app.api.routes.runs import get_run_screenshot
from app.automation.artifacts import save_artifact
from app.core.config import settings
from app.models.run import ApplicationRun


@pytest.mark.asyncio
async def test_save_artifact_supabase():
    """Verify save_artifact dispatches to _save_supabase and uploads via httpx."""
    mock_page = AsyncMock()
    mock_page.screenshot = AsyncMock(return_value=b"fake-screenshot-bytes")
    mock_page.content = AsyncMock(return_value="<html><body>Mock Page</body></html>")

    run_id = uuid.uuid4()

    with (
        patch.object(settings, "storage_driver", "supabase"),
        patch.object(settings, "supabase_url", "https://testref.supabase.co"),
        patch.object(settings, "supabase_service_role_key", "mock-service-key"),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
    ):
        mock_post.return_value = Response(
            200,
            json={"Key": "mock/key"},
            request=httpx.Request("POST", "https://testref.supabase.co/storage/v1/object/artifacts"),
        )

        storage_key = await save_artifact(mock_page, run_id, "confirmation")

        assert storage_key.startswith(f"{run_id}/")
        assert storage_key.endswith("_confirmation.png")
        assert mock_post.call_count == 2

        # Check call arguments
        call_urls = [call.args[0] for call in mock_post.call_args_list]
        assert any(storage_key in url for url in call_urls)
        assert any(storage_key.replace(".png", ".html") in url for url in call_urls)


@pytest.mark.asyncio
async def test_get_run_screenshot_supabase_signed_url():
    """Verify get_run_screenshot mints a 5-minute signed URL and redirects with 307."""
    run_id = uuid.uuid4()
    mock_run = ApplicationRun(
        id=run_id,
        confirmation_artifact_key=f"{run_id}/timestamp_confirmation.png",
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_run
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch.object(settings, "storage_driver", "supabase"),
        patch.object(settings, "supabase_url", "https://testref.supabase.co"),
        patch.object(settings, "supabase_service_role_key", "mock-service-key"),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
    ):
        mock_post.return_value = Response(
            200,
            json={"signedURL": "/object/sign/artifacts/mock_signed_token"},
            request=httpx.Request("POST", "https://testref.supabase.co/storage/v1/object/sign/artifacts"),
        )

        response = await get_run_screenshot(run_id, db=mock_db)

        assert response.status_code == 307
        expected_redirect = "https://testref.supabase.co/storage/v1/object/sign/artifacts/mock_signed_token"
        assert response.headers["location"] == expected_redirect


@pytest.mark.asyncio
async def test_get_run_screenshot_legacy_artifact_410():
    """Verify get_run_screenshot returns HTTP 410 Gone for legacy local filesystem artifact keys."""
    from fastapi import HTTPException

    run_id = uuid.uuid4()
    mock_run = ApplicationRun(
        id=run_id,
        confirmation_artifact_key="artifacts/runs/old_screenshot.png",
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_run
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await get_run_screenshot(run_id, db=mock_db)

    assert exc_info.value.status_code == 410
    assert "Legacy local artifact from before storage migration" in exc_info.value.detail
