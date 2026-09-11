"""Resume text extraction and AI parsing integration."""

from __future__ import annotations

import re
from pathlib import Path

import structlog
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

try:
    from docx import Document
except ImportError:
    Document = None  # type: ignore[assignment]

from app.core.config import settings
from app.integrations.ai import call_ai
from app.schemas.candidate import CandidateProfileSchema

log = structlog.get_logger(__name__)


class ParsedProfile(BaseModel):
    """Internal model for AI parsing response."""

    model_config = ConfigDict(populate_by_name=True)

    full_name: str
    email: str
    phone: str = ""
    location: str = ""
    work_authorized: bool | None = None
    resume_summary: str = Field(default="", alias="resumeSummary")


def extract_resume_text(path: Path | str) -> str:
    """Extract raw text from a PDF, DOCX, or text resume file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        pages_text: list[str] = []
        for _idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(text)
        return "\n\n".join(pages_text).strip()

    elif suffix in (".docx", ".doc"):
        if Document is None:
            raise RuntimeError("python-docx is not installed.")
        doc = Document(str(file_path))
        text_parts: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text.strip())
        return "\n".join(text_parts).strip()

    else:
        # Fallback: attempt to read as utf-8 plain text
        return file_path.read_text(encoding="utf-8", errors="ignore").strip()


_RESUME_PARSER_SYSTEM_PROMPT = """You are an expert resume summarizer. From the resume text below, produce a compact JSON profile that another AI will later use to fill job application forms.

Return ONLY valid JSON (no markdown, no commentary) in this exact shape:

{
  "full_name": "First Last",
  "email": "email or empty string",
  "phone": "phone with country code if present, or empty string",
  "location": "City, Region/Country, or 'Remote', or empty string",
  "work_authorized": null,
  "resume_summary": "compact structured summary, see rules below"
}

Rules for the top-level fields:
- Extract full_name, email, phone, location verbatim from the resume header.
- For work_authorized:
  - true ONLY if the resume EXPLICITLY states US work authorization, US citizenship, US permanent residence / green card, or equivalent US work-eligible status.
  - Otherwise null. Do NOT guess from location, name, or country. Do NOT default to true.

Rules for resume_summary (the important part):

TARGET LENGTH: aim for ~3000 characters. HARD LIMIT: 5000 characters. Never exceed this. If you would exceed it, cut older jobs and less-relevant details first.

SUMMARIZE. DO NOT COPY. This is not the resume — it is a distilled brief. Do NOT paste bullet points verbatim. Rewrite in your own compact prose and short bullets.

STRUCTURE (use exactly these section headers, in this order, plain text with newlines):

Summary: One short paragraph (2-3 sentences) with current role, total years of experience, and top 2-3 strengths.

Work authorization: Optional. Include ONLY if the resume explicitly mentions work eligibility, US citizenship, permanent residence / green card, or visa status (e.g. "US Citizen", "Authorized to work in the US", "Requires visa sponsorship"). If not stated in the resume, omit this section entirely.

Core skills: A single line, comma-separated. At most 12 items. Group by relevance. Skip generic terms (e.g. "problem solving", "teamwork"). Prefer concrete technologies and domain expertise.

Experience: For each role (most recent first), one line only, in this format:
  <Title> at <Company> (<Start> – <End>): <one-sentence impact focusing on measurable outcomes, scale, or ownership>
Include at most the 4 most recent or most relevant roles. If the resume has more, drop the oldest.

Education: One line per degree, most recent first. Format:
  <Degree>, <Institution> (<Year>)
Skip GPA unless it's exceptional (>= 3.8).

Certifications: Comma-separated on one line. Max 5. Skip if none.

Notable projects: Optional. Max 2 lines. Only include if the resume features prominent personal or open-source work relevant to engineering roles. Otherwise omit this section entirely.

WHAT TO OMIT ENTIRELY:
- Full bullet lists from the original resume.
- Every technology ever touched — keep only the ones that define the candidate.
- Soft skills, language proficiency, references, hobbies, addresses.
- Marketing adjectives ("innovative", "passionate", "results-driven").

STYLE:
- Third person is fine. No first person.
- No markdown symbols like **, ##, ---.
- Preserve original phrasing for job titles and company names.
- Do not invent metrics, employers, dates, or certifications. Only include what the resume states.
"""


def _heuristic_parse_resume(text: str) -> CandidateProfileSchema:
    """Offline heuristic fallback for resume parsing when AI key is not configured."""
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    email = email_match.group(0) if email_match else "candidate@example.com"

    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    phone = phone_match.group(0) if phone_match else ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    first_line = lines[0] if lines else "Candidate"
    # Clean non-alphabetical characters from potential name line
    name = re.sub(r"[^\w\s\.-]", "", first_line).strip() or "Candidate"

    skills = ["Software Engineering", "Python", "TypeScript", "Problem Solving"]
    for known in [
        "React",
        "Next.js",
        "FastAPI",
        "SQL",
        "Docker",
        "AWS",
        "Java",
        "Go",
        "PostgreSQL",
    ]:
        if re.search(rf"\b{re.escape(known)}\b", text, re.IGNORECASE):
            skills.append(known)

    auth_status: str | None = None
    work_auth: bool | None = None
    text_lower = text.lower()
    if any(w in text_lower for w in ["us citizen", "u.s. citizen", "green card", "permanent resident", "authorized to work in the u"]):
        auth_status = "Authorized to work in the US"
        work_auth = True
    elif any(w in text_lower for w in ["visa sponsorship", "requires sponsorship"]):
        auth_status = "Requires visa sponsorship"
        work_auth = False

    unique_skills = list(dict.fromkeys(skills))
    summary_parts = [
        f"Summary: Software professional with skills in {', '.join(unique_skills[:10])}.",
    ]
    if auth_status:
        summary_parts.append(f"\nWork authorization: {auth_status}")
    summary_parts.extend([
        "\nCore skills: " + ", ".join(unique_skills[:12]),
        "\nExperience: (unavailable — AI parser not configured)",
        "\nEducation: (unavailable — AI parser not configured)",
    ])
    resume_summary = "\n".join(summary_parts)[:2000]

    return CandidateProfileSchema(
        fullName=name,
        email=email,
        phone=phone,
        location="Remote",
        workAuthorized=work_auth,
        resumeSummary=resume_summary,
    )


async def parse_resume_text(text: str) -> CandidateProfileSchema:
    """Parse raw resume text into a structured CandidateProfileSchema via AI."""
    # Check if AI key is placeholder or empty
    if not settings.active_ai_api_key or "your-" in settings.active_ai_api_key.lower():
        log.warning("resume.ai_key_missing_using_heuristic", provider=settings.ai_provider)
        return _heuristic_parse_resume(text)

    try:
        parsed = await call_ai(
            system_prompt=_RESUME_PARSER_SYSTEM_PROMPT,
            user_content=text[:12000],  # Limit to 12k chars to fit full resumes
            response_model=ParsedProfile,
            temperature=0.0,
            max_tokens=1500,
        )
        if parsed.resume_summary and len(parsed.resume_summary) > 5000:
            log.info("resume.summary_hard_clipped", original_len=len(parsed.resume_summary))
            parsed.resume_summary = parsed.resume_summary[:5000].rstrip() + "..."

        return CandidateProfileSchema(
            fullName=parsed.full_name,
            email=parsed.email,
            phone=parsed.phone,
            location=parsed.location,
            workAuthorized=parsed.work_authorized,
            resumeSummary=parsed.resume_summary,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("resume.ai_parse_failed_falling_back", error=str(exc))
        return _heuristic_parse_resume(text)
