"""Pydantic v2 schemas for Candidate and Resume."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    profile: dict[str, Any] = Field(default_factory=dict)


class CandidateCreate(CandidateBase):
    """Schema for creating a new candidate."""


class CandidateUpdate(BaseModel):
    """Schema for partial candidate updates."""

    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = None
    profile: dict[str, Any] | None = None


class CandidateRead(CandidateBase):
    """Schema for reading a candidate (includes DB-generated fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class CandidateProfileSchema(BaseModel):
    """Full flat candidate profile that matches the frontend CandidateProfile interface."""

    model_config = ConfigDict(populate_by_name=True)

    full_name: str = Field(..., alias="fullName")
    email: EmailStr
    phone: str = ""
    location: str = ""
    title: str = ""
    years_experience: int = Field(default=0, alias="yearsExperience")
    work_authorized: bool = Field(default=True, alias="workAuthorized")
    education: str = ""
    skills: list[str] = Field(default_factory=list)


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    storage_key: str
    filename: str
    created_at: datetime
