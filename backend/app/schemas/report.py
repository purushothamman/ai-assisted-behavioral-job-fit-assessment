"""
schemas/report.py
Pydantic schemas for Phase 8: Assessment Reports & Recruiter Dashboard.

Provides structured, explainable report contracts containing:
  - Session and candidate context
  - Executive summary with deterministic alignment score
  - Dimension-level comparison against job benchmark weights
  - Question-by-question candidate responses, scores, and behavioral evidence
  - Recruiter inquiry prompts and ethical decision-support safeguards
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportEvidenceItem(BaseModel):
    """Evidence snippet and similarity match for an indicator."""
    indicator_name: str
    matched:        bool
    level:          str   # 'strong' | 'partial' | 'none'
    similarity:     float # 0.0 - 1.0
    evidence_text:  Optional[str] = None


class ReportQuestionItem(BaseModel):
    """Complete candidate response, score, and evidence for one interview question."""
    question_id:        UUID
    question_text:      str
    dimension_name:     str
    dimension_label:    str
    question_type:      str
    difficulty:         str
    candidate_response: Optional[str] = None
    word_count:         int = 0
    response_score:     Optional[int] = None   # 0-100 normalized score
    confidence:         float = 0.0            # 0.0-1.0
    status:             str = "unanswered"     # 'scored' | 'unanswered' | 'invalid:*'
    evidence:           List[ReportEvidenceItem] = []


class ReportDimensionItem(BaseModel):
    """Dimension-level comparison between job requirements and evaluated performance."""
    dimension_name:     str
    dimension_label:    str
    job_weight:         float # 0-100 benchmark weight
    weight_percentage:  float # % of total job requirement weight
    candidate_score:    float # 0-100 evaluated candidate score
    benchmark_gap:      float # candidate_score - job_weight
    contribution:       float # points contributed to overall 0-100 score
    status:             str   # 'assessed' | 'missing' | 'unweighted'
    confidence:         float # 0.0-1.0
    response_count:     int
    indicators_matched: int = 0
    total_indicators:   int = 0


class ReportExecutiveSummary(BaseModel):
    """High-level performance summary for recruiter decision-support."""
    overall_alignment_score:   float = Field(ge=0.0, le=100.0)
    total_job_weight:          int
    assessed_dimensions_count: int
    total_dimensions_count:    int
    average_confidence:        float
    is_complete:               bool
    strengths:                 List[str] = []
    areas_for_review:          List[str] = []
    inquiry_prompts:           List[str] = []


class AssessmentReportRead(BaseModel):
    """Comprehensive recruiter assessment report."""
    session_id:         UUID
    job_id:             UUID
    job_title:          str
    candidate_name:     str
    candidate_email:    str
    status:             str # 'completed' | 'in_progress' | 'pending'
    submitted_at:       Optional[datetime] = None
    created_at:         Optional[datetime] = None
    executive_summary:  ReportExecutiveSummary
    dimension_breakdown:List[ReportDimensionItem] = []
    questions_evidence: List[ReportQuestionItem] = []
    compliance_notice:  str
    metadata:           Dict[str, Any] = {}
    generated_at:       datetime


class SessionReportSummaryItem(BaseModel):
    """Brief candidate report summary for dashboard tables."""
    session_id:              UUID
    candidate_name:          str
    candidate_email:         str
    status:                  str
    submitted_at:            Optional[datetime] = None
    overall_alignment_score: Optional[float] = None
    top_strength:            Optional[str] = None
    primary_review_area:     Optional[str] = None
    is_scored:               bool
