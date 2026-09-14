"""Arq worker configuration and task definitions.

The worker picks up ``run_application`` tasks from the Redis queue.
Each task:
  1. Checks for duplicate SUBMITTED runs (idempotency).
  2. Delegates to the pipeline orchestrator.
  3. Catches all exceptions so one failing job never crashes the worker.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from arq.connections import RedisSettings
from sqlalchemy import select, update

from app.automation.errors import RunStatus
from app.automation.pipeline import run_application as _run_pipeline
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.redis import clean_redis_url
from app.db.session import AsyncSessionLocal
from app.models.job import JobPosting
from app.models.run import ApplicationRun

log = structlog.get_logger(__name__)


async def run_application(ctx: dict[str, Any], run_id: str) -> None:
    """Arq task: execute the full application pipeline for one run.

    This is the entry point called by Arq. It wraps the pipeline so that
    any unhandled exception is logged and swallowed — one job's failure
    must never crash the worker process.

    Args:
        ctx:    Arq worker context (contains Redis connection, etc.).
        run_id: String UUID of the ApplicationRun to process.
    """
    run_uuid = uuid.UUID(run_id)
    bound_log = log.bind(run_id=run_id)

    try:
        # ----------------------------------------------------------------
        # Deduplicate: skip if this candidate already SUBMITTED for this URL
        # ----------------------------------------------------------------
        if await _is_duplicate(run_uuid):
            bound_log.info("worker.skipped_duplicate")
            async with AsyncSessionLocal() as session:
                run = await session.get(ApplicationRun, run_uuid)
                if run:
                    run.status = RunStatus.SKIPPED_DUPLICATE.value
                    await session.commit()
            return

        # ----------------------------------------------------------------
        # Execute the pipeline
        # ----------------------------------------------------------------
        bound_log.info("worker.task_started")
        await _run_pipeline(run_uuid)
        bound_log.info("worker.task_finished")

    except asyncio.CancelledError:
        # Arq's job_timeout fires this. Mark FAILED then re-raise so Arq
        # doesn't think the job is still running.
        bound_log.warning("worker.task_cancelled_by_timeout")
        try:
            async with AsyncSessionLocal() as session:
                run = await session.get(ApplicationRun, run_uuid)
                if run is not None and run.status in (
                    RunStatus.QUEUED.value,
                    RunStatus.RUNNING.value,
                ):
                    run.status = RunStatus.FAILED.value
                    run.error_reason = "Timed out (exceeded worker job_timeout)"
                    await session.commit()
        except Exception as db_exc:  # noqa: BLE001
            bound_log.error("worker.cancel_status_write_failed", error=str(db_exc))
        raise  # re-raise so Arq/asyncio handle cancellation properly

    except Exception as exc:  # noqa: BLE001
        # Safety net: log the error but do not re-raise.
        # Re-raising would crash the Arq worker process.
        bound_log.exception("worker.task_unhandled_error", error=str(exc))
        try:
            async with AsyncSessionLocal() as session:
                run = await session.get(ApplicationRun, run_uuid)
                if run is not None and run.status in (
                    RunStatus.QUEUED.value,
                    RunStatus.RUNNING.value,
                ):
                    run.status = RunStatus.FAILED.value
                    run.error_reason = f"Worker-level failure: {type(exc).__name__}: {exc}"
                    await session.commit()
        except Exception as db_exc:  # noqa: BLE001
            bound_log.error("worker.failed_status_write_failed", error=str(db_exc))


async def _is_duplicate(run_id: uuid.UUID) -> bool:
    """Return True if this candidate already has a SUBMITTED run for the same URL."""
    async with AsyncSessionLocal() as session:
        # Load the run to get job_id + candidate_id
        run = await session.get(ApplicationRun, run_id)
        if run is None:
            return False

        # Find the normalized URL for this job
        job = await session.get(JobPosting, run.job_id)
        if job is None:
            return False

        # Look for any other SUBMITTED run for the same candidate + normalised URL
        stmt = (
            select(ApplicationRun)
            .join(JobPosting, ApplicationRun.job_id == JobPosting.id)
            .where(
                ApplicationRun.candidate_id == run.candidate_id,
                ApplicationRun.status == RunStatus.SUBMITTED.value,
                JobPosting.url_normalized == job.url_normalized,
                ApplicationRun.id != run_id,  # exclude self
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook: configure logging and reconcile orphaned runs."""
    configure_logging()
    log.info("worker.started", concurrency=settings.worker_concurrency)

    # Reconcile orphans: any RUNNING/QUEUED row older than 15 minutes must be
    # from a previous worker process that died mid-job. Mark FAILED so the
    # dashboard is accurate.
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ApplicationRun)
                .where(
                    ApplicationRun.status.in_([RunStatus.RUNNING.value, RunStatus.QUEUED.value]),
                    ApplicationRun.updated_at < cutoff,
                )
                .values(
                    status=RunStatus.FAILED.value,
                    error_reason="Orphaned by previous worker crash or spin-down",
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            rowcount = getattr(result, "rowcount", 0)
            if rowcount:
                log.warning("worker.reconciled_orphaned_runs", count=rowcount)
    except Exception as exc:  # noqa: BLE001
        log.error("worker.orphan_reconciliation_failed", error=str(exc))


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook."""
    log.info("worker.shutting_down")


class WorkerSettings:
    """Arq WorkerSettings class — passed to ``arq`` CLI as the settings object.

    Run with::

        uv run arq app.workers.worker.WorkerSettings
    """

    functions = [run_application]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(clean_redis_url(settings.redis_url))
    max_jobs = settings.worker_concurrency
    job_timeout = 180  # 3 minutes max per job
    keep_result = 3600  # keep job results for 1 hour
