"""Candidate and Resume management endpoints."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.integrations.resume import extract_resume_text, parse_resume_text
from app.models.candidate import Candidate, Resume
from app.schemas.candidate import CandidateProfileSchema

log = structlog.get_logger(__name__)

router = APIRouter()

_UPLOAD_DIR = Path("artifacts") / "resumes"


def _serialize_candidate_profile(candidate: Candidate) -> CandidateProfileSchema:
    """Combine Candidate columns and profile JSONB into the flat CandidateProfileSchema."""
    profile_data = candidate.profile or {}

    resume_summary = profile_data.get("resumeSummary") or profile_data.get("resume_summary", "")
    if not resume_summary:
        # Synthesize from legacy fields on read
        parts: list[str] = []
        if title := profile_data.get("title"):
            parts.append(f"Title: {title}")
        years = profile_data.get("yearsExperience") or profile_data.get("years_experience")
        if years is not None and str(years).strip():
            parts.append(f"Years of Experience: {years}")
        if edu := profile_data.get("education"):
            parts.append(f"Education: {edu}")
        if skills := profile_data.get("skills"):
            if isinstance(skills, list):
                parts.append("Skills: " + ", ".join(str(s) for s in skills if s))
            elif isinstance(skills, str):
                parts.append(f"Skills: {skills}")
        resume_summary = "\n".join(parts).strip()
        if resume_summary:
            log.info("candidate.profile.legacy_shape_migrated", candidate_id=str(candidate.id))

    return CandidateProfileSchema(
        fullName=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone or "",
        location=profile_data.get("location", ""),
        workAuthorized=profile_data.get(
            "workAuthorized", profile_data.get("work_authorized", None)
        ),
        resumeSummary=resume_summary,
    )


@router.get("", response_model=CandidateProfileSchema | None)
@router.get("/", response_model=CandidateProfileSchema | None)
async def get_candidate(db: AsyncSession = Depends(get_db)) -> CandidateProfileSchema | None:
    """Return the current candidate profile, or None if none exists."""
    stmt = select(Candidate).order_by(Candidate.created_at.asc()).limit(1)
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if candidate is None:
        return None
    return _serialize_candidate_profile(candidate)


@router.put("", response_model=CandidateProfileSchema)
@router.put("/", response_model=CandidateProfileSchema)
async def update_candidate(
    payload: CandidateProfileSchema,
    db: AsyncSession = Depends(get_db),
) -> CandidateProfileSchema:
    """Create or update the single candidate profile."""
    stmt = select(Candidate).order_by(Candidate.created_at.asc()).limit(1)
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    profile_dict = {
        "location": payload.location,
        "workAuthorized": payload.work_authorized,
        "resumeSummary": payload.resume_summary,
    }

    if candidate is None:
        candidate = Candidate(
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            profile=profile_dict,
        )
        db.add(candidate)
    else:
        candidate.full_name = payload.full_name
        candidate.email = payload.email
        candidate.phone = payload.phone
        candidate.profile = profile_dict

    await db.commit()
    await db.refresh(candidate)
    return _serialize_candidate_profile(candidate)


@router.post("/resume", response_model=CandidateProfileSchema)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> CandidateProfileSchema:
    """Upload a resume file (PDF or DOCX), extract text, parse with AI, and persist."""
    filename = file.filename or "resume.pdf"
    file_ext = Path(filename).suffix.lower()
    if file_ext not in (".pdf", ".docx", ".doc", ".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_ext}'. Allowed: .pdf, .docx, .txt",
        )

    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_filename = f"{uuid.uuid4()}_{filename}"
    saved_path = _UPLOAD_DIR / saved_filename

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        raw_text = extract_resume_text(saved_path)
    except Exception as exc:
        log.error("candidate.resume_extract_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to read text from resume: {exc}",
        ) from exc

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Resume file contains no extractable text. "
                "Please upload a PDF or DOCX file with selectable text "
                "(not a scanned image or screenshot)."
            ),
        )

    # Parse profile with AI (or fallback)
    parsed_profile = await parse_resume_text(raw_text)

    # Persist or update Candidate
    stmt = select(Candidate).order_by(Candidate.created_at.asc()).limit(1)
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    profile_dict = {
        "location": parsed_profile.location,
        "workAuthorized": parsed_profile.work_authorized,
        "resumeSummary": parsed_profile.resume_summary,
    }

    if candidate is None:
        candidate = Candidate(
            full_name=parsed_profile.full_name,
            email=parsed_profile.email,
            phone=parsed_profile.phone,
            profile=profile_dict,
        )
        db.add(candidate)
        await db.flush()
    else:
        candidate.full_name = parsed_profile.full_name
        candidate.email = parsed_profile.email
        candidate.phone = parsed_profile.phone
        candidate.profile = profile_dict

    # Record resume row
    resume_row = Resume(
        candidate_id=candidate.id,
        storage_key=str(saved_path),
        filename=filename,
    )
    db.add(resume_row)

    await db.commit()
    await db.refresh(candidate)

    return _serialize_candidate_profile(candidate)
