"""Unit tests for the three bug fixes: proxy opt-in, work_authorized gating, and Supabase startup checks."""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.routes.candidates import _serialize_candidate_profile
from app.automation.proxy import get_playwright_proxy_config
from app.automation.steps.map_fields import _heuristic_map_fields
from app.core.config import settings
from app.integrations.resume import _heuristic_parse_resume
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateProfileSchema


def test_proxy_opt_in_behavior():
    """Verify proxy is ONLY returned when proxy_enabled=True AND proxy_url is non-empty."""
    # 1. By default proxy is off
    with patch.object(settings, "proxy_enabled", False), patch.object(settings, "proxy_url", None):
        assert get_playwright_proxy_config() is None

    # 2. Proxy url set but proxy_enabled=False -> Still None
    with patch.object(settings, "proxy_enabled", False), patch.object(settings, "proxy_url", "http://1.2.3.4:8080"):
        assert get_playwright_proxy_config() is None

    # 3. proxy_enabled=True but proxy_url is None/empty -> None
    with patch.object(settings, "proxy_enabled", True), patch.object(settings, "proxy_url", ""):
        assert get_playwright_proxy_config() is None

    # 4. proxy_enabled=True AND proxy_url set -> Returns parsed proxy
    with patch.object(settings, "proxy_enabled", True), patch.object(settings, "proxy_url", "http://1.2.3.4:8080"):
        cfg = get_playwright_proxy_config()
        assert cfg is not None
        assert cfg["server"] == "http://1.2.3.4:8080"


def test_work_authorized_defaults_to_none():
    """Verify CandidateProfileSchema and heuristic parser default work_authorized to None."""
    schema = CandidateProfileSchema(fullName="Elena Rodriguez", email="elena@example.com")
    assert schema.work_authorized is None

    heuristic = _heuristic_parse_resume("Elena Rodriguez\nelena@example.com\nSoftware Engineer")
    assert heuristic.work_authorized is None

    # Serialization with no profile info should keep workAuthorized as None
    cand = Candidate(full_name="Elena Rodriguez", email="elena@example.com", profile={})
    serialized = _serialize_candidate_profile(cand)
    assert serialized.work_authorized is None


def test_map_fields_work_authorized_handling():
    """Verify map_fields skips work authorization when workAuthorized is None."""
    auth_field = [{
        "id": "work_auth",
        "label": "Are you legally authorized to work in the United States?",
        "type": "select",
        "options": ["Yes", "No"],
        "selector": "#auth_select",
    }]

    # When None -> should skip
    res_none = _heuristic_map_fields(auth_field, {"fullName": "Elena", "workAuthorized": None})
    assert len(res_none) == 1
    assert res_none[0].action == "skip"

    # When True -> should select Yes
    res_true = _heuristic_map_fields(auth_field, {"fullName": "Elena", "workAuthorized": True})
    assert len(res_true) == 1
    assert res_true[0].action == "select"
    assert res_true[0].value == "Yes"

    # When False -> should select No
    res_false = _heuristic_map_fields(auth_field, {"fullName": "Elena", "workAuthorized": False})
    assert len(res_false) == 1
    assert res_false[0].action == "select"
    assert res_false[0].value == "No"


@pytest.mark.asyncio
async def test_supabase_startup_check():
    """Verify lifespan logs supabase_misconfigured or supabase_ready."""
    from app.main import app, lifespan

    # Test misconfigured when missing keys
    with (
        patch("app.main.close_arq_pool", new_callable=AsyncMock),
        patch.object(settings, "storage_driver", "supabase"),
        patch.object(settings, "supabase_url", None),
        patch("app.main.log.error") as mock_err,
    ):
        async with lifespan(app):
            mock_err.assert_called_once()
            assert "storage.supabase_misconfigured" in mock_err.call_args[0][0]

    # Test ready when keys present
    with (
        patch("app.main.close_arq_pool", new_callable=AsyncMock),
        patch.object(settings, "storage_driver", "supabase"),
        patch.object(settings, "supabase_url", "https://xyz.supabase.co"),
        patch.object(settings, "supabase_service_role_key", "valid-key"),
        patch.object(settings, "supabase_storage_bucket", "artifacts"),
        patch("app.main.log.info") as mock_info,
    ):
        async with lifespan(app):
            assert any(call[0][0] == "storage.supabase_ready" for call in mock_info.call_args_list)
