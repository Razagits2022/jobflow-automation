"""ORM model for JobPosting."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.run import ApplicationRun


class JobPosting(Base):
    """A job listing URL submitted for automated application."""

    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # Normalised URL used for deduplication (strip UTM params, trailing slashes, etc.).
    # Unique-ish: two identical postings on different ATS domains will have different keys.
    url_normalized: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    # ATS platform detected by the registry (workday, greenhouse, lever, icims, generic).
    ats_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Lifecycle status of the posting itself (not the run).
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    runs: Mapped[list[ApplicationRun]] = relationship("ApplicationRun", back_populates="job")
