"""
schemas/requirements.py
Pydantic models for job_requirements CRUD operations.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RequirementRead(BaseModel):
    """A single behavioral requirement row returned to the recruiter."""
    id: UUID
    job_id: UUID
    dimension_id: UUID
    dimension_name: Optional[str] = None   # joined from behavioral_dimensions
    importance: int
    reason: Optional[str] = None
    confirmed: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RequirementConfirm(BaseModel):
    """
    Payload for PATCH /api/jobs/{id}/requirements/{req_id}.
    Recruiter can adjust importance, edit reason, and confirm.
    """
    importance: Optional[int] = Field(default=None, ge=0, le=100)
    reason: Optional[str] = Field(default=None, min_length=5)
    confirmed: Optional[bool] = None
