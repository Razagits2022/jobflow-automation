"""Pydantic v2 schemas for JobPosting."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobPostingCreate(BaseModel):
    """Schema for submitting a new job URL."""

    url: str = Field(..., description="The full job posting URL.")
    candidate_id: uuid.UUID = Field(..., description="The candidate to apply for this job.")


class JobPostingRead(BaseModel):
    """Schema for reading a job posting."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    url_normalized: str
    ats_type: str | None
    status: str
    created_at: datetime


class EnqueueRunRequest(BaseModel):
    """Schema for the enqueue-run endpoint on jobs."""

    candidate_id: uuid.UUID


class EnqueueRunResponse(BaseModel):
    """Returned after a run is enqueued."""

    run_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    message: str


class JobUrlSchema(BaseModel):
    """Matches the frontend JobUrl interface."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    url: str
    added_at: str = Field(..., alias="addedAt")


class JobBatchCreateRequest(BaseModel):
    """Payload for POST /api/jobs."""

    urls: list[str]
