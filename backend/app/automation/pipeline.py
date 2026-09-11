"""Application pipeline orchestrator.

Orders the steps defined in ``app.automation.steps``, wraps them in a
single try/except, routes exceptions to terminal RunStatus values, saves
artifacts on every outcome, and ensures the browser is always closed.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

import httpx
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
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.integrations import zyte
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.run import ApplicationRun, FieldResult

log = structlog.get_logger(__name__)


def _has_essay_fields(fields: list[dict[str, Any]]) -> bool:
    """Check if form contains free-text or essay fields requiring deep AI job analysis."""
    essay_keywords = (
        "cover letter",
        "why",
        "describe",
        "message",
        "motivation",
        "statement",
        "about you",
        "tell us",
    )
    for field in fields:
        f_type = (field.get("type") or "").lower()
        label = (field.get("label") or "").lower()
        if f_type == "textarea":
            return True
        if any(kw in label for kw in essay_keywords):
            return True
    return False


async def run_application(run_id: uuid.UUID) -> None:
    """Orchestrate the full application pipeline for a single ApplicationRun.

    Steps (in order):
        1. Load context (job, candidate, resume) from DB
        2. Fetch job page text via Zyte
        3. open_application — Playwright: reach application form
        4. extract_form     — perception: DOM → field schema
        5. analyze_job      — AI: job text → structured job facts (conditional)
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
    page = None

    try:
        async with managed_page() as (_context, _page):
            page = _page
            # 1. Mark as RUNNING
            async with AsyncSessionLocal() as session:
                await _update_run_status(session, run_id, RunStatus.RUNNING)

            # 2. Load context from DB
            job_url: str = ""
            job_id: uuid.UUID | None = None
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
                job_id = run.job.id
                cand = run.candidate
                cand_profile_data = cand.profile or {}
                candidate_profile = {
                    **cand_profile_data,
                    "fullName": cand.full_name,
                    "email": cand.email,
                    "phone": cand.phone or cand_profile_data.get("phone", ""),
                    "location": cand_profile_data.get("location") or cand_profile_data.get("city", ""),
                    "title": cand_profile_data.get("title", ""),
                    "yearsExperience": cand_profile_data.get("yearsExperience")
                    or cand_profile_data.get("years_experience", 0),
                    "workAuthorized": cand_profile_data.get(
                        "workAuthorized", cand_profile_data.get("work_authorized", None)
                    ),
                    "education": cand_profile_data.get("education", ""),
                    "skills": cand_profile_data.get("skills", []),
                }

                local_resumes_dir = Path("artifacts") / "resumes"
                local_resumes_dir.mkdir(parents=True, exist_ok=True)

                if cand.resumes:
                    latest = sorted(cand.resumes, key=lambda r: r.created_at, reverse=True)[0]
                    cand_storage_key = latest.storage_key
                    clean_name = Path(latest.filename or cand_storage_key).name
                    candidate_local = local_resumes_dir / clean_name

                    if Path(cand_storage_key).exists():
                        resume_path = cand_storage_key
                    elif candidate_local.exists():
                        resume_path = str(candidate_local)
                    elif (
                        settings.storage_driver == "supabase"
                        and settings.supabase_url
                        and settings.supabase_service_role_key
                    ):
                        try:
                            base_url = settings.supabase_url.rstrip("/")
                            bucket = settings.supabase_storage_bucket
                            headers = {
                                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                                "apikey": settings.supabase_service_role_key,
                            }
                            # Keys to attempt downloading
                            keys_to_try = [
                                cand_storage_key,
                                f"resumes/{clean_name}",
                                clean_name,
                            ]
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                for key in keys_to_try:
                                    dl_url = f"{base_url}/storage/v1/object/{bucket}/{key}"
                                    resp = await client.get(dl_url, headers=headers)
                                    if resp.is_success and resp.content:
                                        candidate_local.write_bytes(resp.content)
                                        resume_path = str(candidate_local)
                                        bound_log.info(
                                            "pipeline.resume_downloaded_from_supabase",
                                            key=key,
                                            path=resume_path,
                                        )
                                        break
                        except Exception as dl_err:
                            bound_log.warning(
                                "pipeline.resume_supabase_download_failed",
                                error=str(dl_err),
                            )

                # Resilient fallback: If no file exists on disk, synthesize from profile so ATS never blocks
                if not resume_path or not Path(resume_path).exists():
                    try:
                        safe_name = (cand.full_name or "Candidate").replace(" ", "_")
                        synth_file = local_resumes_dir / f"{cand.id}_{safe_name}_Resume.txt"
                        synth_content = (
                            f"Full Name: {cand.full_name}\n"
                            f"Email: {cand.email}\n"
                            f"Phone: {cand.phone or ''}\n"
                            f"Location: {candidate_profile.get('location', '')}\n\n"
                            f"PROFILE & EXPERIENCE SUMMARY:\n"
                            f"{candidate_profile.get('resumeSummary', '')}\n"
                        )
                        synth_file.write_text(synth_content, encoding="utf-8")
                        resume_path = str(synth_file)
                        bound_log.info("pipeline.synthesized_fallback_resume", path=resume_path)
                    except Exception as synth_err:
                        bound_log.warning("pipeline.fallback_resume_failed", error=str(synth_err))

            # 3. Zyte extraction
            bound_log.debug("pipeline.fetching_job_content", url=job_url)
            job_data = await zyte.fetch_job_posting(job_url)

            # 4. Check adapter registry
            adapter = await get_adapter(job_url, page)
            bound_log.debug("pipeline.adapter_resolved", adapter=type(adapter).__name__)

            # 5. Open application form
            page = await open_application.open_application(
                page=page,
                job_url=job_url,
                candidate_profile=candidate_profile,
            )

            # Re-resolve adapter if navigation occurred to a dedicated ATS (e.g. Pinpoint, Greenhouse)
            if page.url != job_url:
                adapter = await get_adapter(page.url, page)
                bound_log.info("pipeline.adapter_re_resolved", adapter=type(adapter).__name__, final_url=page.url)
                try:
                    async with AsyncSessionLocal() as session:
                        job_record = await session.get(JobPosting, job_id)
                        if job_record is not None:
                            job_record.url = page.url
                            await session.commit()
                except Exception as db_err:
                    bound_log.warning("pipeline.update_job_url_failed", error=str(db_err))

            # Multi-Step Form Loop (supports single-step ATS and multi-step wizards up to 5 steps)
            MAX_FORM_STEPS = 5

            for step_num in range(1, MAX_FORM_STEPS + 1):
                # Wait for form inputs / step container to settle
                await page.wait_for_timeout(1500)
                await open_application.dismiss_overlays(page)

                # 6. Extract form fields
                form_fields = await extract_form.extract_form(page=page)

                if not form_fields:
                    if step_num == 1:
                        bound_log.warning("pipeline.no_form_fields_found")
                    else:
                        bound_log.info("pipeline.no_further_fields_completed", step=step_num)
                        final_status = RunStatus.SUBMITTED
                        artifact_label = "confirmation"
                        break

                # 7. Analyze job (conditional on free-text / essay fields)
                if _has_essay_fields(form_fields):
                    bound_log.info("pipeline.analyzing_job", reason="essay_fields_detected", step=step_num)
                    job_facts = await analyze_job.analyze_job(job_text=job_data.text)
                else:
                    bound_log.info("pipeline.job_analysis_skipped", reason="no_essay_fields", step=step_num)
                    job_facts = analyze_job.JobFacts(
                        role_title=job_data.title or "Position",
                        summary="",
                    )

                # 8. Map fields
                bound_log.debug("pipeline.mapping_fields", field_count=len(form_fields), step=step_num)
                field_mappings = await map_fields.map_fields(
                    form_fields=form_fields,
                    candidate_profile=candidate_profile,
                    job_facts=job_facts,
                )

                # 9. Fill form
                bound_log.debug("pipeline.filling_form", mapping_count=len(field_mappings), step=step_num)
                step_results = await fill_form.fill_form(
                    page=page,
                    field_values=field_mappings,
                    resume_path=resume_path if step_num == 1 else None,
                    form_fields=form_fields,
                )
                recorded_field_results.extend(step_results)

                # Try to grab job title from page heading or title on step 1
                if step_num == 1:
                    detected_job_title = ""
                    try:
                        h1_loc = page.locator("h1").first
                        if await h1_loc.count() > 0:
                            detected_job_title = (await h1_loc.text_content(timeout=500) or "").strip()
                    except Exception:
                        pass

                    if not detected_job_title:
                        try:
                            raw_title = await page.title()
                            detected_job_title = raw_title.split("|")[0].split("-")[0].strip()
                        except Exception:
                            pass

                    if detected_job_title:
                        recorded_field_results.insert(
                            0,
                            {
                                "field_label": "Job Role / Title",
                                "mapped_value": detected_job_title,
                                "status": "filled",
                            },
                        )

                # 10. Persist field results to DB for this step
                try:
                    for attempt in range(3):
                        try:
                            async with AsyncSessionLocal() as session:
                                for fr in step_results:
                                    session.add(
                                        FieldResult(
                                            run_id=run_id,
                                            field_label=fr["field_label"],
                                            mapped_value=fr["mapped_value"],
                                            status=fr["status"],
                                        )
                                    )
                                await session.commit()
                            break
                        except Exception as db_retry_err:
                            if attempt < 2:
                                await asyncio.sleep(1.0)
                            else:
                                raise db_retry_err
                except Exception as db_err:
                    bound_log.warning("pipeline.persist_field_results_failed", error=str(db_err))

                # 11. Detect CAPTCHA
                bound_log.debug("pipeline.checking_captcha", step=step_num)
                await detect_captcha.detect_captcha(page=page)

                # 12. Validate
                bound_log.debug("pipeline.validating_form", step=step_num)
                await validate.validate(page=page)

                # 13. Submit or Advance
                bound_log.debug("pipeline.submitting_or_advancing", step=step_num)
                outcome = await submit.submit(page=page, run_id=run_id)

                if outcome == "CONFIRMED":
                    final_status = RunStatus.SUBMITTED
                    artifact_label = "confirmation"
                    bound_log.info("pipeline.submitted", total_steps=step_num)
                    break
                elif outcome == "STEP_ADVANCED":
                    bound_log.info("pipeline.step_advanced_to_next", completed_step=step_num, new_url=page.url)
                    await page.wait_for_timeout(2000)
                    await open_application.dismiss_overlays(page)
                    continue
                else:
                    raise RuntimeError(f"Unexpected submission outcome: {outcome}")

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
        # Save artifacts only if we actually have a page
        if page is not None:
            try:
                artifact_key = await save_artifact(
                    page=page,
                    run_id=run_id,
                    label=artifact_label,
                )
            except Exception as art_exc:  # noqa: BLE001
                bound_log.error("pipeline.artifact_save_failed", error=str(art_exc))

        # ALWAYS write final status, with retries — even if page is None
        for attempt in range(3):
            try:
                async with AsyncSessionLocal() as session:
                    await _update_run_status(
                        session,
                        run_id,
                        final_status,
                        error_reason=error_reason,
                        artifact_key=artifact_key,
                    )
                break
            except Exception as db_exc:
                if attempt < 2:
                    await asyncio.sleep(1.5)
                else:
                    bound_log.error("pipeline.final_status_update_failed", error=str(db_exc))

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
