"""Pydantic v2 schemas for ApplicationRun and FieldResult."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FieldResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    field_label: str
    mapped_value: str | None
    status: str


class ApplicationRunRead(BaseModel):
    """Schema for reading an ApplicationRun."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    confirmation_artifact_key: str | None
    error_reason: str | None
    created_at: datetime
    updated_at: datetime
    field_results: list[FieldResultRead] = []


class ApplicationRunList(BaseModel):
    """Paginated list of runs."""

    items: list[ApplicationRunRead]
    total: int
    page: int
    page_size: int


class RunFieldSchema(BaseModel):
    """Matches the frontend RunField interface."""

    label: str
    value: str


class RunResponseSchema(BaseModel):
    """Matches the frontend Run interface."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    url: str
    status: str
    created_at: str = Field(..., alias="createdAt")
    fields: list[RunFieldSchema] | None = None
    error_reason: str | None = Field(default=None, alias="errorReason")


class StatsResponseSchema(BaseModel):
    """Matches the frontend stats response."""

    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    submitted: int = 0
    failed: int = 0
    failed_captcha: int = Field(default=0, alias="failedCaptcha")
    running: int = 0
    queued: int = 0
