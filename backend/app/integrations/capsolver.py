"""CapSolver API integration — solve automated bot challenges (reCAPTCHA, Turnstile).

Uses CapSolver's ProxyLess task types:
  - ReCaptchaV2TaskProxyLess
  - AntiTurnstileTaskProxyLess
  - ReCaptchaV3TaskProxyLess
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

_CREATE_TASK_URL = "https://api.capsolver.com/createTask"
_GET_RESULT_URL = "https://api.capsolver.com/getTaskResult"


class CapSolverError(Exception):
    """Raised when CapSolver API encounters an unrecoverable failure."""


async def _create_and_poll_task(
    task_payload: dict[str, Any],
    *,
    timeout_seconds: int = 60,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Submit a task to CapSolver and poll until ready or timed out."""
    client_key = settings.capsolver_api_key.strip()
    if not client_key or "your-" in client_key.lower():
        raise CapSolverError("CapSolver API key is missing or unconfigured.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        create_body = {
            "clientKey": client_key,
            "task": task_payload,
        }
        try:
            resp = await client.post(_CREATE_TASK_URL, json=create_body)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.error("capsolver.create_task_failed", error=str(exc))
            raise CapSolverError(f"Failed to create CapSolver task: {exc}") from exc

        if data.get("errorId", 0) != 0:
            err_code = data.get("errorCode", "UNKNOWN_ERROR")
            err_desc = data.get("errorDescription", "")
            log.error("capsolver.create_task_error", error_code=err_code, desc=err_desc)
            raise CapSolverError(f"CapSolver error: {err_code} — {err_desc}")

        task_id = data.get("taskId")
        if not task_id:
            raise CapSolverError("CapSolver did not return a valid taskId.")

        log.info("capsolver.task_created", task_id=task_id, task_type=task_payload.get("type"))

        # Poll for completion
        poll_body = {
            "clientKey": client_key,
            "taskId": task_id,
        }
        elapsed = 0.0
        while elapsed < timeout_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            try:
                poll_resp = await client.post(_GET_RESULT_URL, json=poll_body)
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()
            except Exception as poll_exc:
                log.warning("capsolver.poll_network_error", error=str(poll_exc), elapsed=elapsed)
                continue

            if poll_data.get("errorId", 0) != 0:
                err_code = poll_data.get("errorCode", "UNKNOWN")
                err_desc = poll_data.get("errorDescription", "")
                raise CapSolverError(f"CapSolver task failed: {err_code} — {err_desc}")

            status = poll_data.get("status")
            if status == "ready":
                log.info("capsolver.task_solved", task_id=task_id, elapsed=elapsed)
                return poll_data.get("solution", {})

        raise CapSolverError(f"CapSolver task timed out after {timeout_seconds}s.")


async def solve_recaptcha_v2(
    website_url: str,
    sitekey: str,
    *,
    is_invisible: bool = False,
) -> str:
    """Solve Google reCAPTCHA v2 and return the response token."""
    task = {
        "type": "ReCaptchaV2TaskProxyLess",
        "websiteURL": website_url,
        "websiteKey": sitekey,
        "isInvisible": is_invisible,
    }
    solution = await _create_and_poll_task(task)
    token = solution.get("gRecaptchaResponse", "")
    if not token:
        raise CapSolverError("CapSolver solved reCAPTCHA v2 but returned an empty token.")
    return token


async def solve_turnstile(
    website_url: str,
    sitekey: str,
    *,
    action: str = "",
) -> str:
    """Solve Cloudflare Turnstile and return the response token."""
    task: dict[str, Any] = {
        "type": "AntiTurnstileTaskProxyLess",
        "websiteURL": website_url,
        "websiteKey": sitekey,
    }
    if action:
        task["metadata"] = {"action": action}

    solution = await _create_and_poll_task(task)
    token = solution.get("token", "")
    if not token:
        raise CapSolverError("CapSolver solved Turnstile but returned an empty token.")
    return token


async def solve_recaptcha_v3(
    website_url: str,
    sitekey: str,
    *,
    page_action: str = "submit",
) -> str:
    """Solve Google reCAPTCHA v3 and return the response token."""
    task = {
        "type": "ReCaptchaV3TaskProxyLess",
        "websiteURL": website_url,
        "websiteKey": sitekey,
        "pageAction": page_action,
    }
    solution = await _create_and_poll_task(task)
    token = solution.get("gRecaptchaResponse", "")
    if not token:
        raise CapSolverError("CapSolver solved reCAPTCHA v3 but returned an empty token.")
    return token
