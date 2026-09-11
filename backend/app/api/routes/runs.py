"""Application run orchestration, status monitoring, and artifact streaming."""

from __future__ import annotations

import uuid
from pathlib import Path

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.automation.errors import RunStatus
from app.automation.throttle import compute_start_offsets
from app.core.config import settings
from app.core.redis import get_arq_pool
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.run import ApplicationRun
from app.schemas.run import RunFieldSchema, RunResponseSchema

log = structlog.get_logger(__name__)

router = APIRouter()


def _map_backend_status_to_frontend(raw_status: str) -> str:
    """Map the backend RunStatus string to the frontend union."""
    status_upper = raw_status.upper()
    mapping = {
        RunStatus.QUEUED.value: "queued",
        RunStatus.RUNNING.value: "running",
        RunStatus.SUBMITTED.value: "submitted",
        RunStatus.FAILED.value: "failed",
        RunStatus.FAILED_CAPTCHA.value: "failed_captcha",
        RunStatus.FAILED_VALIDATION.value: "failed_validation",
        RunStatus.SKIPPED_DUPLICATE.value: "skipped_duplicate",
    }
    return mapping.get(status_upper, "failed")


def _serialize_run(run: ApplicationRun, job_url: str) -> RunResponseSchema:
    fields: list[RunFieldSchema] | None = None
    loaded_fields = run.__dict__.get("field_results")
    if loaded_fields:
        fields = [
            RunFieldSchema(label=fr.field_label, value=fr.mapped_value or "")
            for fr in loaded_fields
        ]

    return RunResponseSchema(
        id=str(run.id),
        url=job_url,
        status=_map_backend_status_to_frontend(run.status),
        createdAt=run.created_at.isoformat(),
        fields=fields,
        errorReason=run.error_reason,
    )


@router.post("/start", response_model=list[RunResponseSchema])
async def start_applying(
    db: AsyncSession = Depends(get_db),
) -> list[RunResponseSchema]:
    """Convert all queued JobPostings into active ApplicationRuns and enqueue to Arq."""
    # Find active candidate
    candidate_stmt = select(Candidate).order_by(Candidate.created_at.asc()).limit(1)
    cand_res = await db.execute(candidate_stmt)
    candidate = cand_res.scalar_one_or_none()

    if candidate is None:
        # Create baseline candidate placeholder if none exists
        candidate = Candidate(
            full_name="Candidate",
            email="candidate@example.com",
            profile={},
        )
        db.add(candidate)
        await db.flush()

    # Find queued jobs
    jobs_stmt = (
        select(JobPosting)
        .where(JobPosting.status == "queued")
        .order_by(JobPosting.created_at.asc())
    )
    jobs_res = await db.execute(jobs_stmt)
    queued_jobs = jobs_res.scalars().all()

    if not queued_jobs:
        return []

    created_runs: list[tuple[ApplicationRun, str]] = []
    for job in queued_jobs:
        run = ApplicationRun(
            job_id=job.id,
            candidate_id=candidate.id,
            status=RunStatus.QUEUED.value,
        )
        job.status = "enqueued"
        db.add(run)
        created_runs.append((run, job.url))

    await db.commit()

    # Refresh runs to load generated IDs
    for run, _ in created_runs:
        await db.refresh(run)

    # Enqueue to Arq Redis
    try:
        redis_pool = await get_arq_pool()
        offsets = compute_start_offsets(len(created_runs))
        for (run, _), offset in zip(created_runs, offsets, strict=False):
            await redis_pool.enqueue_job("run_application", str(run.id), _defer_by=offset)
            log.info(
                "runs.enqueued_to_arq",
                run_id=str(run.id),
                defer_seconds=offset.total_seconds(),
            )
    except Exception as exc:
        log.warning("runs.redis_enqueue_warning", error=str(exc))

    return [_serialize_run(run, url) for run, url in created_runs]


@router.get("", response_model=list[RunResponseSchema])
@router.get("/", response_model=list[RunResponseSchema])
async def list_runs(
    db: AsyncSession = Depends(get_db),
) -> list[RunResponseSchema]:
    """List application runs ordered from most recent to oldest."""
    stmt = (
        select(ApplicationRun)
        .options(selectinload(ApplicationRun.job), selectinload(ApplicationRun.field_results))
        .order_by(ApplicationRun.created_at.desc())
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()

    return [_serialize_run(r, r.job.url if r.job else "Unknown URL") for r in runs]


@router.get("/{run_id}", response_model=RunResponseSchema)
async def get_run_details(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RunResponseSchema:
    """Get complete details and field results of one run."""
    stmt = (
        select(ApplicationRun)
        .where(ApplicationRun.id == run_id)
        .options(selectinload(ApplicationRun.job), selectinload(ApplicationRun.field_results))
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    return _serialize_run(run, run.job.url if run.job else "Unknown URL")


@router.get("/{run_id}/screenshot")
async def get_run_screenshot(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Stream confirmation or failure screenshot artifact via signed URL or local file."""
    stmt = select(ApplicationRun).where(ApplicationRun.id == run_id)
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if run is None or not run.confirmation_artifact_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot artifact not available for this run.",
        )

    key = run.confirmation_artifact_key
    if "\\" in key or key.startswith("artifacts/"):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Legacy local artifact from before storage migration",
        )

    if settings.storage_driver == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase storage credentials not configured.",
            )

        base_url = settings.supabase_url.rstrip("/")
        bucket = settings.supabase_storage_bucket
        key = run.confirmation_artifact_key
        sign_url = f"{base_url}/storage/v1/object/sign/{bucket}/{key}"

        headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(sign_url, json={"expiresIn": 300}, headers=headers)
            if res.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Screenshot object not found in Supabase storage.",
                )
            if res.is_error:
                log.error("runs.supabase_sign_failed", status=res.status_code, body=res.text)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to generate signed screenshot URL.",
                )
            data = res.json()
            signed_path = data.get("signedURL")
            if not signed_path:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid response from Supabase storage sign endpoint.",
                )

            full_signed_url = f"{base_url}/storage/v1{signed_path}"
            return RedirectResponse(url=full_signed_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    file_path = Path(run.confirmation_artifact_key)
    if not file_path.exists():
        # Check relative to backend directory or artifacts root
        alt_path = Path("artifacts") / run.confirmation_artifact_key
        if alt_path.exists():
            file_path = alt_path
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Screenshot file not found on disk.",
            )

    return FileResponse(file_path, media_type="image/png")
