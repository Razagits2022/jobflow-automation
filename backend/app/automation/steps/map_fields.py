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
- "select": For <select> dropdowns and comboboxes. Pick BEST matching option from field `options`.
- "check": For radio/checkboxes. Provide option text or value to select.
- "upload": For file inputs (resume/cv). Provide "__RESUME__" as value.
- "skip": ONLY when the field is optional and cannot be filled safely, or requires sensitive private credentials (SSN, credit card, passwords). NEVER skip a required field!

Special Handling for Questions NOT in Candidate's Resume:
1. "How did you hear about us?" / "Source" / "Referral":
   - If options are provided, select "LinkedIn", "Company Website", "Careers Page", or "Job Board". If none of those exist, pick the first sensible option.
   - If text input, fill "LinkedIn".
2. "Have you ever worked here before?" / "Former employee or contractor?":
   - Select "No", "I have never worked at [Company]", or the negative option.
3. "Preferred office / location":
   - Pick the option matching candidate's location, "Remote", or the first available office option.
4. General Required Fields with missing resume info:
   - If required dropdown/radio: NEVER skip. Pick the most sensible default or the first valid option.
   - If required text/textarea: Fill a sensible professional answer (e.g. "LinkedIn", "N/A", or a brief relevant sentence based on job title).

Constraints:
1. For selects and radios, value MUST closely match one of the strings in `options`.
2. For US Work Authorization, choose the option indicating authorization if authorized.
3. NEVER invent private credentials (SSN, credit card, passwords). Mark as "skip".
4. Return ONLY the JSON object. No Markdown code fences or extra text."""


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
    city = candidate_profile.get("city", "")
    state = (
        candidate_profile.get("state")
        or candidate_profile.get("county")
        or candidate_profile.get("province")
        or candidate_profile.get("region")
        or city
    )
    country = candidate_profile.get("country", "United Kingdom")
    postal_code = (
        candidate_profile.get("postal_code")
        or candidate_profile.get("postalCode")
        or candidate_profile.get("zip")
        or candidate_profile.get("zip_code", "")
    )
    address = (
        candidate_profile.get("address")
        or candidate_profile.get("address_line_1")
        or candidate_profile.get("addressLine1", "")
    )
    location = candidate_profile.get("location") or city or "London"
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
            # Only map the primary / first resume upload field to __RESUME__ to prevent multiple uploads wiping ATS forms
            if not any(m.action == "upload" for m in mappings):
                mappings.append(FieldMapping(selector=selector, value="__RESUME__", action="upload"))
            else:
                mappings.append(FieldMapping(selector=selector, value="", action="skip"))
            continue

        # Check country phone code BEFORE general phone
        if (
            "country code" in label
            or "phone code" in label
            or "dial code" in label
            or "countryphonecode" in selector.lower()
        ):
            act_code: Literal["select", "fill"] = "select" if (f_type == "select" or options) else "fill"
            mappings.append(FieldMapping(selector=selector, value=country, action=act_code))
        elif "first name" in label:
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
        elif "address line 2" in label or "address 2" in label:
            mappings.append(FieldMapping(selector=selector, value="", action="skip"))
        elif "address line 1" in label or "address 1" in label or ("address" in label and "line" in label):
            mappings.append(FieldMapping(selector=selector, value=address or location, action="fill"))
        elif "country" in label or "nation" in label:
            act_country: Literal["select", "fill"] = "select" if (f_type == "select" or options) else "fill"
            mappings.append(FieldMapping(selector=selector, value=country, action=act_country))
        elif "county" in label or "state" in label or "province" in label or "region" in label:
            mappings.append(FieldMapping(selector=selector, value=state or city or "Greater London", action="fill"))
        elif "postcode" in label or "postal" in label or "zip" in label:
            mappings.append(FieldMapping(selector=selector, value=postal_code or "SW1A 1AA", action="fill"))
        elif "city" in label or "town" in label:
            mappings.append(FieldMapping(selector=selector, value=city or location, action="fill"))
        elif "location" in label or "address" in label:
            mappings.append(
                FieldMapping(selector=selector, value=location or address or "Remote", action="fill")
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
        elif "referr" in label or "worked" in label or "former employee" in label or "previously employed" in label:
            # Negative answer to avoid conditional required questions like "Please name referrer"
            if options:
                neg_opt = next(
                    (
                        o
                        for o in options
                        if re.search(r"\b(never|no\b|not\b|false\b)", o, re.IGNORECASE)
                    ),
                    options[-1],
                )
                act_neg: Literal["select", "check"] = "select" if f_type == "select" else "check"
                mappings.append(FieldMapping(selector=selector, value=neg_opt, action=act_neg))
            else:
                mappings.append(FieldMapping(selector=selector, value="No", action="fill"))
        elif "hear" in label or "source" in label:
            if options:
                source_opt = next(
                    (
                        o
                        for o in options
                        if re.search(r"\b(linkedin|website|career|job board|online)\b", o, re.IGNORECASE)
                    ),
                    options[0],
                )
                act: Literal["select", "check"] = "select" if f_type == "select" else "check"
                mappings.append(FieldMapping(selector=selector, value=source_opt, action=act))
            else:
                mappings.append(FieldMapping(selector=selector, value="LinkedIn", action="fill"))
        elif "office" in label or "preferred location" in label:
            if options:
                loc_opt = next(
                    (
                        o
                        for o in options
                        if (location and location.lower() in o.lower()) or "remote" in o.lower()
                    ),
                    options[0],
                )
                act_loc: Literal["select", "check"] = "select" if f_type == "select" else "check"
                mappings.append(FieldMapping(selector=selector, value=loc_opt, action=act_loc))
            else:
                mappings.append(FieldMapping(selector=selector, value=location or "Remote", action="fill"))
        elif "education" in label or "degree" in label:
            mappings.append(
                FieldMapping(
                    selector=selector, value=education or "Bachelor's Degree", action="fill"
                )
            )
        elif f_type == "checkbox" and (
            field.get("required")
            or any(
                k in label
                for k in ["certif", "true and complete", "terms", "agree", "policy", "accuracy", "acknowledge", "consent"]
            )
        ):
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

    # Filter to only essential field metadata to minimise token burn
    sanitized_fields = [
        {
            "id": f.get("id", ""),
            "label": f.get("label", ""),
            "type": f.get("type", "text"),
            "required": bool(f.get("required", False)),
            "options": f.get("options", []),
            "selector": f.get("selector", ""),
        }
        for f in form_fields
    ]

    # Send only concise job title and short summary
    if isinstance(job_facts, BaseModel):
        job_summary = {
            "role_title": getattr(job_facts, "role_title", ""),
            "summary": getattr(job_facts, "summary", "")[:300],
        }
    elif isinstance(job_facts, dict):
        job_summary = {
            "role_title": job_facts.get("role_title", ""),
            "summary": str(job_facts.get("summary", ""))[:300],
        }
    else:
        job_summary = {"role_title": "Position", "summary": ""}

    user_payload = {
        "form_fields": sanitized_fields,
        "candidate_profile": candidate_profile,
        "job_facts": job_summary,
    }

    # Token cap with room for custom essay answers and cover letters
    token_cap = 2000

    try:
        res = await call_ai(
            system_prompt=_MAP_FIELDS_SYSTEM_PROMPT,
            user_content=f"Payload to map:\n{json.dumps(user_payload, separators=(',', ':'))}",
            response_model=FieldMappingResponse,
            temperature=0.0,
            max_tokens=token_cap,
        )
        return res.mappings
    except Exception as exc:  # noqa: BLE001
        log.error("map_fields.failed_falling_back", error=str(exc))
        return _heuristic_map_fields(form_fields, candidate_profile)
