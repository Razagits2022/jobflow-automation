"""Application run metrics and statistics endpoint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.automation.errors import RunStatus
from app.models.run import ApplicationRun
from app.schemas.run import StatsResponseSchema

log = structlog.get_logger(__name__)

router = APIRouter()


@router.get("", response_model=StatsResponseSchema)
@router.get("/", response_model=StatsResponseSchema)
async def get_application_stats(
    db: AsyncSession = Depends(get_db),
) -> StatsResponseSchema:
    """Compute dashboard metrics: total, submitted, failed, failedCaptcha, running, queued."""
    stmt = select(ApplicationRun.status)
    result = await db.execute(stmt)
    statuses = result.scalars().all()

    total = len(statuses)
    submitted = 0
    failed = 0
    failed_captcha = 0
    running = 0
    queued = 0

    for s in statuses:
        s_upper = s.upper()
        if s_upper == RunStatus.SUBMITTED.value:
            submitted += 1
        elif s_upper in (RunStatus.FAILED.value, RunStatus.FAILED_VALIDATION.value):
            failed += 1
        elif s_upper == RunStatus.FAILED_CAPTCHA.value:
            failed_captcha += 1
        elif s_upper == RunStatus.RUNNING.value:
            running += 1
        elif s_upper == RunStatus.QUEUED.value:
            queued += 1
        else:
            failed += 1

    return StatsResponseSchema(
        total=total,
        submitted=submitted,
        failed=failed,
        failedCaptcha=failed_captcha,
        running=running,
        queued=queued,
    )
