"""Job posting queue management endpoints."""

from __future__ import annotations

import re
import uuid
from urllib.parse import urlsplit, urlunsplit

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.automation.ats.registry import detect_ats_from_url
from app.models.job import JobPosting
from app.schemas.job import JobBatchCreateRequest, JobUrlSchema

log = structlog.get_logger(__name__)

router = APIRouter()


def normalize_job_url(raw_url: str) -> str:
    """Normalize a job URL for deduplication."""
    url = raw_url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = f"https://{url}"

    parsed = urlsplit(url)
    # Lowercase netloc and strip trailing slash from path
    clean_netloc = parsed.netloc.lower().removeprefix("www.")
    clean_path = parsed.path.rstrip("/")

    # Strip analytics query params (utm_*, ref, etc.)
    clean_query = "&".join(
        param
        for param in parsed.query.split("&")
        if param and not param.lower().startswith(("utm_", "ref", "source", "fbclid"))
    )

    return urlunsplit((parsed.scheme.lower(), clean_netloc, clean_path, clean_query, ""))


@router.post("", response_model=list[JobUrlSchema], status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=list[JobUrlSchema], status_code=status.HTTP_201_CREATED)
async def create_jobs(
    payload: JobBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> list[JobUrlSchema]:
    """Accept an array of URLs, normalize, deduplicate, and enqueue into JobPosting."""
    raw_urls = payload.urls

    if not raw_urls:
        return []

    # Filter empties and normalize
    seen_normalized: set[str] = set()
    cleaned_pairs: list[tuple[str, str]] = []  # (original, normalized)

    for raw in raw_urls:
        trimmed = raw.strip()
        if not trimmed:
            continue
        try:
            norm = normalize_job_url(trimmed)
            if norm not in seen_normalized:
                seen_normalized.add(norm)
                cleaned_pairs.append((trimmed, norm))
        except Exception:
            continue

    if not cleaned_pairs:
        return []

    # Check for already queued jobs in DB
    norm_list = [norm for _, norm in cleaned_pairs]
    existing_stmt = select(JobPosting.url_normalized).where(
        JobPosting.url_normalized.in_(norm_list),
        JobPosting.status == "queued",
    )
    existing_result = await db.execute(existing_stmt)
    already_queued = set(existing_result.scalars().all())

    created_jobs: list[JobPosting] = []
    for orig, norm in cleaned_pairs:
        if norm in already_queued:
            continue
        ats = detect_ats_from_url(orig)
        job = JobPosting(
            url=orig,
            url_normalized=norm,
            ats_type=ats,
            status="queued",
        )
        db.add(job)
        created_jobs.append(job)

    if created_jobs:
        await db.commit()
        for j in created_jobs:
            await db.refresh(j)

    return [
        JobUrlSchema(
            id=str(j.id),
            url=j.url,
            addedAt=j.created_at.isoformat(),
        )
        for j in created_jobs
    ]


@router.get("", response_model=list[JobUrlSchema])
@router.get("/", response_model=list[JobUrlSchema])
async def list_queued_jobs(
    db: AsyncSession = Depends(get_db),
) -> list[JobUrlSchema]:
    """List all job postings currently queued."""
    stmt = (
        select(JobPosting)
        .where(JobPosting.status == "queued")
        .order_by(JobPosting.created_at.asc())
    )
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    return [
        JobUrlSchema(
            id=str(j.id),
            url=j.url,
            addedAt=j.created_at.isoformat(),
        )
        for j in jobs
    ]


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_queued_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = delete(JobPosting).where(JobPosting.id == job_id, JobPosting.status == "queued")
    result = await db.execute(stmt)
    deleted_count = getattr(result, "rowcount", 0)

    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queued job '{job_id}' not found.",
        )
    await db.commit()
