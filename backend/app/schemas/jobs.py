"""
schemas/jobs.py
Pydantic models for Job create / read / update operations.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    DRAFT = "draft"
    ANALYZED = "analyzed"
    ACTIVE = "active"
    CLOSED = "closed"


class JobCreate(BaseModel):
    """Payload the recruiter sends when creating a new job."""
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=10)
    responsibilities: Optional[str] = Field(default=None)
    requirements: Optional[str] = Field(default=None)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v.strip()


class JobUpdate(BaseModel):
    """Partial update payload — all fields optional."""
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10)
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    status: Optional[JobStatus] = None


class JobRead(BaseModel):
    """Full job record returned to the recruiter."""
    id: UUID
    recruiter_id: UUID
    title: str
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    """Lightweight job summary for list views."""
    id: UUID
    title: str
    status: JobStatus
    created_at: datetime

    model_config = {"from_attributes": True}
