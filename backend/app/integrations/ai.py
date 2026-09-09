"""AI provider integration.

Builds an AsyncOpenAI client pointed at the configured provider. For DeepSeek,
the standard OpenAI SDK is used with a custom base_url. Switching to native
OpenAI requires only changing AI_PROVIDER in the environment.

JSON contract:
  - The exact JSON shape is stated in the system prompt (not as a response_format schema),
    because DeepSeek's strict JSON-schema support is uneven.
  - The reply is parsed against a Pydantic model.
  - On parse failure, the call is retried once before raising.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import settings

log = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def _build_client() -> AsyncOpenAI:
    """Build an AsyncOpenAI client for the active provider.

    For DeepSeek: uses the DeepSeek base URL and API key.
    For OpenAI:   uses the OpenAI default base URL.
    """
    kwargs: dict[str, Any] = {"api_key": settings.active_ai_api_key}
    if settings.active_ai_base_url:
        kwargs["base_url"] = settings.active_ai_base_url
    return AsyncOpenAI(**kwargs)


# Module-level client singleton — shared across all calls in the process.
_client: AsyncOpenAI = _build_client()


async def call_ai(
    *,
    system_prompt: str,
    user_content: str,
    response_model: type[T],
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> T:
    """Call the AI provider and parse the response into a Pydantic model.

    The system_prompt MUST describe the exact JSON structure expected.
    No response_format schema is passed to the API (DeepSeek compatibility).

    Retry strategy: on Pydantic ValidationError, retry once with an additional
    user message asking the model to correct its JSON. Raises on second failure.

    Args:
        system_prompt:  Instruction + exact JSON schema description for the AI.
        user_content:   The payload to reason about (job text, field list, etc.).
        response_model: Pydantic model to validate/parse the JSON response into.
        temperature:    Sampling temperature (low for deterministic outputs).
        max_tokens:     Per-call output token limit to control burn rate.

    Returns:
        A validated instance of ``response_model``.

    Raises:
        ValidationError: If the model's JSON is invalid after one retry.
        openai.APIError: On API-level failures.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    for attempt in range(2):  # try once, retry once
        # Note: Disable thinking mode so reasoning tokens don't exhaust the max_tokens budget.
        create_kwargs: dict[str, Any] = {
            "model": settings.active_ai_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens
        if settings.ai_provider == "deepseek" or "deepseek" in settings.active_ai_model.lower():
            create_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

        response = await _client.chat.completions.create(**create_kwargs)
        raw = (response.choices[0].message.content or "").strip()

        # Strip markdown code fences if the model wraps JSON in ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(raw)
            return response_model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            if attempt == 0:
                log.warning(
                    "ai.parse_failed_retrying",
                    attempt=attempt,
                    error=str(exc),
                    raw_snippet=raw[:200],
                )
                # Append the bad response and ask for a correction
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your response could not be parsed as valid JSON matching the schema. "
                            f"Error: {exc}. "
                            "Please respond with ONLY the corrected JSON, no explanation."
                        ),
                    }
                )
            else:
                log.error("ai.parse_failed_final", error=str(exc))
                raise

    # Unreachable, but satisfies mypy
    raise RuntimeError("call_ai: exhausted retries without returning")
