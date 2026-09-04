"""Application pipeline orchestrator.

Orders the steps defined in ``app.automation.steps``, wraps them in a
single try/except, routes exceptions to terminal RunStatus values, saves
artifacts on every outcome, and ensures the browser is always closed.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.automation.artifacts import save_artifact
from app.automation.ats.registry import get_adapter
from app.automation.browser import managed_page
from app.automation.errors import (
    CaptchaEncounteredError,
    RunStatus,
    ValidationFailedError,
)
from app.automation.steps import (
    analyze_job,
    detect_captcha,
    extract_form,
    fill_form,
    map_fields,
    open_application,
    submit,
    validate,
)
from app.db.session import AsyncSessionLocal
from app.integrations import zyte
from app.models.candidate import Candidate
from app.models.run import ApplicationRun, FieldResult

log = structlog.get_logger(__name__)


async def run_application(run_id: uuid.UUID) -> None:
    """Orchestrate the full application pipeline for a single ApplicationRun.

    Steps (in order):
        1. Load context (job, candidate, resume) from DB
        2. Fetch job page text via Zyte
        3. analyze_job      — AI: job text → structured job facts
        4. open_application — Playwright: find Apply / Register, reach form
        5. extract_form     — perception: DOM → field schema
        6. map_fields       — AI: fields + candidate → value JSON
        7. fill_form        — Playwright: fill inputs, upload resume, dropdowns
        8. detect_captcha   — detect anti-bot challenge → raise CaptchaEncounteredError
        9. validate         — detect field errors → raise ValidationFailedError
        10. submit          — Playwright: submit + verify confirmation proof

    On CaptchaEncounteredError → status = FAILED_CAPTCHA
    On ValidationFailedError   → status = FAILED_VALIDATION
    On any other exception     → status = FAILED
    On success                 → status = SUBMITTED
    """
    bound_log = log.bind(run_id=str(run_id))
    bound_log.info("pipeline.started")

    final_status: RunStatus = RunStatus.FAILED
    error_reason: str | None = None
    artifact_key: str | None = None
    artifact_label: str = "failure"
    recorded_field_results: list[dict[str, str]] = []

    async with managed_page() as (_context, page):
        try:
            # 1. Mark as RUNNING
            async with AsyncSessionLocal() as session:
                await _update_run_status(session, run_id, RunStatus.RUNNING)

            # 2. Load context from DB
            job_url: str = ""
            candidate_profile: dict[str, Any] = {}
            resume_path: str | None = None

            async with AsyncSessionLocal() as session:
                stmt = (
                    select(ApplicationRun)
                    .where(ApplicationRun.id == run_id)
                    .options(
                        selectinload(ApplicationRun.job),
                        selectinload(ApplicationRun.candidate).selectinload(Candidate.resumes),
                    )
                )
                res = await session.execute(stmt)
                run = res.scalar_one_or_none()

                if run is None or run.job is None or run.candidate is None:
                    raise RuntimeError(f"ApplicationRun context missing for run_id={run_id}")

                job_url = run.job.url
                cand = run.candidate
                cand_profile_data = cand.profile or {}
                candidate_profile = {
                    "fullName": cand.full_name,
                    "email": cand.email,
                    "phone": cand.phone or "",
                    "location": cand_profile_data.get("location", ""),
                    "title": cand_profile_data.get("title", ""),
                    "yearsExperience": cand_profile_data.get("yearsExperience")
                    or cand_profile_data.get("years_experience", 0),
                    "workAuthorized": cand_profile_data.get(
                        "workAuthorized", cand_profile_data.get("work_authorized", True)
                    ),
                    "education": cand_profile_data.get("education", ""),
                    "skills": cand_profile_data.get("skills", []),
                }

                if cand.resumes:
                    latest = sorted(cand.resumes, key=lambda r: r.created_at, reverse=True)[0]
                    resume_path = latest.storage_key

            # 3. Zyte extraction
            bound_log.info("pipeline.fetching_job_content", url=job_url)
            job_data = await zyte.fetch_job_posting(job_url)

            # 4. Analyze job
            bound_log.info("pipeline.analyzing_job")
            job_facts = await analyze_job.analyze_job(job_text=job_data.text)

            # 5. Check adapter registry
            adapter = await get_adapter(job_url, page)
            bound_log.info("pipeline.adapter_resolved", adapter=type(adapter).__name__)

            # 6. Open application form
            bound_log.info("pipeline.opening_application")
            await open_application.open_application(page=page, job_url=job_url)

            # 7. Extract form fields
            bound_log.info("pipeline.extracting_form")
            form_fields = await extract_form.extract_form(page=page)

            if not form_fields:
                bound_log.warning("pipeline.no_form_fields_found")

            # 8. Map fields
            bound_log.info("pipeline.mapping_fields", field_count=len(form_fields))
            field_mappings = await map_fields.map_fields(
                form_fields=form_fields,
                candidate_profile=candidate_profile,
                job_facts=job_facts,
            )

            # 9. Fill form
            bound_log.info("pipeline.filling_form", mapping_count=len(field_mappings))
            recorded_field_results = await fill_form.fill_form(
                page=page,
                field_values=field_mappings,
                resume_path=resume_path,
            )

            # 10. Persist field results to DB
            async with AsyncSessionLocal() as session:
                for fr in recorded_field_results:
                    session.add(
                        FieldResult(
                            run_id=run_id,
                            field_label=fr["field_label"],
                            mapped_value=fr["mapped_value"],
                            status=fr["status"],
                        )
                    )
                await session.commit()

            # 11. Detect CAPTCHA
            bound_log.info("pipeline.checking_captcha")
            await detect_captcha.detect_captcha(page=page)

            # 12. Validate
            bound_log.info("pipeline.validating_form")
            await validate.validate(page=page)

            # 13. Submit
            bound_log.info("pipeline.submitting")
            await submit.submit(page=page, run_id=run_id)

            # Success
            final_status = RunStatus.SUBMITTED
            artifact_label = "confirmation"
            bound_log.info("pipeline.submitted")

        except CaptchaEncounteredError as exc:
            final_status = RunStatus.FAILED_CAPTCHA
            error_reason = str(exc)
            artifact_label = "captcha"
            bound_log.warning("pipeline.captcha_encountered", reason=error_reason)

        except ValidationFailedError as exc:
            final_status = RunStatus.FAILED_VALIDATION
            error_reason = str(exc)
            artifact_label = "validation_error"
            bound_log.warning("pipeline.validation_failed", reason=error_reason)

        except Exception as exc:  # noqa: BLE001
            final_status = RunStatus.FAILED
            error_reason = f"{type(exc).__name__}: {exc}"
            artifact_label = "failure"
            bound_log.exception("pipeline.failed", reason=error_reason)

        finally:
            # Always save screenshot & HTML artifacts
            try:
                artifact_key = await save_artifact(
                    page=page,
                    run_id=run_id,
                    label=artifact_label,
                )
            except Exception as art_exc:  # noqa: BLE001
                bound_log.error("pipeline.artifact_save_failed", error=str(art_exc))

            # Update final status in DB
            async with AsyncSessionLocal() as session:
                await _update_run_status(
                    session,
                    run_id,
                    final_status,
                    error_reason=error_reason,
                    artifact_key=artifact_key,
                )

            bound_log.info("pipeline.finished", status=final_status.value)


async def _update_run_status(
    session: AsyncSession,
    run_id: uuid.UUID,
    status: RunStatus,
    error_reason: str | None = None,
    artifact_key: str | None = None,
) -> None:
    """Persist status update to ApplicationRun."""
    run = await session.get(ApplicationRun, run_id)
    if run is None:
        log.error("pipeline.run_not_found", run_id=str(run_id))
        return
    run.status = status.value
    if error_reason is not None:
        run.error_reason = error_reason
    if artifact_key is not None:
        run.confirmation_artifact_key = artifact_key
    await session.commit()
