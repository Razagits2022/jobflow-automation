"""Step 1 — Analyse job posting with AI."""

from __future__ import annotations

import re

import structlog
from pydantic import BaseModel, Field

from app.core.config import settings
from app.integrations.ai import call_ai

log = structlog.get_logger(__name__)


class JobFacts(BaseModel):
    """Structured facts extracted from a job posting."""

    role_title: str
    company: str = ""
    key_requirements: list[str] = Field(default_factory=list)
    asks_work_authorization: bool = False
    asks_years_experience: bool = False
    screening_questions: list[str] = Field(default_factory=list)
    summary: str = ""


_ANALYZE_JOB_SYSTEM_PROMPT = """You are an expert AI assistant analyzing a job posting.
Extract key structured facts and return ONLY valid JSON matching this schema:
{
  "role_title": "string (Job title, e.g. Frontend Engineer)",
  "company": "string (Company name if mentioned, or empty string)",
  "key_requirements": ["string", ... (List of core skills or qualifications)],
  "asks_work_authorization": boolean (true if mentions visa sponsorship or work auth),
  "asks_years_experience": boolean (true if specifies years of experience required),
  "screening_questions": ["string", ... (Common questions candidates may be asked)],
  "summary": "string (A concise 2-3 sentence overview of the role)"
}

Do not include any Markdown code fence or explanatory text outside the JSON."""


def _heuristic_analyze_job(job_text: str) -> JobFacts:
    """Offline heuristic fallback for job facts extraction."""
    lines = [line.strip() for line in job_text.splitlines() if line.strip()]
    role_title = lines[0][:80] if lines else "Software Professional"

    asks_work_auth = bool(
        re.search(
            r"\b(visa|sponsorship|work authorization|authorized to work|citizen|green card)\b",
            job_text,
            re.IGNORECASE,
        )
    )
    asks_years_exp = bool(
        re.search(r"\b(\d+\+?\s*years?(\s*of)?\s*experience)\b", job_text, re.IGNORECASE)
    )

    requirements: list[str] = []
    for line in lines[1:30]:
        if re.match(r"^[-•*]\s*", line) and len(line) > 10:
            clean = re.sub(r"^[-•*]\s*", "", line).strip()
            requirements.append(clean[:100])
        if len(requirements) >= 5:
            break

    return JobFacts(
        role_title=role_title,
        company="",
        key_requirements=requirements,
        asks_work_authorization=asks_work_auth,
        asks_years_experience=asks_years_exp,
        screening_questions=[],
        summary=job_text[:300].strip(),
    )


async def analyze_job(*, job_text: str) -> JobFacts:
    """Extract structured facts from the raw job-posting text using AI.

    Args:
        job_text: Raw text of the job posting page, as returned by Zyte.

    Returns:
        A validated JobFacts instance.
    """
    if not job_text.strip():
        return JobFacts(role_title="Job Opening", summary="No job text provided.")

    has_ai_key = bool(
        settings.active_ai_api_key and "your-" not in settings.active_ai_api_key.lower()
    )
    if not has_ai_key:
        log.warning("analyze_job.ai_key_missing_using_heuristic")
        return _heuristic_analyze_job(job_text)

    try:
        facts = await call_ai(
            system_prompt=_ANALYZE_JOB_SYSTEM_PROMPT,
            user_content=f"Job Posting Text:\n\n{job_text[:2500]}",
            response_model=JobFacts,
            temperature=0.1,
            max_tokens=800,
        )
        return facts
    except Exception as exc:  # noqa: BLE001
        log.error("analyze_job.failed_falling_back", error=str(exc))
        return _heuristic_analyze_job(job_text)
