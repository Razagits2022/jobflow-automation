"""Resume text extraction and AI parsing integration."""

from __future__ import annotations

import re
from pathlib import Path

import structlog
from pydantic import BaseModel, Field
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

    full_name: str
    email: str
    phone: str = ""
    location: str = ""
    title: str = ""
    years_experience: int = 0
    work_authorized: bool = True
    education: str = ""
    skills: list[str] = Field(default_factory=list)


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


_RESUME_PARSER_SYSTEM_PROMPT = """You are an expert AI resume parsing engine.
Extract the candidate's professional profile and format into JSON with this schema:

{
  "full_name": "Candidate's first and last name",
  "email": "Email address",
  "phone": "Phone number with country code if present, or empty string",
  "location": "City, State / Country, or 'Remote'",
  "title": "Current or target professional title (e.g. Senior Software Engineer)",
  "years_experience": 4,
  "work_authorized": true,
  "education": "Highest degree and institution or field of study",
  "skills": ["Skill1", "Skill2", "Skill3"]
}

Rules:
1. Return ONLY valid JSON matching this schema.
2. If years_experience is unstated, provide your best integer estimate based on career chronology.
3. If work authorization is unstated, infer from location/citizenship cues or default to true.
4. Extract the top 5 to 15 relevant technical or domain skills as an array of strings.
5. Do NOT include markdown code blocks or explanatory commentary outside the JSON."""


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

    return CandidateProfileSchema(
        fullName=name,
        email=email,
        phone=phone,
        location="Remote",
        title="Software Engineer",
        yearsExperience=3,
        workAuthorized=True,
        education="Bachelor's Degree",
        skills=list(dict.fromkeys(skills)),
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
            user_content=text[:10000],  # Limit to 10k chars to fit within context window
            response_model=ParsedProfile,
            temperature=0.0,
        )
        return CandidateProfileSchema(
            fullName=parsed.full_name,
            email=parsed.email,
            phone=parsed.phone,
            location=parsed.location,
            title=parsed.title,
            yearsExperience=parsed.years_experience,
            workAuthorized=parsed.work_authorized,
            education=parsed.education,
            skills=parsed.skills,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("resume.ai_parse_failed_falling_back", error=str(exc))
        return _heuristic_parse_resume(text)
