"""
schemas/questions.py
Pydantic models for interview_questions CRUD (Phase 4).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Read schema — returned from GET endpoints
# ---------------------------------------------------------------------------

class QuestionRead(BaseModel):
    """A single interview question row returned to the recruiter."""
    id: UUID
    job_id: UUID
    dimension_id: UUID
    dimension_name: Optional[str] = None   # joined from behavioral_dimensions
    question: str
    type: str
    difficulty: str
    indicators: List[str] = []
    approved: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Update schema — PATCH payload
# ---------------------------------------------------------------------------

class QuestionUpdate(BaseModel):
    """
    Payload for PATCH /api/questions/{id}.
    All fields are optional — only provided fields are changed.
    """
    question:   Optional[str]  = Field(default=None, min_length=10)
    type:       Optional[Literal["behavioral", "situational", "competency"]] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    indicators: Optional[List[str]] = None
    approved:   Optional[bool] = None
