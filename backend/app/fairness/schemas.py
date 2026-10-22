"""
fairness/schemas.py
Pydantic schemas for demographic fairness evaluation datasets and audit reports.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EvaluationRecordInput(BaseModel):
    """Single candidate or benchmark record in an evaluation dataset."""
    record_id:    str = Field(..., description="Pseudonymized record identifier")
    group:        str = Field(..., min_length=1, max_length=100, description="Sensitive attribute value")
    score:        Optional[float] = Field(None, ge=0.0, le=100.0, description="Alignment / test score (0-100)")
    prediction:   Optional[int] = Field(None, ge=0, le=1, description="Binary selection prediction (0 or 1)")
    ground_truth: Optional[int] = Field(None, ge=0, le=1, description="Binary actual outcome label (0 or 1)")

    @field_validator("group")
    @classmethod
    def validate_group_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Subgroup label cannot be whitespace-only.")
        return s


class FairnessDatasetCreate(BaseModel):
    """Payload to ingest a controlled demographic evaluation dataset."""
    name:                str = Field(..., min_length=1, max_length=120)
    description:         Optional[str] = Field(None, max_length=500)
    sensitive_attribute: str = Field(..., min_length=1, max_length=80, description="e.g. 'gender', 'age_group'")
    reference_group:     Optional[str] = Field(None, description="Baseline subgroup for disparity calculation")
    score_threshold:     float = Field(70.0, ge=0.0, le=100.0, description="Cutoff threshold for score-to-binary mapping")
    records:             List[EvaluationRecordInput] = Field(..., min_length=1, description="Evaluation observations")

    @field_validator("records")
    @classmethod
    def validate_at_least_one_score_or_pred(cls, records: List[EvaluationRecordInput]) -> List[EvaluationRecordInput]:
        for idx, r in enumerate(records):
            if r.score is None and r.prediction is None:
                raise ValueError(f"Record at index {idx} ({r.record_id}) must have either 'score' or 'prediction'.")
        return records


class FairnessAuditRunRequest(BaseModel):
    """Request payload to execute an audit run on an existing dataset."""
    score_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    reference_group: Optional[str] = None
    min_sample_size: Optional[int] = Field(30, ge=1, le=1000)


class SubgroupMetricRead(BaseModel):
    """Calculated metric breakdown for a specific demographic group."""
    group:                            str
    sample_count:                     int
    selection_count:                  int
    selection_rate:                   Optional[float] = None
    rate_difference_from_reference:   Optional[float] = None
    adverse_impact_ratio:             Optional[float] = None
    ground_truth_positives:           Optional[int] = None
    ground_truth_negatives:           Optional[int] = None
    true_positives:                   Optional[int] = None
    false_positives:                  Optional[int] = None
    false_negatives:                  Optional[int] = None
    true_negatives:                   Optional[int] = None
    recall:                           Optional[float] = None
    recall_difference_from_reference: Optional[float] = None
    has_sample_warning:               bool = False
    warnings:                         List[str] = []


class FairnessAuditRead(BaseModel):
    """Full demographic fairness audit report."""
    id:                            UUID
    dataset_id:                    Optional[UUID] = None
    dataset_name:                  str
    sensitive_attribute:           str
    reference_group:               str
    total_samples:                 int
    evaluated_threshold:           float
    has_ground_truth:              bool
    demographic_parity_difference: Optional[float] = None
    equal_opportunity_difference:  Optional[float] = None
    subgroup_metrics:              List[SubgroupMetricRead] = []
    warnings:                      List[str] = []
    limitations:                   List[str] = []
    created_at:                    datetime
    created_by:                    Optional[UUID] = None


class FairnessDatasetRead(BaseModel):
    """Metadata summary of an ingested evaluation dataset."""
    id:                  UUID
    name:                str
    description:         Optional[str] = None
    sensitive_attribute: str
    reference_group:     Optional[str] = None
    score_threshold:     float
    record_count:        int
    groups:              List[str] = []
    has_ground_truth:    bool
    created_at:          datetime
    created_by:          Optional[UUID] = None
