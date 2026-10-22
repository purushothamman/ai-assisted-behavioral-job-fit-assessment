"""
schemas/alignment.py
Pydantic models for Phase 7 Job-Candidate Behavioral Alignment.

Defines the contract for:
  - POST /api/sessions/{session_id}/alignment  (calculate/recalculate alignment)
  - GET  /api/sessions/{session_id}/alignment  (retrieve single session alignment)
  - GET  /api/jobs/{job_id}/alignments         (list all session alignments for a job)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class DimensionAlignmentItem(BaseModel):
    """Alignment breakdown for a single behavioral dimension."""
    dimension_name:    str
    dimension_label:   str
    job_weight:        float   # 0.0 - 100.0 (recruiter importance)
    weight_percentage: float   # % of total job requirement weight
    candidate_score:   float   # 0.0 - 100.0 (evaluated candidate performance)
    contribution:      float   # points contributed to overall 0-100 alignment score
    status:            str     # 'assessed' | 'missing' | 'unweighted'
    confidence:        float   # 0.0 - 1.0 (mean evaluation confidence)
    response_count:    int     # number of responses assessed for this dimension


class SessionAlignmentRead(BaseModel):
    """Complete alignment result for a candidate session."""
    id:                        Optional[UUID] = None
    session_id:                UUID
    job_id:                    UUID
    candidate_name:            str
    job_title:                 str
    overall_score:             float = Field(ge=0.0, le=100.0)
    total_weight:              int
    total_dimensions_count:    int
    assessed_dimensions_count: int
    average_confidence:        float
    dimension_alignments:      List[DimensionAlignmentItem] = []
    strengths:                 List[str] = []
    areas_for_review:          List[str] = []
    metadata:                  Dict[str, Any] = {}
    calculated_at:             Optional[datetime] = None
    reviewed_at:               Optional[datetime] = None
    reviewed_by:               Optional[UUID] = None
    review_action:             Optional[str] = None
    recruiter_notes:           Optional[str] = None
    override_score:            Optional[float] = None

    model_config = {"from_attributes": True}


class AlignmentTriggerPayload(BaseModel):
    """Optional payload when triggering alignment calculation."""
    force_recalculate: bool = False


class SessionReviewPayload(BaseModel):
    """Payload for recruiter oversight review on an assessment session (OV-5)."""
    action:          Optional[str] = Field(None, description="'reviewed' | 'flagged_for_interview' | 'request_reassessment' | 'overridden' | 'completed'")
    review_action:   Optional[str] = Field(None, description="Alias for action")
    notes:           Optional[str] = Field(None, max_length=4000, description="Qualitative recruiter notes and observations")
    recruiter_notes: Optional[str] = Field(None, max_length=4000, description="Alias for notes")
    override_score:  Optional[float] = Field(None, ge=0.0, le=100.0, description="Optional human-overridden overall score")

    @property
    def resolved_action(self) -> str:
        act = self.review_action or self.action or "reviewed"
        return act

    @property
    def resolved_notes(self) -> Optional[str]:
        return self.recruiter_notes if self.recruiter_notes is not None else self.notes


class SessionReviewRead(BaseModel):
    """Confirmation record for submitted recruiter oversight review."""
    session_id:         UUID
    reviewed_at:        datetime
    reviewed_by:        Union[UUID, str]
    review_action:      str
    recruiter_notes:    Optional[str] = None
    original_score:     float
    override_score:     Optional[float] = None
    audit_log_id:       Optional[Union[UUID, str]] = None
    is_repeated_review: bool = False

