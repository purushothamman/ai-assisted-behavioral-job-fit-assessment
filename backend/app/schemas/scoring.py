"""
schemas/scoring.py
Pydantic models for Phase 6 response scoring.

These models define the API request/response shapes for:
  - POST /api/sessions/{session_id}/score  (trigger scoring)
  - GET  /api/sessions/{session_id}/scores (fetch results)
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Evidence — per indicator
# ---------------------------------------------------------------------------

class IndicatorEvidenceRead(BaseModel):
    """Serializable evidence for a single behavioral indicator."""
    indicator_name: str
    similarity:     float   # cosine similarity 0.0–1.0
    score:          int     # 0 | 1 | 2
    matched:        bool
    level:          str     # 'none' | 'partial' | 'strong'


# ---------------------------------------------------------------------------
# Per-response score
# ---------------------------------------------------------------------------

class ResponseScoreRead(BaseModel):
    """
    Scoring result for a single candidate response (one question).
    Stored in the response_scores table.
    """
    id:                 UUID
    session_id:         UUID
    question_id:        UUID
    response_id:        UUID
    dimension_name:     str
    normalized_score:   int     # 0-100
    raw_score:          float   # 0.0-1.0
    confidence:         float   # 0.0-1.0
    indicators_matched: int
    total_indicators:   int
    status:             str     # 'scored' | 'invalid:*' | 'no_indicators' | 'error'
    evidence:           List[IndicatorEvidenceRead] = []
    scored_at:          Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Session-level score summary
# ---------------------------------------------------------------------------

class SessionScoreSummary(BaseModel):
    """
    Aggregated scoring results for a completed session.
    Returned by GET /api/sessions/{id}/scores.
    """
    session_id:          UUID
    candidate_name:      str
    job_title:           str
    total_responses:     int
    scored_responses:    int
    average_score:       float   # mean of normalized_score across all responses
    scores:              List[ResponseScoreRead] = []
    scored_at:           Optional[datetime] = None


# ---------------------------------------------------------------------------
# Trigger payload (currently no fields required, kept for future options)
# ---------------------------------------------------------------------------

class ScoreTrigger(BaseModel):
    """
    Optional payload for POST /api/sessions/{id}/score.
    Reserved for future per-scoring options (e.g. re-score, model override).
    Currently accepts an empty body.
    """
    force_rescore: bool = False
