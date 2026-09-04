"""ORM models for ApplicationRun and FieldResult."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job import JobPosting


class ApplicationRun(Base):
    """One attempt by one candidate to apply for one job.

    Status lifecycle:
        QUEUED → RUNNING → SUBMITTED  (happy path)
                         → FAILED_CAPTCHA
                         → FAILED_VALIDATION
                         → FAILED
                         → SKIPPED_DUPLICATE (candidate already submitted for this URL)
    """

    __tablename__ = "application_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    # Storage key for confirmation screenshot/HTML on success;
    # or error artifact key on failure.
    confirmation_artifact_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Human-readable error reason (exception message or status explanation).
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    job: Mapped[JobPosting] = relationship("JobPosting", back_populates="runs")
    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="runs")
    field_results: Mapped[list[FieldResult]] = relationship(
        "FieldResult", back_populates="run", cascade="all, delete-orphan"
    )


class FieldResult(Base):
    """The value mapped and filled for one form field in an ApplicationRun."""

    __tablename__ = "field_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_label: Mapped[str] = mapped_column(String(255), nullable=False)
    mapped_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Status: filled | skipped | failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="filled")

    run: Mapped[ApplicationRun] = relationship("ApplicationRun", back_populates="field_results")
