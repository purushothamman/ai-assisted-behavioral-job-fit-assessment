"""
schemas/sessions.py
Pydantic models for interview_sessions and candidate_responses (Phase 5).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Session — recruiter creates, candidate accesses via token
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    """Payload for POST /api/jobs/{id}/sessions — create a candidate session."""
    candidate_name:  str = Field(..., min_length=2, max_length=200)
    candidate_email: str = Field(..., min_length=5, max_length=320)
    expires_in_days: int = Field(default=7, ge=1, le=90)
    send_email:      bool = Field(default=True, description="Send invitation email via Resend")


class SessionRead(BaseModel):
    """A session row returned to the recruiter after creation."""
    id:              UUID
    job_id:          UUID
    token:           str
    candidate_name:  str
    candidate_email: str
    status:          str            # pending | in_progress | completed
    expires_at:      Optional[datetime] = None
    submitted_at:    Optional[datetime] = None
    created_at:      Optional[datetime] = None
    email_status:    Optional[str] = "pending"  # pending | sent | failed
    email_error:     Optional[str] = None
    assessment_url:  Optional[str] = None

    model_config = {"from_attributes": True}


class RetryEmailResponse(BaseModel):
    """Response returned when retrying an invitation email."""
    success:      bool
    email_status: str
    email_error:  Optional[str] = None
    message:      str


# ---------------------------------------------------------------------------
# Public session payload — returned to candidate via token
# ---------------------------------------------------------------------------

class PublicQuestion(BaseModel):
    """Minimal question info exposed to the candidate."""
    id:             UUID
    dimension_name: Optional[str] = None
    question:       str
    type:           str
    difficulty:     str
    indicators:     List[str] = []


class PublicSessionRead(BaseModel):
    """
    Full session payload returned to the candidate when they open their link.
    Includes job context + approved questions only.
    """
    session_id:      UUID
    job_title:       str
    job_description: str
    candidate_name:  str
    status:          str
    expires_at:      Optional[datetime] = None
    questions:       List[PublicQuestion] = []


# ---------------------------------------------------------------------------
# Candidate response — submitted per question
# ---------------------------------------------------------------------------

class ResponseCreate(BaseModel):
    """One response submitted by the candidate for a single question."""
    question_id: UUID
    answer:      str = Field(..., min_length=10, max_length=10_000)


class ResponseRead(BaseModel):
    """A saved candidate response row."""
    id:          UUID
    session_id:  UUID
    question_id: UUID
    answer:      str
    created_at:  Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Bulk submission
# ---------------------------------------------------------------------------

class SubmitResponsesPayload(BaseModel):
    """
    Payload for POST /api/sessions/{token}/responses.
    The candidate submits all answers at once.
    """
    responses: List[ResponseCreate] = Field(..., min_length=1)
