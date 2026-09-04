"""Step 4 — Map candidate profile to form field values using AI reasoning."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from app.core.config import settings
from app.integrations.ai import call_ai

log = structlog.get_logger(__name__)


class FieldMapping(BaseModel):
    """Mapping instructions for a single form field."""

    selector: str
    value: str
    action: Literal["fill", "select", "check", "upload", "skip"]


class FieldMappingResponse(BaseModel):
    """Wrapper response model for AI output."""

    mappings: list[FieldMapping] = Field(default_factory=list)


_MAP_FIELDS_SYSTEM_PROMPT = """You are an expert autonomous form-filling agent.
Map candidate profile data and job facts into concrete values and actions for each form field.

Output format must be ONLY valid JSON matching this schema:
{
  "mappings": [
    {
      "selector": "exact CSS selector from the field definition",
      "value": "string value to input, exact option text, or '__RESUME__' for upload",
      "action": "fill" | "select" | "check" | "upload" | "skip"
    }
  ]
}

Action Rules:
- "fill": For text, email, tel, number, textarea inputs. Provide clean string value.
- "select": For <select> dropdowns. Pick BEST matching option from field `options`.
- "check": For radio/checkboxes. Provide option text or value to select.
- "upload": For file inputs (resume/cv). Provide "__RESUME__" as value.
- "skip": When the field cannot be filled safely or requires sensitive info (SSN, password).

Constraints:
1. For selects and radios, value MUST closely match one of the strings in `options`.
2. For US Work Authorization, choose the option indicating authorization if authorized.
3. For custom questions, generate a truthful answer from candidate experience and job facts.
4. NEVER invent private credentials (SSN, credit card, passwords). Mark as "skip".
5. Return ONLY the JSON object. No Markdown code fences or extra text."""



def _heuristic_map_fields(
    form_fields: list[dict[str, Any]],
    candidate_profile: dict[str, Any],
) -> list[FieldMapping]:
    """Offline heuristic mapping for standard application fields."""
    mappings: list[FieldMapping] = []

    full_name = candidate_profile.get("fullName") or candidate_profile.get("full_name", "")
    first_name = full_name.split()[0] if full_name else "Candidate"
    last_name = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""
    email = candidate_profile.get("email", "")
    phone = candidate_profile.get("phone", "")
    location = candidate_profile.get("location", "")
    years_exp = str(
        candidate_profile.get("yearsExperience") or candidate_profile.get("years_experience", "3")
    )
    education = candidate_profile.get("education", "")

    for field in form_fields:
        label = (field.get("label") or "").lower()
        f_type = (field.get("type") or "text").lower()
        selector = field.get("selector") or ""
        options = field.get("options") or []

        if not selector:
            continue

        if f_type == "file" or "resume" in label or "cv" in label:
            mappings.append(FieldMapping(selector=selector, value="__RESUME__", action="upload"))
            continue

        if "first name" in label:
            mappings.append(FieldMapping(selector=selector, value=first_name, action="fill"))
        elif "last name" in label:
            mappings.append(
                FieldMapping(selector=selector, value=last_name or first_name, action="fill")
            )
        elif "full name" in label or "name" in label and "company" not in label:
            mappings.append(
                FieldMapping(selector=selector, value=full_name or first_name, action="fill")
            )
        elif "email" in label:
            mappings.append(FieldMapping(selector=selector, value=email, action="fill"))
        elif "phone" in label or "mobile" in label:
            mappings.append(FieldMapping(selector=selector, value=phone, action="fill"))
        elif "location" in label or "city" in label or "address" in label:
            mappings.append(
                FieldMapping(selector=selector, value=location or "Remote", action="fill")
            )
        elif "year" in label and "experience" in label:
            if f_type in ("select", "radio") and options:
                # Pick closest option
                best_opt = options[0]
                for opt in options:
                    if years_exp in opt:
                        best_opt = opt
                        break
                act: Literal["select", "check"] = "select" if f_type == "select" else "check"
                mappings.append(FieldMapping(selector=selector, value=best_opt, action=act))
            else:
                mappings.append(FieldMapping(selector=selector, value=years_exp, action="fill"))
        elif "authoriz" in label or "sponsorship" in label or "legally" in label:
            if options:
                # Find positive option
                pos_opt = next(
                    (
                        o
                        for o in options
                        if re.search(r"\b(yes|authorized|no sponsorship)\b", o, re.IGNORECASE)
                    ),
                    options[0],
                )
                auth_act: Literal["select", "check"] = "select" if f_type == "select" else "check"
                mappings.append(FieldMapping(selector=selector, value=pos_opt, action=auth_act))

            else:
                mappings.append(FieldMapping(selector=selector, value="Yes", action="fill"))
        elif "education" in label or "degree" in label:
            mappings.append(
                FieldMapping(
                    selector=selector, value=education or "Bachelor's Degree", action="fill"
                )
            )
        elif f_type == "checkbox" and field.get("required"):
            mappings.append(FieldMapping(selector=selector, value="true", action="check"))
        elif field.get("required"):
            if options and f_type == "select":
                mappings.append(FieldMapping(selector=selector, value=options[0], action="select"))
            else:
                mappings.append(FieldMapping(selector=selector, value="N/A", action="fill"))
        else:
            mappings.append(FieldMapping(selector=selector, value="", action="skip"))

    return mappings


async def map_fields(
    *,
    form_fields: list[dict[str, Any]],
    candidate_profile: dict[str, Any],
    job_facts: dict[str, Any] | BaseModel,
) -> list[FieldMapping]:
    """Map candidate profile to form field actions using AI reasoning.

    Args:
        form_fields: List of field schemas extracted by extract_form.
        candidate_profile: Dict with candidate details.
        job_facts: Facts extracted by analyze_job.

    Returns:
        A list of FieldMapping objects.
    """
    if not form_fields:
        return []

    has_ai_key = bool(
        settings.active_ai_api_key and "your-" not in settings.active_ai_api_key.lower()
    )
    if not has_ai_key:
        log.warning("map_fields.ai_key_missing_using_heuristic")
        return _heuristic_map_fields(form_fields, candidate_profile)

    job_facts_dict = job_facts.model_dump() if isinstance(job_facts, BaseModel) else job_facts

    user_payload = {
        "form_fields": form_fields,
        "candidate_profile": candidate_profile,
        "job_facts": job_facts_dict,
    }

    try:
        res = await call_ai(
            system_prompt=_MAP_FIELDS_SYSTEM_PROMPT,
            user_content=f"Payload to map:\n{json.dumps(user_payload, indent=2)}",
            response_model=FieldMappingResponse,
            temperature=0.0,
        )
        return res.mappings
    except Exception as exc:  # noqa: BLE001
        log.error("map_fields.failed_falling_back", error=str(exc))
        return _heuristic_map_fields(form_fields, candidate_profile)
